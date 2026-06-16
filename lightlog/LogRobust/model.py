"""
LogRobust: Attention-based Bi-LSTM for Log Anomaly Detection
Based on: "Robust Log-Based Anomaly Detection on Unstable Log Data" (ESEC/FSE 2019)

Architecture:
1. Embedding: initialized with FastText pre-trained vectors (300-dim), TRAINABLE
2. TF-IDF Aggregation: weighted sum of word embeddings per log event → semantic vector
3. Bi-LSTM: captures contextual information in both directions
4. Attention: learns importance of different log events
5. Classification: weighted sum + softmax
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class LogRobust(nn.Module):
    """
    LogRobust model with trainable FastText-initialized embedding.

    Input: token IDs (batch, max_events, max_words) + TF-IDF weights (batch, max_events, max_words)
    1. Embedding (trainable): maps token IDs to 300-dim vectors
    2. TF-IDF aggregation: semantic_vec = (1/N) * sum(tfidf_i * embed_i)
    3. Bi-LSTM → Attention → FC classification
    """
    def __init__(self, vocab_size, embed_dim=300, hidden_dim=128, num_classes=2, dropout=0.5,
                 num_layers=1, pretrained_embeddings=None):
        super(LogRobust, self).__init__()

        # Word embedding layer - initialized with FastText, TRAINABLE
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        if pretrained_embeddings is not None:
            self.embedding.weight.data.copy_(pretrained_embeddings)
            # Freeze padding_idx
            self.embedding.weight.data[0].fill_(0)

        # Bi-LSTM for contextual understanding
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Attention layer
        self.attention = nn.Linear(hidden_dim * 2, 1)

        # Dropout
        self.dropout = nn.Dropout(dropout)

        # Fully connected layer for classification
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, token_ids, tfidf_weights, event_mask):
        """
        Args:
            token_ids: (batch, max_events, max_words) - word indices
            tfidf_weights: (batch, max_events, max_words) - TF-IDF weights per word
            event_mask: (batch, max_events) - 1.0 for valid events, 0.0 for padding

        Returns:
            output: (batch, num_classes) - classification logits
            attention_weights: (batch, max_events) - attention weights per event
        """
        batch_size, max_events, max_words = token_ids.shape

        # Step 1: Word embedding (trainable)
        # (B, E, W) -> (B, E, W, D)
        word_embeds = self.embedding(token_ids)

        # Step 2: TF-IDF weighted aggregation per event
        # (B, E, W, D) * (B, E, W, 1) -> sum over W -> (B, E, D)
        tfidf_expanded = tfidf_weights.unsqueeze(-1)  # (B, E, W, 1)
        semantic_vecs = (word_embeds * tfidf_expanded).sum(dim=2)  # (B, E, D)

        # Normalize by number of words per event
        word_counts = (token_ids != 0).float().sum(dim=-1, keepdim=True).clamp(min=1)  # (B, E, 1)
        semantic_vecs = semantic_vecs / word_counts

        # Apply event mask
        semantic_vecs = semantic_vecs * event_mask.unsqueeze(-1)  # (B, E, D)

        # Step 3: Bi-LSTM
        lstm_output, _ = self.lstm(semantic_vecs)

        # Step 4: Attention
        attention_scores = self.attention(lstm_output)  # (B, E, 1)
        attention_weights = torch.tanh(attention_scores)

        mask_expanded = event_mask.unsqueeze(-1)
        attention_weights = attention_weights.masked_fill(mask_expanded == 0, 0.0)

        # Step 5: Weighted sum
        context = torch.sum(attention_weights * lstm_output, dim=1)

        # Step 6: Classification
        output = self.dropout(context)
        output = self.fc(output)

        return output, attention_weights.squeeze(-1)
