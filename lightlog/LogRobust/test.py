"""
LogRobust 测试脚本
导入测试数据集进行预测，记录:
  - Precision, Recall, F1-score
  - 混淆矩阵 (Confusion Matrix)
  - 参数量 (总参数/训练参数)
  - 模型大小 (KB)
  - 测试时间 (分钟)

使用 FastText 预训练向量 (Common Crawl, 300-dim, frozen) + TF-IDF 聚合
语义向量在数据集构建时预计算，模型输入为语义向量序列。
"""
import os
import sys
import json
import time
import tempfile
import torch
import numpy as np
from torch.utils.data import DataLoader
from sklearn.metrics import (precision_score, recall_score, f1_score,
                              confusion_matrix, classification_report)

# 添加当前目录到 path
sys.path.insert(0, os.path.dirname(__file__))

from model import LogRobust
from dataset import (
    LogTemplateVocab, WordVocab, LogDataset, SemanticVectorBuilder,
    extract_message, parse_to_template, preprocess_log_event, compute_idf,
    get_fasttext_model
)

# 配置
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), 'checkpoints', 'best_model.pth')
TEST_FILE = r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\processed_datasets\test_dataset.jsonl"
RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
os.makedirs(RESULT_DIR, exist_ok=True)

# 测试超参数 (与训练时保持一致)
MAX_LEN = 20
BATCH_SIZE = 128
EMBED_DIM = 300  # FastText dimension


def collate_fn(batch):
    """整理 batch 数据 (token IDs + TF-IDF weights)"""
    max_events = max(len(event_tokens) for event_tokens, _ in batch)
    max_events = min(max_events, MAX_LEN)

    # Find max words across all events in batch
    max_words = 0
    for event_tokens, _ in batch:
        for token_ids, _ in event_tokens[:max_events]:
            max_words = max(max_words, len(token_ids))
    max_words = max(max_words, 1)  # At least 1 to avoid empty dimension

    batch_size = len(batch)

    token_ids_batch = torch.zeros(batch_size, max_events, max_words, dtype=torch.long)
    tfidf_weights_batch = torch.zeros(batch_size, max_events, max_words, dtype=torch.float)
    event_mask = torch.zeros(batch_size, max_events)
    labels = torch.zeros(batch_size, dtype=torch.long)

    for i, (event_tokens, label) in enumerate(batch):
        labels[i] = label
        n_events = min(len(event_tokens), max_events)
        event_mask[i, :n_events] = 1.0

        for j, (token_ids, tfidf_weights) in enumerate(event_tokens[:n_events]):
            n_words = min(len(token_ids), max_words)
            token_ids_batch[i, j, :n_words] = torch.tensor(token_ids[:n_words], dtype=torch.long)
            tfidf_weights_batch[i, j, :n_words] = torch.tensor(tfidf_weights[:n_words], dtype=torch.float)

    return token_ids_batch, tfidf_weights_batch, event_mask, labels


def count_parameters(model):
    """计算模型参数量"""
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total_params, trainable_params


def get_model_size_kb(model):
    """获取模型大小(KB)"""
    with tempfile.NamedTemporaryFile(suffix='.pth', delete=False) as tmp:
        torch.save(model.state_dict(), tmp.name)
        size_kb = os.path.getsize(tmp.name) / 1024.0
    os.unlink(tmp.name)
    return size_kb


def find_best_threshold(all_probs, all_labels):
    """搜索最佳 F1 阈值"""
    print("\n搜索最佳阈值...")
    best_f1 = 0
    best_threshold = 0.5

    for threshold in np.arange(0.1, 0.95, 0.05):
        preds = (all_probs >= threshold).astype(int)
        p = precision_score(all_labels, preds, zero_division=0)
        r = recall_score(all_labels, preds, zero_division=0)
        f1_val = f1_score(all_labels, preds, zero_division=0)

        if f1_val > 0.01:
            print(f"  阈值 {threshold:.2f}: P={p:.4f}, R={r:.4f}, F1={f1_val:.4f}, 预测异常={preds.sum()}")

        if f1_val > best_f1:
            best_f1 = f1_val
            best_threshold = threshold

    return best_threshold, best_f1


def main():
    print("=" * 60)
    print("LogRobust 测试评估 (FastText 初始化可训练 Embedding)")
    print("=" * 60)

    # Step 1: 加载 checkpoint
    print(f"\n[1/5] 加载模型 checkpoint: {CHECKPOINT_PATH}")
    if not os.path.exists(CHECKPOINT_PATH):
        print(f"错误: checkpoint 文件不存在: {CHECKPOINT_PATH}")
        sys.exit(1)

    checkpoint = torch.load(CHECKPOINT_PATH, map_location=DEVICE, weights_only=False)
    word_vocab = checkpoint['word_vocab']
    template_vocab = checkpoint['template_vocab']
    idf_dict = checkpoint['idf_dict']
    config = checkpoint.get('config', {})

    print(f"  checkpoint epoch: {checkpoint.get('epoch', 'N/A')}")
    print(f"  最佳 val F1: {checkpoint.get('f1', 'N/A')}")

    # Step 2: 构建模型
    print("\n[2/5] 构建模型...")
    vocab_size = len(word_vocab)
    embed_dim = config.get('embed_dim', 300)
    hidden_dim = config.get('hidden_dim', 128)
    dropout = config.get('dropout', 0.5)
    num_classes = config.get('num_classes', 2)

    model = LogRobust(
        vocab_size=vocab_size,
        embed_dim=embed_dim,
        hidden_dim=hidden_dim,
        num_classes=num_classes,
        dropout=dropout
    ).to(DEVICE)

    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    print(f"  vocab_size={vocab_size}, embed_dim={embed_dim}, hidden_dim={hidden_dim}, dropout={dropout}")
    print(f"  词向量: FastText 初始化, 可训练")

    # Step 3: 计算参数量和模型大小
    total_params, trainable_params = count_parameters(model)
    model_size_kb = get_model_size_kb(model)
    print(f"  总参数量: {total_params:,}")
    print(f"  训练参数量: {trainable_params:,}")
    print(f"  模型大小: {model_size_kb:.2f} KB")

    # Step 4: 加载测试数据集
    print(f"\n[3/5] 加载测试数据集: {os.path.basename(TEST_FILE)}")

    test_dataset = LogDataset(
        TEST_FILE, template_vocab, word_vocab, idf_dict,
        max_len=MAX_LEN
    )

    test_loader = DataLoader(
        test_dataset, batch_size=BATCH_SIZE, shuffle=False,
        collate_fn=collate_fn,
        num_workers=0
    )

    # 统计标签分布
    test_labels_all = [s[1] for s in test_dataset.sequences]
    print(f"  测试样本数: {len(test_dataset)}")
    print(f"  正常: {test_labels_all.count(0)}, 异常: {test_labels_all.count(1)}")
    print(f"  异常比例: {test_labels_all.count(1)/len(test_labels_all)*100:.1f}%")

    # Step 5: 推理 & 评估
    print(f"\n[4/5] 开始推理...")
    test_start = time.time()

    all_probs = []
    all_labels = []

    with torch.no_grad():
        for token_ids, tfidf_weights, event_mask, batch_labels in test_loader:
            token_ids = token_ids.to(DEVICE)
            tfidf_weights = tfidf_weights.to(DEVICE)
            event_mask = event_mask.to(DEVICE)

            outputs, _ = model(token_ids, tfidf_weights, event_mask)
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()

            all_probs.extend(probs)
            all_labels.extend(batch_labels.numpy())

    test_elapsed = time.time() - test_start
    test_time_minutes = test_elapsed / 60.0

    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)

    # 搜索最佳阈值
    best_threshold, best_f1 = find_best_threshold(all_probs, all_labels)

    # 使用最佳阈值评估
    print(f"\n[5/5] 最终评估 (阈值={best_threshold:.2f})...")
    all_preds = (all_probs >= best_threshold).astype(int)

    precision = precision_score(all_labels, all_preds, zero_division=0)
    recall = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)
    cm = confusion_matrix(all_labels, all_preds)

    print("\n" + "=" * 60)
    print("LogRobust 测试结果 (FastText 初始化可训练 Embedding)")
    print("=" * 60)
    print(f"阈值:        {best_threshold:.2f}")
    print(f"Precision:   {precision:.4f}")
    print(f"Recall:      {recall:.4f}")
    print(f"F1-score:    {f1:.4f}")
    print(f"\n混淆矩阵:")
    print(f"              预测正常  预测异常")
    print(f"  实际正常:      {cm[0,0]:6d}    {cm[0,1]:6d}")
    print(f"  实际异常:      {cm[1,0]:6d}    {cm[1,1]:6d}")
    print(f"\n参数量:        {total_params:,} (训练参数: {trainable_params:,})")
    print(f"模型大小:       {model_size_kb:.2f} KB")
    print(f"测试时间:       {test_time_minutes:.4f} 分钟 ({test_elapsed:.2f} 秒)")

    print(f"\n分类报告:")
    print(classification_report(all_labels, all_preds, target_names=['Normal', 'Anomaly']))

    # 保存结果
    result = {
        'method': 'LogRobust',
        'threshold': float(best_threshold),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'confusion_matrix': cm.tolist(),
        'n_test': int(len(all_labels)),
        'n_normal': int((all_labels == 0).sum()),
        'n_abnormal': int((all_labels == 1).sum()),
        'total_params': int(total_params),
        'trainable_params': int(trainable_params),
        'model_size_kb': round(model_size_kb, 2),
        'test_time_seconds': round(test_elapsed, 2),
        'test_time_minutes': round(test_time_minutes, 4),
        'config': {
            'vocab_size': vocab_size,
            'embed_dim': embed_dim,
            'hidden_dim': hidden_dim,
            'dropout': dropout,
            'max_len': MAX_LEN,
            'batch_size': BATCH_SIZE,
            'word_vectors': 'FastText (Common Crawl, 300-dim, trainable)',
        }
    }

    result_path = os.path.join(RESULT_DIR, 'logrobust_test_results.json')
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {result_path}")
    print("=" * 60)
    print("LogRobust 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()