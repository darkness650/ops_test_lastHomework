import numba
import numpy as np

from fluxev.spot import SPOT, EstimatorName


def calc_ewma(input_arr: np.ndarray, alpha: float = 0.2, adjust: bool = True) -> float:
    """
    计算指数加权移动平均值。

    Args:
        input_arr: 一维输入数组。
        alpha: 平滑系数，取值范围为 (0, 1]。
        adjust: 为 True 时使用归一化权重；为 False 时使用递推形式。
    """

    arr_len: int = int(len(input_arr))
    if arr_len == 0:
        raise ValueError("input_arr 不能为空")

    if adjust:
        power_arr: np.ndarray = np.arange(arr_len - 1, -1, -1)
        base_arr: np.ndarray = np.full(arr_len, 1 - alpha)
        weight_arr: np.ndarray = np.power(base_arr, power_arr)
        return float(np.sum(input_arr * weight_arr) / np.sum(weight_arr))

    ret: float = float(input_arr[0])
    for i in range(1, arr_len):
        ret = alpha * float(input_arr[i]) + (1 - alpha) * ret
    return ret


@numba.njit
def calc_ewma_v2(input_arr: np.ndarray, alpha: float = 0.2) -> float:
    arr_len: int = len(input_arr)
    ret: float = float(input_arr[0])
    for i in range(1, arr_len):
        ret = alpha * float(input_arr[i]) + (1 - alpha) * ret
    return ret


def calc_first_smooth(input_arr: np.ndarray) -> float:
    return float(max(np.nanstd(input_arr) - np.nanstd(input_arr[:-1]), 0))


def calc_second_smooth(input_arr: np.ndarray) -> float:
    return float(max(np.nanmax(input_arr) - np.nanmax(input_arr[:-1]), 0))


def detect(
    data_arr: np.ndarray,
    train_len: int,
    period: int,
    smoothing: int = 2,
    s_w: int = 10,
    p_w: int = 7,
    half_d_w: int = 2,
    q: float = 0.001,
    estimator: EstimatorName = "MOM",
    verbose: bool = True,
) -> np.ndarray:
    """
    在一维序列上运行 FluxEV 流式异常检测。

    返回 0/1 数组，其中 0 表示正常点，1 表示异常点。
    """

    if smoothing not in {1, 2}:
        raise ValueError("smoothing 必须是 1 或 2")

    data_len: int = int(len(data_arr))
    spot = SPOT(q, estimator=estimator)

    d_w: int = half_d_w * 2
    fs_idx: int = s_w * 2
    fs_lm_idx: int = fs_idx + d_w
    ss_idx: int = fs_idx + half_d_w + period * (p_w - 1)

    pred_err: np.ndarray = np.full(data_len, np.nan)
    fs_err: np.ndarray = np.full(data_len, np.nan)
    fs_err_lm: np.ndarray = np.full(data_len, np.nan)
    ss_err: np.ndarray = np.full(data_len, np.nan)

    alarms: list[int] = []
    if smoothing == 1:
        for i in range(s_w, data_len):
            pi_value: float = calc_ewma_v2(data_arr[i - s_w : i])
            pred_err[i] = data_arr[i] - pi_value

            if i >= fs_idx:
                fs_err[i] = calc_first_smooth(pred_err[i - s_w : i + 1])

            if i == train_len - 1:
                spot.fit(fs_err[fs_idx : i + 1])
                spot.initialize(verbose=verbose)

            if i >= train_len:
                _threshold, alarm = spot.run_step(float(fs_err[i]))
                alarms.append(alarm)

    else:
        for i in range(s_w, data_len):
            pi_value = calc_ewma_v2(data_arr[i - s_w : i])
            pred_err[i] = data_arr[i] - pi_value

            if i >= fs_idx:
                fs_err[i] = calc_first_smooth(pred_err[i - s_w : i + 1])

                if i >= fs_lm_idx:
                    fs_err_lm[i - half_d_w] = np.nanmax(fs_err[i - d_w : i + 1])

                if i >= ss_idx:
                    periodic_values: np.ndarray = fs_err_lm[i - period * (p_w - 1) : i : period]
                    ss_err[i] = calc_second_smooth(np.append(periodic_values, fs_err[i]))

            if i == train_len - 1:
                spot.fit(ss_err[ss_idx : i + 1])
                spot.initialize(verbose=verbose)

            if i >= train_len:
                _threshold, alarm = spot.run_step(float(ss_err[i]))

                if alarm:
                    fs_err[i] = np.nan
                    fs_err_lm[i - half_d_w] = np.nanmax(fs_err[i - d_w : i + 1])

                alarms.append(alarm)

    return np.asarray(alarms, dtype=np.int_)
