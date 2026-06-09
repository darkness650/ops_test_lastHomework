from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast, overload

import more_itertools as mit
import numpy as np
import pandas as pd

from fluxev.plotting import show_filled_data

FilledValue = str | float | int


@overload
def complete_timestamp(
    timestamp: np.ndarray | Sequence[int],
    arrays: Iterable[np.ndarray],
    filled_value: FilledValue = "nan",
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], int, float]: ...


@overload
def complete_timestamp(
    timestamp: np.ndarray | Sequence[int],
    arrays: None = None,
    filled_value: FilledValue = "nan",
) -> tuple[np.ndarray, np.ndarray, int, float]: ...


def complete_timestamp(
    timestamp: np.ndarray | Sequence[int],
    arrays: Iterable[np.ndarray] | None = None,
    filled_value: FilledValue = "nan",
) -> (
    tuple[np.ndarray, np.ndarray, list[np.ndarray], int, float]
    | tuple[np.ndarray, np.ndarray, int, float]
):
    """
    补全时间戳，使序列间隔保持一致。

    返回的 missing 数组会标记补出的缺失点；如果传入 arrays，
    则会在每个数组的对应缺失位置插入填充值。
    """

    timestamp_arr: np.ndarray = np.asarray(timestamp, dtype=np.int64)
    if len(timestamp_arr.shape) != 1:
        raise ValueError("`timestamp` 必须是一维数组")

    has_arrays: bool = arrays is not None
    arrays_list: list[np.ndarray] = [np.asarray(array) for array in (arrays or ())]
    for i, array in enumerate(arrays_list):
        if array.shape != timestamp_arr.shape:
            raise ValueError(
                "``arrays[{}]`` 的形状与 `timestamp` 不一致 ({} vs {})".format(
                    i, array.shape, timestamp_arr.shape
                )
            )

    src_index: np.ndarray = np.argsort(timestamp_arr)
    timestamp_sorted: np.ndarray = timestamp_arr[src_index]
    intervals: np.ndarray = np.unique(np.diff(timestamp_sorted))
    interval: int = int(np.min(intervals))
    max_missing_num: float = float(np.max(intervals) / interval)

    if interval == 0:
        raise ValueError("`timestamp` 中存在重复值")
    for interval_value in intervals:
        if int(interval_value) % interval != 0:
            raise ValueError("`timestamp` 中并非所有间隔都是最小间隔的整数倍")

    length: int = int((timestamp_sorted[-1] - timestamp_sorted[0]) // interval + 1)
    ret_timestamp: np.ndarray = np.arange(
        timestamp_sorted[0], timestamp_sorted[-1] + interval, interval, dtype=np.int64
    )
    ret_missing: np.ndarray = np.ones([length], dtype=np.int32)
    if filled_value == "nan":
        ret_arrays: list[np.ndarray] = [np.full([length], np.nan) for _array in arrays_list]
    else:
        ret_arrays = [np.full([length], filled_value, dtype=array.dtype) for array in arrays_list]

    dst_index: np.ndarray = np.asarray(
        (timestamp_sorted - timestamp_sorted[0]) // interval, dtype=np.int_
    )
    ret_missing[dst_index] = 0
    for ret_array, array in zip(ret_arrays, arrays_list):
        ret_array[dst_index] = array[src_index]

    if has_arrays:
        return ret_timestamp, ret_missing, ret_arrays, interval, max_missing_num
    return ret_timestamp, ret_missing, interval, max_missing_num


def standardize_kpi(
    values: np.ndarray | Sequence[float],
    mean: float | None = None,
    std: float | None = None,
    excludes: np.ndarray | Sequence[bool] | None = None,
) -> tuple[np.ndarray, float, float]:
    """标准化一条 KPI 曲线。"""

    values_arr: np.ndarray = np.asarray(values, dtype=np.float32)
    if len(values_arr.shape) != 1:
        raise ValueError("`values` 必须是一维数组")
    if (mean is None) != (std is None):
        raise ValueError("`mean` 和 `std` 必须同时为空或同时非空")

    excludes_arr: np.ndarray | None = None
    if excludes is not None:
        excludes_arr = np.asarray(excludes, dtype=np.bool_)
        if excludes_arr.shape != values_arr.shape:
            raise ValueError(
                "`excludes` 的形状与 `values` 不一致 ({} vs {})".format(
                    excludes_arr.shape, values_arr.shape
                )
            )

    if mean is None or std is None:
        selected_values: np.ndarray = (
            values_arr[np.logical_not(excludes_arr)] if excludes_arr is not None else values_arr
        )
        mean = float(selected_values.mean())
        std = float(selected_values.std())

    return (values_arr - mean) / std, float(mean), float(std)


def read_data(path: str | Path) -> pd.DataFrame:
    data_path = Path(path)
    if data_path.suffix == ".hdf":
        return cast(pd.DataFrame, pd.read_hdf(data_path))
    if data_path.suffix == ".csv":
        return pd.read_csv(data_path)
    raise TypeError("当前文件类型不支持")


def process_kpi_data(
    train_path: str | Path,
    test_path: str | Path,
    out_path: str | Path,
    standard: bool = False,
    filled_type: str = "linear",
) -> None:
    """
    填充 KPI 缺失点，并把训练集与测试集合并保存为一个 CSV。
    """

    columns = ["timestamp", "value", "label", "KPI ID"]
    train_df = cast(pd.DataFrame, read_data(train_path).loc[:, columns]).copy()
    test_df = cast(pd.DataFrame, read_data(test_path).loc[:, columns]).copy()

    data_df = pd.DataFrame(columns=["timestamp", "value", "label", "KPI ID", "missing", "is_test"])
    grouped_frames = (train_df.groupby("KPI ID"), test_df.groupby("KPI ID"))

    mean_std_by_kpi: dict[str, tuple[float, float]] = {}
    for is_test, grouped in enumerate(grouped_frames):
        for name_obj, group in grouped:
            name: str = str(name_obj)
            print(name)
            temp_df = pd.DataFrame(
                columns=["timestamp", "value", "label", "KPI ID", "missing", "is_test"]
            )
            timestamp = group["timestamp"].to_numpy()
            value = group["value"].to_numpy()
            label = group["label"].to_numpy()

            timestamp, missing, completed_arrays, interval, max_miss_num = complete_timestamp(
                timestamp, (value, label)
            )
            value = completed_arrays[0]
            label = completed_arrays[1]

            if standard:
                if is_test == 0:
                    value, mean, std = standardize_kpi(
                        value, excludes=np.logical_or(label, missing)
                    )
                    mean_std_by_kpi[name] = (mean, std)
                else:
                    mean, std = mean_std_by_kpi[name]
                    value, _, _ = standardize_kpi(value, mean=mean, std=std)

            label[np.isnan(label)] = 0
            print("max_miss_num: ", max_miss_num)

            temp_df["timestamp"] = timestamp
            temp_df["missing"] = missing
            temp_df["value"] = value
            temp_df["label"] = label
            temp_df["KPI ID"] = name
            temp_df["is_test"] = is_test

            period: int = 1440 * 60 // interval
            length: int = int(len(value))
            num_padding: int = (length // period + 1) * period - length
            if filled_type == "linear":
                temp_df["value"] = temp_df["value"].interpolate(method="linear")
            elif filled_type == "periodic":
                tmp_value: np.ndarray = np.concatenate((value, np.full([num_padding], np.nan)))
                tmp_2d_array: np.ndarray = np.reshape(tmp_value, (-1, period))
                nan_num: np.ndarray = np.sum(np.isnan(tmp_2d_array), axis=1)
                for k in range(tmp_2d_array.shape[0]):
                    if nan_num[k] <= 5:
                        continue
                    filled_idx: np.ndarray = np.where(np.isnan(tmp_2d_array[k]))[0]
                    filled_idx_list: list[list[int]] = [
                        list(g) for g in mit.consecutive_groups(filled_idx)
                    ]
                    for idx_values in filled_idx_list:
                        idx_seg: np.ndarray = np.array(idx_values)
                        if 5 < len(idx_seg) < 0.6 * period:
                            mean_diff: float = float(
                                np.nanmean(tmp_2d_array[k]) - np.nanmean(tmp_2d_array[k - 1])
                            )
                            tmp_2d_array[k, idx_seg] = tmp_2d_array[k - 1, idx_seg] + mean_diff / 2
                        elif len(idx_seg) > 0.6 * period:
                            tmp_2d_array[k, idx_seg] = tmp_2d_array[k - 1, idx_seg]
                flatten_value: np.ndarray = tmp_2d_array.flatten()[:length]
                temp_df["value"] = flatten_value
                temp_df["value"] = temp_df["value"].interpolate(method="linear")
            else:
                raise TypeError("不支持该缺失值填充类型")

            data_df = pd.concat([data_df, temp_df], ignore_index=True)
            # 如需人工检查填充效果，可打开下面这一行绘图。
            # show_filled_data(name, filled_type, temp_df["value"].values, temp_df["missing"].values)

    data_df.to_csv(Path(out_path), index=False)


__all__ = [
    "complete_timestamp",
    "process_kpi_data",
    "read_data",
    "show_filled_data",
    "standardize_kpi",
]
