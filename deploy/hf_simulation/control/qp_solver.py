import osqp
import numpy as np
import scipy.sparse as sparse

class QPSolver:
    """Lightweight wrapper around OSQP for solving small QPs.

    The problem is defined as:
        minimize 0.5 * x.T @ H @ x + f.T @ x
        subject to A @ x <= b
    where H is positive definite.
    """

    def __init__(self, max_solve_time_ms: float = 5.0):
        self.max_solve_time_ms = max_solve_time_ms
        self.solver = None
        self.last_solution = None

    def setup(self, H: np.ndarray, f: np.ndarray, A: np.ndarray, b: np.ndarray) -> None:
        # Convert to CSC format required by OSQP
        P = sparse.csc_matrix((H + H.T) / 2.0)  # ensure symmetry
        q = f.astype(np.float64)
        A_csc = sparse.csc_matrix(A)
        l = -np.inf * np.ones_like(b)
        u = b.astype(np.float64)
        self.solver = osqp.OSQP()
        self.solver.setup(P=P, q=q, A=A_csc, l=l, u=u, polish=True, eps_abs=1e-5, eps_rel=1e-5, max_iter=10000, warm_start=True, time_limit=self.max_solve_time_ms / 1000.0)

    def solve(self, warm_start: bool = True):
        if warm_start and self.last_solution is not None:
            self.solver.warm_start(x=self.last_solution)
        result = self.solver.solve()
        if result.info.status != 'solved':
            return None, result.info.status, result.info.solve_time
        x = result.x
        self.last_solution = x
        return x, result.info.status, result.info.solve_time

