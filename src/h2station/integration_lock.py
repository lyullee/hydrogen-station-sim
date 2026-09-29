"""Serialize calls into SciPy's non-reentrant ODEPACK integrator."""

from threading import RLock


nonreentrant_integrator_lock = RLock()
