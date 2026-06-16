"""
Dataset and data loading utilities for LogRobust
Based on paper: "Robust Log-Based Anomaly Detection on Unstable Log Data" (ESEC/FSE 2019)

Implements the Semantic Vectorization pipeline from the paper (Section 3.2):
1. Log Parsing: extract log event templates from raw messages
2. Pre-processing: remove non-character tokens, stop words, split CamelCase
3. Word Vectorization: map words to vectors via FastText pre-trained vectors (FROZEN)
4. TF-IDF Aggregation: aggregate word vectors into a fixed-dimension semantic vector per log event

Key difference from previous implementation:
- FastText pre-trained vectors (Common Crawl, 300-dim) are used instead of trainable nn.Embedding
- Semantic vectors are pre-computed during dataset construction (NOT during model forward)
- Model input is semantic vectors, not token IDs
"""
import json
import re
import math
import os
import torch
import numpy as np
from torch.utils.data import Dataset
from collections import Counter, OrderedDict
from tqdm import tqdm


# Global FastText model singleton (loaded once)
_FASTTEXT_MODEL = None


def get_fasttext_model():
    """Load FastText pre-trained model (Common Crawl, 300-dim vectors).
    The model is loaded once and cached globally.
    
    If fasttext Python package is not available, falls back to gensim.
    If neither is available, raises an error with install instructions.
    """
    global _FASTTEXT_MODEL
    if _FASTTEXT_MODEL is not None:
        return _FASTTEXT_MODEL
    
    # Try to load from common cache locations
    # Note: FastText C++ backend cannot handle paths with spaces (e.g. Windows usernames)
    # So we prioritize paths without spaces and copy the model if needed
    cache_dirs = [
        os.path.dirname(__file__),
        r"d:\code\python\paper\LightLog",
        os.path.expanduser("~/.cache/fasttext/"),
    ]
    
    model_path = None
    for d in cache_dirs:
        for fname in ["cc.en.300.bin", "crawl-300d-2M.vec", "wiki-news-300d-1M.vec"]:
            candidate = os.path.join(d, fname)
            if os.path.exists(candidate):
                model_path = candidate
                break
        if model_path:
            break
    
    if model_path is None:
        # Try to download FastText model
        print("FastText model not found in cache. Downloading cc.en.300.bin...")
        try:
            import fasttext.util
            fasttext.util.download_model('en', if_exists='ignore')
            model_path = os.path.expanduser("~/.cache/fasttext/cc.en.300.bin")
        except Exception as e:
            print(f"Failed to download: {e}")
            print("Falling back to gensim for loading FastText vectors...")
    
    # If model path contains spaces, copy it to a local path without spaces
    # (FastText C++ backend fails on paths with spaces on Windows)
    if model_path and ' ' in model_path:
        import shutil
        local_path = os.path.join(os.path.dirname(__file__), os.path.basename(model_path))
        if not os.path.exists(local_path):
            print(f"Copying model to path without spaces: {local_path}")
            shutil.copy2(model_path, local_path)
        model_path = local_path
    
    # Try fasttext package first
    if model_path and model_path.endswith('.bin'):
        try:
            import fasttext
            _FASTTEXT_MODEL = fasttext.load_model(model_path)
            print(f"Loaded FastText model from {model_path}")
            return _FASTTEXT_MODEL
        except ImportError:
            print("fasttext package not installed. Trying gensim...")
    
    # Fallback: try gensim for .vec files
    if model_path and model_path.endswith('.vec'):
        try:
            from gensim.models import KeyedVectors
            _FASTTEXT_MODEL = KeyedVectors.load_word2vec_format(model_path, limit=500000)
            print(f"Loaded FastText vectors from {model_path} via gensim")
            return _FASTTEXT_MODEL
        except ImportError:
            print("gensim not installed either.")
    
    # Last resort: try to download with gensim
    try:
        import gensim.downloader as api
        print("Downloading fasttext-wiki-news-subwords-300 via gensim...")
        _FASTTEXT_MODEL = api.load('fasttext-wiki-news-subwords-300')
        print("Loaded via gensim downloader")
        return _FASTTEXT_MODEL
    except Exception as e:
        print(f"Failed to load via gensim downloader: {e}")
    
    raise RuntimeError(
        "Cannot load FastText model. Please install one of:\n"
        "  pip install fasttext          (recommended, for .bin models)\n"
        "  pip install gensim            (fallback, for .vec models)\n"
        "Then download the model:\n"
        "  python -c \"import fasttext.util; fasttext.util.download_model('en', if_exists='ignore')\""
    )


def get_word_vector(word, ft_model=None):
    """Get FastText word vector for a given word.
    Returns a 300-dim numpy array, or zeros if word not found.
    """
    if ft_model is None:
        ft_model = get_fasttext_model()
    
    try:
        # fasttext package returns numpy array
        if hasattr(ft_model, 'get_word_vector'):
            return ft_model.get_word_vector(word)
        # gensim KeyedVectors
        elif hasattr(ft_model, 'get_vector'):
            return ft_model.get_vector(word)
        elif hasattr(ft_model, '__getitem__'):
            return ft_model[word]
    except (KeyError, Exception):
        pass
    
    # Word not found: return zero vector
    return np.zeros(300, dtype=np.float32)


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
    'over',
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
    """Word vocabulary (kept for compatibility with old checkpoints and IDF computation)."""
    
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
        return self.word2idx.get(word, 0)
    
    def __len__(self):
        return len(self.word2idx) + 1


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
        
        idx = 2
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
    Builds semantic vectors using FastText pre-trained word vectors + TF-IDF aggregation.
    
    This follows the paper's Semantic Vectorization pipeline (Section 3.2):
    - Each word in a log event is mapped to a 300-dim FastText vector (FROZEN)
    - TF-IDF weights are computed per word
    - Semantic vector: V = (1/N) * sum(w_i * v_i)  (Eq. 1 in paper)
    
    The resulting semantic vectors are of fixed dimension (300) regardless of the
    number of words in the log event.
    """
    
    def __init__(self, word_vocab, idf_dict, fasttext_model=None):
        self.word_vocab = word_vocab
        self.idf_dict = idf_dict
        if fasttext_model is None:
            fasttext_model = get_fasttext_model()
        self.ft_model = fasttext_model
    
    def build_semantic_vector(self, template):
        """
        Given a log event template, compute its semantic vector using FastText + TF-IDF.
        
        Eq. 1: V = (1/N) * sum(w_i * v_i)
        where w_i = TF * IDF, v_i = FastText pre-trained word vector
        
        Returns:
            numpy array of shape (300,) - the semantic vector
        """
        tokens = preprocess_log_event(template)
        if not tokens:
            return np.zeros(300, dtype=np.float32)
        
        N = len(tokens)
        tf_counter = Counter(tokens)
        
        semantic_vec = np.zeros(300, dtype=np.float32)
        
        for word, count in tf_counter.items():
            tf = count / N
            idf = self.idf_dict.get(word, 0.0)
            w = tf * idf
            
            word_vec = get_word_vector(word, self.ft_model)
            semantic_vec += w * word_vec
        
        # Normalize by N (Eq. 1)
        semantic_vec = semantic_vec / N
        
        return semantic_vec


class LogDataset(Dataset):
    """
    PyTorch Dataset for log anomaly detection.

    Each sample returns:
    - event_tokens: list of (token_ids, tfidf_weights) per log event
    - label: 0 (normal) or 1 (anomaly)

    The model uses a trainable nn.Embedding initialized with FastText vectors.
    """

    def __init__(self, file_path, template_vocab, word_vocab, idf_dict,
                 max_len=200, max_words=10, max_groups=None):
        self.template_vocab = template_vocab
        self.word_vocab = word_vocab
        self.idf_dict = idf_dict
        self.max_len = max_len
        self.max_words = max_words
        self.sequences = []  # list of (event_tokens_list, label)
        # event_tokens_list: list of (token_ids, tfidf_weights) per event

        print(f"Loading {os.path.basename(file_path)}...")
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

                    # Build token IDs and TF-IDF weights for each log event
                    event_tokens = []
                    for log_entry in logs:
                        msg = extract_message(log_entry)
                        if msg:
                            template = parse_to_template(msg)
                            token_ids, tfidf_weights = self._encode_event(template)
                            event_tokens.append((token_ids, tfidf_weights))
                        else:
                            event_tokens.append(([], []))

                    if event_tokens:
                        self.sequences.append((event_tokens, label))
                        count += 1
                except Exception as e:
                    continue

        print(f"Loaded {len(self.sequences)} samples")

    def _encode_event(self, template):
        """Encode a log event template into token IDs and TF-IDF weights."""
        tokens = preprocess_log_event(template)
        if not tokens:
            return [], []

        # Truncate to max_words
        tokens = tokens[:self.max_words]
        N = len(tokens)
        tf_counter = Counter(tokens)

        token_ids = []
        tfidf_weights = []
        for word in tokens:
            idx = self.word_vocab.encode(word) if self.word_vocab else 0
            tf = tf_counter[word] / N
            idf = self.idf_dict.get(word, 0.0) if self.idf_dict else 0.0
            w = tf * idf
            token_ids.append(idx)
            tfidf_weights.append(w)

        return token_ids, tfidf_weights

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        event_tokens, label = self.sequences[idx]

        # Truncate events to max_len
        if len(event_tokens) > self.max_len:
            event_tokens = event_tokens[:self.max_len]

        return event_tokens, torch.tensor(label, dtype=torch.long)
    
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