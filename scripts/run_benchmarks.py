"""Run the load grid against one deployment and collect three Markdown tables."""

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def percentiles(report, metric):
    return " / ".join(f"{report[metric][p]:.2f}" for p in ("p50", "p95", "p99"))


def result_row(report, language, mode, value):
    cells = [
        language.upper(),
        f"{'RPS' if mode == 'rps' else 'concurrency'}={value}",
        percentiles(report, "time_to_first_token"),
        percentiles(report, "inter_token_latency"),
        percentiles(report, "request_latency"),
        f"{report['output_token_throughput']['avg']:.2f}",
        percentiles(report, "output_sequence_length"),
    ]
    for metric in (
        "spec_decode_overall_draft_acceptance_rate",
        "spec_decode_token_weighted_acceptance_length",
    ):
        metric_value = report.get(metric, {}).get("avg")
        cells.append("—" if metric_value is None else f"{metric_value:.2f}")
    return "| " + " | ".join(cells) + " |"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rps", nargs="*", type=float, default=[1, 2, 4, 8, 16])
    parser.add_argument("--concurrency", nargs="*", type=int, default=[1])
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "results" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
    )
    args = parser.parse_args()
    loads = [("concurrency", str(value)) for value in args.concurrency]
    loads += [("rps", f"{value:g}") for value in args.rps]
    if not loads:
        parser.error("Specify at least one RPS or concurrency value")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    summary = output_dir / "tables.md"
    lines = [
        "# Результаты одного деплоя",
        "",
        "Разминка: 30 с; подача нагрузки: 120 с. Время ожидания ответов — по умолчанию AIPerf.",
        "Перцентили в ячейках: p50 / p95 / p99. TPOT соответствует inter_token_latency в AIPerf.",
    ]
    for target in (100, 500, 1000):
        lines += [
            "", f"## Декод ≈ {target} токенов", "",
            "| Язык | Нагрузка | TTFT p50/p95/p99, мс | TPOT p50/p95/p99, мс | Latency p50/p95/p99, мс | Output tokens/s | Длина p50/p95/p99, токены | Acceptance Rate, % | Acceptance Length |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for language in ("ru", "en"):
            for mode, value in loads:
                profile = f"{language}_{target}"
                run_dir = output_dir / f"{profile}_{mode}_{value}"
                print(f"Running {profile}: {mode}={value}", flush=True)
                subprocess.run(
                    ["bash", str(ROOT / "scripts/benchmark.sh"),
                     profile, mode, value, str(run_dir)],
                    cwd=ROOT, check=True,
                )
                report = json.loads((run_dir / "profile_export_aiperf.json").read_text())
                if report.get("was_cancelled") or report.get("is_complete") is False:
                    raise RuntimeError(f"Incomplete benchmark: {run_dir}")
                lines.append(result_row(report, language, mode, value))
                summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Tables saved to {summary}")


if __name__ == "__main__":
    main()
