"""
Step 4: Build Log Sequences - 构建日志序列
参考 LogAnomaly 论文:
  - Sequential features: 将模板语义向量按时间排列成序列
  - Quantitative features: 日志计数向量 (仅统计 top-K 高频模板, 避免维度爆炸)
  - 序列长度 = 20 (论文 window=20)
  
count vector 优化: 全量 vocab=16280 会导致 13+ GiB 内存爆炸
  改为仅统计 top-500 高频模板, dense 存储约 428 MB
"""
import pandas as pd
import numpy as np
from collections import Counter
import json
import os

# 超参数
MAX_SEQ_LEN = 20       # 序列窗口大小 (论文: window=20)
TARGET_DIM = 20        # 语义向量维度
CNT_TOP_K = 500        # count vector 只保留 top-K 最高频模板


def get_topk_templates(templated_csv_path, k=CNT_TOP_K):
    """从训练集统计 top-K 高频模板ID (用于限制 count vector 维度)"""
    df = pd.read_csv(templated_csv_path)
    counter = Counter()
    for _, row in df.iterrows():
        tid = int(row['template_id'])
        if tid > 0:
            counter[tid] += 1
    topk = {tid for tid, _ in counter.most_common(k)}
    print(f"[Step4] Top-{k} 模板覆盖 {sum(counter[t] for t in topk)}/{sum(counter.values())} 条日志")
    return topk


if __name__ == "__main__":
    print("=" * 60)
    print("Step 4: 构建日志序列 (顺序特征 + top-K 计数向量)")
    print("=" * 60)
    
    os.makedirs('./data', exist_ok=True)
    
    # 加载语义向量
    with open('./data/loganomaly_semantic_vec.json', 'r') as f:
        template_vectors_pca = json.load(f)
    
    vocab_size = max(int(k) for k in template_vectors_pca.keys()) + 1
    print(f"模板词汇量: {vocab_size}")
    
    # 从训练集获取 top-K 高频模板 (只统计训练集, 避免数据泄露)
    topk_templates = get_topk_templates('train_templated.csv', k=CNT_TOP_K)
    
    # 构建 top-K ID 到 count vector 索引的映射
    # 将原始 template_id 映射到 0..K-1 的连续索引
    tid_list = sorted(topk_templates)
    tid_to_idx = {tid: i for i, tid in enumerate(tid_list)}
    
    def build_with_topk(csv_path):
        """使用 top-K 映射构建序列"""
        df = pd.read_csv(csv_path)
        groups = df.groupby('group_id')
        
        X_seq_list = []
        X_cnt_list = []
        y_list = []
        
        for group_id, group_df in groups:
            label = group_df['label'].iloc[0]
            template_ids = group_df['template_id'].tolist()
            
            # 顺序特征
            seq_embeddings = []
            for tid in template_ids:
                str_tid = str(tid)
                if str_tid in template_vectors_pca:
                    seq_embeddings.append(template_vectors_pca[str_tid])
                else:
                    seq_embeddings.append(np.zeros(TARGET_DIM, dtype=np.float32))
            
            if len(seq_embeddings) > MAX_SEQ_LEN:
                seq_embeddings = seq_embeddings[:MAX_SEQ_LEN]
            else:
                seq_embeddings = seq_embeddings + [np.zeros(TARGET_DIM, dtype=np.float32)] * (MAX_SEQ_LEN - len(seq_embeddings))
            
            X_seq_list.append(seq_embeddings)
            
            # 定量特征: top-K count vector
            cnt_vec = np.zeros(CNT_TOP_K, dtype=np.float32)
            for tid in template_ids[:MAX_SEQ_LEN]:
                tid_int = int(tid)
                idx = tid_to_idx.get(tid_int, -1)
                if idx >= 0:
                    cnt_vec[idx] = min(cnt_vec[idx] + 1, 255)
            
            X_cnt_list.append(cnt_vec)
            y_list.append(label)
        
        X_seq = np.array(X_seq_list, dtype=np.float32)
        X_cnt = np.array(X_cnt_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.int32)
        return X_seq, X_cnt, y
    
    print("\n构建训练集...")
    X_train_seq, X_train_cnt, y_train = build_with_topk('train_templated.csv')
    print(f"训练集: {len(y_train)} 序列, X_seq={X_train_seq.shape}, X_cnt={X_train_cnt.shape}")
    
    print("\n构建测试集...")
    X_test_seq, X_test_cnt, y_test = build_with_topk('test_templated.csv')
    print(f"测试集: {len(y_test)} 序列, X_seq={X_test_seq.shape}, X_cnt={X_test_cnt.shape}")
    
    # 保存
    save_dir = './data'
    np.save(os.path.join(save_dir, 'X_train_seq.npy'), X_train_seq)
    np.save(os.path.join(save_dir, 'X_train_cnt.npy'), X_train_cnt)
    np.save(os.path.join(save_dir, 'y_train.npy'), y_train)
    np.save(os.path.join(save_dir, 'X_test_seq.npy'), X_test_seq)
    np.save(os.path.join(save_dir, 'X_test_cnt.npy'), X_test_cnt)
    np.save(os.path.join(save_dir, 'y_test.npy'), y_test)
    
    # 保存 top-K 映射
    np.save(os.path.join(save_dir, 'cnt_topk_mapping.npy'), np.array(tid_list, dtype=np.int32))
    
    print(f"\n[Step4] 完成. 内存估算:")
    print(f"  X_train_cnt: {X_train_cnt.nbytes / 1024**2:.1f} MB")
    print(f"  X_test_cnt:  {X_test_cnt.nbytes / 1024**2:.1f} MB")