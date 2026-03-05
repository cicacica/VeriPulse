"""
Collection of gate definitions used in MBQC
"""

import numpy as np
from numpy import cos, sin, exp

# Type aliases
Matrix = np.ndarray


def rz(theta: float) -> Matrix:
    """
    Rotation around Z: Exp[-i theta/2 Z].
    State preparation in the XY-plane can be obtained by application of  rz(theta)|+>
    """
    return np.array([[1, 0], [0, exp(1j * theta)]])


def rx(theta: float) -> Matrix:
    """
    Rotation around X: Exp[-i theta/2 X].
    State preparation in the YZ-plane can be obtained by application of  rx(theta)|0>
    """
    return np.array(
        [
            [1, 0],
            [
                0,
            ],
        ]
    )


def rhox(theta: float) -> Matrix:
    """
    Returns rho_theta: |theta><theta|  as the prepared state for YZ blind quantum computing
    """
    return np.array(
        [
            [cos(theta / 2) ** 2, 1j * 0.5 * sin(theta)],
            [-1j * 0.5 * sin(theta), sin(theta / 2) ** 2],
        ]
    )


def rhoz(theta: float) -> Matrix:
    """
    Returns rho_theta: |theta><theta|  as the prepared state for XY blind quantum computing
    """
    return np.array([[0.5, 0.5 * exp(-1j * theta)], [0.5 * exp(1j * theta), 0.5]])
