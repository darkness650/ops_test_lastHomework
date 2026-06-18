import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 检查训练集
train_count = 0
train_normal = 0
train_abnormal = 0
with open('./data/train_dataset.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        group = json.loads(line)
        train_count += 1
        if group.get('label', 0) == 0:
            train_normal += 1
        else:
            train_abnormal += 1

print(f"训练集: {train_count} 个序列")
print(f"  正常: {train_normal}, 异常: {train_abnormal}")

# 检查测试集
test_count = 0
test_normal = 0
test_abnormal = 0
with open('./data/test_dataset.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        group = json.loads(line)
        test_count += 1
        if group.get('label', 0) == 0:
            test_normal += 1
        else:
            test_abnormal += 1

print(f"\n测试集: {test_count} 个序列")
print(f"  正常: {test_normal}, 异常: {test_abnormal}")
