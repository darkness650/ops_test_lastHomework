"""
Step 5: LSTM Training - LogAnomaly 核心模型训练
参考 LogAnomaly 论文:
  - 2层 LSTM, 每层 128 个神经元
  - 输入: 模板语义向量序列 (sequential) + 日志计数向量 (quantitative)
  - 同时检测顺序异常和定量异常
  - 使用正常数据训练 + 异常检测阈值
"""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.utils import shuffle
import os
import json
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

# 超参数 (与论文一致: 2 LSTM layers, 128 neurons, window=20)
MAX_SEQ_LEN = 20
SEQ_FEAT_DIM = 20     # 语义向量维度
LSTM_HIDDEN = 128     # LSTM 隐藏层大小
LSTM_LAYERS = 2       # LSTM 层数
BATCH_SIZE = 64
EPOCHS = 100
LR = 0.001
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class LogAnomalyLSTM(nn.Module):
    """
    LogAnomaly LSTM 模型
    参考论文: 2层 LSTM, 128 hidden units
    输入: 模板语义向量序列 + 计数向量
    输出: 正常/异常二分类
    """
    def __init__(self, input_dim, cnt_dim, hidden_dim=LSTM_HIDDEN, num_layers=LSTM_LAYERS, dropout=0.3):
        super(LogAnomalyLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM 处理顺序特征
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=False
        )
        
        # 融合层: LSTM输出 + 计数向量
        fusion_dim = hidden_dim + cnt_dim
        self.fc1 = nn.Linear(fusion_dim, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 2)  # 二分类
        
    def forward(self, x_seq, x_cnt):
        # x_seq: (batch, seq_len, input_dim)
        # x_cnt: (batch, cnt_dim)
        lstm_out, (h_n, c_n) = self.lstm(x_seq)
        
        # 取最后时间步的输出
        lstm_last = lstm_out[:, -1, :]  # (batch, hidden_dim)
        
        # 融合 LSTM 输出和计数向量
        fused = torch.cat([lstm_last, x_cnt], dim=1)
        
        x = self.relu(self.fc1(fused))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def compute_anomaly_score(model, x_seq, x_cnt, normal_only=True):
    """
    计算异常分数
    基于 LSTM 预测误差: 分数越高越可能是异常
    使用 softmax 输出的异常类概率作为分数
    """
    model.eval()
    with torch.no_grad():
        x_seq_t = torch.FloatTensor(x_seq).to(DEVICE)
        x_cnt_t = torch.FloatTensor(x_cnt).to(DEVICE)
        outputs = model(x_seq_t, x_cnt_t)
        probs = torch.softmax(outputs, dim=1)
        anomaly_scores = probs[:, 1].cpu().numpy()  # 异常类的概率
    return anomaly_scores


def train_model(model, train_loader, val_data, class_weight=None):
    """训练 LogAnomaly LSTM 模型"""
    
    criterion = nn.CrossEntropyLoss(weight=class_weight)
    optimizer = optim.Adam(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=10)
    
    best_val_f1 = 0
    best_state = None
    patience = 15
    patience_counter = 0
    
    history = {'train_loss': [], 'val_loss': [], 'val_f1': [], 'val_precision': [], 'val_recall': []}
    
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for batch_seq, batch_cnt, batch_labels in train_loader:
            batch_seq = batch_seq.to(DEVICE)
            batch_cnt = batch_cnt.to(DEVICE)
            batch_labels = batch_labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(batch_seq, batch_cnt)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            total_loss += loss.item()
        
        avg_loss = total_loss / len(train_loader)
        history['train_loss'].append(avg_loss)
        
        # 验证
        val_seq, val_cnt, val_labels = val_data
        val_probs = compute_anomaly_score(model, val_seq, val_cnt)
        val_pred = (val_probs > 0.5).astype(int)
        val_f1 = f1_score(val_labels, val_pred, zero_division=0)
        val_precision = precision_score(val_labels, val_pred, zero_division=0)
        val_recall = recall_score(val_labels, val_pred, zero_division=0)
        
        history['val_f1'].append(val_f1)
        history['val_precision'].append(val_precision)
        history['val_recall'].append(val_recall)
        
        scheduler.step(1 - val_f1)
        
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1}/{EPOCHS}: loss={avg_loss:.4f}, val_precision={val_precision:.4f}, val_recall={val_recall:.4f}, val_f1={val_f1:.4f}, lr={optimizer.param_groups[0]['lr']:.6f}")
        
        if patience_counter >= patience:
            print(f"  Early stopping at epoch {epoch+1}")
            break
    
    # 恢复最佳模型
    if best_state:
        model.load_state_dict(best_state)
    return model, history


def plot_training_history(history, save_path='./result/training_curves.png'):
    """绘制训练过程可视化曲线"""
    epochs = range(1, len(history['train_loss']) + 1)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 左图: Loss 曲线
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train Loss', linewidth=2)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].set_title('Training Loss', fontsize=14)
    axes[0].legend(fontsize=11)
    axes[0].grid(True, alpha=0.3)
    
    # 右图: Precision, Recall, F1 曲线
    axes[1].plot(epochs, history['val_precision'], 'g-', label='Precision', linewidth=2)
    axes[1].plot(epochs, history['val_recall'], 'r-', label='Recall', linewidth=2)
    axes[1].plot(epochs, history['val_f1'], 'b-', label='F1-Score', linewidth=2)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Score', fontsize=12)
    axes[1].set_title('Validation Metrics', fontsize=14)
    axes[1].legend(fontsize=11)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"训练曲线已保存到 {save_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("Step 5: LogAnomaly LSTM 模型训练")
    print("=" * 60)
    print(f"设备: {DEVICE}")
    
    os.makedirs('./saved_models', exist_ok=True)
    os.makedirs('./result', exist_ok=True)
    
    # 加载数据
    print("\n加载数据...")
    X_train_seq = np.load('./data/X_train_seq.npy')
    X_train_cnt = np.load('./data/X_train_cnt.npy')
    y_train = np.load('./data/y_train.npy')
    X_test_seq = np.load('./data/X_test_seq.npy')
    X_test_cnt = np.load('./data/X_test_cnt.npy')
    y_test = np.load('./data/y_test.npy')
    
    print(f"训练集: {len(y_train)}, 正常: {(y_train==0).sum()}, 异常: {(y_train==1).sum()}")
    print(f"测试集: {len(y_test)}, 正常: {(y_test==0).sum()}, 异常: {(y_test==1).sum()}")
    
    # 打乱训练数据
    X_train_seq, X_train_cnt, y_train = shuffle(X_train_seq, X_train_cnt, y_train, random_state=42)
    
    # 划分训练/验证集 (90/10)
    split_idx = int(len(y_train) * 0.9)
    X_tr_seq, X_val_seq = X_train_seq[:split_idx], X_train_seq[split_idx:]
    X_tr_cnt, X_val_cnt = X_train_cnt[:split_idx], X_train_cnt[split_idx:]
    y_tr, y_val = y_train[:split_idx], y_train[split_idx:]
    
    print(f"训练/验证: {len(y_tr)}/{len(y_val)}")
    
    # DataLoader
    train_dataset = TensorDataset(
        torch.FloatTensor(X_tr_seq), torch.FloatTensor(X_tr_cnt), torch.LongTensor(y_tr)
    )
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # 类别权重 (处理不平衡)
    n_normal = (y_tr == 0).sum()
    n_abnormal = (y_tr == 1).sum()
    if n_abnormal > 0:
        weight_normal = 1.0
        weight_abnormal = n_normal / n_abnormal
        class_weight = torch.FloatTensor([weight_normal, weight_abnormal]).to(DEVICE)
        print(f"类别权重: normal={weight_normal:.2f}, abnormal={weight_abnormal:.2f}")
    else:
        class_weight = None
    
    # 构建模型
    cnt_dim = X_train_cnt.shape[1]
    model = LogAnomalyLSTM(
        input_dim=SEQ_FEAT_DIM,
        cnt_dim=cnt_dim,
        hidden_dim=LSTM_HIDDEN,
        num_layers=LSTM_LAYERS
    ).to(DEVICE)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"\n模型参数量: {total_params:,}")
    print(f"LSTM层数: {LSTM_LAYERS}, 隐藏单元: {LSTM_HIDDEN}")
    print(f"输入维度: seq={SEQ_FEAT_DIM}, cnt={cnt_dim}")
    
    # 训练
    print("\n开始训练...")
    model, history = train_model(
        model, train_loader,
        val_data=(X_val_seq, X_val_cnt, y_val),
        class_weight=class_weight
    )
    
    # 保存模型
    model_path = './saved_models/loganomaly_lstm.pth'
    torch.save({
        'model_state_dict': model.state_dict(),
        'history': history,
        'config': {
            'input_dim': SEQ_FEAT_DIM,
            'cnt_dim': cnt_dim,
            'hidden_dim': LSTM_HIDDEN,
            'num_layers': LSTM_LAYERS,
            'max_seq_len': MAX_SEQ_LEN
        }
    }, model_path)
    print(f"\n模型已保存到 {model_path}")
    
    # 验证集评估
    val_scores = compute_anomaly_score(model, X_val_seq, X_val_cnt)
    val_pred = (val_scores > 0.5).astype(int)
    val_precision = precision_score(y_val, val_pred, zero_division=0)
    val_recall = recall_score(y_val, val_pred, zero_division=0)
    val_f1 = f1_score(y_val, val_pred, zero_division=0)
    
    print(f"\n验证集结果:")
    print(f"  Precision: {val_precision:.4f}")
    print(f"  Recall:    {val_recall:.4f}")
    print(f"  F1-score:  {val_f1:.4f}")
    
    # 绘制训练曲线
    print("\n生成训练可视化...")
    plot_training_history(history)
    
    print("[Step5] 完成.")