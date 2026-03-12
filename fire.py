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
    render() updates state and returns a 120x150 PIL RGB Image each call.
    """

    def __init__(self):
        self._heat = np.zeros((_FIRE_H, _FIRE_W), dtype=np.float32)
        self._intensity = float(INTENSITY_LISTENING)
        self._lut = _LUT

    def set_intensity(self, value):
        self._intensity = float(value)

    def render(self):
        H, W = self._heat.shape

        # --- Propagate heat upward (vectorized, no Python loops) ---
        # For each pixel in rows 0..H-2, pull from the row below with
        # a random horizontal spread of -1/0/+1 and subtract a small decay.
        spread = np.random.randint(-1, 2, size=(H - 1, W), dtype=np.int32)
        decay  = np.random.uniform(0.0, 2.0, size=(H - 1, W)).astype(np.float32)

        col_idx = np.clip(
            np.arange(W, dtype=np.int32)[np.newaxis, :] + spread,
            0, W - 1,
        )
        row_idx = np.arange(1, H, dtype=np.int32)[:, np.newaxis]

        self._heat[:-1] = np.maximum(0.0, self._heat[row_idx, col_idx] - decay)

        # --- Seed bottom row each frame ---
        noise = np.random.uniform(-20.0, 20.0, size=(W,)).astype(np.float32)
        self._heat[-1] = np.clip(self._intensity + noise, 0.0, 255.0)

        # --- Map heat values to RGB via lookup table ---
        heat_idx = self._heat.astype(np.uint8)  # clips float to uint8 range
        rgb = self._lut[heat_idx]               # shape (H, W, 3)
        return Image.fromarray(rgb, 'RGB')
