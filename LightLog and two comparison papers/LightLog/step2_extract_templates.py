import re
import pandas as pd
from collections import Counter
import json


def normalize_log(log):
    """将日志内容归一化，变量替换为通配符"""
    if pd.isna(log) or not log:
        return ""

    log = str(log)
    if len(log) < 5:
        return ""

    log = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '<UUID>', log)
    log = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TIME>', log)
    log = re.sub(r'\d+\.\d+\.\d+\.\d+', '<IP>', log)
    log = re.sub(r'\b\d+\b', '<NUM>', log)
    log = re.sub(r'\d{2}:\d{2}:\d{2}', '<TIME>', log)
    log = re.sub(r'\d+ms', '<TIME>ms', log)
    log = re.sub(r'time[=:]\s*\d+', 'time=<NUM>', log)
    log = re.sub(r'\s+', ' ', log).strip()

    return log[:300]


def extract_templates(df, min_support=2):
    """
    单条日志抽模板（参考 BGL 的 structure_bgl.py）
    每条日志对应一个模板 ID
    """
    print("提取日志模板（单条日志方式）...")
    
    template_counter = Counter()
    
    for _, row in df.iterrows():
        norm = normalize_log(row['log_content'])
        if norm:
            template_counter[norm] += 1
    
    template_to_id = {}
    for template, count in template_counter.items():
        if count >= min_support and template:
            template_to_id[template] = len(template_to_id) + 1
    
    print(f"唯一模板数: {len(template_to_id)}")
    
    df['template_id'] = df['log_content'].apply(
        lambda x: template_to_id.get(normalize_log(x), 0)
    )
    
    total_logs = len(df)
    covered = sum(1 for _, row in df.iterrows() if normalize_log(row['log_content']) in template_to_id)
    print(f"模板覆盖率: {covered}/{total_logs} = {covered / total_logs * 100:.1f}%")
    
    return df, template_to_id


if __name__ == "__main__":
    print("=" * 60)
    print("步骤2: 日志模板提取（单条日志方式）")
    print("=" * 60)

    print("\n加载展平后的单条日志...")
    train_df = pd.read_csv('train_flat.csv')
    test_df = pd.read_csv('test_flat.csv')

    print(f"训练集: {len(train_df)} 条日志")
    print(f"测试集: {len(test_df)} 条日志")

    # 合并训练集和测试集一起抽模板（参考 BGL 的做法）
    print("\n合并训练集和测试集，统一抽取模板...")
    combined_df = pd.concat([train_df, test_df], ignore_index=True)
    print(f"合并后: {len(combined_df)} 条日志")

    # 从合并数据中抽取模板
    combined_df, template_to_id = extract_templates(combined_df, min_support=2)

    # 拆分回训练集和测试集
    train_df = combined_df.iloc[:len(train_df)].copy()
    test_df = combined_df.iloc[len(train_df):].copy()

    print(f"\n训练集模板化: {len(train_df)} 条日志")
    print(f"测试集模板化: {len(test_df)} 条日志")

    print("\n保存结果...")
    train_df.to_csv('train_templated.csv', index=False)
    test_df.to_csv('test_templated.csv', index=False)

    with open('template_to_id.json', 'w') as f:
        json.dump(template_to_id, f)
    print("✅ 模板字典已保存")

    print("\n✅ 完成！")
