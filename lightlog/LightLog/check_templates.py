import pandas as pd
import json
from collections import Counter
import os

# 切换到 Mytest 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 加载模板化数据
train_df = pd.read_csv('train_templated.csv')

# 分别统计正常和异常的模板分布
normal_df = train_df[train_df['label'] == 0]
abnormal_df = train_df[train_df['label'] == 1]

print(f"正常日志: {len(normal_df)} 条")
print(f"异常日志: {len(abnormal_df)} 条")

# 正常日志的 top 10 模板
normal_templates = normal_df['template_id'].value_counts().head(10)
print("\n正常日志 Top 10 模板:")
for tid, count in normal_templates.items():
    print(f"  ID={tid}: {count} 次")

# 异常日志的 top 10 模板
abnormal_templates = abnormal_df['template_id'].value_counts().head(10)
print("\n异常日志 Top 10 模板:")
for tid, count in abnormal_templates.items():
    print(f"  ID={tid}: {count} 次")

# 检查模板重叠
normal_tids = set(normal_df['template_id'].unique())
abnormal_tids = set(abnormal_df['template_id'].unique())
overlap = normal_tids & abnormal_tids
print(f"\n正常独有模板: {len(normal_tids - abnormal_tids)}")
print(f"异常独有模板: {len(abnormal_tids - normal_tids)}")
print(f"重叠模板: {len(overlap)}")

# 加载模板字典查看内容
with open('template_to_id.json', 'r') as f:
    template_to_id = json.load(f)

# 查看异常独有模板
abnormal_only = abnormal_tids - normal_tids
if abnormal_only:
    print(f"\n异常独有模板 (共 {len(abnormal_only)} 个):")
    for tid in list(abnormal_only)[:5]:
        for t, t_id in template_to_id.items():
            if t_id == tid:
                print(f"  ID={tid}: {t[:150]}")
                break

# 检查序列级别的模板分布
print("\n\n=== 序列级别分析 ===")
seq_df = pd.read_csv('train_templated.csv')
groups = seq_df.groupby('group_id')

normal_seq_templates = []
abnormal_seq_templates = []

for gid, gdf in groups:
    label = gdf['label'].iloc[0]
    tids = gdf['template_id'].tolist()
    if label == 0:
        normal_seq_templates.append(Counter(tids))
    else:
        abnormal_seq_templates.append(Counter(tids))

print(f"正常序列数: {len(normal_seq_templates)}")
print(f"异常序列数: {len(abnormal_seq_templates)}")
