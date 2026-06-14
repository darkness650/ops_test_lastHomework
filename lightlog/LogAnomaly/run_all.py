"""
run_all.py - LogAnomaly 完整实验流程
一键运行从日志解析到模型评估的所有步骤
"""
import subprocess
import os
import sys
import time

# 切换到脚本所在目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

STEPS = [
    ("Step 1: 日志解析", "step1_parse_logs.py"),
    ("Step 2: 模板提取", "step2_extract_templates.py"),
    ("Step 3: Template2Vec", "step3_template2vec.py"),
    ("Step 4: 构建序列", "step4_build_sequences.py"),
    ("Step 5: LSTM 训练", "step5_train_lstm.py"),
    ("Step 6: 模型评估", "step6_evaluate.py"),
]


def run_step(name, script):
    print("\n" + "=" * 70)
    print(f"  {name}")
    print("=" * 70)
    
    start = time.time()
    result = subprocess.run(
        [sys.executable, script],
        capture_output=False,
        text=True
    )
    elapsed = time.time() - start
    
    if result.returncode != 0:
        print(f"\n{'='*70}")
        print(f"  错误: {name} 执行失败 (exit code: {result.returncode})")
        print(f"{'='*70}")
        return False
    
    print(f"\n{name} 完成. 耗时: {elapsed:.1f}s")
    return True


if __name__ == "__main__":
    total_start = time.time()
    
    print("=" * 70)
    print("  LogAnomaly 实验 (IJCAI-19)")
    print("  基于 LSTM 的日志异常检测")
    print("=" * 70)
    print()
    print("论文核心架构:")
    print("  1. FT-Tree 日志解析 -> 模板提取")
    print("  2. Template2Vec: Word2Vec + WordNet同义词/反义词")
    print("  3. PCA-PPA 语义向量降维")
    print("  4. 2层 LSTM (128 units) 顺序 + 定量异常检测")
    print()
    
    # 检查数据文件
    if not os.path.exists('./data/train_dataset.jsonl'):
        print("错误: 找不到 ./data/train_dataset.jsonl")
        sys.exit(1)
    if not os.path.exists('./data/test_dataset.jsonl'):
        print("错误: 找不到 ./data/test_dataset.jsonl")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs('./data', exist_ok=True)
    os.makedirs('./saved_models', exist_ok=True)
    os.makedirs('./result', exist_ok=True)
    
    # 运行所有步骤
    for name, script in STEPS:
        if not run_step(name, script):
            print(f"\n实验中断于: {name}")
            sys.exit(1)
    
    total_elapsed = time.time() - total_start
    
    print("\n" + "=" * 70)
    print("  LogAnomaly 实验完成!")
    print(f"  总耗时: {total_elapsed:.1f}s")
    print("=" * 70)
    print("\n输出文件:")
    print("  train_flat.csv / test_flat.csv          - 展平的日志")
    print("  train_templated.csv / test_templated.csv - 带模板ID的日志")
    print("  template_to_id.json                     - 模板字典")
    print("  data/loganomaly_semantic_vec.json       - 语义向量")
    print("  data/X_*.npy / y_*.npy                 - 训练/测试数据")
    print("  saved_models/loganomaly_lstm.pth        - 训练好的模型")
    print("  result/loganomaly_results.json           - 评估结果")