"""
LogRobust: Attention-based Bi-LSTM for Log Anomaly Detection
Based on: "Robust Log-Based Anomaly Detection on Unstable Log Data" (ESEC/FSE 2019)

Architecture (as described in paper, Figure 8):
1. Input: word-level token IDs + TF-IDF weights for each log event in the sequence
2. Word Embedding (trainable nn.Embedding): maps word IDs to dense vectors
3. TF-IDF Aggregation (Eq. 1): weighted average of word vectors → semantic vector per log event
4. Bi-LSTM: captures contextual information in both directions
5. Attention: learns importance of different log events (Eq. 2)
   - u_t = tanh(W_a · h_t), α_t = softmax(u_t)
6. Classification: weighted sum + softmax (Eq. 3)
   - v = Σ α_t · h_t, pred = softmax(W · v)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class LogRobust(nn.Module):
    """
    LogRobust model architecture (as described in paper):
    
    Input: word token IDs + TF-IDF weights for each log event in a sequence
    1. nn.Embedding (trainable): word_id → word vector
    2. TF-IDF weighted aggregation → semantic vector per log event (Eq. 1)
    3. Bi-LSTM: captures contextual information in log sequences
    4. Attention: learns importance of different log events (Eq. 2 in paper)
    5. Fully connected layer: binary classification (normal/anomaly)
    """
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_classes=2, dropout=0.5, num_layers=1):
        super(LogRobust, self).__init__()
        
        # Word embedding layer (trainable, gradient flows through)
        # Note: index 0 is reserved for PAD/UNK, embeddings[0] stays as zeros
        self.word_embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        
        # Bi-LSTM for contextual understanding
        # Input: semantic vectors (dimension = embed_dim)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Attention layer (Eq. 2 in paper): FC layer with tanh activation
        # Input: concatenated hidden state h_t (hidden_dim * 2 for bidirectional)
        # Output: attention score u_t (scalar)
        self.attention = nn.Linear(hidden_dim * 2, 1)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # Fully connected layer for classification
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, token_ids, token_weights, event_mask):
        """
        Args:
            token_ids: (batch, max_events, max_tokens) - word vocabulary indices
            token_weights: (batch, max_events, max_tokens) - TF-IDF weights
            event_mask: (batch, max_events) - 1.0 for valid events, 0.0 for padding
        
        Returns:
            output: (batch, num_classes) - classification logits
            attention_weights: (batch, max_events) - attention weights per event
        """
        batch_size, max_events, max_tokens = token_ids.shape
        
        # Step 1: Word embedding lookup
        # (batch, max_events, max_tokens) -> (batch, max_events, max_tokens, embed_dim)
        word_vectors = self.word_embedding(token_ids)
        
        # Step 2: TF-IDF weighted aggregation → semantic vector per log event (Eq. 1)
        # V = (1/N) * sum(w_i * v_i)
        token_weights_expanded = token_weights.unsqueeze(-1)  # (B, E, T, 1)
        weighted = word_vectors * token_weights_expanded  # (B, E, T, D)
        # Sum over tokens: (B, E, T, D) -> (B, E, D)
        semantic_vecs = weighted.sum(dim=2)
        
        # Apply event mask to zero out padded events
        semantic_vecs = semantic_vecs * event_mask.unsqueeze(-1)  # (B, E, D)
        
        # Step 3: Bi-LSTM
        # (batch, max_events, embed_dim) -> (batch, max_events, hidden_dim*2)
        lstm_output, _ = self.lstm(semantic_vecs)
        
        # Step 4: Attention (Eq. 2)
        # u_t = tanh(W_a · h_t)
        attention_scores = self.attention(lstm_output)  # (batch, max_events, 1)
        attention_scores = torch.tanh(attention_scores)
        
        # Mask padded positions
        mask_expanded = event_mask.unsqueeze(-1)  # (B, E, 1)
        attention_scores = attention_scores.masked_fill(mask_expanded == 0, -1e9)
        
        # α_t = softmax(u_t)
        attention_weights = F.softmax(attention_scores, dim=1)  # (batch, max_events, 1)
        
        # Step 5: Weighted sum (Eq. 3)
        # v = Σ α_t · h_t
        context = torch.sum(attention_weights * lstm_output, dim=1)  # (batch, hidden_dim*2)
        
        # Step 6: Classification
        output = self.dropout(context)
        output = self.fc(output)  # (batch, num_classes)
        
        return output, attention_weights.squeeze(-1)