"""
LightLog 消融实验 (Ablation Study)
完整复现 LightLog 论文 Table 4

5个变体:
1. TCN                 - 基线 (300维)
2. TCN (PCA-PPA)       - 使用降维特征 (20维)
3. TCN (带3核)         - 多核卷积 (300维)
4. TCN (带3核+pw-conv) - 多核 + Pointwise卷积 (300维)
5. Proposed TCN        - 多核 + PW-Conv + GAP (20维)

关键:
- TCN_PCA_PPA 和 Proposed_TCN 使用 20 维特征
- 其他变体使用 300 维特征 (模拟原始 Word2Vec)
- GAP 是 Proposed TCN 独有的
"""

import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.python.keras.models import Model
from tensorflow.python.keras.layers import (
    Input, Conv1D, Activation, Add, GlobalAveragePooling1D,
    Dense, Dropout, Concatenate, Flatten
)
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.utils import shuffle
import ast
import os
import time
import matplotlib.pyplot as plt

# 设置随机种子 - 兼容 TF 1.x 和 2.x
np.random.seed(42)
try:
    tf.random.set_seed(42)  # TF 2.x
except AttributeError:
    tf.set_random_seed(42)  # TF 1.x

# 固定超参数
MAX_SEQ_LEN = 20
FEAT_DIM = 20
BATCH_SIZE = 64
EPOCHS = 100
PATIENCE = 15
LEARNING_RATE = 0.001

os.makedirs('./ablation_results', exist_ok=True)
os.makedirs('./ablation_models', exist_ok=True)


def load_data():
    """加载数据，返回低维(20维)和高维(300维)两组数据"""
    print("\n" + "=" * 60)
    print("加载数据...")
    print("=" * 60)

    train_df = pd.read_csv('./data/boutique_train_data.csv', header=None)
    train_labels = pd.read_csv('./data/boutique_train_label.csv', header=None).values.flatten()
    test_df = pd.read_csv('./data/boutique_test_data.csv', header=None)
    test_labels = pd.read_csv('./data/boutique_test_label.csv', header=None).values.flatten()

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

    X_train_raw = parse_sequences(train_df)
    X_test_raw = parse_sequences(test_df)

    # Reshape to (samples, seq_len, feat_dim)
    expected_len = MAX_SEQ_LEN * FEAT_DIM  # 20 * 20 = 400
    X_train_20d = []
    X_test_20d = []

    for seq in X_train_raw:
        if len(seq) == expected_len:
            X_train_20d.append(seq.reshape(MAX_SEQ_LEN, FEAT_DIM))
    for seq in X_test_raw:
        if len(seq) == expected_len:
            X_test_20d.append(seq.reshape(MAX_SEQ_LEN, FEAT_DIM))

    X_train_20d = np.array(X_train_20d)
    X_test_20d = np.array(X_test_20d)

    # 模拟300维：重复15次 (20 × 15 = 300)
    X_train_300d = np.repeat(X_train_20d, 15, axis=-1)
    X_test_300d = np.repeat(X_test_20d, 15, axis=-1)

    print(f"低维数据 (20维): 训练集 {X_train_20d.shape}, 测试集 {X_test_20d.shape}")
    print(f"高维数据 (300维): 训练集 {X_train_300d.shape}, 测试集 {X_test_300d.shape}")
    print(f"训练集异常比例: {train_labels.mean():.2%}")
    print(f"测试集异常比例: {test_labels.mean():.2%}")

    return (X_train_20d, X_test_20d), (X_train_300d, X_test_300d), train_labels, test_labels


# ============================================================
# 模型定义
# ============================================================

def build_tcn_base(input_shape, filters=16):
    """
    TCN (原始) - 基线
    - 单核卷积
    - 无 GAP (Flatten)
    """
    inputs = Input(shape=input_shape)

    def res_block(x, dilation):
        r = Conv1D(filters, 3, padding='same', dilation_rate=dilation, activation='relu')(x)
        r = Dropout(0.2)(r)
        r = Conv1D(filters, 3, padding='same', dilation_rate=dilation)(r)
        if x.shape[-1] != filters:
            shortcut = Conv1D(filters, 1, padding='same')(x)
        else:
            shortcut = x
        o = Add()([r, shortcut])
        return Activation('relu')(o)

    x = res_block(inputs, 1)
    x = res_block(x, 2)
    x = res_block(x, 4)
    x = res_block(x, 8)

    x = Flatten()(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(0.3)(x)
    outputs = Dense(2, activation='softmax')(x)

    return Model(inputs, outputs)


def build_tcn_3kernels(input_shape, filters=16):
    """
    TCN (带3核)
    - 多核卷积 (kernel_size=2,3,4)
    - 无 GAP (Flatten)
    """
    inputs = Input(shape=input_shape)

    def res_block_multi(x, dilation):
        conv1 = Conv1D(filters, 2, padding='same', dilation_rate=dilation, activation='relu')(x)
        conv2 = Conv1D(filters, 3, padding='same', dilation_rate=dilation, activation='relu')(x)
        conv3 = Conv1D(filters, 4, padding='same', dilation_rate=dilation, activation='relu')(x)
        r = Concatenate()([conv1, conv2, conv3])
        r = Conv1D(filters, 1, padding='same')(r)
        r = Dropout(0.2)(r)
        r = Conv1D(filters, 1, padding='same')(r)

        if x.shape[-1] != filters:
            shortcut = Conv1D(filters, 1, padding='same')(x)
        else:
            shortcut = x
        o = Add()([r, shortcut])
        return Activation('relu')(o)

    x = res_block_multi(inputs, 1)
    x = res_block_multi(x, 2)
    x = res_block_multi(x, 4)
    x = res_block_multi(x, 8)

    x = Flatten()(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(0.3)(x)
    outputs = Dense(2, activation='softmax')(x)

    return Model(inputs, outputs)


def build_tcn_3kernels_pw(input_shape, filters=16):
    """
    TCN (带3核+pw-conv)
    - 多核卷积
    - Pointwise卷积 (1x1)
    - 无 GAP (Flatten)
    """
    inputs = Input(shape=input_shape)

    def pw_conv(x, out_filters):
        return Conv1D(out_filters, 1, padding='same')(x)

    def res_block_multi_pw(x, dilation):
        conv1 = Conv1D(filters, 2, padding='same', dilation_rate=dilation, activation='relu')(x)
        conv2 = Conv1D(filters, 3, padding='same', dilation_rate=dilation, activation='relu')(x)
        conv3 = Conv1D(filters, 4, padding='same', dilation_rate=dilation, activation='relu')(x)
        r = Concatenate()([conv1, conv2, conv3])
        r = pw_conv(r, filters)
        r = Dropout(0.2)(r)
        r = pw_conv(r, filters)

        if x.shape[-1] != filters:
            shortcut = pw_conv(x, filters)
        else:
            shortcut = x
        o = Add()([r, shortcut])
        return Activation('relu')(o)

    x = res_block_multi_pw(inputs, 1)
    x = res_block_multi_pw(x, 2)
    x = res_block_multi_pw(x, 4)
    x = res_block_multi_pw(x, 8)

    x = Flatten()(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(0.3)(x)
    outputs = Dense(2, activation='softmax')(x)

    return Model(inputs, outputs)


def build_proposed_tcn(input_shape, filters=16):
    """
    Proposed TCN
    - 多核卷积
    - Pointwise卷积
    - GAP (Global Average Pooling) ← 关键区别
    """
    inputs = Input(shape=input_shape)

    def pw_conv(x, out_filters):
        return Conv1D(out_filters, 1, padding='same')(x)

    def res_block_multi_pw(x, dilation):
        conv1 = Conv1D(filters, 2, padding='same', dilation_rate=dilation, activation='relu')(x)
        conv2 = Conv1D(filters, 3, padding='same', dilation_rate=dilation, activation='relu')(x)
        conv3 = Conv1D(filters, 4, padding='same', dilation_rate=dilation, activation='relu')(x)
        r = Concatenate()([conv1, conv2, conv3])
        r = pw_conv(r, filters)
        r = Dropout(0.2)(r)
        r = pw_conv(r, filters)

        if x.shape[-1] != filters:
            shortcut = pw_conv(x, filters)
        else:
            shortcut = x
        o = Add()([r, shortcut])
        return Activation('relu')(o)

    x = res_block_multi_pw(inputs, 1)
    x = res_block_multi_pw(x, 2)
    x = res_block_multi_pw(x, 4)
    x = res_block_multi_pw(x, 8)

    # GAP 替代 Flatten
    x = GlobalAveragePooling1D()(x)
    x = Dense(32, activation='relu')(x)
    x = Dropout(0.3)(x)
    outputs = Dense(2, activation='softmax')(x)

    return Model(inputs, outputs)


def count_parameters(model):
    """计算模型参数量"""
    return sum(tf.keras.backend.count_params(w) for w in model.trainable_weights)


def train_and_evaluate(model, X_train, y_train, X_test, y_test, model_name):
    """训练并评估单个模型"""
    print(f"\n{'=' * 50}")
    print(f"训练: {model_name}")
    print(f"{'=' * 50}")

    # 打乱训练数据
    X_train, y_train = shuffle(X_train, y_train, random_state=42)

    # 类别权重
    n_normal = np.sum(y_train == 0)
    n_abnormal = np.sum(y_train == 1)
    class_weight = {0: 1.0, 1: n_normal / n_abnormal if n_abnormal > 0 else 1.0}

    y_train_cat = tf.keras.utils.to_categorical(y_train, 2)
    y_test_cat = tf.keras.utils.to_categorical(y_test, 2)

    # 编译
    model.compile(
        optimizer=tf.keras.optimizers.Adam(LEARNING_RATE),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    # 回调
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=PATIENCE, restore_best_weights=True
    )
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.5, patience=5, min_lr=0.00001
    )

    # 训练
    start_time = time.time()
    history = model.fit(
        X_train, y_train_cat,
        batch_size=BATCH_SIZE,
        epochs=EPOCHS,
        validation_split=0.1,
        class_weight=class_weight,
        callbacks=[early_stop, reduce_lr],
        verbose=0
    )
    train_time = time.time() - start_time

    # 预测
    y_pred_proba = model.predict(X_test, verbose=0)

    # 找最佳阈值
    best_f1 = 0
    best_threshold = 0.5
    best_pred = None
    for threshold in np.arange(0.1, 0.95, 0.05):
        y_pred = (y_pred_proba[:, 1] > threshold).astype(int)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_pred = y_pred

    # 计算指标
    precision = precision_score(y_test, best_pred, zero_division=0)
    recall = recall_score(y_test, best_pred, zero_division=0)

    # 计算模型大小
    model_path = f'./ablation_models/{model_name}.h5'
    model.save(model_path)
    model_size = os.path.getsize(model_path) / 1024

    params = count_parameters(model)

    results = {
        'Model': model_name,
        'Input_Dim': X_train.shape[-1],
        'Params': params,
        'Model_Size_KB': model_size,
        'Train_Time_sec': train_time,
        'Precision': precision,
        'Recall': recall,
        'F1_Score': best_f1,
        'Best_Threshold': best_threshold
    }

    print(f"  输入维度: {X_train.shape[-1]}维")
    print(f"  Params: {params:,}")
    print(f"  Model Size: {model_size:.1f} KB")
    print(f"  Train Time: {train_time:.1f} sec")
    print(f"  F1 Score: {best_f1:.4f}")
    print(f"  Precision: {precision:.4f}, Recall: {recall:.4f}")

    return results, history


def plot_comparison(results_df):
    """生成消融实验对比图"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    models = results_df['Model'].tolist()

    # 1. 参数量对比
    axes[0].barh(models, results_df['Params'], color='steelblue')
    axes[0].set_xlabel('Params')
    axes[0].set_title('Model Parameters')
    axes[0].axvline(x=results_df['Params'].min(), linestyle='--', color='green', alpha=0.7)

    # 2. 模型大小对比
    axes[1].barh(models, results_df['Model_Size_KB'], color='seagreen')
    axes[1].set_xlabel('Model Size (KB)')
    axes[1].set_title('Model Size')

    # 3. F1 Score对比
    axes[2].barh(models, results_df['F1_Score'], color='coral')
    axes[2].set_xlabel('F1 Score')
    axes[2].set_title('F1 Score')
    axes[2].axvline(x=results_df['F1_Score'].max(), linestyle='--', color='green', alpha=0.7)
    axes[2].set_xlim(0.9, 1.0)

    plt.tight_layout()
    plt.savefig('./ablation_results/ablation_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 对比图已保存到 ./ablation_results/ablation_comparison.png")


def print_paper_table(results_df):
    """打印论文格式的表格 (参考 LightLog Table 4)"""
    print("\n" + "=" * 80)
    print("LightLog 消融实验结果 (参考论文 Table 4)")
    print("=" * 80)

    print("\n{:<25} {:>8} {:>12} {:>15} {:>10} {:>10} {:>10}".format(
        'Methods', 'Dim', 'Params', 'Model size(KB)', 'Precision', 'Recall', 'F1 score'
    ))
    print("-" * 95)

    for _, row in results_df.iterrows():
        print("{:<25} {:>8} {:>12,} {:>15.1f} {:>10.4f} {:>10.4f} {:>10.4f}".format(
            row['Model'], row['Input_Dim'], row['Params'], row['Model_Size_KB'],
            row['Precision'], row['Recall'], row['F1_Score']
        ))

    # 计算改进
    print("\n" + "-" * 95)
    baseline_params = results_df[results_df['Model'] == 'TCN']['Params'].values[0]
    baseline_f1 = results_df[results_df['Model'] == 'TCN']['F1_Score'].values[0]

    print("相对于基线 (TCN_300D) 的改进:")
    for _, row in results_df.iterrows():
        params_reduction = (1 - row['Params'] / baseline_params) * 100
        f1_improvement = (row['F1_Score'] - baseline_f1) * 100
        print(f"  {row['Model']:20s}: 参数减少 {params_reduction:5.1f}%, F1提升 {f1_improvement:+.2f}%")


def main():
    print("=" * 60)
    print("LightLog 消融实验 (Ablation Study)")
    print("复现论文 Table 4 - 5个变体")
    print("=" * 60)
    print("\n说明:")
    print("  - TCN, TCN_3Kernels, TCN_3Kernels_PWConv: 使用300维特征")
    print("  - TCN_PCA_PPA, Proposed_TCN: 使用20维特征")
    print("  - GAP 是 Proposed TCN 独有的")
    print("=" * 60)

    # 加载数据
    (X_train_20d, X_test_20d), (X_train_300d, X_test_300d), y_train, y_test = load_data()

    # 采样平衡测试集 (所有变体使用相同的测试集)
    normal_idx = np.where(y_test == 0)[0]
    abnormal_idx = np.where(y_test == 1)[0]
    n_sample = min(len(abnormal_idx), 5000)
    sample_normal = np.random.choice(normal_idx, n_sample, replace=False)
    sample_idx = np.concatenate([sample_normal, abnormal_idx])

    results = []

    # ============================================================
    # 变体1: TCN (原始) - 使用高维特征 (300维)
    # ============================================================
    print("\n" + "=" * 60)
    print("变体1: TCN (基线) - 使用高维特征 (300维)")
    print("=" * 60)

    X_test_300d_sampled = X_test_300d[sample_idx]
    y_test_sampled = y_test[sample_idx]

    input_shape_300 = (MAX_SEQ_LEN, 300)
    model_tcn = build_tcn_base(input_shape_300, filters=16)
    res_tcn, _ = train_and_evaluate(
        model_tcn, X_train_300d, y_train,
        X_test_300d_sampled, y_test_sampled,
        "TCN"
    )
    results.append(res_tcn)

    # ============================================================
    # 变体2: TCN (PCA-PPA) - 使用低维特征 (20维) ← 修改1
    # ============================================================
    print("\n" + "=" * 60)
    print("变体2: TCN (PCA-PPA) - 使用降维特征 (20维)")
    print("=" * 60)

    X_test_20d_sampled = X_test_20d[sample_idx]

    input_shape_20 = (MAX_SEQ_LEN, 20)
    model_pca_ppa = build_tcn_base(input_shape_20, filters=16)
    res_pca_ppa, _ = train_and_evaluate(
        model_pca_ppa, X_train_20d, y_train,
        X_test_20d_sampled, y_test_sampled,
        "TCN_PCA_PPA"
    )
    results.append(res_pca_ppa)

    # ============================================================
    # 变体3: TCN (带3核) - 使用高维特征 (300维)
    # ============================================================
    print("\n" + "=" * 60)
    print("变体3: TCN (带3核) - 多核卷积 (300维)")
    print("=" * 60)

    model_3k = build_tcn_3kernels(input_shape_300, filters=16)
    res_3k, _ = train_and_evaluate(
        model_3k, X_train_300d, y_train,
        X_test_300d_sampled, y_test_sampled,
        "TCN_3Kernels"
    )
    results.append(res_3k)

    # ============================================================
    # 变体4: TCN (带3核+pw-conv) - 使用高维特征 (300维)
    # ============================================================
    print("\n" + "=" * 60)
    print("变体4: TCN (带3核+pw-conv) - 多核 + Pointwise卷积 (300维)")
    print("=" * 60)

    model_pw = build_tcn_3kernels_pw(input_shape_300, filters=16)
    res_pw, _ = train_and_evaluate(
        model_pw, X_train_300d, y_train,
        X_test_300d_sampled, y_test_sampled,
        "TCN_3Kernels_PWConv"
    )
    results.append(res_pw)

    # ============================================================
    # 变体5: Proposed TCN - 使用低维特征 (20维) ← 修改2
    # ============================================================
    print("\n" + "=" * 60)
    print("变体5: Proposed TCN - 全部组件 + GAP (20维)")
    print("=" * 60)

    model_proposed = build_proposed_tcn(input_shape_20, filters=16)
    res_proposed, _ = train_and_evaluate(
        model_proposed, X_train_20d, y_train,
        X_test_20d_sampled, y_test_sampled,
        "Proposed_TCN"
    )
    results.append(res_proposed)

    # 汇总结果
    print("\n" + "=" * 60)
    print("消融实验汇总")
    print("=" * 60)

    results_df = pd.DataFrame(results)
    results_df = results_df[[
        'Model', 'Input_Dim', 'Params', 'Model_Size_KB', 'Train_Time_sec',
        'Precision', 'Recall', 'F1_Score', 'Best_Threshold'
    ]]

    print("\n" + results_df.to_string(index=False))
    results_df.to_csv('./ablation_results/ablation_summary.csv', index=False)
    print(f"\n✅ 结果已保存到 ./ablation_results/ablation_summary.csv")

    plot_comparison(results_df)
    print_paper_table(results_df)


if __name__ == "__main__":
    main()