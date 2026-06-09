from typing import Any

import matplotlib.pyplot as plt
import more_itertools as mit
import numpy as np
from matplotlib.figure import Figure


def label_segments(label_arr: np.ndarray, pad_singletons: bool = False) -> list[tuple[int, int]]:
    groups: list[list[int]] = [list(g) for g in mit.consecutive_groups(np.where(label_arr)[0])]
    if pad_singletons:
        return [(g[0], g[-1]) if g[0] != g[-1] else (g[0] - 1, g[0] + 1) for g in groups]
    return [(g[0], g[-1]) if g[0] != g[-1] else (g[0] - 1, g[0]) for g in groups]


def plot_ft(fig_name: str, data_arr: np.ndarray, label_arr: np.ndarray, ft_arr: np.ndarray) -> None:
    label_segs: list[tuple[int, int]] = label_segments(label_arr)

    data_len: int = int(len(data_arr))
    xs: np.ndarray = np.linspace(0, data_len - 1, data_len)
    fig: Figure = plt.figure(figsize=(12, 6))
    axes: Any = fig.subplots(2, 1, sharex="all")

    axes[0].set_title(f"id: {fig_name}")
    axes[0].plot(xs, data_arr, "lightgrey")
    axes[1].plot(xs, ft_arr)
    for start, end in label_segs:
        seg_x: np.ndarray = np.linspace(start, end, end - start + 1).astype(dtype=int)
        axes[0].plot(seg_x, data_arr[seg_x], color="r")
        axes[1].plot(seg_x, ft_arr[seg_x], color="r")

    plt.tight_layout()
    plt.show()


def show_filled_data(
    kpi_id: str,
    fill_type: str,
    data: np.ndarray,
    missing: np.ndarray,
    label: np.ndarray | None = None,
) -> None:
    missing_segs: list[tuple[int, int]] = label_segments(missing, pad_singletons=True)

    data_len: int = int(len(data))
    xs: np.ndarray = np.linspace(0, data_len - 1, data_len)
    plt.figure(figsize=(9, 6))
    plt.title(f"id: {kpi_id}, type: {fill_type}")
    plt.xticks([])
    plt.yticks([])
    plt.plot(xs, data, "mediumblue")
    for start, end in missing_segs:
        seg_x: np.ndarray = np.linspace(start, end, end - start + 1).astype(dtype=int)
        plt.plot(seg_x, data[seg_x], color="g")

    if label is not None:
        for start, end in label_segments(label, pad_singletons=True):
            seg_x = np.linspace(start, end, end - start + 1).astype(dtype=int)
            plt.plot(seg_x, data[seg_x], color="r")
    plt.show()
