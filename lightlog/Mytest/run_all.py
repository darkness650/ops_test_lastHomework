import subprocess
import os

print("="*60)
print("LightLog Boutique 数据集完整实验")
print("="*60)

# 确保目录存在
os.makedirs('./data', exist_ok=True)
os.makedirs('./model', exist_ok=True)
os.makedirs('./result', exist_ok=True)

# 检查输入文件
if not os.path.exists('./data/train_dataset.jsonl'):
    print("❌ 错误: 找不到 ./data/train_dataset.jsonl 文件！")
    exit(1)
if not os.path.exists('./data/test_dataset.jsonl'):
    print("❌ 错误: 找不到 ./data/test_dataset.jsonl 文件！")
    exit(1)

# 步骤1: 解析 JSON 日志
print("\n" + "="*60)
print("步骤1: 解析 JSON 日志")
print("="*60)
subprocess.run(["python", "step1_parse_logs.py"])

# 步骤2: 提取日志模板
print("\n" + "="*60)
print("步骤2: 提取日志模板")
print("="*60)
subprocess.run(["python", "step2_extract_templates.py"])

# 步骤3: Word2Vec + PCA-PPA
print("\n" + "="*60)
print("步骤3: Word2Vec 训练 + PCA-PPA 降维")
print("="*60)
subprocess.run(["python", "step3_word2vec_pca_fixed.py"])

# 步骤4: 训练模型
print("\n" + "="*60)
print("步骤4: 训练 LightLog 模型")
print("="*60)
subprocess.run(["python", "step4_train.py"])

print("\n" + "="*60)
print("✅ 实验完成！")
print("="*60)
print("\n结果文件:")
print("  - ./model/boutique_weights.h5 (模型权重)")
print("  - ./result/result_boutique.csv (评估结果)")