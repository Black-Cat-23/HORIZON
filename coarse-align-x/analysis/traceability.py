"""
Claim Traceability Lineage Matrix Engine
========================================
Maps every reported numeric claim and statistical value in technical validation reports
to its exact underlying source lineage tuple: (experiment_id, seed, scenario_id, metric_name, analysis_method).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class ClaimTraceabilityMatrix:
    """Tracks and registers empirical evidence claims for 100% audit traceability."""

    def __init__(self) -> None:
        self.claims: List[Dict[str, Any]] = []

    def register_claim(
        self,
        claim_id: str,
        value: Any,
        experiment_id: str,
        seed: Optional[int],
        scenario_id: str,
        metric_name: str,
        analysis_method: str,
    ) -> Dict[str, Any]:
        """Register a single claim mapping to its exact audit lineage."""
        claim_entry = {
            "claim_id": claim_id,
            "value": value,
            "experiment_id": experiment_id,
            "seed": seed if seed is not None else "AGGREGATED_ALL",
            "scenario_id": scenario_id,
            "metric_name": metric_name,
            "analysis_method": analysis_method,
        }
        self.claims.append(claim_entry)
        return claim_entry

    def generate_traceability_table_markdown(self) -> str:
        """Generate Markdown table rendering for claim traceability."""
        lines = [
            "### Empirical Claim Traceability Matrix",
            "| Claim ID | Value | Experiment ID | Seed | Scenario | Metric | Analysis Method |",
            "|---|---|---|---|---|---|---|",
        ]
        for c in self.claims:
            lines.append(
                f"| `{c['claim_id']}` | **{c['value']}** | `{c['experiment_id']}` | `{c['seed']}` | `{c['scenario_id']}` | `{c['metric_name']}` | `{c['analysis_method']}` |"
            )
        return "\n".join(lines)

    def generate_traceability_table_html(self) -> str:
        """Generate HTML table rendering for claim traceability."""
        lines = [
            "<div class='table-responsive'>",
            "<table class='matrix-table'>",
            "<thead><tr><th>Claim ID</th><th>Value</th><th>Experiment ID</th><th>Seed</th><th>Scenario</th><th>Metric</th><th>Analysis Method</th></tr></thead>",
            "<tbody>",
        ]
        for c in self.claims:
            lines.append(
                f"<tr><td><code>{c['claim_id']}</code></td><td><strong>{c['value']}</strong></td><td><code>{c['experiment_id']}</code></td><td><code>{c['seed']}</code></td><td><code>{c['scenario_id']}</code></td><td><code>{c['metric_name']}</code></td><td><code>{c['analysis_method']}</code></td></tr>"
            )
        lines.append("</tbody></table></div>")
        return "\n".join(lines)
