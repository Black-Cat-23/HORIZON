"""
Accuracy vs Latency Trade-off & Pareto Frontier Generator
=========================================================
Computes Pareto efficiency frontiers and generates embedded SVG charts for Accuracy vs Latency, Success vs Latency, and Robustness vs Latency.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


class TradeoffAnalyzer:
    """Computes trade-off metrics and Pareto frontiers across algorithm paths."""

    @staticmethod
    def compute_tradeoff_matrix(
        trials_by_alg: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Compute mean latency, accuracy score, success rate, and lock retention per algorithm."""
        summary: Dict[str, Dict[str, float]] = {}

        for alg, t_list in trials_by_alg.items():
            if not t_list:
                continue

            latencies = [t["metrics"].get("processing_time", 0.0) for t in t_list if "metrics" in t]
            errors = [t["metrics"].get("mean_tracking_error", 0.0) for t in t_list if "metrics" in t]
            rmse_errors = [t["metrics"].get("RMSE_tracking_error", 0.0) for t in t_list if "metrics" in t]
            successes = [1.0 if t.get("success", False) else 0.0 for t in t_list]
            locks = [t["metrics"].get("lock_retention_rate", 0.0) for t in t_list if "metrics" in t]

            mean_lat = float(np.mean(latencies)) if latencies else 0.0
            mean_err = float(np.mean(errors)) if errors else 0.0
            mean_rmse = float(np.mean(rmse_errors)) if rmse_errors else 0.0
            succ_rate = float(np.mean(successes)) * 100.0 if successes else 0.0
            lock_rate = float(np.mean(locks)) * 100.0 if locks else 0.0

            # Accuracy metric: 100 / (1 + mean_rmse)
            accuracy_score = 100.0 / (1.0 + mean_rmse)

            summary[alg] = {
                "latency_ms": mean_lat,
                "mean_error_px": mean_err,
                "rmse_error_px": mean_rmse,
                "accuracy_score": accuracy_score,
                "success_rate_pct": succ_rate,
                "robustness_score_pct": lock_rate,
            }

        # Identify Pareto optimal points (lower latency & higher accuracy/success)
        pareto_points = []
        for alg_a, data_a in summary.items():
            is_dominated = False
            for alg_b, data_b in summary.items():
                if alg_a == alg_b:
                    continue
                if (
                    data_b["latency_ms"] <= data_a["latency_ms"]
                    and data_b["accuracy_score"] >= data_a["accuracy_score"]
                    and (data_b["latency_ms"] < data_a["latency_ms"] or data_b["accuracy_score"] > data_a["accuracy_score"])
                ):
                    is_dominated = True
                    break
            if not is_dominated:
                pareto_points.append(alg_a)

        return {
            "algorithm_summary": summary,
            "pareto_frontier_algorithms": pareto_points,
        }

    @classmethod
    def generate_tradeoff_svg(cls, tradeoff_data: Dict[str, Any], metric_y: str = "accuracy_score", title: str = "Accuracy vs Latency") -> str:
        """Generate a lightweight SVG scatter chart representing accuracy/latency tradeoffs."""
        summary = tradeoff_data.get("algorithm_summary", {})
        if not summary:
            return "<svg width='400' height='200'><text x='20' y='100'>No Trade-off Data</text></svg>"

        points = []
        for alg, data in summary.items():
            points.append({
                "alg": alg,
                "x": data.get("latency_ms", 0.0),
                "y": data.get(metric_y, 0.0),
            })

        max_x = max([p["x"] for p in points] + [10.0]) * 1.2
        max_y = max([p["y"] for p in points] + [100.0]) * 1.1

        width, height = 500, 300
        pad_x, pad_y = 60, 40

        chart_w = width - 2 * pad_x
        chart_h = height - 2 * pad_y

        svg_lines = [
            f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' width='100%' height='280' style='background:#18181b; border-radius:8px; border:1px solid #27272a;'>",
            f"<text x='{width/2}' y='25' fill='#f4f4f5' font-family='sans-serif' font-size='14' font-weight='bold' text-anchor='middle'>{title}</text>",
            f"<line x1='{pad_x}' y1='{height-pad_y}' x2='{width-pad_x}' y2='{height-pad_y}' stroke='#52525b' stroke-width='1.5'/>",
            f"<line x1='{pad_x}' y1='{pad_y}' x2='{pad_x}' y2='{height-pad_y}' stroke='#52525b' stroke-width='1.5'/>",
            f"<text x='{width/2}' y='{height-10}' fill='#a1a1aa' font-family='sans-serif' font-size='11' text-anchor='middle'>Latency (ms)</text>",
            f"<text x='15' y='{height/2}' fill='#a1a1aa' font-family='sans-serif' font-size='11' text-anchor='middle' transform='rotate(-90 15 {height/2})'>{title.split(' vs ')[0]}</text>",
        ]

        colors = {"B0": "#ef4444", "B1": "#f59e0b", "B2": "#3b82f6", "OURS": "#10b981"}

        for p in points:
            cx = pad_x + (p["x"] / max_x) * chart_w
            cy = (height - pad_y) - (p["y"] / max_y) * chart_h
            color = colors.get(p["alg"], "#a855f7")

            svg_lines.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='7' fill='{color}' stroke='#ffffff' stroke-width='1.5'/>")
            svg_lines.append(f"<text x='{cx + 10:.1f}' y='{cy + 4:.1f}' fill='#f4f4f5' font-family='sans-serif' font-size='12' font-weight='600'>{p['alg']} ({p['x']:.1f}ms, {p['y']:.1f})</text>")

        svg_lines.append("</svg>")
        return "\n".join(svg_lines)
