"""
Check training and test data distribution
"""
import json
from collections import Counter

train_file = r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\processed_datasets\train_dataset.jsonl"
test_file = r"d:\code\python\paper\LightLog\BGL&HDFS dataset and Methods of data processing\mylog\processed_datasets\test_dataset.jsonl"

def check_dataset(filepath, name):
    print(f"\n{'='*60}")
    print(f"Checking {name}: {filepath}")
    print(f"{'='*60}")
    
    labels = []
    seq_lengths = []
    templates = []
    
    with open(filepath, 'r') as f:
        for line in f:
            data = json.loads(line)
            labels.append(data['label'])
            # Support both 'sequence' and 'logs' keys
            seq = data.get('sequence', data.get('logs', []))
            seq_lengths.append(len(seq))
            if isinstance(seq[0], dict):
                # Extract template if it's a log dict
                templates.extend([log.get('template', log.get('log', '')) for log in seq])
            else:
                templates.extend(seq)
    
    label_counts = Counter(labels)
    print(f"Total samples: {len(labels)}")
    print(f"Label distribution: {dict(label_counts)}")
    print(f"  Normal (0): {label_counts[0]} ({label_counts[0]/len(labels)*100:.2f}%)")
    print(f"  Anomaly (1): {label_counts[1]} ({label_counts[1]/len(labels)*100:.2f}%)")
    print(f"\nSequence length stats:")
    print(f"  Min: {min(seq_lengths)}")
    print(f"  Max: {max(seq_lengths)}")
    print(f"  Mean: {sum(seq_lengths)/len(seq_lengths):.2f}")
    
    unique_templates = set(templates)
    print(f"\nUnique templates: {len(unique_templates)}")
    
    return labels, seq_lengths, set(templates)

train_labels, train_seq_lens, train_templates = check_dataset(train_file, "TRAIN")
test_labels, test_seq_lens, test_templates = check_dataset(test_file, "TEST")

# Check overlap
overlap = train_templates & test_templates
print(f"\n{'='*60}")
print(f"Template overlap analysis:")
print(f"{'='*60}")
print(f"Train unique templates: {len(train_templates)}")
print(f"Test unique templates: {len(test_templates)}")
print(f"Overlap: {len(overlap)}")
print(f"  Overlap rate (test): {len(overlap)/len(test_templates)*100:.2f}%")
print(f"  Overlap rate (train): {len(overlap)/len(train_templates)*100:.2f}%")

# Check label distribution similarity
train_anomaly_rate = sum(train_labels) / len(train_labels)
test_anomaly_rate = sum(test_labels) / len(test_labels)
print(f"\nAnomaly rate:")
print(f"  Train: {train_anomaly_rate*100:.4f}%")
print(f"  Test: {test_anomaly_rate*100:.4f}%")
