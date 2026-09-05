"""
HORIZON Covariance Mathematics & Diagnostics
===================================================
Numerical validation, symmetry enforcement, positive semi-definiteness
checks, and spectral decomposition for covariance uncertainty ellipses.

Strict Invariant: Zero access to true target position or ground-truth state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class CovarianceEllipseData:
    """Parametric representation of a 2D positional covariance ellipse."""
    center_x: float
    center_y: float
    semi_major_axis: float
    semi_minor_axis: float
    major_axis: float        # Total diameter = 2 * semi_major
    minor_axis: float        # Total diameter = 2 * semi_minor
    orientation_deg: float   # Angle of major axis relative to +X axis [degrees]
    confidence_level: float  # e.g., 0.95 for 95% containment


def validate_covariance(
    P: np.ndarray,
    tol: float = 1e-6,
) -> Tuple[bool, str]:
    """Validate numerical properties of a covariance matrix.

    Checks:
      1. Correct shape (4×4 or 2×2 square matrix).
      2. All elements are finite (no NaN, no Inf).
      3. Matrix is symmetric within numerical tolerance tol.
      4. Diagonal elements are non-negative.
      5. Matrix is positive semi-definite (all eigenvalues >= -tol).

    Args:
        P: Covariance matrix array.
        tol: Numerical tolerance for symmetry and PSD tests.

    Returns:
        (is_valid, reason_str)
    """
    if not isinstance(P, np.ndarray):
        return False, "Covariance is not a numpy array"

    if P.ndim != 2 or P.shape[0] != P.shape[1]:
        return False, f"Covariance must be 2D square matrix, got shape {P.shape}"

    if not np.all(np.isfinite(P)):
        return False, "Covariance contains non-finite values (NaN or Inf)"

    # Symmetry check
    asym = np.max(np.abs(P - P.T))
    if asym > tol:
        return False, f"Covariance asymmetry {asym:.2e} exceeds tolerance {tol:.2e}"

    # Diagonal check
    diag = np.diag(P)
    if np.any(diag < -tol):
        return False, f"Covariance has negative diagonal element: {diag.min():.2e}"

    # Positive semi-definiteness via eigenvalues
    eigvals = np.linalg.eigvalsh(0.5 * (P + P.T))
    min_eig = float(np.min(eigvals))
    if min_eig < -tol:
        return False, f"Covariance has negative eigenvalue: {min_eig:.2e}"

    return True, "Valid"


def enforce_symmetry(P: np.ndarray) -> np.ndarray:
    """Enforce exact symmetry and non-negative diagonal on a covariance matrix.

    P_sym = 0.5 * (P + P^T)
    """
    P_sym = 0.5 * (P + P.T)
    # Clip any tiny negative numerical roundoff on the diagonal
    np.fill_diagonal(P_sym, np.maximum(np.diag(P_sym), 0.0))
    return P_sym


def compute_covariance_ellipse(
    P: np.ndarray,
    center_x: float = 0.0,
    center_y: float = 0.0,
    confidence_level: float = 0.95,
) -> CovarianceEllipseData:
    """Compute parametric 2D error ellipse from a 4×4 or 2×2 covariance matrix.

    Mathematical Derivation:
        Extracts 2×2 positional submatrix P_pos = P[0:2, 0:2].
        Eigendecomposition: P_pos * v = lambda * v.
        For a 2D Gaussian distribution, the squared Mahalanobis distance
        follows a Chi-squared distribution with 2 degrees of freedom:
            k = sqrt(-2 * ln(1 - confidence_level))
        For confidence_level = 0.95:
            k = sqrt(-2 * ln(0.05)) = sqrt(5.991) ≈ 2.4477
        For 1-sigma (k = 1.0, confidence ≈ 0.393):
            k = 1.0

        Semi-major axis = k * sqrt(max(lambda_1, lambda_2))
        Semi-minor axis = k * sqrt(min(lambda_1, lambda_2))
        Orientation angle = atan2(v_y, v_x) of the principal eigenvector.

    Args:
        P: 4×4 state covariance matrix or 2×2 positional covariance matrix.
        center_x: Ellipse center horizontal coordinate [px].
        center_y: Ellipse center vertical coordinate [px].
        confidence_level: Enclosed probability in (0.0, 1.0), default 0.95.

    Returns:
        CovarianceEllipseData containing axes, orientation, and center.
    """
    if P.shape[0] >= 2 and P.shape[1] >= 2:
        P_pos = P[0:2, 0:2].copy()
    else:
        raise ValueError(f"Matrix shape {P.shape} too small for 2D position extraction")

    P_pos = enforce_symmetry(P_pos)

    # Chi-square scaling factor for 2 DOF
    conf = float(np.clip(confidence_level, 0.01, 0.9999))
    k = math.sqrt(-2.0 * math.log(1.0 - conf))

    # Eigen decomposition (eigvalsh guarantees sorted ascending real eigenvalues)
    eigvals, eigvecs = np.linalg.eigh(P_pos)

    # Ensure non-negative
    l1 = max(0.0, float(eigvals[1]))  # larger eigenvalue
    l2 = max(0.0, float(eigvals[0]))  # smaller eigenvalue

    semi_major = k * math.sqrt(l1)
    semi_minor = k * math.sqrt(l2)

    # Principal eigenvector corresponds to the largest eigenvalue (index 1)
    v_major = eigvecs[:, 1]
    angle_rad = math.atan2(v_major[1], v_major[0])
    angle_deg = math.degrees(angle_rad)

    return CovarianceEllipseData(
        center_x=float(center_x),
        center_y=float(center_y),
        semi_major_axis=float(semi_major),
        semi_minor_axis=float(semi_minor),
        major_axis=float(2.0 * semi_major),
        minor_axis=float(2.0 * semi_minor),
        orientation_deg=float(angle_deg),
        confidence_level=conf,
    )
