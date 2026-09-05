"""
Test Reproducibility & Report Generation
"""
from analysis.reporting.report_builder import ReportBuilder

def test_report_builder(tmp_path):
    builder = ReportBuilder()
    data = {
        "total_trials": 10,
        "algorithms": {
            "OURS": {
                "success_rate": 0.5,
                "ci_low": 0.3,
                "ci_high": 0.7,
                "lock_retention": 0.8,
                "mean_error": 12.5,
                "rmse": 15.0,
                "p95": 25.0,
                "latency": 10.0,
            }
        }
    }
    md_file = tmp_path / "test_report.md"
    html_file = tmp_path / "test_report.html"
    builder.build_markdown_report(data, str(md_file))
    builder.build_html_report(data, str(html_file))

    assert md_file.exists()
    assert html_file.exists()
