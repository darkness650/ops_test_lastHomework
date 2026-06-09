import numpy as np


def adjust_predicts(predict: np.ndarray, label: np.ndarray, delay: int = 7) -> np.ndarray:
    """
    按延迟容忍规则调整预测标签。

    该策略来自 AIOps Challenge 的 KPI 异常检测比赛评估脚本。
    """

    splits: np.ndarray = np.where(label[1:] != label[:-1])[0] + 1
    is_anomaly: bool = bool(label[0] == 1)
    new_predict: np.ndarray = np.array(predict, copy=True)
    pos: int = 0

    for split_value in splits:
        split: int = int(split_value)
        if is_anomaly:
            window_end: int = min(pos + delay + 1, split)
            new_predict[pos:split] = 1 if 1 in predict[pos:window_end] else 0
        is_anomaly = not is_anomaly
        pos = split

    end: int = int(len(label))
    if is_anomaly:
        window_end = min(pos + delay + 1, end)
        new_predict[pos:end] = 1 if 1 in predict[pos:window_end] else 0

    return new_predict
