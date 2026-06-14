"""
Step 2: Log Template Extraction - 日志模板提取
参考 LogAnomaly 论文使用 FT-Tree 提取模板，这里用正则归一化实现
将每条日志中的变量替换为通配符，相同模式归为同一模板
"""
import re
import pandas as pd
from collections import Counter
import json


def normalize_log(log):
    """
    日志归一化：将变量替换为通配符 <*>
    参考 LogAnomaly 的 FT-Tree 方法，将 IP、数字、UUID、路径等替换为通配符
    """
    if pd.isna(log) or not log:
        return ""
    log = str(log)
    if len(log) < 3:
        return ""

    # UUID: 8-4-4-4-12
    log = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '<*>', log)
    # ISO timestamp: 2026-06-06T13:49:08.717631908Z
    log = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\.\d]*Z?', '<*>', log)
    # IP address
    log = re.sub(r'\d+\.\d+\.\d+\.\d+', '<*>', log)
    # Pure numbers
    log = re.sub(r'\b\d+\b', '<*>', log)
    # Hex strings (8+ hex chars)
    log = re.sub(r'\b[a-f0-9]{8,}\b', '<*>', log)
    # Session IDs, request IDs etc.
    log = re.sub(r'session=\S+', 'session=<*>', log)
    log = re.sub(r'userId=\S+', 'userId=<*>', log)
    log = re.sub(r'productId=\S+', 'productId=<*>', log)
    log = re.sub(r'quantity=\d+', 'quantity=<*>', log)
    # URLs
    log = re.sub(r'http[s]?://\S+', '<*>', log)
    # port numbers
    log = re.sub(r':\d{2,5}', ':<*>', log)
    # Collapse whitespace
    log = re.sub(r'\s+', ' ', log).strip()
    
    return log[:500]


def extract_templates(df, min_support=2):
    """
    从展平的日志 DataFrame 中提取模板
    返回带 template_id 的 DataFrame 和 template_to_id 映射
    """
    print("[Step2] 提取日志模板...")
    
    template_counter = Counter()
    log_to_template = {}
    
    for _, row in df.iterrows():
        norm = normalize_log(row['log_content'])
        log_to_template[row.name] = norm
        if norm:
            template_counter[norm] += 1
    
    # 只保留出现次数 >= min_support 的模板
    template_to_id = {}
    for template, count in template_counter.items():
        if count >= min_support and len(template) > 2:
            template_to_id[template] = len(template_to_id) + 1  # 从1开始，0留给padding
    
    print(f"[Step2] 唯一模板数: {len(template_to_id)}")
    
    # 分配 template_id
    df['template_id'] = df.index.map(
        lambda idx: template_to_id.get(log_to_template.get(idx, ''), 0)
    )
    
    # 显示模板分布
    covered = (df['template_id'] > 0).sum()
    print(f"[Step2] 模板覆盖率: {covered}/{len(df)} = {covered/len(df)*100:.1f}%")
    
    # 打印 top-10 模板
    print("\n[Step2] Top-10 模板:")
    for i, (template, count) in enumerate(template_counter.most_common(10)):
        tid = template_to_id.get(template, 0)
        print(f"  T{tid}: (出现{count}次) {template[:120]}...")
    
    return df, template_to_id


if __name__ == "__main__":
    print("=" * 60)
    print("Step 2: 日志模板提取")
    print("=" * 60)
    
    # 加载展平后的日志
    train_df = pd.read_csv('train_flat.csv')
    test_df = pd.read_csv('test_flat.csv')
    print(f"训练集: {len(train_df)} 条日志")
    print(f"测试集: {len(test_df)} 条日志")
    
    # 合并训练集和测试集统一提取模板
    combined_df = pd.concat([train_df, test_df], ignore_index=True)
    print(f"合并后: {len(combined_df)} 条日志")
    
    # 提取模板
    combined_df, template_to_id = extract_templates(combined_df, min_support=2)
    
    # 拆分回训练集和测试集
    train_df = combined_df.iloc[:len(train_df)].copy()
    test_df = combined_df.iloc[len(train_df):].copy()
    
    print(f"\n训练集带模板: {len(train_df)} 条, 测试集带模板: {len(test_df)} 条")
    
    # 保存
    train_df.to_csv('train_templated.csv', index=False)
    test_df.to_csv('test_templated.csv', index=False)
    with open('template_to_id.json', 'w', encoding='utf-8') as f:
        json.dump(template_to_id, f, ensure_ascii=False)
    print("[Step2] 模板字典已保存到 template_to_id.json")
    print("[Step2] 完成.")