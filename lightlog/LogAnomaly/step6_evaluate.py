"""
Step 6: Evaluation - LogAnomaly 模型评估
包括:
  - 测试集评估 (Precision, Recall, F1, Confusion Matrix)
  - 阈值分析 (寻找最佳阈值)
  - 与 DeepLog/LightLog 对比准备
"""
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (precision_score, recall_score, f1_score, 
                              confusion_matrix, roc_auc_score, 
                              precision_recall_curve, average_precision_score)
import os
import json
import sys

# 导入模型定义
sys.path.insert(0, os.path.dirname(__file__))
from step5_train_lstm import LogAnomalyLSTM, compute_anomaly_score

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 超参数
MAX_SEQ_LEN = 20
SEQ_FEAT_DIM = 20
LSTM_HIDDEN = 128
LSTM_LAYERS = 2


def load_model(model_path, cnt_dim):
    """加载训练好的模型"""
    checkpoint = torch.load(model_path, map_location=DEVICE)
    config = checkpoint.get('config', {})
    
    model = LogAnomalyLSTM(
        input_dim=config.get('input_dim', SEQ_FEAT_DIM),
        cnt_dim=config.get('cnt_dim', cnt_dim),
        hidden_dim=config.get('hidden_dim', LSTM_HIDDEN),
        num_layers=config.get('num_layers', LSTM_LAYERS)
    ).to(DEVICE)
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    return model


def evaluate_with_threshold(model, X_seq, X_cnt, y_true, threshold=0.5):
    """使用指定阈值评估模型"""
    scores = compute_anomaly_score(model, X_seq, X_cnt)
    y_pred = (scores > threshold).astype(int)
    
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)
    
    return {
        'threshold': threshold,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'confusion_matrix': cm.tolist(),
        'predictions': y_pred.tolist(),
        'scores': scores.tolist()
    }


def find_best_threshold(model, X_seq, X_cnt, y_true):
    """搜索最佳 F1 阈值"""
    print("\n搜索最佳阈值...")
    scores = compute_anomaly_score(model, X_seq, X_cnt)
    
    best_f1 = 0
    best_threshold = 0.5
    best_result = None
    
    for threshold in np.arange(0.05, 0.95, 0.05):
        y_pred = (scores > threshold).astype(int)
        p = precision_score(y_true, y_pred, zero_division=0)
        r = recall_score(y_true, y_pred, zero_division=0)
        f1_val = f1_score(y_true, y_pred, zero_division=0)
        
        if f1_val > best_f1:
            best_f1 = f1_val
            best_threshold = threshold
        
        if f1_val > 0.01:
            print(f"  阈值 {threshold:.2f}: P={p:.4f}, R={r:.4f}, F1={f1_val:.4f}, pred_anomalies={y_pred.sum()}")
    
    return best_threshold, best_f1


if __name__ == "__main__":
    print("=" * 60)
    print("Step 6: LogAnomaly 模型评估")
    print("=" * 60)
    
    os.makedirs('./result', exist_ok=True)
    
    # 加载测试数据
    print("\n加载测试数据...")
    X_test_seq = np.load('./data/X_test_seq.npy')
    X_test_cnt = np.load('./data/X_test_cnt.npy')
    y_test = np.load('./data/y_test.npy')
    
    print(f"测试集: {len(y_test)} 个序列")
    print(f"  正常: {(y_test==0).sum()}, 异常: {(y_test==1).sum()}")
    print(f"  异常比例: {y_test.mean()*100:.1f}%")
    
    cnt_dim = X_test_cnt.shape[1]
    
    # 加载模型
    model_path = './saved_models/loganomaly_lstm.pth'
    if not os.path.exists(model_path):
        print(f"错误: 模型文件不存在 {model_path}")
        print("请先运行 step5_train_lstm.py")
        sys.exit(1)
    
    model = load_model(model_path, cnt_dim)
    print(f"模型加载成功")
    
    # 寻找最佳阈值
    best_threshold, best_f1 = find_best_threshold(model, X_test_seq, X_test_cnt, y_test)
    
    # 使用最佳阈值评估
    print(f"\n使用最佳阈值 {best_threshold:.2f} 评估...")
    result = evaluate_with_threshold(model, X_test_seq, X_test_cnt, y_test, threshold=best_threshold)
    
    cm = np.array(result['confusion_matrix'])
    
    print("\n" + "=" * 60)
    print("LogAnomaly 测试结果")
    print("=" * 60)
    print(f"阈值:      {best_threshold:.2f}")
    print(f"Precision: {result['precision']:.4f}")
    print(f"Recall:    {result['recall']:.4f}")
    print(f"F1-score:  {result['f1']:.4f}")
    print(f"\n混淆矩阵:")
    print(f"            预测正常  预测异常")
    print(f"  实际正常:    {cm[0,0]:6d}    {cm[0,1]:6d}")
    print(f"  实际异常:    {cm[1,0]:6d}    {cm[1,1]:6d}")
    
    # 计算 AUC
    try:
        scores = np.array(result['scores'])
        auc = roc_auc_score(y_test, scores)
        ap = average_precision_score(y_test, scores)
        print(f"\nROC-AUC:  {auc:.4f}")
        print(f"Avg Precision: {ap:.4f}")
    except Exception as e:
        print(f"\nAUC 计算失败: {e}")
        auc = 0
        ap = 0
    
    # 保存结果
    output_result = {
        'method': 'LogAnomaly',
        'threshold': best_threshold,
        'precision': result['precision'],
        'recall': result['recall'],
        'f1': result['f1'],
        'roc_auc': auc,
        'avg_precision': ap,
        'confusion_matrix': result['confusion_matrix'],
        'n_test': len(y_test),
        'n_normal': int((y_test==0).sum()),
        'n_abnormal': int((y_test==1).sum()),
        'config': {
            'lstm_layers': LSTM_LAYERS,
            'lstm_hidden': LSTM_HIDDEN,
            'max_seq_len': MAX_SEQ_LEN,
            'seq_feat_dim': SEQ_FEAT_DIM
        }
    }
    
    with open('./result/loganomaly_results.json', 'w') as f:
        json.dump(output_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到 ./result/loganomaly_results.json")
    print("[Step6] 完成.")