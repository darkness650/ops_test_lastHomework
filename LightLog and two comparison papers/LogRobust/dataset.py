"""
Dataset and data loading utilities for LogRobust
Based on paper: "Robust Log-Based Anomaly Detection on Unstable Log Data" (ESEC/FSE 2019)

Implements the Semantic Vectorization pipeline from the paper (Section 3.2):
1. Log Parsing: extract log event templates from raw messages
2. Pre-processing: remove non-character tokens, stop words, split CamelCase
3. Word Vectorization: map words to vectors via trainable nn.Embedding
4. TF-IDF Aggregation: aggregate word vectors into a fixed-dimension semantic vector per log event

Each log sequence becomes a sequence of semantic vectors, fed into Attention-based Bi-LSTM.

IMPORTANT: Word embeddings are trainable (nn.Embedding inside the model).
The dataset returns raw token IDs + TF-IDF weights; semantic vector aggregation happens
inside the model forward pass so gradients flow through the embeddings.
"""
import json
import re
import math
import torch
import numpy as np
from torch.utils.data import Dataset
from collections import Counter, OrderedDict
from tqdm import tqdm


def extract_message(log_entry):
    """Extract the message field from a log entry (which contains JSON string)."""
    if isinstance(log_entry, dict):
        log_str = log_entry.get('log', '')
    else:
        log_str = str(log_entry)

    if not log_str:
        return ''

    try:
        log_content = json.loads(log_str)
        msg = log_content.get('message', '')
        if not msg:
            parts = []
            if 'severity' in log_content:
                parts.append(str(log_content['severity']))
            if 'http.req.path' in log_content:
                parts.append(str(log_content['http.req.path']))
            if 'http.req.method' in log_content:
                parts.append(str(log_content['http.req.method']))
            if 'name' in log_content:
                parts.append(str(log_content['name']))
            msg = ' '.join(parts)
        return str(msg) if msg else str(log_content)
    except (json.JSONDecodeError, TypeError):
        return log_str


# Regex patterns for parameter masking (log parsing)
_PARAM_PATTERNS = [
    (r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '{uuid}'),
    (r'\b[0-9a-f]{24}\b', '{hex24}'),
    (r'\b[0-9a-f]{32}\b', '{hex32}'),
    (r'\b[0-9a-f]{40}\b', '{hex40}'),
    (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b', '{ip}'),
    (r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*\b', '{datetime}'),
    (r'\b\d{2,4}/\d{2}/\d{2,4}\b', '{date}'),
    (r'\b[0-9a-f]{6,}\b', '{hex}'),
    (r'\b\d+\.\d+\b', '{float}'),
    (r'\b\d+\b', '{num}'),
    (r"'[^']*'", "'{str}'"),
    (r'"[^"]*"', '"{str}"'),
    (r'\b[A-Z][A-Z0-9]{2,}\b', '{const}'),
]


def parse_to_template(message):
    """Convert a log message to a template by masking parameters."""
    template = str(message).strip()
    for pattern, replacement in _PARAM_PATTERNS:
        template = re.sub(pattern, replacement, template)
    return template


# English stop words (common subset for log pre-processing)
_STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'need', 'must',
    'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
    'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his',
    'our', 'their', 'what', 'which', 'who', 'whom', 'when', 'where', 'why',
    'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
    'too', 'very', 'just', 'don', 'now', 'if', 'as', 'about', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'between', 'under', 'again',
    'further', 'then', 'once', 'here', 'there', 'any', 'up', 'down', 'out', 'off',
    'over', 'the', 'to', 'of', 'and', 'a', 'in', 'is', 'it', 'you', 'that',
}


def split_camel_case(token):
    """Split CamelCase token into individual words."""
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', token)
    result = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', result)
    return result.lower().split()


def preprocess_log_event(template):
    """
    Pre-process a log event template (Section 3.2.1):
    1. Remove non-character tokens (delimiters, operators, punctuation, numbers)
    2. Remove stop words
    3. Split CamelCase variable names
    """
    tokens = template.split()
    
    processed = []
    for token in tokens:
        if not re.search(r'[a-zA-Z]', token):
            continue
        
        if token.startswith('{') and token.endswith('}'):
            continue
        
        sub_tokens = split_camel_case(token)
        for sub in sub_tokens:
            sub_clean = re.sub(r'[^a-zA-Z]', '', sub).lower()
            if sub_clean and len(sub_clean) > 1 and sub_clean not in _STOP_WORDS:
                processed.append(sub_clean)
    
    return processed


class WordVocab:
    """Word vocabulary for building semantic vectors."""
    
    def __init__(self, min_freq=2):
        self.min_freq = min_freq
        self.word2idx = OrderedDict()
        self.idx2word = {}
        self.word_counter = Counter()
        self._frozen = False
    
    def build(self, sequences):
        """Build word vocabulary from all log sequences."""
        self.word_counter.clear()
        
        for seq in sequences:
            for log_entry in seq:
                msg = extract_message(log_entry)
                if msg:
                    template = parse_to_template(msg)
                    tokens = preprocess_log_event(template)
                    self.word_counter.update(tokens)
        
        # Reserve index 0 for <PAD>/<UNK>
        idx = 1
        for word, freq in self.word_counter.most_common():
            if freq >= self.min_freq:
                self.word2idx[word] = idx
                self.idx2word[idx] = word
                idx += 1
        
        self._frozen = True
        print(f"Word vocabulary: {len(self.word2idx)} words (min_freq={self.min_freq})")
        return self
    
    def encode(self, word):
        """Convert word to ID. Returns 0 for unseen words."""
        return self.word2idx.get(word, 0)
    
    def __len__(self):
        return len(self.word2idx) + 1  # +1 for PAD/UNK(0)


class LogTemplateVocab:
    """Build vocabulary of log event templates (kept for compatibility)."""
    
    def __init__(self, min_freq=2):
        self.min_freq = min_freq
        self.template2idx = OrderedDict()
        self.idx2template = {}
        self.template_counter = Counter()
        self._frozen = False
    
    def build(self, sequences):
        self.template_counter.clear()
        for seq in sequences:
            for log_entry in seq:
                msg = extract_message(log_entry)
                if msg:
                    template = parse_to_template(msg)
                    self.template_counter[template] += 1
        
        idx = 2  # 0: <PAD>, 1: <UNK>
        for template, freq in self.template_counter.most_common():
            if freq >= self.min_freq:
                self.template2idx[template] = idx
                self.idx2template[idx] = template
                idx += 1
        
        self._frozen = True
        print(f"Template vocabulary: {len(self.template2idx)} templates (min_freq={self.min_freq})")
        return self
    
    def encode(self, template):
        return self.template2idx.get(template, 1)
    
    def __len__(self):
        return len(self.template2idx) + 2
    
    def template_stats(self):
        print(f"\nTop 20 log event templates:")
        for i, (template, freq) in enumerate(self.template_counter.most_common(20)):
            print(f"  [{freq:6d}] {template[:120]}")
        print()


def compute_idf(sequences, word_vocab):
    """
    Compute IDF for each word in the vocabulary.
    IDF(word) = log(total_log_events / num_log_events_containing_word)
    """
    total_events = 0
    word_doc_freq = Counter()
    
    for seq in sequences:
        for log_entry in seq:
            msg = extract_message(log_entry)
            if msg:
                template = parse_to_template(msg)
                tokens = preprocess_log_event(template)
                unique_tokens = set(tokens)
                word_doc_freq.update(unique_tokens)
                total_events += 1
    
    idf = {}
    for word in word_vocab.word2idx:
        df = word_doc_freq.get(word, 0)
        if df > 0:
            idf[word] = math.log(total_events / df)
        else:
            idf[word] = 0.0
    
    return idf


class SemanticVectorBuilder:
    """
    Prepares word-level token data from log templates.
    
    Outputs (word_ids, tfidf_weights) per log event. The actual semantic vector
    aggregation with trainable nn.Embedding happens inside the model forward pass.
    
    Eq. 1: V = (1/N) * sum(w_i * v_i) where w_i = TF-IDF weight, v_i = word vector
    The model uses nn.Embedding for v_i so gradients can flow through.
    """
    
    def __init__(self, word_vocab, idf_dict):
        self.word_vocab = word_vocab
        self.idf_dict = idf_dict
    
    def build_token_data(self, template):
        """
        Given a log event template, return (word_ids, weights) for each word.
        
        Returns:
            word_ids: list of int (word vocabulary indices)
            weights: list of float (TF-IDF weights)
        """
        tokens = preprocess_log_event(template)
        if not tokens:
            return [], []
        
        # Compute TF
        tf_counter = Counter(tokens)
        total = len(tokens)
        
        word_ids = []
        weights = []
        
        for word, count in tf_counter.items():
            tf = count / total
            idf = self.idf_dict.get(word, 0.0)
            w = tf * idf
            
            word_id = self.word_vocab.encode(word)
            word_ids.append(word_id)
            weights.append(w)
        
        # Normalize: divide each weight by N (Eq. 1 in paper)
        N = len(tokens)
        weights = [w / N for w in weights]
        
        return word_ids, weights
    
    def build_sequence_vectors(self, template_ids, templates_list):
        """Deprecated: use model's forward pass instead."""
        raise NotImplementedError("Use model.forward() which has learnable nn.Embedding")


class LogDataset(Dataset):
    """
    PyTorch Dataset for log anomaly detection.
    
    Each sample returns raw token data per log event:
    - events_tokens: list of (word_ids, weights) tuples, one per log event
    - label: 0 (normal) or 1 (anomaly)
    
    The model's nn.Embedding + aggregation produce semantic vectors during training.
    """
    
    def __init__(self, file_path, template_vocab, semantic_builder=None, max_len=200, max_groups=None):
        self.template_vocab = template_vocab
        self.semantic_builder = semantic_builder
        self.max_len = max_len
        self.sequences = []  # list of (events_token_data, label)
        
        print(f"Loading {file_path.split(chr(92))[-1]}...")
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="Reading"):
                if max_groups and count >= max_groups:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    logs = item.get('logs', [])
                    label = item.get('label', 0)
                    
                    if not logs:
                        continue
                    
                    # Extract templates and build token data per event
                    events_tokens = []
                    for log_entry in logs:
                        msg = extract_message(log_entry)
                        if msg:
                            template = parse_to_template(msg)
                            if semantic_builder is not None:
                                word_ids, weights = semantic_builder.build_token_data(template)
                            else:
                                word_ids, weights = [], []
                            events_tokens.append((word_ids, weights))
                    
                    if events_tokens:
                        self.sequences.append((events_tokens, label))
                        count += 1
                except Exception:
                    continue
        
        print(f"Loaded {len(self.sequences)} samples")
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        events_tokens, label = self.sequences[idx]
        
        # Truncate if too long
        if len(events_tokens) > self.max_len:
            events_tokens = events_tokens[:self.max_len]
        
        return events_tokens, torch.tensor(label, dtype=torch.long)
    
    def get_sequence_length_stats(self):
        """Print statistics about sequence lengths."""
        lengths = [len(s[0]) for s in self.sequences]
        lengths = np.array(lengths)
        print(f"\nSequence length stats:")
        print(f"  Min: {lengths.min()}, Max: {lengths.max()}")
        print(f"  Mean: {lengths.mean():.1f}, Median: {np.median(lengths):.1f}")
        print(f"  90th percentile: {np.percentile(lengths, 90):.0f}")
        print(f"  95th percentile: {np.percentile(lengths, 95):.0f}")
        print(f"  99th percentile: {np.percentile(lengths, 99):.0f}")