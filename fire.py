import numpy as np
from PIL import Image

INTENSITY_IDLE       = 150
INTENSITY_LISTENING  = 200
INTENSITY_THINKING   = 230
INTENSITY_RESPONDING = 200

_FIRE_W = 120
_FIRE_H = 150


def _build_lut():
    """256-entry RGB lookup table for the fire colour gradient."""
    x_pts = [0,   64,  128, 192, 255]
    r_pts = [0,   80,  220, 255, 255]
    g_pts = [0,   0,   50,  160, 255]
    b_pts = [0,   0,   0,   0,   255]
    idx = np.arange(256, dtype=np.float32)
    lut = np.stack([
        np.interp(idx, x_pts, r_pts),
        np.interp(idx, x_pts, g_pts),
        np.interp(idx, x_pts, b_pts),
    ], axis=1).astype(np.uint8)
    return lut


def _build_shape_mask(H, W):
    """Return a (H, W) float32 teardrop mask.

    The mask is 1.0 at the centre of the bottom row and narrows to a point
    at the top row.  It is applied every frame *at render time only* so that
    the heat grid can diffuse freely while the visible output is always
    constrained to the teardrop silhouette.

    Width at each row scales with frac**exp where frac runs from 1.0
    (bottom) to 0.0 (top).  The cosine-squared profile gives smooth
    fall-off within each row rather than a sharp hard edge.
    """
    x    = np.linspace(-1.0, 1.0, W, dtype=np.float32)          # (W,)
    frac = (H - 1 - np.arange(H, dtype=np.float32)) / float(H - 1)  # (H,)

    # stretch: 1.0 at the bottom, ~0 at the top.
    # Exponent < 1 keeps the flame wider for longer before it tapers.
    stretch = (frac ** 0.55)[:, np.newaxis] + 1e-4              # (H, 1)

    # Clip so cos() never gets an argument outside [-π/2, π/2].
    arg  = np.clip(x[np.newaxis, :] / stretch, -1.0, 1.0)       # (H, W)
    mask = (np.cos(arg * (np.pi / 2)) ** 2).astype(np.float32)  # (H, W)
    return mask


_LUT  = _build_lut()
_MASK = _build_shape_mask(_FIRE_H, _FIRE_W)


class ForgeFlame:
    """Doom-style fire animation for the Pocket Forge status screen.

    Heat grid is (H=150, W=120), row 0 = top, row H-1 = bottom.

    The Doom propagation algorithm naturally fills the full grid width in
    steady state regardless of the seed shape.  The teardrop silhouette is
    enforced by multiplying a precomputed 2-D mask into the heat values at
    render time (display only — the mask does not modify self._heat so
    propagation is unaffected).

    render() advances the simulation one step and returns a 120×150 PIL
    RGB Image.
    """

    def __init__(self):
        H, W = _FIRE_H, _FIRE_W
        self._intensity = float(INTENSITY_LISTENING)
        self._lut  = _LUT
        self._mask = _MASK
        self._rng  = np.random.default_rng()

        # Pre-allocate index arrays — reused every frame, no per-call allocation.
        self._col_base = np.arange(W, dtype=np.int32)
        self._row_idx  = np.arange(1, H, dtype=np.int32)[:, np.newaxis]

        # Pre-warm grid so fire appears immediately on the first render() call.
        # Seed with intensity × mask × height-fraction so the initial state
        # already resembles the steady-state teardrop.
        frac = (H - 1 - np.arange(H, dtype=np.float32)) / float(H - 1)
        self._heat = (
            self._intensity * self._mask * frac[:, np.newaxis]
        ).astype(np.float32)

    def set_intensity(self, value: float) -> None:
        self._intensity = float(value)

    def render(self):
        """Advance one simulation step; return a 120×150 PIL RGB Image."""
        H, W = self._heat.shape

        # ── Propagate heat upward (fully vectorised, no Python loops) ─────────
        # One random call: mod-3 gives spread offset (-1/0/+1),
        # floor-div-3 gives decay (0 or 1).  Halves random-generation cost.
        rng_val = self._rng.integers(0, 6, size=(H - 1, W), dtype=np.uint8)
        spread  = rng_val % 3                          # 0/1/2  →  -1/0/+1
        decay   = (rng_val // 3).astype(np.float32)   # 0 or 1

        col_idx = np.clip(
            self._col_base[np.newaxis, :] + spread.astype(np.int32) - 1,
            0, W - 1,
        )

        self._heat[:-1] = np.maximum(
            0.0,
            self._heat[self._row_idx, col_idx] - decay,
        )

        # ── Seed bottom row: full-width with small random variation ───────────
        noise = self._rng.uniform(-15.0, 15.0, size=(W,)).astype(np.float32)
        self._heat[-1] = np.clip(self._intensity + noise, 0.0, 255.0)

        # ── Render: apply teardrop mask, then map through colour LUT ──────────
        # heat_display is a masked copy used only for colour lookup;
        # self._heat is left unmodified so propagation is unaffected.
        heat_display = self._heat * self._mask          # (H, W) float32
        rgb = self._lut[heat_display.astype(np.uint8)]  # (H, W, 3) uint8
        return Image.fromarray(rgb, 'RGB')
