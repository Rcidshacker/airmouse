# core/filter.py
"""
1€ Filter — Casiez, Roussel, Vogel (CHI 2012)
Speed-dependent adaptive low-pass filter that eliminates jitter at rest
and removes lag during fast motion. Strictly outperforms Kalman for 2D cursor paths.

Paper: https://doi.org/10.1145/2207676.2208639
"""

import math
import time


class _LowPassFilter:
    """Single exponential low-pass filter — internal building block."""

    def __init__(self, alpha: float):
        self._alpha = alpha
        self._y: float | None = None
        self._s: float | None = None

    def set_alpha(self, alpha: float) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        self._alpha = alpha

    def filter(self, value: float) -> float:
        if self._y is None:
            self._y = value
            self._s = value
        else:
            self._y = self._alpha * value + (1.0 - self._alpha) * self._s
            self._s = self._y
        return self._y

    @property
    def last_value(self) -> float | None:
        return self._s


def _smoothing_factor(t_e: float, cutoff: float) -> float:
    """Compute alpha from time elapsed and cutoff frequency."""
    r = 2.0 * math.pi * cutoff * t_e
    return r / (r + 1.0)


class OneEuroFilter:
    """
    1€ Filter for a single scalar dimension.
    Instantiate one per axis (x and y tracked separately).

    Args:
        freq:      Nominal sampling frequency in Hz (e.g., 60.0)
        mincutoff: Minimum cutoff frequency — lower reduces jitter at rest
        beta:      Speed coefficient — higher reduces lag during fast motion
        dcutoff:   Cutoff for derivative; leave at 1.0 unless you have a reason
    """

    def __init__(
        self,
        freq: float,
        mincutoff: float = 1.0,
        beta: float = 0.007,
        dcutoff: float = 1.0,
    ) -> None:
        if freq <= 0:
            raise ValueError("freq must be positive")
        self._freq = freq
        self._mincutoff = mincutoff
        self._beta = beta
        self._dcutoff = dcutoff
        self._x = _LowPassFilter(_smoothing_factor(1.0 / freq, mincutoff))
        self._dx = _LowPassFilter(_smoothing_factor(1.0 / freq, dcutoff))
        self._last_time: float | None = None

    def __call__(self, x: float, timestamp: float | None = None) -> float:
        """
        Filter a new scalar sample.

        Args:
            x:         Raw input value
            timestamp: Wall-clock time in seconds; if None, uses 1/freq increment

        Returns:
            Smoothed value
        """

        if timestamp is None:
            timestamp = time.perf_counter()

        if self._last_time is None:
            t_e = 1.0 / self._freq
        else:
            t_e = timestamp - self._last_time
            if t_e <= 0:
                t_e = 1.0 / self._freq  # guard against clock anomalies

        self._last_time = timestamp

        # Set derivative filter alpha BEFORE filtering (correct 1€ filter order)
        edx_alpha = _smoothing_factor(t_e, self._dcutoff)
        self._dx.set_alpha(edx_alpha)

        # Estimate derivative: dx/dt using actual elapsed time, not nominal frequency
        dx = 0.0 if self._x.last_value is None else (x - self._x.last_value) / t_e
        edx = self._dx.filter(dx)

        # Adaptive cutoff: increases with speed
        cutoff = self._mincutoff + self._beta * abs(edx)

        # Filter position
        alpha = _smoothing_factor(t_e, cutoff)
        self._x.set_alpha(alpha)
        return self._x.filter(x)
