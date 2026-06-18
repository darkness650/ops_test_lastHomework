"""
Step 3: Template2Vec - 日志模板的语义向量表示
参考 LogAnomaly 论文核心创新 template2vec:
1. Word2Vec 训练获取词向量
2. WordNet 同义词/反义词增强语义
3. 模板向量 = 所有词向量求和
4. PCA-PPA 降维到低维空间
"""
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

# 超参数 (与论文一致)
WORD_EMBEDDING_DIM = 300   # Word2Vec 词向量维度
TARGET_DIM = 20            # PCA-PPA 降维目标维度
MAX_SEQ_LEN = 20           # 日志序列窗口大小 (论文window=20)


def try_load_synonyms():
    """
    尝试从 NLTK WordNet 加载同义词/反义词字典
    如果 nltk 不可用，返回空字典
    """
    syn_ant = {}
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            print("[Step3] 下载 WordNet...")
            nltk.download('wordnet', quiet=True)
        
        for synset in list(wn.all_synsets())[:50000]:  # 限制数量避免太慢
            for lemma in synset.lemmas():
                word = lemma.name().lower().replace('_', ' ')
                if word not in syn_ant:
                    syn_ant[word] = {'synonyms': set(), 'antonyms': set()}
                # 同义词
                for syn_lemma in synset.lemmas():
                    syn_word = syn_lemma.name().lower().replace('_', ' ')
                    if syn_word != word:
                        syn_ant[word]['synonyms'].add(syn_word)
                # 反义词
                if lemma.antonyms():
                    for ant in lemma.antonyms():
                        syn_ant[word]['antonyms'].add(ant.name().lower().replace('_', ' '))
        
        print(f"[Step3] WordNet 加载成功，{len(syn_ant)} 个词条")
    except ImportError:
        print("[Step3] NLTK 未安装，跳过同义词/反义词增强")
    except Exception as e:
        print(f"[Step3] WordNet 加载失败: {e}，跳过增强")
    
    return syn_ant


def augment_sentences_with_synonyms(sentences, syn_ant):
    """
    用同义词增强训练语料
    对每个句子中的每个词，随机替换为同义词，生成增强句子
    """
    import random
    augmented = list(sentences)
    for sent in sentences:
        if random.random() < 0.3:  # 30% 概率增强
            new_sent = []
            for word in sent:
                if word in syn_ant and syn_ant[word]['synonyms']:
                    if random.random() < 0.2:
                        syn = random.choice(list(syn_ant[word]['synonyms']))
                        new_sent.append(syn)
                    else:
                        new_sent.append(word)
                else:
                    new_sent.append(word)
            augmented.append(new_sent)
    return augmented


def train_word2vec(template_to_id, syn_ant=None):
    """
    训练 Word2Vec 模型获取模板词向量
    参考 LogAnomaly 的 template2vec 方法
    """
    print("[Step3] 训练 Word2Vec (template2vec)...")
    
    # 构建训练语料：每个模板是一个句子
    sentences = []
    for template in template_to_id.keys():
        words = template.split()
        sentences.append(words)
    
    print(f"[Step3] 原始语料: {len(sentences)} 个模板(句子)")
    
    # 同义词增强
    if syn_ant and len(syn_ant) > 0:
        sentences = augment_sentences_with_synonyms(sentences, syn_ant)
        print(f"[Step3] 增强后语料: {len(sentences)} 个句子")
    
    if len(sentences) < 2:
        print("[Step3] 模板太少，返回随机向量")
        return None
    
    # Word2Vec 训练 (CBOW模式)
    model = Word2Vec(
        sentences=sentences,
        vector_size=WORD_EMBEDDING_DIM,
        window=5,
        min_count=1,
        workers=1,
        epochs=20,
        sg=0  # CBOW
    )
    
    # L2 归一化词向量
    embeddings = model.wv.vectors
    normalized_embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
    
    # 每个模板的向量 = 所有词向量求和 (template2vec方法)
    template_vectors = {}
    for template, tid in template_to_id.items():
        words = template.split()
        vector = np.zeros(WORD_EMBEDDING_DIM)
        word_count = 0
        for word in words:
            if word in model.wv.key_to_index:
                idx = model.wv.key_to_index[word]
                vector += normalized_embeddings[idx]
                word_count += 1
        if word_count > 0:
            vector = vector / word_count  # 平均
        template_vectors[tid] = vector.tolist()
    
    print(f"[Step3] Word2Vec 完成，词汇量: {len(model.wv.key_to_index)}")
    return template_vectors


def pca_ppa_reduction(embeddings_matrix, target_dim=TARGET_DIM, remove_d=7):
    """
    PCA-PPA 降维
    参考 LogAnomaly 论文: 先用 PCA 降维，再移除 top-d 个主成分
    """
    if embeddings_matrix is None or len(embeddings_matrix) < target_dim:
        print(f"[Step3] 数据不足 ({len(embeddings_matrix) if embeddings_matrix is not None else 0})，使用随机向量")
        return np.random.randn(max(50, target_dim), target_dim) * 0.01

    print(f"[Step3] PCA-PPA 降维: {embeddings_matrix.shape[1]} -> {target_dim}")

    # 第一阶段 PCA: 降维到中间维度
    n_components = min(target_dim * 2, embeddings_matrix.shape[0], embeddings_matrix.shape[1])
    pca1 = PCA(n_components=n_components)
    pca_result = pca1.fit_transform(embeddings_matrix)
    pca_result = pca_result - np.mean(pca_result, axis=0)

    # 第二阶段 PCA + PPA: 移除 top-d 主成分
    pca2 = PCA(n_components=min(target_dim + remove_d, pca_result.shape[0], pca_result.shape[1]))
    pca_result2 = pca2.fit_transform(pca_result)
    U = pca2.components_

    remove_d = min(remove_d, U.shape[0])
    ppa_result = []
    for x in pca_result:
        for u in U[:remove_d]:
            x = x - np.dot(u.T, x) * u
        ppa_result.append(x)

    ppa_result = np.array(ppa_result)
    
    # 调整维度到 target_dim
    if ppa_result.shape[1] < target_dim:
        pad = np.zeros((ppa_result.shape[0], target_dim - ppa_result.shape[1]))
        ppa_result = np.hstack([ppa_result, pad])
    elif ppa_result.shape[1] > target_dim:
        ppa_result = ppa_result[:, :target_dim]

    print(f"[Step3] PCA-PPA 完成: {ppa_result.shape}")
    return ppa_result


def build_template_vectors_pca(template_to_id, template_vectors_raw, target_dim=TARGET_DIM):
    """将模板向量构建为矩阵，进行PCA-PPA降维，返回 tid -> low_dim_vector 映射"""
    
    if template_vectors_raw is None:
        # Fallback: 随机向量
        template_vectors_pca = {}
        for tid in template_to_id.values():
            template_vectors_pca[tid] = (np.random.randn(target_dim) * 0.01).tolist()
        return template_vectors_pca
    
    # 构建嵌入矩阵
    max_tid = max(template_vectors_raw.keys())
    embeddings_matrix = np.zeros((max_tid + 1, WORD_EMBEDDING_DIM))
    for tid, vec in template_vectors_raw.items():
        embeddings_matrix[tid] = vec
    
    # PCA-PPA 降维
    low_dim = pca_ppa_reduction(embeddings_matrix, target_dim=target_dim)
    
    # 构建映射
    template_vectors_pca = {}
    for tid in range(len(low_dim)):
        template_vectors_pca[tid] = low_dim[tid].tolist()
    
    return template_vectors_pca


if __name__ == "__main__":
    print("=" * 60)
    print("Step 3: Template2Vec - 语义向量提取")
    print("=" * 60)
    
    os.makedirs('./data', exist_ok=True)
    
    # 加载模板字典
    with open('template_to_id.json', 'r', encoding='utf-8') as f:
        template_to_id = json.load(f)
    print(f"加载 {len(template_to_id)} 个模板")
    
    # 尝试加载 WordNet (同义词/反义词增强)
    print("\n--- 尝试加载 WordNet ---")
    syn_ant = try_load_synonyms()
    
    # 训练 Word2Vec
    template_vectors_raw = train_word2vec(template_to_id, syn_ant)
    
    # PCA-PPA 降维
    template_vectors_pca = build_template_vectors_pca(template_to_id, template_vectors_raw)
    
    # 保存语义向量
    output_path = './data/loganomaly_semantic_vec.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in template_vectors_pca.items()}, f)
    print(f"[Step3] 语义向量已保存到 {output_path}")
    print(f"[Step3] 向量维度: {len(next(iter(template_vectors_pca.values())))}, 模板数: {len(template_vectors_pca)}")
    print("[Step3] 完成.")