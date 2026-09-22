"""
Phase 10 Analysis CLI Entry Point
=================================
Executes scientific validation, statistical hypothesis testing, failure mode taxonomy analysis, and report generation.

Usage:
    python -m analysis.run_analysis --results-dir results --output-report AUTOMATED_ENGINEERING_REPORT.md
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from analysis.report_generator import EngineeringReportGenerator
from analysis.reporting.report_builder import ReportBuilder
from analysis.reporting.export import DataExporter
from analysis.reporting.tables import TableFormatter

logger = logging.getLogger("analysis.run_analysis")


def main() -> None:
    parser = argparse.ArgumentParser(description="HORIZON Phase 10 Scientific Validation & Report Generator")
    parser.add_argument("--results-dir", type=str, default="results", help="Directory containing trial results")
    parser.add_argument("--html-report", type=str, default="HORIZON_VALIDATION_REPORT.html", help="Output path for HTML report")
    parser.add_argument("--md-report", type=str, default="PHASE10_VALIDATION_UPGRADE_REPORT.md", help="Output path for Markdown report")

    import sys
    args_list = None if (len(sys.argv) > 0 and "run_analysis" in sys.argv[0]) else []
    args = parser.parse_args(args=args_list)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    logger.info("Executing Phase 10 statistical validation analysis and report generation...")
    generator = EngineeringReportGenerator(trials_dir=args.results_dir)
    res = generator.generate_all_reports(
        html_out_path=args.html_report,
        md_out_path=args.md_report,
    )

    logger.info(f"Successfully generated HTML report: {res['html_report']}")
    logger.info(f"Successfully generated Markdown report: {res['markdown_report']}")
    print("PHASE 10 VALIDATION UPGRADE COMPLETE — REPORTS GENERATED")


if __name__ == "__main__":
    main()
