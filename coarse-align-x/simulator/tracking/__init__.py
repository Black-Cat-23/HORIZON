"""
HORIZON Simulator Tracking Alias
========================================
Re-exports the top-level `tracking` package so that both:
    from tracking import ...
and
    from simulator.tracking import ...
function identically and reliably across the codebase.
"""

from tracking import *
from tracking import __all__
