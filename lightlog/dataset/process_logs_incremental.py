import json
import os
from datetime import datetime

# 配置
LOGS_DIR = r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\logs\test-normal"
OUTPUT_DIR = r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\processed_datasets"
GROUP_SIZE = 20
CHUNK_SIZE = 50000


def extract_timestamp_str(log_entry):
    """从日志条目中提取时间戳字符串"""
    try:
        log_content = json.loads(log_entry.get('log', '{}'))
        ts = log_content.get('timestamp', '')
        if ts:
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts).isoformat()
            return str(ts)
    except:
        pass

    try:
        ts = log_entry.get('timestamp', '')
        if ts:
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts).isoformat()
            return str(ts)
    except:
        pass

    return ''


def is_anomaly(log_entry):
    """判断日志是否为异常"""
    try:
        log_content = json.loads(log_entry.get('log', '{}'))
        severity = log_content.get('severity', '').lower()

        if severity in ['error', 'critical', 'fatal', 'panic', 'emerg', 'alert']:
            return True

        status = log_content.get('http.resp.status', 0)
        if isinstance(status, int) and status >= 500:
            return True

        message = log_content.get('message', '').lower()
        if any(kw in message for kw in ['error', 'fail', 'exception', 'crash', 'fatal']):
            return True

    except:
        pass

    return False


def get_last_group_id(file_path):
    """获取数据集中最后一组的 group_id，文件不存在则返回 0"""
    if not os.path.exists(file_path):
        return 0
    try:
        with open(file_path, 'rb') as f:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            last_line = f.readline().decode('utf-8')
        last_entry = json.loads(last_line)
        return last_entry.get('group_id', 0)
    except:
        return 0


def main():
    NEW_LOG_DIR = LOGS_DIR  # 新采集的数据目录

    if not os.path.isdir(NEW_LOG_DIR):
        print(f"目录不存在: {NEW_LOG_DIR}")
        return

    print(f"增量处理日志目录: {NEW_LOG_DIR}")

    # 收集新目录下所有日志文件
    log_files = []
    for root, dirs, files in os.walk(NEW_LOG_DIR):
        for file in files:
            if file.endswith('.log'):
                log_files.append(os.path.join(root, file))

    if not log_files:
        print("未找到 .log 文件")
        return

    print(f"找到 {len(log_files)} 个日志文件")

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    normal_file = os.path.join(OUTPUT_DIR, 'normal_dataset.jsonl')
    anomaly_file = os.path.join(OUTPUT_DIR, 'anomaly_dataset.jsonl')

    # 获取已有数据集的最后一个 group_id，确保增量追加时 id 不冲突
    last_normal_id = get_last_group_id(normal_file)
    last_anomaly_id = get_last_group_id(anomaly_file)
    start_group_id = max(last_normal_id, last_anomaly_id) + 1
    batch_num = start_group_id - 1  # 后续循环中先 +1 再使用

    print(f"已有 normal_dataset 最大 group_id: {last_normal_id}")
    print(f"已有 anomaly_dataset 最大 group_id: {last_anomaly_id}")
    print(f"新数据起始 group_id: {start_group_id}")

    # 流式处理，块内排序后直接分组写入（追加模式）
    print("\n开始增量处理...")
    total_lines = 0
    skipped = 0
    normal_count = 0
    anomaly_count = 0
    batch = []
    buffer = []

    with open(normal_file, 'a', encoding='utf-8') as f_normal, \
         open(anomaly_file, 'a', encoding='utf-8') as f_anomaly:

        for idx, file_path in enumerate(log_files, 1):
            print(f"处理文件 {idx}/{len(log_files)}: {os.path.basename(file_path)}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                log_entry = json.loads(line)
                                ts = extract_timestamp_str(log_entry)
                                anomaly = is_anomaly(log_entry)
                                buffer.append((ts, anomaly, log_entry))
                                total_lines += 1

                                if len(buffer) >= CHUNK_SIZE:
                                    # 块内排序
                                    buffer.sort(key=lambda x: x[0])

                                    # 分组写入
                                    for item_ts, item_anomaly, item_log in buffer:
                                        batch.append({
                                            'timestamp': item_ts,
                                            'anomaly': item_anomaly,
                                            'log': item_log
                                        })

                                        if len(batch) >= GROUP_SIZE:
                                            batch_num += 1
                                            has_anomaly = any(item['anomaly'] for item in batch)

                                            group_data = {
                                                'group_id': batch_num,
                                                'label': 1 if has_anomaly else 0,
                                                'start_time': batch[0]['timestamp'],
                                                'end_time': batch[-1]['timestamp'],
                                                'logs': [item['log'] for item in batch]
                                            }

                                            if has_anomaly:
                                                f_anomaly.write(json.dumps(group_data, ensure_ascii=False) + '\n')
                                                anomaly_count += 1
                                            else:
                                                f_normal.write(json.dumps(group_data, ensure_ascii=False) + '\n')
                                                normal_count += 1

                                            batch = []

                                    buffer = []

                                    if batch_num % 10000 == 0 and batch_num > 0:
                                        print(f"  已处理 {batch_num} 组...")
                            except json.JSONDecodeError:
                                skipped += 1
                                continue
            except Exception as e:
                print(f"读取文件 {file_path} 时出错: {e}")

            if total_lines % 500000 == 0 and total_lines > 0:
                print(f"  已读取 {total_lines} 条...")

        # 处理剩余数据
        if buffer:
            buffer.sort(key=lambda x: x[0])
            for item_ts, item_anomaly, item_log in buffer:
                batch.append({
                    'timestamp': item_ts,
                    'anomaly': item_anomaly,
                    'log': item_log
                })

        # 处理最后一批
        while len(batch) >= GROUP_SIZE:
            batch_num += 1
            has_anomaly = any(item['anomaly'] for item in batch[:GROUP_SIZE])

            group_data = {
                'group_id': batch_num,
                'label': 1 if has_anomaly else 0,
                'start_time': batch[0]['timestamp'],
                'end_time': batch[GROUP_SIZE - 1]['timestamp'],
                'logs': [item['log'] for item in batch[:GROUP_SIZE]]
            }

            if has_anomaly:
                f_anomaly.write(json.dumps(group_data, ensure_ascii=False) + '\n')
                anomaly_count += 1
            else:
                f_normal.write(json.dumps(group_data, ensure_ascii=False) + '\n')
                normal_count += 1

            batch = batch[GROUP_SIZE:]

    # 输出统计信息
    normal_size = os.path.getsize(normal_file)
    anomaly_size = os.path.getsize(anomaly_file)

    print("\n" + "=" * 50)
    print("增量处理完成！统计信息：")
    print("=" * 50)
    print(f"本次处理日志数: {total_lines}")
    print(f"跳过: {skipped}")
    print(f"本次新增组数: {normal_count + anomaly_count}")
    print(f"  - 新增正常组: {normal_count}")
    print(f"  - 新增异常组: {anomaly_count}")
    print(f"数据集当前总大小:")
    print(f"  - normal_dataset: {normal_size / (1024 * 1024):.2f} MB")
    print(f"  - anomaly_dataset: {anomaly_size / (1024 * 1024):.2f} MB")
    print(f"group_id 范围: {start_group_id} ~ {batch_num}")
    print("=" * 50)


if __name__ == "__main__":
    main()