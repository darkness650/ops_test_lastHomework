"""
Training script for LogRobust
Based on: "Robust Log-Based Anomaly Detection on Unstable Log Data" (ESEC/FSE 2019)

Uses semantic vectors (TF-IDF weighted word vectors) as model input, following the paper.
Each log message is parsed to a template, pre-processed, and transformed into a semantic vector.
Sequences of semantic vectors are fed into the Attention-based Bi-LSTM model.

Key: Word embeddings are trainable nn.Embedding inside the model, so gradients flow
from the loss all the way through the Bi-LSTM + Attention into the word vectors.
"""
import os
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torch.optim import SGD
from tqdm import tqdm
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report

from model import LogRobust
from dataset import (
    LogTemplateVocab, WordVocab, LogDataset, SemanticVectorBuilder,
    extract_message, parse_to_template, preprocess_log_event, compute_idf
)


# Configuration
CONFIG = {
    # Data paths
    'train_file': r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\processed_datasets\train_dataset.jsonl",
    'test_file': r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\processed_datasets\test_dataset.jsonl",
    
    # Model hyperparameters (matching paper)
    'embed_dim': 300,      # FastText dimension (Section 3.2.2)
    'hidden_dim': 128,     # Bi-LSTM hidden dimension
    'dropout': 0.5,
    'num_classes': 2,
    
    # Training hyperparameters (matching paper Section 4.1.2)
    'batch_size': 128,     # Paper uses 128
    'max_len': 20,
    'max_tokens_per_event': 30,  # max words per log event after preprocessing
    'epochs': 30,          # Paper's architecture, 30 epochs
    'lr': 0.01,            # SGD learning rate (paper Section 4.1.2)
    'weight_decay': 1e-4,  # Paper uses 0.0001
    'momentum': 0.9,       # Paper uses 0.9 momentum
    'val_ratio': 0.2,
    'patience': 3,         # Early stopping patience
    'word_min_freq': 2,
    'template_min_freq': 2,
    
    # Other
    'seed': 42,
    'device': 'cuda' if torch.cuda.is_available() else 'cpu',
    'save_dir': r"d:\code\python\paper\LightLog\LogRobust\checkpoints",
}


def set_seed(seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_raw_sequences(file_path, max_groups=None):
    """Load raw log sequences (list of log entries) from file for vocabulary building."""
    sequences = []
    count = 0
    print(f"Loading raw sequences from {os.path.basename(file_path)}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Loading"):
            if max_groups and count >= max_groups:
                break
            try:
                item = json.loads(line.strip())
                logs = item.get('logs', [])
                if logs:
                    sequences.append(logs)
                    count += 1
            except:
                continue
    print(f"Loaded {len(sequences)} sequences")
    return sequences


def build_vocabularies(train_file, max_groups=None):
    """Build word vocabulary and template vocabulary from training data."""
    print("\nBuilding vocabularies...")
    sequences = load_raw_sequences(train_file, max_groups=max_groups)
    
    # Build word vocabulary (for semantic vectorization)
    print("\nBuilding word vocabulary...")
    word_vocab = WordVocab(min_freq=CONFIG['word_min_freq'])
    word_vocab.build(sequences)
    
    # Compute IDF for TF-IDF aggregation
    print("\nComputing IDF values...")
    idf_dict = compute_idf(sequences, word_vocab)
    
    # Build template vocabulary (kept for compatibility)
    print("\nBuilding template vocabulary...")
    template_vocab = LogTemplateVocab(min_freq=CONFIG['template_min_freq'])
    template_vocab.build(sequences)
    template_vocab.template_stats()
    
    return word_vocab, template_vocab, idf_dict


def collate_fn(batch, max_tokens_per_event=30):
    """
    Collate function for batching variable-length token data.
    
    Each sample: (events_tokens, label) where
      events_tokens: list of (word_ids, weights) per log event
    
    Returns:
      token_ids: (batch, max_events, max_tokens) padded with 0
      token_weights: (batch, max_events, max_tokens) padded with 0.0
      event_mask: (batch, max_events) 1.0 for valid events
      labels: (batch,) tensor
    """
    max_events = max(len(events) for events, _ in batch)
    max_events = min(max_events, CONFIG['max_len'])
    
    # Find max tokens across all events in the batch
    max_tokens = 0
    for events, _ in batch:
        for word_ids, _ in events[:max_events]:
            max_tokens = max(max_tokens, len(word_ids))
    max_tokens = min(max_tokens, max_tokens_per_event)
    
    batch_size = len(batch)
    token_ids = torch.zeros(batch_size, max_events, max_tokens, dtype=torch.long)
    token_weights = torch.zeros(batch_size, max_events, max_tokens)
    event_mask = torch.zeros(batch_size, max_events)
    labels = torch.zeros(batch_size, dtype=torch.long)
    
    for i, (events, label) in enumerate(batch):
        labels[i] = label
        for j, (word_ids, weights) in enumerate(events[:max_events]):
            event_mask[i, j] = 1.0
            # Truncate tokens
            n_tokens = min(len(word_ids), max_tokens)
            for k in range(n_tokens):
                token_ids[i, j, k] = word_ids[k]
                token_weights[i, j, k] = weights[k]
    
    return token_ids, token_weights, event_mask, labels


def plot_training_curves(history, save_path):
    """Plot and save training curves"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Plot 1: Loss
    epochs = range(1, len(history['train_loss']) + 1)
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train Loss', marker='o')
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val Loss', marker='s')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Training and Validation Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Plot 2: Accuracy
    axes[1].plot(epochs, history['train_acc'], 'b-', label='Train Acc', marker='o')
    axes[1].plot(epochs, history['val_acc'], 'r-', label='Val Acc', marker='s')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Accuracy')
    axes[1].set_title('Training and Validation Accuracy')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # Plot 3: Precision, Recall, F1
    axes[2].plot(epochs, history['val_precision'], 'r-', label='Precision', marker='s')
    axes[2].plot(epochs, history['val_recall'], 'g-', label='Recall', marker='^')
    axes[2].plot(epochs, history['val_f1'], 'b-', label='F1', marker='o')
    axes[2].set_xlabel('Epoch')
    axes[2].set_ylabel('Score')
    axes[2].set_title('Validation Metrics')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Training curves saved to {save_path}")


def train_epoch(model, dataloader, criterion, optimizer, device):
    """Train for one epoch"""
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    pbar = tqdm(dataloader, desc="Training")
    for token_ids, token_weights, event_mask, batch_labels in pbar:
        token_ids = token_ids.to(device)
        token_weights = token_weights.to(device)
        event_mask = event_mask.to(device)
        batch_labels = batch_labels.to(device)
        
        optimizer.zero_grad()
        
        outputs, _ = model(token_ids, token_weights, event_mask)
        loss = criterion(outputs, batch_labels)
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        correct += (predicted == batch_labels).sum().item()
        total += batch_labels.size(0)
        
        pbar.set_postfix({'loss': f'{loss.item():.4f}', 'acc': f'{correct/total:.4f}'})
    
    return total_loss / len(dataloader), correct / total


def evaluate_with_threshold(model, dataloader, criterion, device, threshold=0.5):
    """Evaluate the model with a custom threshold"""
    model.eval()
    total_loss = 0
    
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for token_ids, token_weights, event_mask, batch_labels in tqdm(dataloader, desc="Evaluating"):
            token_ids = token_ids.to(device)
            token_weights = token_weights.to(device)
            event_mask = event_mask.to(device)
            batch_labels = batch_labels.to(device)
            
            outputs, _ = model(token_ids, token_weights, event_mask)
            loss = criterion(outputs, batch_labels)
            
            total_loss += loss.item()
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
            
            all_probs.extend(probs)
            all_labels.extend(batch_labels.cpu().numpy())
    
    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)
    all_preds = (all_probs >= threshold).astype(int)
    
    tp = np.sum((all_preds == 1) & (all_labels == 1))
    fp = np.sum((all_preds == 1) & (all_labels == 0))
    fn = np.sum((all_preds == 0) & (all_labels == 1))
    tn = np.sum((all_preds == 0) & (all_labels == 0))
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / len(all_labels)
    
    avg_loss = total_loss / len(dataloader)
    
    return avg_loss, accuracy, precision, recall, f1, all_preds, all_labels, all_probs


def find_best_threshold(model, dataloader, criterion, device, target_precision=0.95):
    """Find the best threshold on validation set targeting high precision"""
    print(f"\nFinding best threshold (target precision >= {target_precision})...")
    model.eval()
    
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for token_ids, token_weights, event_mask, batch_labels in tqdm(dataloader, desc="Threshold search"):
            token_ids = token_ids.to(device)
            token_weights = token_weights.to(device)
            event_mask = event_mask.to(device)
            batch_labels = batch_labels.to(device)
            
            outputs, _ = model(token_ids, token_weights, event_mask)
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
            
            all_probs.extend(probs)
            all_labels.extend(batch_labels.cpu().numpy())
    
    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)
    
    # Try different thresholds
    best_threshold = 0.5
    best_f1 = 0
    best_metrics = None
    
    for threshold in np.arange(0.05, 1.0, 0.05):
        preds = (all_probs >= threshold).astype(int)
        
        tp = np.sum((preds == 1) & (all_labels == 1))
        fp = np.sum((preds == 1) & (all_labels == 0))
        fn = np.sum((preds == 0) & (all_labels == 1))
        tn = np.sum((preds == 0) & (all_labels == 0))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        if precision >= target_precision and f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_metrics = (precision, recall, f1)
    
    if best_metrics:
        print(f"Best threshold: {best_threshold:.2f} (P={best_metrics[0]:.4f}, R={best_metrics[1]:.4f}, F1={best_metrics[2]:.4f})")
    else:
        # Fallback: use default
        preds = (all_probs >= 0.5).astype(int)
        tp = np.sum((preds == 1) & (all_labels == 1))
        fp = np.sum((preds == 1) & (all_labels == 0))
        fn = np.sum((preds == 0) & (all_labels == 1))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        print(f"No threshold meets target precision. Using default 0.5 (F1={f1:.4f})")
    
    return best_threshold


def main():
    set_seed(CONFIG['seed'])
    device = CONFIG['device']
    print(f"Using device: {device}")
    print(f"Config: {json.dumps(CONFIG, indent=2, ensure_ascii=False)}")
    
    # Step 1: Build vocabularies from training data
    word_vocab, template_vocab, idf_dict = build_vocabularies(CONFIG['train_file'])
    vocab_size = len(word_vocab)
    print(f"Vocab size: {vocab_size}")
    
    # Step 2: Create semantic builder (no embeddings, just tokenizes)
    semantic_builder = SemanticVectorBuilder(word_vocab, idf_dict)
    
    # Step 3: Load datasets
    print("\nLoading datasets...")
    train_dataset = LogDataset(
        CONFIG['train_file'], template_vocab, semantic_builder,
        max_len=CONFIG['max_len']
    )
    
    test_dataset = LogDataset(
        CONFIG['test_file'], template_vocab, semantic_builder,
        max_len=CONFIG['max_len']
    )
    
    # Step 4: Split train into train/val
    num_train = len(train_dataset)
    indices = list(range(num_train))
    np.random.shuffle(indices)
    split = int(num_train * (1 - CONFIG['val_ratio']))
    train_indices = indices[:split]
    val_indices = indices[split:]
    
    train_subset = Subset(train_dataset, train_indices)
    val_subset = Subset(train_dataset, val_indices)
    
    print(f"Train: {len(train_subset)}, Val: {len(val_subset)}, Test: {len(test_dataset)}")
    
    # Check label distribution
    train_labels = [train_dataset.sequences[i][1] for i in train_indices]
    val_labels = [train_dataset.sequences[i][1] for i in val_indices]
    test_labels = [s[1] for s in test_dataset.sequences]
    print(f"Train labels: normal={train_labels.count(0)}, anomaly={train_labels.count(1)}")
    print(f"Val labels: normal={val_labels.count(0)}, anomaly={val_labels.count(1)}")
    print(f"Test labels: normal={test_labels.count(0)}, anomaly={test_labels.count(1)}")
    
    # Create DataLoaders
    max_tokens = CONFIG['max_tokens_per_event']
    train_loader = DataLoader(
        train_subset, batch_size=CONFIG['batch_size'], shuffle=False,
        collate_fn=lambda batch: collate_fn(batch, max_tokens), num_workers=0
    )
    val_loader = DataLoader(
        val_subset, batch_size=CONFIG['batch_size'], shuffle=False,
        collate_fn=lambda batch: collate_fn(batch, max_tokens), num_workers=0
    )
    test_loader = DataLoader(
        test_dataset, batch_size=CONFIG['batch_size'], shuffle=False,
        collate_fn=lambda batch: collate_fn(batch, max_tokens), num_workers=0
    )
    
    # Step 5: Create model (vocab_size passed for nn.Embedding)
    model = LogRobust(
        vocab_size=vocab_size,
        embed_dim=CONFIG['embed_dim'],
        hidden_dim=CONFIG['hidden_dim'],
        num_classes=CONFIG['num_classes'],
        dropout=CONFIG['dropout']
    ).to(device)
    
    print(f"\nModel architecture:")
    print(f"  Word Embedding: {vocab_size} words x {CONFIG['embed_dim']}d (trainable)")
    print(f"  Bi-LSTM hidden: {CONFIG['hidden_dim']} ({CONFIG['hidden_dim']*2} bidirectional)")
    print(f"  Dropout: {CONFIG['dropout']}")
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Total parameters: {total_params:,}")
    print(f"  Trainable parameters: {trainable_params:,}")
    
    criterion = nn.CrossEntropyLoss()
    
    # Use SGD as in the paper (Section 4.1.2)
    # Note: all model params (including nn.Embedding) are now trainable
    optimizer = SGD(model.parameters(), lr=CONFIG['lr'],
                    weight_decay=CONFIG['weight_decay'], momentum=CONFIG['momentum'])
    
    # Training loop
    os.makedirs(CONFIG['save_dir'], exist_ok=True)
    best_f1 = 0
    patience_counter = 0
    
    # History tracking for visualization
    history = {
        'train_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': [],
        'val_precision': [],
        'val_recall': [],
        'val_f1': [],
    }
    
    print(f"\nStarting training for {CONFIG['epochs']} epochs...")
    print(f"Early stopping patience: {CONFIG['patience']}")
    print("=" * 60)
    
    for epoch in range(CONFIG['epochs']):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        
        val_loss, val_acc, val_precision, val_recall, val_f1, _, _, _ = evaluate_with_threshold(
            model, val_loader, criterion, device, threshold=0.5
        )
        
        # Record history
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        history['val_precision'].append(val_precision)
        history['val_recall'].append(val_recall)
        history['val_f1'].append(val_f1)
        
        current_lr = optimizer.param_groups[0]['lr']
        print(f"\nEpoch {epoch + 1}/{CONFIG['epochs']} (lr={current_lr:.6f})")
        print(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f}")
        print(f"  Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}")
        print(f"  Val Precision: {val_precision:.4f} | Val Recall: {val_recall:.4f} | Val F1: {val_f1:.4f}")
        
        # Save best model
        if val_f1 > best_f1:
            best_f1 = val_f1
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'word_vocab': word_vocab,
                'idf_dict': idf_dict,
                'template_vocab': template_vocab,
                'vocab_size': vocab_size,
                'f1': val_f1,
                'config': CONFIG,
            }, os.path.join(CONFIG['save_dir'], 'best_model.pth'))
            print(f"  *** Best model saved! F1: {val_f1:.4f} ***")
        else:
            patience_counter += 1
            print(f"  Patience: {patience_counter}/{CONFIG['patience']}")
        
        if patience_counter >= CONFIG['patience']:
            print(f"\nEarly stopping triggered at epoch {epoch + 1}!")
            break
        
        print("=" * 60)
    
    # Save training curves
    plot_training_curves(history, os.path.join(CONFIG['save_dir'], 'training_curves.png'))
    
    # Find best threshold and evaluate
    print(f"\n{'=' * 60}")
    print("Loading best model for threshold tuning...")
    print("=" * 60)
    checkpoint = torch.load(os.path.join(CONFIG['save_dir'], 'best_model.pth'), weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    best_threshold = find_best_threshold(model, val_loader, criterion, device, target_precision=0.95)
    
    # Final evaluation on test set
    print(f"\n{'=' * 60}")
    print(f"Final evaluation on TEST set (threshold={best_threshold:.2f})...")
    print("=" * 60)
    test_loss, test_acc, test_precision, test_recall, test_f1, all_preds, all_labels, _ = evaluate_with_threshold(
        model, test_loader, criterion, device, threshold=best_threshold
    )
    
    print(f"\nTest Results:")
    print(f"  Loss: {test_loss:.4f} | Acc: {test_acc:.4f}")
    print(f"  Precision: {test_precision:.4f} | Recall: {test_recall:.4f} | F1: {test_f1:.4f}")
    
    cm = confusion_matrix(all_labels, all_preds)
    print(f"\nConfusion Matrix:\n{cm}")
    print(f"\nClassification Report:")
    print(classification_report(all_labels, all_preds, target_names=['Normal', 'Anomaly']))
    
    print(f"\nTraining complete!")
    print(f"Best Val F1: {best_f1:.4f}")
    print(f"Test F1: {test_f1:.4f}")


if __name__ == "__main__":
    main()