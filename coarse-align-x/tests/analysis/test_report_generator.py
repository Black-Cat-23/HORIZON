"""
Unit & Integration tests for EngineeringReportGenerator.
"""

from analysis.report_generator import EngineeringReportGenerator


def test_engineering_report_generator(tmp_path):
    out_file = tmp_path / "TEST_REPORT.md"
    gen = EngineeringReportGenerator(trials_dir="results/trials")
    content = gen.generate_report(output_path=out_file)

    assert out_file.exists()
    assert "# HORIZON COARSE-ALIGN-X — Automated Engineering Validation Report" in content
    assert "Baseline Battlefield Comparison Matrix" in content
