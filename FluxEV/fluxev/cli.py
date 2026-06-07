import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from fluxev.datasets import DetectionConfig, run_kpi, run_yahoo
from fluxev.preprocessing import process_kpi_data
from fluxev.spot import EstimatorName


def parse_estimator(value: str) -> EstimatorName:
    normalized = value.upper()
    if normalized not in {"MOM", "MLE"}:
        raise argparse.ArgumentTypeError("estimator 必须是 'MOM' 或 'MLE'")
    return cast(EstimatorName, normalized)


def build_detection_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FluxEV 流式异常检测",
        epilog="KPI 预处理请使用 `uv run -m fluxev.cli preprocess-kpi --help`。",
    )
    parser.add_argument("--dataset", type=str, default="Yahoo", choices=["KPI", "Yahoo"])
    parser.add_argument("--delay", type=int, default=7, help="评估时允许延迟命中的点数")
    parser.add_argument("--q", type=float, default=0.003, help="SPOT 风险系数")
    parser.add_argument(
        "--s_w",
        type=int,
        default=10,
        help="一阶平滑使用的连续窗口大小，用于提取局部波动",
    )
    parser.add_argument("--p_w", type=int, default=5, help="二阶平滑使用的周期窗口大小")
    parser.add_argument("--half_d_w", type=int, default=2, help="处理数据漂移时使用的半窗口大小")
    parser.add_argument(
        "--estimator",
        type=parse_estimator,
        default="MOM",
        help="SPOT 分布参数估计方法，可选 'MOM' 或 'MLE'",
    )
    parser.add_argument(
        "--train_len",
        type=int,
        default=None,
        help="用于初始化 SPOT 的训练长度；省略时使用数据集默认策略",
    )
    parser.add_argument("--ret_file", type=str, default="{}-s{}-p{}-d{}-q{}.txt")
    return parser


def build_preprocess_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="预处理 AIOps KPI 数据集")
    parser.add_argument(
        "--train-path",
        type=str,
        default="./data/AIOps/phase2_train.csv",
        help="原始 KPI 训练 CSV 路径",
    )
    parser.add_argument(
        "--test-path",
        type=str,
        default="./data/AIOps/phase2_ground_truth.hdf",
        help="原始 KPI 测试标注 HDF 路径",
    )
    parser.add_argument(
        "--out-path",
        type=str,
        default="./data/AIOps/total_data.csv",
        help="预处理后合并 CSV 的输出路径",
    )
    parser.add_argument(
        "--filled-type",
        type=str,
        default="periodic",
        choices=["linear", "periodic"],
        help="缺失值填充策略",
    )
    parser.add_argument(
        "--standard",
        action="store_true",
        help="使用训练集统计量标准化 KPI 数值",
    )
    return parser


def config_from_namespace(args: argparse.Namespace) -> DetectionConfig:
    return DetectionConfig(
        ret_file=args.ret_file,
        estimator=args.estimator,
        s_w=args.s_w,
        p_w=args.p_w,
        half_d_w=args.half_d_w,
        q=args.q,
        delay=args.delay,
        train_len=args.train_len,
    )


def run_detection(args: argparse.Namespace) -> None:
    config = config_from_namespace(args)

    if args.dataset == "KPI":
        config.delay = 7
        config.q = 0.003
        base_dir = Path("data") / "AIOps"
        data_path = base_dir / "total_data.csv"
        run_kpi(config, base_dir, data_path)
    elif args.dataset == "Yahoo":
        config.delay = 3
        config.q = 0.001
        run_yahoo(config, Path("data") / "Yahoo")
    else:
        raise ValueError(f"不支持的数据集: {args.dataset}")


def run_preprocess_kpi(args: argparse.Namespace) -> None:
    process_kpi_data(
        train_path=args.train_path,
        test_path=args.test_path,
        out_path=args.out_path,
        standard=args.standard,
        filled_type=args.filled_type,
    )


def main(argv: Sequence[str] | None = None) -> None:
    arg_list = list(argv) if argv is not None else sys.argv[1:]
    if arg_list and arg_list[0] == "preprocess-kpi":
        args = build_preprocess_parser().parse_args(arg_list[1:])
        run_preprocess_kpi(args)
        return

    args = build_detection_parser().parse_args(arg_list)
    run_detection(args)


if __name__ == "__main__":
    main()
