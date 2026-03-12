import numpy as np
from PIL import Image

INTENSITY_IDLE       = 150
INTENSITY_LISTENING  = 200
INTENSITY_THINKING   = 230
INTENSITY_RESPONDING = 200

_FIRE_W = 120
_FIRE_H = 150


def _build_lut():
    """Build a 256-entry RGB lookup table for the fire color gradient."""
    x_pts = [0,  64,  128, 192, 255]
    r_pts = [0,  80,  220, 255, 255]
    g_pts = [0,  0,   50,  160, 255]
    b_pts = [0,  0,   0,   0,   255]
    idx = np.arange(256, dtype=np.float32)
    lut = np.stack([
        np.interp(idx, x_pts, r_pts),
        np.interp(idx, x_pts, g_pts),
        np.interp(idx, x_pts, b_pts),
    ], axis=1).astype(np.uint8)
    return lut


_LUT = _build_lut()


class ForgeFlame:
    """Doom-style fire animation for the Pocket Forge status screen.

    Heat grid is (H=150, W=120), row 0 = top, row H-1 = bottom.
    The bottom row is seeded with a cosine-bell taper so the flame
    is hottest in the center and tapers to black at the edges, producing
    a natural teardrop shape as heat rises and spreads.
    render() updates state and returns a 120x150 PIL RGB Image each call.
    """

    def __init__(self):
        H, W = _FIRE_H, _FIRE_W
        self._intensity = float(INTENSITY_LISTENING)
        self._lut = _LUT
        self._rng = np.random.default_rng()

        # Pre-allocate index arrays reused every frame
        self._col_base = np.arange(W, dtype=np.int32)
        self._row_idx  = np.arange(1, H, dtype=np.int32)[:, np.newaxis]

        # Cosine-bell taper: 1.0 at center column, 0.0 at left/right edges.
        # Applied to the bottom-row seed so the flame naturally narrows upward.
        x = np.linspace(-1.0, 1.0, W)
        self._taper = (np.cos(x * np.pi / 2) ** 2).astype(np.float32)

        # Pre-warm the grid so fire is visible on the very first frame.
        # Each row starts with heat proportional to its distance from the top,
        # already shaped by the taper so the initial state matches steady state.
        self._heat = np.zeros((H, W), dtype=np.float32)
        for row in range(H):
            frac = (H - 1 - row) / float(H - 1)   # 1.0 at bottom, 0.0 at top
            self._heat[row] = self._intensity * self._taper * frac

    def set_intensity(self, value):
        self._intensity = float(value)

    def render(self):
        H, W = self._heat.shape

        # --- Propagate heat upward (vectorized, no Python loops) ---
        # spread: 0/1/2 → offset of -1/0/+1 from the column below
        # decay:  0 or 1
        spread = self._rng.integers(0, 3, size=(H - 1, W), dtype=np.uint8)
        decay  = self._rng.integers(0, 2, size=(H - 1, W), dtype=np.uint8)

        col_idx = np.clip(
            self._col_base[np.newaxis, :] + spread.astype(np.int32) - 1,
            0, W - 1,
        )

        self._heat[:-1] = np.maximum(
            0.0,
            self._heat[self._row_idx, col_idx] - decay,
        )

        # --- Seed bottom row: tapered intensity + noise ---
        noise = self._rng.uniform(-15.0, 15.0, size=(W,)).astype(np.float32)
        self._heat[-1] = np.clip(
            self._intensity * self._taper + noise,
            0.0, 255.0,
        )

        # --- Map heat values to RGB via lookup table ---
        rgb = self._lut[self._heat.astype(np.uint8)]   # shape (H, W, 3)
        return Image.fromarray(rgb, 'RGB')
