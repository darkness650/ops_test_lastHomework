from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

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
    f_score: float = float(f1_score(y_true_arr, y_pred_arr))
    recall: float = float(recall_score(y_true_arr, y_pred_arr))
    precision: float = float(precision_score(y_true_arr, y_pred_arr))
    return f_score, recall, precision


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
