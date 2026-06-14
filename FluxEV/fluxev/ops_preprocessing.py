from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pandas as pd

EventName = str
ManualFilterKey = tuple[str, str]


def timestamp(value: str) -> pd.Timestamp:
    return cast(pd.Timestamp, pd.Timestamp(value))


@dataclass(frozen=True)
class EventWindow:
    name: EventName
    start: pd.Timestamp
    end: pd.Timestamp


@dataclass(frozen=True)
class FileRule:
    source_prefix: str
    relative_dir: str
    filename_glob: str
    selector: str


EVENT_WINDOWS: dict[EventName, EventWindow] = {
    "network-loss": EventWindow(
        name="network-loss",
        start=timestamp("2026-06-04 17:51:45"),
        end=timestamp("2026-06-04 18:21:45"),
    ),
    "stress-test": EventWindow(
        name="stress-test",
        start=timestamp("2026-06-04 19:55:13"),
        end=timestamp("2026-06-04 20:25:13"),
    ),
}

ALL_EVENTS: tuple[EventName, ...] = ("network-loss", "stress-test")

FILE_RULES: tuple[FileRule, ...] = (
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__CPU",
        relative_dir="CPU Memory Net Disk",
        filename_glob="CPU-data-*.csv",
        selector="cpu",
    ),
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__Memory",
        relative_dir="CPU Memory Net Disk",
        filename_glob="Memory-data-*.csv",
        selector="all_events",
    ),
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__Network_Traffic",
        relative_dir="CPU Memory Net Disk",
        filename_glob="Network Traffic-data-*.csv",
        selector="all_events",
    ),
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__Network_Saturation",
        relative_dir="CPU Memory Net Disk",
        filename_glob="Network Saturation-data-*.csv",
        selector="all_events",
    ),
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__Disk_IOps",
        relative_dir="CPU Memory Net Disk",
        filename_glob="Disk IOps-data-*.csv",
        selector="disk_iops",
    ),
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__Disk_Throughput",
        relative_dir="CPU Memory Net Disk",
        filename_glob="Disk Throughput-data-*.csv",
        selector="disk_throughput",
    ),
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__Disk_IO_Utilization",
        relative_dir="CPU Memory Net Disk",
        filename_glob="Disk I_O Utilization-data-*.csv",
        selector="disk_io_utilization",
    ),
    FileRule(
        source_prefix="CPU_Memory_Net_Disk__Pressure",
        relative_dir="CPU Memory Net Disk",
        filename_glob="Pressure Stall Information-data-*.csv",
        selector="pressure",
    ),
    FileRule(
        source_prefix="System_Processes__Processes_Forks",
        relative_dir="System Processes",
        filename_glob="Processes Forks-data-*.csv",
        selector="all_events",
    ),
    FileRule(
        source_prefix="System_Processes__CPU_Saturation",
        relative_dir="System Processes",
        filename_glob="CPU Saturation per Core-data-*.csv",
        selector="all_events",
    ),
    FileRule(
        source_prefix="Network_Sockstat__Sockstat_Memory_Size",
        relative_dir="Network Sockstat",
        filename_glob="Sockstat Memory Size-data-*.csv",
        selector="sockstat_memory_size",
    ),
    FileRule(
        source_prefix="Network_Netstat__TCP_Errors",
        relative_dir="Network Netstat",
        filename_glob="TCP Errors-data-*.csv",
        selector="tcp_errors",
    ),
)

MANUAL_FILTER_SOURCE_PREFIXES: dict[str, str] = {
    "Network_Traffic": "CPU_Memory_Net_Disk__Network_Traffic",
    "Network_Saturation": "CPU_Memory_Net_Disk__Network_Saturation",
}

MANUAL_FILTER_DIRECTIONS: dict[str, str] = {
    "Rx_in": " - Rx in",
    "Tx_out": " - Tx out",
}

MANUAL_FILTER_DEVICES: dict[str, dict[str, tuple[str, ...]]] = {
    "Network_Traffic": {
        "Rx_in": (
            "veth1a1311ea",
            "veth1ab2ce35",
            "veth23b72f28",
            "veth4d5ad56b",
            "veth63a0bdbf",
            "veth8189d14e",
            "veth9cfe6466",
            "vetha5d56989",
            "vethde56b93d",
            "vethe9298b11",
            "vethee72330e",
            "vethf347c1b6",
            "vethf59accf3",
        ),
        "Tx_out": (
            "veth0898283a",
            "veth1a1311ea",
            "veth3d1fc018",
            "veth4d5ad56b",
            "veth5dc2fb4d",
            "veth5f9eb48f",
            "veth63a0bdbf",
            "veth67ba92c8",
            "veth8189d14e",
            "veth8262aa09",
            "veth8de63f6a",
            "veth9cfe6466",
            "vetha5d56989",
            "vethd22aedbd",
            "vethde56b93d",
            "vethe9298b11",
            "vethee72330e",
            "vethf347c1b6",
            "vethf59accf3",
        ),
    },
    "Network_Saturation": {
        "Rx_in": (
            "veth1a1311ea",
            "veth1ab2ce35",
            "veth23b72f28",
            "veth4d5ad56b",
            "veth63a0bdbf",
            "veth8189d14e",
            "veth9cfe6466",
            "vetha5d56989",
            "vethde56b93d",
            "vethe9298b11",
            "vethee72330e",
            "vethf347c1b6",
            "vethf59accf3",
        ),
        "Tx_out": (
            "veth0898283a",
            "veth1a1311ea",
            "veth3d1fc018",
            "veth4d5ad56b",
            "veth5dc2fb4d",
            "veth5f9eb48f",
            "veth63a0bdbf",
            "veth67ba92c8",
            "veth8189d14e",
            "veth8262aa09",
            "veth8de63f6a",
            "veth9cfe6466",
            "vetha5d56989",
            "vethd22aedbd",
            "vethde56b93d",
            "vethe9298b11",
            "vethee72330e",
            "vethf347c1b6",
            "vethf59accf3",
        ),
    },
}

MANUAL_FILTERS: set[ManualFilterKey] = {
    (MANUAL_FILTER_SOURCE_PREFIXES[source_name], f"{device}{MANUAL_FILTER_DIRECTIONS[direction]}")
    for source_name, direction_devices in MANUAL_FILTER_DEVICES.items()
    for direction, devices in direction_devices.items()
    for device in devices
}

UNIT_MULTIPLIERS: dict[str, float] = {
    "": 1.0,
    "%": 1.0,
    "k": 1_000.0,
    "K": 1_000.0,
    "M": 1_000_000.0,
    "G": 1_000_000_000.0,
    "b": 1.0,
    "B": 1.0,
    "kb": 1_000.0,
    "Kb": 1_000.0,
    "kB": 1_000.0,
    "KB": 1_000.0,
    "Mb": 1_000_000.0,
    "MB": 1_000_000.0,
    "Gb": 1_000_000_000.0,
    "GB": 1_000_000_000.0,
    "KiB": 1024.0,
    "MiB": 1024.0**2,
    "GiB": 1024.0**3,
    "b/s": 1.0,
    "B/s": 1.0,
    "kb/s": 1_000.0,
    "Kb/s": 1_000.0,
    "kB/s": 1_000.0,
    "KB/s": 1_000.0,
    "Mb/s": 1_000_000.0,
    "MB/s": 1_000_000.0,
    "Gb/s": 1_000_000_000.0,
    "GB/s": 1_000_000_000.0,
    "KiB/s": 1024.0,
    "MiB/s": 1024.0**2,
    "GiB/s": 1024.0**3,
    "ops/s": 1.0,
    "io/s": 1.0,
    "p/s": 1.0,
    "mp/s": 0.001,
    "s": 1.0,
    "ms": 0.001,
}

VALUE_RE = re.compile(r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")
FILENAME_RE = re.compile(r"[^A-Za-z0-9]+")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
DEFAULT_METRICS_ROOT = WORKSPACE_ROOT / "ops" / "metrics"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "OPS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess collected OPS Grafana metrics for FluxEV."
    )
    parser.add_argument(
        "--metrics-root",
        type=Path,
        default=DEFAULT_METRICS_ROOT,
        help="Path to raw /ops/metrics.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for processed CSV files.",
    )
    parser.add_argument(
        "--lower-quantile",
        type=float,
        default=0.01,
        help="Lower baseline quantile used for point labels.",
    )
    parser.add_argument(
        "--upper-quantile",
        type=float,
        default=0.99,
        help="Upper baseline quantile used for point labels.",
    )
    return parser.parse_args()


def safe_filename(value: str) -> str:
    cleaned = FILENAME_RE.sub("_", value).strip("_")
    return cleaned or "metric"


def category_dir_name(rule: FileRule) -> str:
    return safe_filename(rule.relative_dir)


def source_file_prefix(rule: FileRule) -> str:
    category_prefix = category_dir_name(rule)
    prefix = rule.source_prefix
    if prefix.startswith(f"{category_prefix}__"):
        return prefix.removeprefix(f"{category_prefix}__")
    return prefix


def parse_metric_value(value: object) -> float:
    if cast(bool, pd.isna(value)):
        return float("nan")
    if isinstance(value, int | float):
        return float(value)

    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "null", "none"}:
        return float("nan")

    match = VALUE_RE.match(text)
    if match is None:
        raise ValueError(f"Cannot parse metric value: {value!r}")

    number = float(match.group(1))
    unit = match.group(2).strip()
    multiplier = UNIT_MULTIPLIERS.get(unit)
    if multiplier is None:
        raise ValueError(f"Unsupported unit {unit!r} in value {value!r}")
    return number * multiplier


def select_column_events(selector: str, metric_name: str) -> tuple[EventName, ...] | None:
    if selector == "all_events":
        return ALL_EVENTS

    if selector == "cpu":
        return () if metric_name.startswith("Idle - ") else ("stress-test",)

    if selector == "disk_iops":
        return ALL_EVENTS if metric_name.startswith("sdd - ") else None

    if selector == "disk_throughput":
        return ("stress-test",) if metric_name == "sdd - Read" else None

    if selector == "disk_io_utilization":
        return ALL_EVENTS if metric_name == "sdd" else None

    if selector == "pressure":
        if metric_name.startswith("CPU - "):
            return ALL_EVENTS
        if metric_name.startswith("Memory - "):
            return ("stress-test",)
        return None

    if selector == "sockstat_memory_size":
        return ALL_EVENTS if metric_name == "TCP" else None

    if selector == "tcp_errors":
        if metric_name == "Segment Retransmits":
            return ALL_EVENTS
        if metric_name in {"RST Sent", "TCP Timeouts"}:
            return ("network-loss",)
        return None

    raise ValueError(f"Unknown selector: {selector}")


def build_labels(timestamps: pd.Series, event_names: tuple[EventName, ...]) -> pd.Series:
    labels = pd.Series(0, index=timestamps.index, dtype="int64")
    for event_name in event_names:
        event = EVENT_WINDOWS[event_name]
        mask = (timestamps >= event.start) & (timestamps < event.end)
        labels.loc[mask] = 1
    return labels


def build_point_labels(
    timestamps: pd.Series,
    values: pd.Series,
    event_names: tuple[EventName, ...],
    lower_quantile: float,
    upper_quantile: float,
) -> tuple[pd.Series, pd.Series, float, float]:
    window_labels = build_labels(timestamps, event_names)
    any_event_labels = build_labels(timestamps, ALL_EVENTS)
    baseline_values = cast(pd.Series, values[any_event_labels == 0]).dropna()
    if baseline_values.empty:
        raise ValueError("No baseline values outside experiment windows")

    lower_bound = float(baseline_values.quantile(lower_quantile))
    upper_bound = float(baseline_values.quantile(upper_quantile))
    outside_baseline_range = (values < lower_bound) | (values > upper_bound)
    point_labels = (window_labels.eq(1) & outside_baseline_range).astype("int64")
    return point_labels, window_labels, lower_bound, upper_bound


def should_skip_uninformative_veth_rx(
    rule: FileRule, metric_name: str, point_labels: pd.Series
) -> bool:
    is_target_network_source = rule.source_prefix in {
        "CPU_Memory_Net_Disk__Network_Traffic",
        "CPU_Memory_Net_Disk__Network_Saturation",
    }
    is_veth_rx = metric_name.startswith("veth") and metric_name.endswith(" - Rx in")
    return is_target_network_source and is_veth_rx and int(point_labels.sum()) == 0


def resolve_single_file(metrics_root: Path, rule: FileRule) -> Path:
    candidates = sorted((metrics_root / rule.relative_dir).glob(rule.filename_glob))
    if len(candidates) != 1:
        candidate_list = ", ".join(str(path) for path in candidates) or "none"
        raise FileNotFoundError(
            f"Expected one file for {rule.relative_dir}/{rule.filename_glob}, got "
            f"{len(candidates)}: {candidate_list}"
        )
    return candidates[0]


def process_rule(
    metrics_root: Path,
    output_dir: Path,
    rule: FileRule,
    manual_filters: set[ManualFilterKey],
    lower_quantile: float,
    upper_quantile: float,
) -> list[dict[str, object]]:
    source_path = resolve_single_file(metrics_root, rule)
    source_df = pd.read_csv(source_path)
    if "Time" not in source_df.columns:
        raise ValueError(f"{source_path} does not contain a Time column")

    timestamps = cast(pd.Series, pd.to_datetime(source_df["Time"]))
    records: list[dict[str, object]] = []

    for metric_name in source_df.columns[1:]:
        event_names = select_column_events(rule.selector, metric_name)
        if event_names is None:
            continue
        if (rule.source_prefix, metric_name) in manual_filters:
            continue

        output_name = f"{source_file_prefix(rule)}__{safe_filename(metric_name)}.csv"
        output_subdir = output_dir / category_dir_name(rule)
        output_subdir.mkdir(parents=True, exist_ok=True)
        output_path = output_subdir / output_name
        metric_values = cast(pd.Series, source_df[metric_name])
        value = metric_values.map(parse_metric_value)
        label, window_label, lower_bound, upper_bound = build_point_labels(
            timestamps, value, event_names, lower_quantile, upper_quantile
        )
        if should_skip_uninformative_veth_rx(rule, metric_name, label):
            continue

        metric_df = pd.DataFrame(
            {
                "timestamp": timestamps.dt.strftime("%Y-%m-%d %H:%M:%S"),
                "value": value,
                "label": label,
                "window_label": window_label,
            }
        )
        metric_df.to_csv(output_path, index=False)

        records.append(
            {
                "output_file": str(output_path.relative_to(output_dir)),
                "source_file": str(source_path.relative_to(metrics_root)),
                "metric_name": metric_name,
                "events": ";".join(event_names) if event_names else "",
                "rows": len(metric_df),
                "positive_labels": int(label.sum()),
                "window_positive_labels": int(window_label.sum()),
                "baseline_p01": lower_bound,
                "baseline_p99": upper_bound,
            }
        )

    return records


def process_ops_metrics(
    metrics_root: str | Path = DEFAULT_METRICS_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> pd.DataFrame:
    if not 0 <= lower_quantile < upper_quantile <= 1:
        raise ValueError(
            "--lower-quantile and --upper-quantile must satisfy 0 <= lower < upper <= 1"
        )

    metrics_root = Path(metrics_root).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_records: list[dict[str, object]] = []
    for rule in FILE_RULES:
        manifest_records.extend(
            process_rule(
                metrics_root,
                output_dir,
                rule,
                MANUAL_FILTERS,
                lower_quantile,
                upper_quantile,
            )
        )

    manifest_df = pd.DataFrame(manifest_records)
    manifest_df.to_csv(output_dir / "manifest.csv", index=False)
    print(f"Wrote {len(manifest_df)} metric files to {output_dir}")
    print(f"Manifest: {output_dir / 'manifest.csv'}")
    return manifest_df


def main() -> None:
    args = parse_args()
    process_ops_metrics(
        metrics_root=args.metrics_root,
        output_dir=args.output_dir,
        lower_quantile=args.lower_quantile,
        upper_quantile=args.upper_quantile,
    )


if __name__ == "__main__":
    main()
