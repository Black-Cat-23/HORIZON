"""
Test Ablation & Pareto Frontier
"""
from analysis.comparison.ablation import AblationAnalyzer
from analysis.comparison.pareto import ParetoFrontier

def test_ablation():
    analyzer = AblationAnalyzer()
    res = analyzer.evaluate_ablation({})
    assert "A" in res
    assert "E" in res

def test_pareto_frontier():
    points = [
        {"algorithm": "B0", "mean_error_px": 100.0, "mean_latency_ms": 5.0},
        {"algorithm": "B1", "mean_error_px": 50.0, "mean_latency_ms": 10.0},
        {"algorithm": "OURS", "mean_error_px": 20.0, "mean_latency_ms": 15.0},
    ]
    frontier = ParetoFrontier.calculate_pareto_frontier(points)
    assert len(frontier) > 0
