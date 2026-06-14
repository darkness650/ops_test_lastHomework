import json
import pandas as pd


def flatten_jsonl(file_path, output_csv):
    """
    将 JSONL 展平为单条日志（参考 BGL 的 01_handle BGL dataset.py）
    输出格式：group_id, label, log_content
    不改变原始顺序，不打乱
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
    print(f"展平 {len(df)} 条日志 -> {output_csv}")
    return df


if __name__ == "__main__":
    # 展平为单条日志 CSV（用于 step2 抽模板）
    flatten_jsonl('./data/train_dataset.jsonl', 'train_flat.csv')
    flatten_jsonl('./data/test_dataset.jsonl', 'test_flat.csv')
