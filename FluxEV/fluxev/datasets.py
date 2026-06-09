import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

from fluxev.detector import detect
from fluxev.evaluation import adjust_predicts
from fluxev.spot import EstimatorName


@dataclass(slots=True)
class DetectionConfig:
    ret_file: str
    estimator: EstimatorName = "MOM"
    s_w: int = 10
    p_w: int = 5
    half_d_w: int = 2
    q: float = 0.003
    delay: int = 7
    train_len: int | None = None


def result_file_path(base_dir: str | Path, ret_file: str, config: DetectionConfig) -> Path:
    path_template = str(Path(base_dir) / ret_file)
    return Path(
        path_template.format(
            config.estimator,
            config.s_w,
            config.p_w,
            config.half_d_w,
            config.q,
        )
    )


def read_yahoo_data(path: str | Path) -> tuple[pd.DataFrame, str, int]:
    file_path = Path(path)
    file_name: str = file_path.stem
    benchmark_name: str = file_path.parent.name
    dir_id: int = int(benchmark_name[1])

    if dir_id < 3:
        timestamp_col: str = "timestamp"
        value_col: str = "value"
        label_col: str = "is_anomaly"
    else:
        timestamp_col = "timestamps"
        value_col = "value"
        label_col = "anomaly"

    df = cast(
        pd.DataFrame,
        pd.read_csv(file_path).loc[:, [timestamp_col, value_col, label_col]],
    ).copy()
    df[[timestamp_col, label_col]] = df[[timestamp_col, label_col]].astype(int)
    df = df.rename(columns={timestamp_col: "timestamp", value_col: "value", label_col: "label"})

    return df, file_name, dir_id


def score_predictions(
    y_true: list[np.ndarray], y_pred: list[np.ndarray]
) -> tuple[float, float, float]:
    y_true_arr: np.ndarray = np.concatenate(y_true)
    y_pred_arr: np.ndarray = np.concatenate(y_pred)
    true_positive = int(np.sum((y_true_arr == 1) & (y_pred_arr == 1)))
    false_positive = int(np.sum((y_true_arr == 0) & (y_pred_arr == 1)))
    false_negative = int(np.sum((y_true_arr == 1) & (y_pred_arr == 0)))

    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative

    precision = true_positive / precision_denominator if precision_denominator else 0.0
    recall = true_positive / recall_denominator if recall_denominator else 0.0
    f_score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return float(f_score), float(recall), float(precision)


def append_scores(ret_file_path: str | Path, scores: tuple[float, float, float]) -> None:
    f_score, recall, precision = scores
    with Path(ret_file_path).open("a", encoding="utf-8") as f:
        f.write(f"总 F1/召回率/精确率: {f_score}, {recall}, {precision}\n")


def run_yahoo(config: DetectionConfig, data_dir: str | Path) -> None:
    data_root = Path(data_dir)
    ret_file_path: Path = result_file_path(data_root, config.ret_file, config)

    file_list: list[Path] = []
    for benchmark_id in [1, 2, 3, 4]:
        sub_dir = data_root / f"A{benchmark_id}Benchmark"
        file_list.extend(sub_dir.glob("*.csv"))

    y_true: list[np.ndarray] = []
    y_pred: list[np.ndarray] = []
    for data_path in file_list:
        data_df, file_name, dir_id = read_yahoo_data(data_path)

        print(file_name)
        value: np.ndarray = data_df["value"].to_numpy()
        label: np.ndarray = data_df["label"].to_numpy()

        period: int = 24
        train_len: int = len(value) // 2 if config.train_len is None else config.train_len
        smoothing: int = 1 if dir_id == 2 else 2

        label_test: np.ndarray = label[train_len:]
        alarms: np.ndarray = detect(
            value,
            train_len,
            period,
            smoothing,
            config.s_w,
            config.p_w,
            config.half_d_w,
            config.q,
            estimator=config.estimator,
        )

        ret_test: np.ndarray = adjust_predicts(predict=alarms, label=label_test, delay=config.delay)

        y_true.append(label_test)
        y_pred.append(ret_test)

    append_scores(ret_file_path, score_predictions(y_true, y_pred))


def run_kpi(config: DetectionConfig, base_dir: str | Path, data_path: str | Path) -> None:
    ret_dir = Path(base_dir) / "results"
    ret_file_path: Path = result_file_path(ret_dir, config.ret_file, config)
    ret_dir.mkdir(parents=True, exist_ok=True)

    data_df: pd.DataFrame = pd.read_csv(Path(data_path))
    data_df[["timestamp", "label", "missing", "is_test"]] = data_df[
        ["timestamp", "label", "missing", "is_test"]
    ].astype(int)

    y_true: list[np.ndarray] = []
    y_pred: list[np.ndarray] = []
    for name, group in data_df.sort_values(by=["KPI ID", "timestamp"], ascending=True).groupby(
        "KPI ID"
    ):
        print(name)

        group = group.reset_index(drop=True)
        timestamp: np.ndarray = group["timestamp"].to_numpy()
        value: np.ndarray = group["value"].to_numpy()
        label: np.ndarray = group["label"].to_numpy()
        missing: np.ndarray = group["missing"].to_numpy()

        train_len: int = (
            int(np.sum(group["is_test"].to_numpy() == 0))
            if config.train_len is None
            else config.train_len
        )

        interval: int = int(timestamp[1] - timestamp[0])
        period: int = 1440 * 60 // interval

        label_test: np.ndarray = label[train_len:]
        test_missing: np.ndarray = missing[train_len:]
        alarms: np.ndarray = detect(
            value,
            train_len,
            period,
            2,
            config.s_w,
            config.p_w,
            config.half_d_w,
            config.q,
            estimator=config.estimator,
        )

        alarms[np.where(test_missing == 1)] = 0
        ret_test: np.ndarray = adjust_predicts(predict=alarms, label=label_test, delay=config.delay)

        y_true.append(label_test)
        y_pred.append(ret_test)

    append_scores(ret_file_path, score_predictions(y_true, y_pred))


def read_ops_data(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    df = cast(pd.DataFrame, pd.read_csv(file_path).loc[:, ["timestamp", "value", "label"]]).copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["label"] = df["label"].astype(int)
    df = df.sort_values(by="timestamp", ascending=True).reset_index(drop=True)
    df["value"] = df["value"].interpolate(method="linear").bfill().ffill()
    return df


def ops_metric_paths(data_dir: str | Path) -> list[Path]:
    data_root = Path(data_dir)
    manifest_path = data_root / "manifest.csv"
    if manifest_path.exists():
        manifest_df = pd.read_csv(manifest_path)
        return [data_root / str(output_file) for output_file in manifest_df["output_file"]]
    return sorted(path for path in data_root.rglob("*.csv") if path.name != "manifest.csv")


def default_ops_train_len(label: np.ndarray, data_len: int, min_train_len: int) -> int:
    positive_idx: np.ndarray = np.flatnonzero(label == 1)
    candidate = int(positive_idx[0]) if positive_idx.size else data_len // 2
    return min(max(candidate, min_train_len), data_len - 1)


def run_ops(config: DetectionConfig, data_dir: str | Path) -> None:
    data_root = Path(data_dir)
    ret_dir = data_root / "results"
    ret_file_path = result_file_path(ret_dir, config.ret_file, config)
    per_metric_path = ret_file_path.with_suffix(".csv")
    ret_dir.mkdir(parents=True, exist_ok=True)

    y_true: list[np.ndarray] = []
    y_pred: list[np.ndarray] = []
    metric_records: list[dict[str, object]] = []
    min_train_len = config.s_w * 2 + 1

    for data_path in ops_metric_paths(data_root):
        metric_name = str(data_path.relative_to(data_root))
        print(metric_name)

        try:
            data_df = read_ops_data(data_path)
            value = data_df["value"].to_numpy(dtype=float)
            label = data_df["label"].to_numpy(dtype=int)

            if len(value) <= min_train_len:
                raise ValueError(
                    f"序列长度 {len(value)} 不足以初始化 s_w={config.s_w} 的检测窗口"
                )

            train_len = (
                default_ops_train_len(label, len(value), min_train_len)
                if config.train_len is None
                else min(max(config.train_len, min_train_len), len(value) - 1)
            )

            label_test = label[train_len:]
            status = "ok"
            error = ""
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    alarms = detect(
                        value,
                        train_len,
                        period=1,
                        smoothing=1,
                        s_w=config.s_w,
                        p_w=config.p_w,
                        half_d_w=config.half_d_w,
                        q=config.q,
                        estimator=config.estimator,
                        verbose=False,
                    )
            except Exception as exc:
                status = "zero_fallback"
                error = str(exc)
                alarms = np.zeros(len(value) - train_len, dtype=np.int_)

            ret_test = adjust_predicts(predict=alarms, label=label_test, delay=config.delay)
            f_score, recall, precision = score_predictions([label_test], [ret_test])

            y_true.append(label_test)
            y_pred.append(ret_test)
            metric_records.append(
                {
                    "metric_file": metric_name,
                    "status": status,
                    "train_len": train_len,
                    "rows": len(value),
                    "positive_labels": int(label.sum()),
                    "predicted_positives": int(ret_test.sum()),
                    "f1": f_score,
                    "recall": recall,
                    "precision": precision,
                    "error": error,
                }
            )
        except Exception as exc:
            metric_records.append(
                {
                    "metric_file": metric_name,
                    "status": "failed",
                    "train_len": "",
                    "rows": "",
                    "positive_labels": "",
                    "predicted_positives": "",
                    "f1": "",
                    "recall": "",
                    "precision": "",
                    "error": str(exc),
                }
            )

    pd.DataFrame(metric_records).to_csv(per_metric_path, index=False)
    if not y_true:
        raise RuntimeError("OPS 数据集中没有任何指标成功完成检测")

    with ret_file_path.open("w", encoding="utf-8") as f:
        f.write(f"指标数: {len(y_true)} / {len(metric_records)}\n")
        f.write(f"逐指标结果: {per_metric_path}\n")
    append_scores(ret_file_path, score_predictions(y_true, y_pred))
