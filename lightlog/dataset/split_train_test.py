import json
import os
import random

OUTPUT_DIR = r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\processed_datasets"
NORMAL_FILE = os.path.join(OUTPUT_DIR, 'normal_dataset.jsonl')
ANOMALY_FILE = os.path.join(OUTPUT_DIR, 'anomaly_dataset.jsonl')
TRAIN_FILE = os.path.join(OUTPUT_DIR, 'train_dataset.jsonl')
TEST_FILE = os.path.join(OUTPUT_DIR, 'test_dataset.jsonl')

print("开始划分训练集和测试集...")

# 流式读取正常数据集
print("读取正常数据集...")
normal_data = []
with open(NORMAL_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        normal_data.append(line.strip())

normal_total = len(normal_data)
print(f"正常数据集共 {normal_total} 组")

# 流式读取异常数据集
print("读取异常数据集...")
anomaly_data = []
with open(ANOMALY_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        anomaly_data.append(line.strip())

anomaly_total = len(anomaly_data)
print(f"异常数据集共 {anomaly_total} 组")

# 随机打乱
print("随机打乱...")
random.seed(42)
random.shuffle(normal_data)
random.shuffle(anomaly_data)

# 划分
train_normal = normal_data[:8000]
test_normal = normal_data[8000:]

# 测试集异常 = 剩余正常测试集的2.9%
test_anomaly_count = int(len(test_normal) * 0.029)
train_anomaly = anomaly_data[:8000]
test_anomaly = anomaly_data[8000:8000+test_anomaly_count]

print(f"\n训练集: 正常 {len(train_normal)} 组, 异常 {len(train_anomaly)} 组")
print(f"测试集: 正常 {len(test_normal)} 组, 异常 {len(test_anomaly)} 组")


# 写入训练集
print(f"\n保存训练集到 {TRAIN_FILE}...")
train_all = train_normal + train_anomaly
random.shuffle(train_all)
with open(TRAIN_FILE, 'w', encoding='utf-8') as f:
    for line in train_all:
        f.write(line + '\n')

# 写入测试集
print(f"保存测试集到 {TEST_FILE}...")
test_all = test_normal + test_anomaly
random.shuffle(test_all)
with open(TEST_FILE, 'w', encoding='utf-8') as f:
    for line in test_all:
        f.write(line + '\n')

# 统计大小
train_size = os.path.getsize(TRAIN_FILE)
test_size = os.path.getsize(TEST_FILE)

print("\n" + "="*50)
print("划分完成！统计信息：")
print("="*50)
print(f"训练集: {len(train_normal) + len(train_anomaly)} 组 ({train_size / (1024*1024):.2f} MB)")
print(f"  - 正常: {len(train_normal)} 组")
print(f"  - 异常: {len(train_anomaly)} 组")
print(f"测试集: {len(test_normal) + len(test_anomaly)} 组 ({test_size / (1024*1024):.2f} MB)")
print(f"  - 正常: {len(test_normal)} 组")
print(f"  - 异常: {len(test_anomaly)} 组")
print(f"\n文件保存位置: {OUTPUT_DIR}")
print("="*50)
