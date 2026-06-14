"""
Step 1: Log Parsing - 将 JSONL 格式日志展平为单条日志 CSV
参考 LogAnomaly 论文的日志解析步骤，使用正则表达式预先归一化
"""
import json
import pandas as pd
import os


def flatten_jsonl(file_path, output_csv):
    """
    将 JSONL 每条 group 展平为单条日志记录
    输出格式：group_id, label, log_content
    """
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            group = json.loads(line)
            label = group.get('label', 0)
            group_id = group.get('group_id', 0)
            logs = group.get('logs', [])
            
            for log_entry in logs:
                raw_log = log_entry.get('log', '').strip()
                # 尝试解析 JSON 格式的 log，提取 message 字段
                try:
                    log_obj = json.loads(raw_log)
                    message = log_obj.get('message', raw_log)
                except:
                    message = raw_log
                
                records.append({
                    'group_id': group_id,
                    'label': label,
                    'log_content': message
                })

    df = pd.DataFrame(records)
    df.to_csv(output_csv, index=False)
    print(f"[Step1] 展平 {len(df)} 条日志 -> {output_csv}")
    return df


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
    flatten_jsonl(
        os.path.join(data_dir, 'train_dataset.jsonl'),
        'train_flat.csv'
    )
    flatten_jsonl(
        os.path.join(data_dir, 'test_dataset.jsonl'),
        'test_flat.csv'
    )
    print("[Step1] 日志解析完成.")