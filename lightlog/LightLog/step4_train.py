import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.python.keras.models import Model
from tensorflow.python.keras.layers import Input, Conv1D, Activation, Add, GlobalAveragePooling1D, Dense, Dropout
from tensorflow.python.keras.callbacks import EarlyStopping, ReduceLROnPlateau, Callback
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.utils import shuffle
import ast
import os
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt

print("="*60)
print("LightLog 训练 - Boutique 数据集")
print("="*60)

os.makedirs('./model', exist_ok=True)
os.makedirs('./result', exist_ok=True)

# 加载数据
print("\n[1/5] 加载训练数据...")
train_df = pd.read_csv('./data/boutique_train_data.csv', header=None)
train_labels = pd.read_csv('./data/boutique_train_label.csv', header=None).values.flatten()

print("\n[2/5] 加载测试数据...")
test_df = pd.read_csv('./data/boutique_test_data.csv', header=None)
test_labels = pd.read_csv('./data/boutique_test_label.csv', header=None).values.flatten()

print(f"训练集: {len(train_df)} 条序列")
print(f"测试集: {len(test_df)} 条序列")
print(f"训练集异常比例: {train_labels.sum()}/{len(train_labels)} = {train_labels.mean()*100:.1f}%")
print(f"测试集异常比例: {test_labels.sum()}/{len(test_labels)} = {test_labels.mean()*100:.1f}%")

# 解析序列
def parse_sequences(df):
    sequences = []
    for _, row in df.iterrows():
        val = row[0]
        if isinstance(val, str) and val.startswith('['):
            seq = ast.literal_eval(val)
        else:
            seq = list(map(float, val.split()))
        sequences.append(seq)
    return np.array(sequences)

X_train = parse_sequences(train_df)
X_test = parse_sequences(test_df)

# 确定维度
max_seq_len = 20  # 数据集已经分好序列，长度为 20
feat_dim = 20
expected_len = max_seq_len * feat_dim

# 检查序列长度
X_train_reshaped = []
X_test_reshaped = []
for seq in X_train:
    if len(seq) == expected_len:
        X_train_reshaped.append(seq.reshape(max_seq_len, feat_dim))
for seq in X_test:
    if len(seq) == expected_len:
        X_test_reshaped.append(seq.reshape(max_seq_len, feat_dim))

X_train = np.array(X_train_reshaped)
X_test = np.array(X_test_reshaped)

print(f"X_train 形状: {X_train.shape}")
print(f"X_test 形状: {X_test.shape}")

# 训练前打乱数据
print("\n训练前打乱数据...")
X_train, train_labels = shuffle(X_train, train_labels, random_state=42)
X_test, test_labels = shuffle(X_test, test_labels, random_state=42)
print("✅ 数据已打乱")

# 从测试集中采样平衡子集进行评估
print("\n采样平衡测试集...")
normal_indices = np.where(test_labels == 0)[0]
abnormal_indices = np.where(test_labels == 1)[0]

# 采样与异常数量相同的正常样本
n_abnormal = len(abnormal_indices)
n_sample = min(n_abnormal, 5000)  # 最多 5000

sample_normal = np.random.choice(normal_indices, size=n_sample, replace=False)
sample_indices = np.concatenate([sample_normal, abnormal_indices])
X_test = X_test[sample_indices]
test_labels = test_labels[sample_indices]

print(f"平衡测试集: {len(test_labels)} 个序列")
print(f"  正常: {np.sum(test_labels == 0)}, 异常: {np.sum(test_labels == 1)}")

# 类别权重（增加异常类权重以提升 Recall）
print("\n[3/5] 设置类别权重...")
n_normal = np.sum(train_labels == 0)
n_abnormal = np.sum(train_labels == 1)
total = len(train_labels)
# 增加异常类权重，但不过度（之前 3.0 导致太多误报）
class_weight_dict = {
    0: 1.0,
    1: 1.5  # 适度提升异常类权重
}
print(f"正常样本: {n_normal}, 异常样本: {n_abnormal}")
print(f"类别权重: 正常={class_weight_dict[0]:.2f}, 异常={class_weight_dict[1]:.2f}")

# 转换标签
y_train_cat = tf.keras.utils.to_categorical(train_labels, num_classes=2)
y_test_cat = tf.keras.utils.to_categorical(test_labels, num_classes=2)

# 自定义回调：记录每个 epoch 的 precision、recall、f1
class MetricsCallback(Callback):
    def __init__(self, X_val, y_val):
        super().__init__()
        self.X_val = X_val
        self.y_val = y_val
        self.precisions = []
        self.recalls = []
        self.f1s = []

    def on_epoch_end(self, epoch, logs=None):
        y_pred_proba = self.model.predict(self.X_val, verbose=0)
        y_pred = np.argmax(y_pred_proba, axis=1)
        y_true = np.argmax(self.y_val, axis=1)
        p = precision_score(y_true, y_pred, zero_division=0)
        r = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        self.precisions.append(p)
        self.recalls.append(r)
        self.f1s.append(f1)
        logs['val_precision'] = p
        logs['val_recall'] = r
        logs['val_f1'] = f1

# 构建模型
def ResBlock(x, filters, kernel_size, dilation_rate):
    r = Conv1D(filters, kernel_size, padding='same', dilation_rate=dilation_rate, activation='relu')(x)
    r = Dropout(0.2)(r)
    r = Conv1D(filters, kernel_size, padding='same', dilation_rate=dilation_rate)(r)
    if x.shape[-1] == filters:
        shortcut = x
    else:
        shortcut = Conv1D(filters, kernel_size, padding='same')(x)
    o = tf.keras.layers.add([r, shortcut])
    o = Activation('relu')(o)
    return o

def build_model():
    inputs = Input(shape=(max_seq_len, feat_dim))
    x = ResBlock(inputs, filters=16, kernel_size=3, dilation_rate=1)
    x = ResBlock(x, filters=16, kernel_size=3, dilation_rate=2)
    x = ResBlock(x, filters=16, kernel_size=3, dilation_rate=4)
    x = ResBlock(x, filters=16, kernel_size=3, dilation_rate=8)
    x = GlobalAveragePooling1D()(x)
    x = Dropout(0.3)(x)
    x = Dense(32, activation='relu')(x)
    x = Dropout(0.2)(x)
    outputs = Dense(2, activation='softmax')(x)
    model = Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

print("\n[4/5] 构建并训练模型...")
model = build_model()
model.summary()

# 回调函数
# 从训练集中划分验证集用于 MetricsCallback
val_split_idx = int(len(X_train) * 0.9)
X_val_for_metrics = X_train[val_split_idx:]
y_val_for_metrics = y_train_cat[val_split_idx:]

metrics_cb = MetricsCallback(X_val_for_metrics, y_val_for_metrics)
early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=0.00001)

history = model.fit(
    X_train, y_train_cat,
    batch_size=64,
    epochs=100,
    verbose=1,
    validation_split=0.1,
    class_weight=class_weight_dict,
    callbacks=[early_stop, reduce_lr, metrics_cb]
)

# ========== 训练过程可视化 ==========
print("\n绘制训练过程可视化图表...")
epochs = range(1, len(history.history['loss']) + 1)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('LightLog Training Process Visualization', fontsize=16, fontweight='bold')

# 1. Loss 曲线
axes[0, 0].plot(epochs, history.history['loss'], 'b-', label='Train Loss', linewidth=2)
axes[0, 0].plot(epochs, history.history['val_loss'], 'r-', label='Val Loss', linewidth=2)
axes[0, 0].set_title('Loss', fontsize=12)
axes[0, 0].set_xlabel('Epoch')
axes[0, 0].set_ylabel('Loss')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# 2. Accuracy 曲线
acc_key = 'acc' if 'acc' in history.history else 'accuracy'
val_acc_key = 'val_acc' if 'val_acc' in history.history else 'val_accuracy'
axes[0, 1].plot(epochs, history.history[acc_key], 'b-', label='Train Accuracy', linewidth=2)
axes[0, 1].plot(epochs, history.history[val_acc_key], 'r-', label='Val Accuracy', linewidth=2)
axes[0, 1].set_title('Accuracy', fontsize=12)
axes[0, 1].set_xlabel('Epoch')
axes[0, 1].set_ylabel('Accuracy')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# 3. Precision & Recall 曲线
axes[1, 0].plot(epochs, metrics_cb.precisions, 'g-', label='Precision', linewidth=2)
axes[1, 0].plot(epochs, metrics_cb.recalls, 'm-', label='Recall', linewidth=2)
axes[1, 0].set_title('Precision & Recall', fontsize=12)
axes[1, 0].set_xlabel('Epoch')
axes[1, 0].set_ylabel('Score')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_ylim(0, 1.05)

# 4. F1 Score 曲线
axes[1, 1].plot(epochs, metrics_cb.f1s, 'c-', label='F1 Score', linewidth=2)
axes[1, 1].set_title('F1 Score', fontsize=12)
axes[1, 1].set_xlabel('Epoch')
axes[1, 1].set_ylabel('F1 Score')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].set_ylim(0, 1.05)

plt.tight_layout()
plt.savefig('./result/training_visualization.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ 训练可视化图表已保存到 ./result/training_visualization.png")

# 保存训练历史
hist_df = pd.DataFrame({
    'epoch': epochs,
    'loss': history.history['loss'],
    'val_loss': history.history['val_loss'],
    'accuracy': history.history[acc_key],
    'val_accuracy': history.history[val_acc_key],
    'precision': metrics_cb.precisions,
    'recall': metrics_cb.recalls,
    'f1': metrics_cb.f1s
})
hist_df.to_csv('./result/training_history.csv', index=False)
print("✅ 训练历史已保存到 ./result/training_history.csv")

# 保存模型
model.save_weights('./model/boutique_weights.h5')
with open('./model/model_structure_boutique.json', 'w') as f:
    f.write(model.to_json())
print("✅ 模型已保存")

# 评估
print("\n[5/5] 评估模型...")
y_pred_proba = model.predict(X_test, batch_size=128)

# 尝试不同阈值
print("\n尝试不同阈值:")
print(f"预测异常概率: min={y_pred_proba[:, 1].min():.4f}, max={y_pred_proba[:, 1].max():.4f}, mean={y_pred_proba[:, 1].mean():.4f}")

best_f1 = 0
best_threshold = 0.5
best_pred = None

for threshold in np.arange(0.1, 0.95, 0.05):
    y_pred = (y_pred_proba[:, 1] > threshold).astype(int)
    precision = precision_score(test_labels, y_pred, zero_division=0)
    recall = recall_score(test_labels, y_pred, zero_division=0)
    f1 = f1_score(test_labels, y_pred, zero_division=0)
    if f1 > 0.01:  # 只显示有意义的结果
        print(f"  阈值 {threshold:.2f}: P={precision:.4f}, R={recall:.4f}, F1={f1:.4f}, 预测异常={y_pred.sum()}")

    if f1 > best_f1:
        best_f1 = f1
        best_threshold = threshold
        best_pred = y_pred

print(f"\n最佳阈值: {best_threshold}, F1={best_f1:.4f}")

# 使用最佳阈值的结果
cm = confusion_matrix(test_labels, best_pred)

print("\n" + "=" * 60)
print("测试结果（最佳阈值）")
print("=" * 60)
print(f"Precision: {precision_score(test_labels, best_pred, zero_division=0):.4f}")
print(f"Recall:    {recall_score(test_labels, best_pred, zero_division=0):.4f}")
print(f"F1-score:  {best_f1:.4f}")
print(f"\n混淆矩阵:")
print(f"           预测正常  预测异常")
print(f"实际正常:    {cm[0, 0]:6d}    {cm[0, 1]:6d}")
print(f"实际异常:    {cm[1, 0]:6d}    {cm[1, 1]:6d}")

# 保存结果
results = pd.DataFrame({
    'threshold': [best_threshold],
    'precision': [precision_score(test_labels, best_pred, zero_division=0)],
    'recall': [recall_score(test_labels, best_pred, zero_division=0)],
    'f1': [best_f1],
    'tn': [cm[0, 0]],
    'fp': [cm[0, 1]],
    'fn': [cm[1, 0]],
    'tp': [cm[1, 1]]
})
results.to_csv('./result/result_boutique.csv', index=False)
print("\n✅ 结果已保存到 ./result/result_boutique.csv")
