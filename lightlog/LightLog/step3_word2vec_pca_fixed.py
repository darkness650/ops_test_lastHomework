import pandas as pd
import numpy as np
from gensim.models import Word2Vec
from sklearn.decomposition import PCA
import json
import os
import random
import re

np.random.seed(42)
random.seed(42)

MAX_SEQ_LEN = 20
WORD_EMBEDDING_DIM = 300
TARGET_DIM = 20


def normalize_log(log):
    if pd.isna(log) or not log:
        return ""
    log = str(log)
    if len(log) < 5:
        return ""
    log = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '<UUID>', log)
    log = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TIME>', log)
    log = re.sub(r'\d+\.\d+\.\d+\.\d+', '<IP>', log)
    log = re.sub(r'\b\d+\b', '<NUM>', log)
    log = re.sub(r'\d{2}:\d{2}:\d{2}', '<TIME>', log)
    log = re.sub(r'\d+ms', '<TIME>ms', log)
    log = re.sub(r'time[=:]\s*\d+', 'time=<NUM>', log)
    log = re.sub(r'\s+', ' ', log).strip()
    return log[:300]


def train_word2vec_on_templates(template_to_id):
    """参考 BGL 的 02_handle BGL templates.py"""
    print("训练 Word2Vec（词级别）...")
    
    sentences = []
    for template in template_to_id.keys():
        words = template.split()
        sentences.append(words)
    
    print(f"共 {len(sentences)} 个模板（句子）")
    
    if len(sentences) < 2:
        print("⚠️ 模板数量不足")
        return None
    
    model = Word2Vec(
        sentences=sentences,
        size=WORD_EMBEDDING_DIM,
        window=5,
        min_count=0,
        workers=1,
        iter=20,
        sg=0
    )
    
    embeddings = model.wv.vectors
    normalized_embeddings = embeddings / (embeddings**2).sum(axis=1).reshape((-1, 1))**0.5
    
    # 每个模板的向量 = 所有词向量求和（参考 BGL）
    template_vectors = {}
    for template, tid in template_to_id.items():
        words = template.split()
        vector = np.zeros(WORD_EMBEDDING_DIM)
        for word in words:
            if word in model.wv.vocab:
                vector += normalized_embeddings[model.wv.vocab[word].index]
        template_vectors[tid] = vector.tolist()
    
    print(f"✅ Word2Vec 完成，词汇表: {len(model.wv.vocab)}")
    return template_vectors


def pca_ppa_reduction(embeddings_matrix, target_dim=TARGET_DIM, remove_d=7):
    if embeddings_matrix is None or len(embeddings_matrix) < target_dim:
        return np.random.randn(50, target_dim)

    print(f"PCA-PPA 降维: {embeddings_matrix.shape[1]} -> {target_dim} 维")

    n_components = min(target_dim, embeddings_matrix.shape[0], embeddings_matrix.shape[1])
    pca1 = PCA(n_components=n_components)
    pca_result = pca1.fit_transform(embeddings_matrix)
    result = pca_result - np.mean(pca_result, axis=0)

    pca2 = PCA(n_components=min(target_dim, result.shape[0], result.shape[1]))
    pca_result2 = pca2.fit_transform(result)
    U = pca2.components_

    remove_d = min(remove_d, U.shape[0])
    ppa_result = []
    for x in result:
        for u in U[0:remove_d]:
            x = x - np.dot(u.T, x) * u
        ppa_result.append(x)

    ppa_result = np.array(ppa_result)
    if ppa_result.shape[1] < target_dim:
        pad = np.zeros((ppa_result.shape[0], target_dim - ppa_result.shape[1]))
        ppa_result = np.hstack([ppa_result, pad])
    elif ppa_result.shape[1] > target_dim:
        ppa_result = ppa_result[:, :target_dim]

    print(f"✅ PCA-PPA 完成: {ppa_result.shape}")
    return ppa_result


def build_sequences_from_templated_csv(csv_path, template_vectors_pca, max_seq_len=MAX_SEQ_LEN):
    """
    从抽好模板的 CSV 重建序列（参考 BGL 的 03_1_constructing sequences by length.py）
    按 group_id 分组，截断/填充到 max_seq_len
    """
    print(f"从模板化 CSV 重建序列（max_seq_len={max_seq_len}）...")

    df = pd.read_csv(csv_path)
    groups = df.groupby('group_id')
    
    all_sequences_x = []
    all_sequences_y = []
    
    for group_id, group_df in groups:
        label = group_df['label'].iloc[0]
        template_ids = group_df['template_id'].tolist()
        
        if len(template_ids) > max_seq_len:
            template_ids = template_ids[:max_seq_len]
        elif len(template_ids) < max_seq_len:
            template_ids = template_ids + [0] * (max_seq_len - len(template_ids))
        
        seq_embeddings = []
        for tid in template_ids:
            if tid in template_vectors_pca:
                seq_embeddings.append(template_vectors_pca[tid])
            else:
                seq_embeddings.append(np.zeros(TARGET_DIM))
        
        all_sequences_x.append(seq_embeddings)
        all_sequences_y.append(label)

    X = np.array(all_sequences_x)
    y = np.array(all_sequences_y)

    print(f"✅ {len(X)} 个序列, 正常: {np.sum(y==0)}, 异常: {np.sum(y==1)}")
    return X, y


if __name__ == "__main__":
    os.makedirs('./data', exist_ok=True)

    with open('template_to_id.json', 'r') as f:
        template_to_id = json.load(f)
    
    print(f"模板数: {len(template_to_id)}")

    template_vectors = train_word2vec_on_templates(template_to_id)
    
    max_tid = max(template_vectors.keys())
    embeddings_matrix = np.zeros((max_tid + 1, WORD_EMBEDDING_DIM))
    for tid, vec in template_vectors.items():
        embeddings_matrix[tid] = vec
    
    low_dim_embeddings = pca_ppa_reduction(embeddings_matrix, target_dim=TARGET_DIM, remove_d=7)
    
    template_vectors_pca = {}
    for tid in range(len(low_dim_embeddings)):
        template_vectors_pca[tid] = low_dim_embeddings[tid]

    with open('./data/boutique_semantic_vec.json', 'w') as f:
        json.dump({str(k): v.tolist() for k, v in template_vectors_pca.items()}, f)
    print("✅ 保存语义向量")

    X_train, y_train = build_sequences_from_templated_csv(
        'train_templated.csv', template_vectors_pca, max_seq_len=MAX_SEQ_LEN
    )
    X_test, y_test = build_sequences_from_templated_csv(
        'test_templated.csv', template_vectors_pca, max_seq_len=MAX_SEQ_LEN
    )

    def save_sequences(X, y, prefix):
        seq_str_list = [' '.join(map(str, seq.flatten())) for seq in X]
        seq_df = pd.DataFrame({0: seq_str_list, 1: y})
        seq_df.to_csv(f'./data/{prefix}_data.csv', index=False, header=False)
        label_df = pd.DataFrame(y)
        label_df.to_csv(f'./data/{prefix}_label.csv', index=False, header=False)
        print(f"✅ {prefix}: {len(X)} 个序列")

    save_sequences(X_train, y_train, 'boutique_train')
    save_sequences(X_test, y_test, 'boutique_test')
