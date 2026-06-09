"""FluxEV 时间序列异常检测包。"""

from fluxev.detector import (
    calc_ewma,
    calc_ewma_v2,
    calc_first_smooth,
    calc_second_smooth,
    detect,
)
from fluxev.evaluation import adjust_predicts
from fluxev.spot import SPOT, EstimatorName

__all__ = [
    "SPOT",
    "EstimatorName",
    "adjust_predicts",
    "calc_ewma",
    "calc_ewma_v2",
    "calc_first_smooth",
    "calc_second_smooth",
    "detect",
]
