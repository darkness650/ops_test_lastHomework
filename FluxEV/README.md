# FluxEV

本项目是论文["FluxEV: A Fast and Effective Unsupervised Framework for Time-Series Anomaly Detection"](https://dl.acm.org/doi/10.1145/3437963.3441823)的重构版实现。论文发表于 WSDM 2021。

Flux 表示波动，EV 表示极值。

## 项目结构

代码已经拆分为 `fluxev/` 包：

- `main.py`：本地启动脚本，转发到真正的 CLI。
- `fluxev/cli.py`：唯一命令行入口模块。
- `fluxev/detector.py`：FluxEV 特征提取与流式检测逻辑。
- `fluxev/spot.py`：SPOT 检测器与 GPD 参数估计。
- `fluxev/datasets.py`：Yahoo 与 KPI 数据集运行流程。
- `fluxev/preprocessing.py`：KPI 时间戳补全、缺失值填充与标准化。
- `fluxev/evaluation.py`：延迟容忍评估策略。
- `fluxev/plotting.py`：绘图辅助函数。

建议在单独的VSCode窗口打开整个项目，以获得最佳的编辑和类型检查体验。如果在`ops_test_lastHomework`窗口编辑，会遇到导入错误和类型检查失效的问题，且运行前需要先cd到`FluxEV`目录（不是`FluxEV/fluxev`）。

运行：

```bash
uv run -m fluxev.cli ...
```

或：

```bash
uv run main.py ...
```

## 环境准备

项目依赖写在 `pyproject.toml` 中，使用 `uv` 同步环境：

```bash
uv sync --dev
```

`pyright` 已作为开发依赖加入，用于模拟 Pylance 的类型检查：

```bash
uv run pyright
```

## 数据准备

### KPI 数据集

下载 AIOps/KPI 原始文件，并放到：

```text
data/AIOps/phase2_train.csv
data/AIOps/phase2_ground_truth.hdf
```

参考地址：
<https://github.com/NetManAIOps/KPI-Anomaly-Detection/tree/master/Finals_dataset>

### Yahoo 数据集

下载 Yahoo Webscope S5 benchmark，并按下面结构放置 CSV：

```text
data/Yahoo/A1Benchmark/*.csv
data/Yahoo/A2Benchmark/*.csv
data/Yahoo/A3Benchmark/*.csv
data/Yahoo/A4Benchmark/*.csv
```

参考地址：
<https://webscope.sandbox.yahoo.com/catalog.php?datatype=s&did=70>

## 复现流程

### 1. 预处理 KPI

KPI 检测前需要先生成 `total_data.csv`：

```bash
uv run -m fluxev.cli preprocess-kpi
```

等价脚本方式：

```bash
uv run main.py preprocess-kpi
```

默认读取：

```text
data/AIOps/phase2_train.csv
data/AIOps/phase2_ground_truth.hdf
```

默认写出：

```text
data/AIOps/total_data.csv
```

也可以显式指定路径和填充方式：

```bash
uv run -m fluxev.cli preprocess-kpi \
  --train-path data/AIOps/phase2_train.csv \
  --test-path data/AIOps/phase2_ground_truth.hdf \
  --out-path data/AIOps/total_data.csv \
  --filled-type periodic
```

可选项：

- `--filled-type linear`：使用线性插值。
- `--filled-type periodic`：使用周期信息填充较长缺失段。
- `--standard`：使用训练集统计量标准化 KPI 数值。

### 2. 运行 KPI 检测

```bash
uv run -m fluxev.cli --dataset KPI
```

等价脚本方式：

```bash
uv run main.py --dataset KPI
```

默认结果写入：

```text
data/AIOps/results/MOM-s10-p5-d2-q0.003.txt
```

### 3. 运行 Yahoo 检测

```bash
uv run -m fluxev.cli --dataset Yahoo
```

等价脚本方式：

```bash
uv run main.py --dataset Yahoo
```

默认结果写在 `data/Yahoo/` 目录下，文件名由 `--ret_file` 模板决定。

## 常用参数

```bash
uv run -m fluxev.cli --dataset Yahoo --estimator MOM --s_w 10 --p_w 5 --half_d_w 2
```

- `--dataset`：选择 `KPI` 或 `Yahoo`。
- `--estimator`：SPOT 参数估计方法，支持 `MOM` 或 `MLE`。
- `--s_w`：连续窗口大小。
- `--p_w`：周期窗口大小。
- `--half_d_w`：漂移处理半窗口大小。
- `--train_len`：手动指定训练长度。
- `--ret_file`：结果文件名模板。

## 验证命令

修改代码后建议运行：

```bash
uv run pyright
python -m compileall main.py fluxev
```

## 相关来源

FluxEV 论文：
<https://dl.acm.org/doi/10.1145/3437963.3441823>

SPOT 原始实现：
<https://github.com/Amossys-team/SPOT>

## 引用

```bibtex
@inproceedings{li2021fluxev,
  title={FluxEV: A Fast and Effective Unsupervised Framework for Time-Series Anomaly Detection},
  author={Li, Jia and Di, Shimin and Shen, Yanyan and Chen, Lei},
  booktitle={Proceedings of the 14th ACM International Conference on Web Search and Data Mining},
  pages={824--832},
  year={2021}
}
```
