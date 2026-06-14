import pandas as pd
import numpy as np
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 检查训练标签
train_label = pd.read_csv('./data/boutique_train_label.csv', header=None)
print("训练标签分布:")
print(train_label[0].value_counts())
print(f"异常比例: {train_label[0].mean():.4f}")

# 检查测试标签
test_label = pd.read_csv('./data/boutique_test_label.csv', header=None)
print("\n测试标签分布:")
print(test_label[0].value_counts())
print(f"异常比例: {test_label[0].mean():.4f}")

# 检查训练数据形状
train_data = pd.read_csv('./data/boutique_train_data.csv', header=None)
print(f"\n训练数据形状: {train_data.shape}")
print(f"第一条数据样例: {str(train_data.iloc[0, 0])[:100]}...")
