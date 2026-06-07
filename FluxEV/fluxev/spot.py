#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FluxEV 使用的 SPOT 实现。

原始 SPOT 代码来自 Alban Siffer / Amossys，许可证为 GNU GPLv3。
"""

from collections.abc import Callable, Sequence
from math import floor, log
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import minimize

EstimatorName = Literal["MLE", "MOM"]
Estimator = Callable[[], tuple[float, float, float]]

deep_saffron: str = "#FF9933"
air_force_blue: str = "#5D8AA8"


class SPOT:
    """用于单变量序列的流式 Peaks-Over-Threshold 检测器。"""

    def __init__(self, q: float = 1e-4, estimator: EstimatorName = "MOM") -> None:
        self.proba: float = q
        self.extreme_quantile: float | None = None
        self.data: np.ndarray | None = None
        self.init_data: np.ndarray | None = None
        self.init_threshold: float | None = None
        self.peaks: np.ndarray | None = None
        self.n: int = 0
        self.Nt: int = 0

        if estimator == "MLE":
            self.estimator: Estimator = self._grimshaw
        elif estimator == "MOM":
            self.estimator = self._mom
        else:
            raise TypeError("不支持该估计方法")

    def __str__(self) -> str:
        lines: list[str] = [
            "Streaming Peaks-Over-Threshold Object",
            f"Detection level q = {self.proba}",
        ]
        if self.data is None:
            lines.append("Data imported : No")
            return "\n".join(lines) + "\n"

        if self.init_data is None:
            raise ValueError("打印数据信息前必须先 fit SPOT 对象")

        lines.extend(
            [
                "Data imported : Yes",
                f"\t initialization  : {self.init_data.size} values",
                f"\t stream : {self.data.size} values",
            ]
        )

        if self.n == 0:
            lines.append("Algorithm initialized : No")
        else:
            if self.init_threshold is None:
                raise ValueError("打印状态前必须先初始化 SPOT 对象")
            lines.extend(
                [
                    "Algorithm initialized : Yes",
                    f"\t initial threshold : {self.init_threshold}",
                ]
            )

            run_count: int = self.n - self.init_data.size
            if run_count > 0:
                lines.extend(
                    [
                        "Algorithm run : Yes",
                        "\t number of observations : "
                        f"{run_count} ({100 * run_count / self.n:.2f} %)",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"\t number of peaks  : {self.Nt}",
                        f"\t extreme quantile : {self.extreme_quantile}",
                        "Algorithm run : No",
                    ]
                )
        return "\n".join(lines) + "\n"

    def fit(self, init_data: Sequence[float] | np.ndarray | pd.Series) -> None:
        """设置用于校准的初始数据批次。"""

        if isinstance(init_data, np.ndarray):
            self.init_data = init_data.astype(float, copy=False)
        elif isinstance(init_data, pd.Series):
            self.init_data = init_data.to_numpy(dtype=float)
        else:
            self.init_data = np.asarray(init_data, dtype=float)

    def initialize(self, level: float = 0.98, verbose: bool = True) -> None:
        """执行校准初始化步骤。"""

        level = level - floor(level)

        if self.init_data is None:
            raise ValueError("初始化前必须先 fit SPOT 对象")

        n_init: int = int(self.init_data.size)
        sorted_data: np.ndarray = np.sort(self.init_data)
        self.init_threshold = float(sorted_data[int(level * n_init)])

        self.peaks = self.init_data[self.init_data > self.init_threshold] - self.init_threshold
        self.Nt = int(self.peaks.size)
        self.n = n_init

        if verbose:
            print(f"Initial threshold : {self.init_threshold}")
            print(f"Number of peaks : {self.Nt}")
            print("Grimshaw 极大似然估计 ... ", end="")

        gamma, sigma, ll_value = self.estimator()
        self.extreme_quantile = self._quantile(gamma, sigma)

        if verbose:
            print("[done]")
            print("\t" + chr(0x03B3) + " = " + str(gamma))
            print("\t" + chr(0x03C3) + " = " + str(sigma))
            print("\tL = " + str(ll_value))
            print(f"极端分位数 (概率 = {self.proba}): {self.extreme_quantile}")

    @staticmethod
    def _roots_finder(
        fun: Callable[[float], float],
        jac: Callable[[float], float],
        bounds: tuple[float, float],
        npoints: int,
        method: Literal["regular", "random"],
    ) -> np.ndarray:
        """寻找标量函数的候选根。"""

        if method == "regular":
            step: float = (bounds[1] - bounds[0]) / (npoints + 1)
            x0: np.ndarray = np.arange(bounds[0] + step, bounds[1], step)
        elif method == "random":
            x0 = np.random.uniform(bounds[0], bounds[1], npoints)
        else:
            raise ValueError("不支持该根搜索方法")

        def objective(
            x_values: np.ndarray,
            func: Callable[[float], float],
            jac_func: Callable[[float], float],
        ) -> tuple[float, np.ndarray]:
            score: float = 0.0
            jacobian: np.ndarray = np.zeros(x_values.shape)
            for i, x_value in enumerate(x_values):
                fx: float = func(float(x_value))
                score += fx**2
                jacobian[i] = 2 * fx * jac_func(float(x_value))
            return score, jacobian

        opt = minimize(
            lambda x_values: objective(x_values, fun, jac),
            x0,
            method="L-BFGS-B",
            jac=True,
            bounds=[bounds] * len(x0),
        )

        return np.unique(np.round(opt.x, decimals=5))

    _rootsFinder = _roots_finder

    @staticmethod
    def _log_likelihood(values: np.ndarray, gamma: float, sigma: float) -> float:
        """计算阈值以上观测值的 GPD 对数似然。"""

        count: int = int(values.size)
        if gamma != 0:
            tau: float = gamma / sigma
            likelihood: float = -count * log(sigma) - (1 + (1 / gamma)) * float(
                np.log(1 + tau * values).sum()
            )
        else:
            likelihood = count * (1 + log(float(values.mean())))
        return likelihood

    def _grimshaw(self, epsilon: float = 1e-8, n_points: int = 10) -> tuple[float, float, float]:
        """使用 Grimshaw 方法估计 GPD 参数。"""

        if self.peaks is None:
            raise ValueError("估计 GPD 参数前必须先初始化 SPOT 对象")

        peaks: np.ndarray = self.peaks

        def u(s: np.ndarray) -> float:
            return float(1 + np.log(s).mean())

        def v(s: np.ndarray) -> float:
            return float(np.mean(1 / s))

        def w(values: np.ndarray, t: float) -> float:
            scaled: np.ndarray = 1 + t * values
            return u(scaled) * v(scaled) - 1

        def jac_w(values: np.ndarray, t: float) -> float:
            scaled: np.ndarray = 1 + t * values
            us: float = u(scaled)
            vs: float = v(scaled)
            jac_us: float = (1 / t) * (1 - vs)
            jac_vs: float = float((1 / t) * (-vs + np.mean(1 / scaled**2)))
            return us * jac_vs + vs * jac_us

        ymin: float = float(peaks.min())
        ymax: float = float(peaks.max())
        ymean: float = float(peaks.mean())

        a: float = -1 / ymax
        if abs(a) < 2 * epsilon:
            epsilon = abs(a) / n_points

        a += epsilon
        b: float = 2 * (ymean - ymin) / (ymean * ymin)
        c: float = 2 * (ymean - ymin) / (ymin**2)

        left_zeros: np.ndarray = SPOT._roots_finder(
            lambda t: w(peaks, t),
            lambda t: jac_w(peaks, t),
            (a + epsilon, -epsilon),
            n_points,
            "regular",
        )
        right_zeros: np.ndarray = SPOT._roots_finder(
            lambda t: w(peaks, t),
            lambda t: jac_w(peaks, t),
            (b, c),
            n_points,
            "regular",
        )
        zeros: np.ndarray = np.concatenate((left_zeros, right_zeros))

        gamma_best: float = 0.0
        sigma_best: float = ymean
        ll_best: float = SPOT._log_likelihood(peaks, gamma_best, sigma_best)

        for z_value in zeros:
            z: float = float(z_value)
            gamma: float = u(1 + z * peaks) - 1
            sigma: float = gamma / z
            ll_value: float = SPOT._log_likelihood(peaks, gamma, sigma)
            if ll_value > ll_best:
                gamma_best = gamma
                sigma_best = sigma
                ll_best = ll_value

        return gamma_best, sigma_best, ll_best

    def _mom(self) -> tuple[float, float, float]:
        """使用矩估计方法估计 GPD 参数。"""

        if self.peaks is None:
            raise ValueError("估计 GPD 参数前必须先初始化 SPOT 对象")
        avg: float = float(np.mean(self.peaks))
        var: float = float(np.var(self.peaks, ddof=1))
        sigma: float = 0.5 * avg * (1 + avg**2 / var)
        gamma: float = 0.5 * (1 - avg**2 / var)
        return gamma, sigma, 0.0

    _MOM = _mom

    def _quantile(self, gamma: float, sigma: float) -> float:
        """计算 GPD 在 1-q 水平上的分位数。"""

        if self.init_threshold is None:
            raise ValueError("计算分位数前必须先初始化 SPOT 对象")
        if self.Nt == 0:
            raise ValueError("SPOT 初始化后没有找到峰值")

        ratio: float = self.n * self.proba / self.Nt
        if gamma != 0:
            return self.init_threshold + (sigma / gamma) * (pow(ratio, -gamma) - 1)
        return self.init_threshold - sigma * log(ratio)

    def run_step(self, data_point: float) -> tuple[float, int]:
        """对单个流式数据点运行 SPOT。"""

        if self.extreme_quantile is None or self.init_threshold is None:
            raise ValueError("运行前必须先初始化 SPOT 对象")
        if self.peaks is None:
            raise ValueError("运行前必须先初始化 SPOT 对象")

        alarm: int = 0
        if data_point > self.extreme_quantile:
            alarm = 1
        elif data_point > self.init_threshold:
            self.peaks = np.append(self.peaks, data_point - self.init_threshold)
            self.Nt += 1
            self.n += 1
            gamma, sigma, _ll_value = self.estimator()
            self.extreme_quantile = self._quantile(gamma, sigma)
        else:
            self.n += 1

        return self.extreme_quantile, alarm
