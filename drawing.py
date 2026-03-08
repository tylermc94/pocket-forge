"""
Drawing game for Pocket Forge.

Controls:
  Trackball move  — move cursor; leaves a rainbow trail in draw mode
  Trackball click — toggle draw / move mode
  Hold click      — exit back to Games menu
  HAT button      — exit back to Games menu
"""

import colorsys
from PIL import Image, ImageDraw

import state
import display


def start_drawing():
    """Initialise drawing state and enter DRAWING mode."""
    state.drawing_canvas   = Image.new('RGB', (240, 280), color=(0, 0, 0))
    state.drawing_draw_ctx = ImageDraw.Draw(state.drawing_canvas)
    state.drawing_mode     = True   # start in draw mode
    state.drawing_hue      = 0.0
    state.drawing_cursor_x = 120
    state.drawing_cursor_y = 140
    state.drawing_dirty    = True
    state.drawing_dx_acc   = 0
    state.drawing_dy_acc   = 0
    state.drawing_exit_requested = False
    state.current_state    = state.AppState.DRAWING
    display.draw_drawing_screen()


def stop_drawing():
    """Clean up drawing state and return to the Games menu."""
    state.drawing_canvas   = None
    state.drawing_draw_ctx = None
    state.drawing_dirty    = False

    # Import here to avoid a circular import at module load time
    import menus
    menus.enter_submenu(state.AppState.GAMES_MENU, state.games_menu_items, "Games")


def toggle_mode():
    """Toggle between draw and move mode and mark display dirty."""
    state.drawing_mode  = not state.drawing_mode
    state.drawing_dirty = True


def clear_canvas():
    """Erase the canvas back to black."""
    if state.drawing_draw_ctx is not None:
        state.drawing_draw_ctx.rectangle((0, 0, 239, 279), fill=(0, 0, 0))
    state.drawing_dirty = True


def handle_movement(raw_dx, raw_dy):
    """
    Process a raw trackball delta (right-left, down-up).

    Cursor speed scales with state.SCROLL_SENSITIVITY so the sensitivity
    setting the user chose in Settings applies here too.
    """
    state.drawing_dx_acc += raw_dx
    state.drawing_dy_acc += raw_dy

    # One pixel of cursor movement per SCROLL_SENSITIVITY raw ticks — mirrors
    # the scroll-accumulator pattern used everywhere else in the main loop.
    thresh = max(1, state.SCROLL_SENSITIVITY)

    dx = 0
    if abs(state.drawing_dx_acc) >= thresh:
        dx = state.drawing_dx_acc // thresh
        state.drawing_dx_acc -= dx * thresh

    dy = 0
    if abs(state.drawing_dy_acc) >= thresh:
        dy = state.drawing_dy_acc // thresh
        state.drawing_dy_acc -= dy * thresh

    if dx == 0 and dy == 0:
        return

    old_x = state.drawing_cursor_x
    old_y = state.drawing_cursor_y
    new_x = max(0, min(239, old_x + dx))
    new_y = max(0, min(279, old_y + dy))

    if state.drawing_mode and state.drawing_draw_ctx is not None:
        # Line thickness 1-3 px depending on movement speed this frame
        speed     = abs(dx) + abs(dy)
        thickness = 1 if speed <= 1 else 2 if speed <= 3 else 3

        r, g, b = colorsys.hsv_to_rgb(state.drawing_hue, 1.0, 1.0)
        color   = (int(r * 255), int(g * 255), int(b * 255))

        state.drawing_draw_ctx.line(
            [(old_x, old_y), (new_x, new_y)],
            fill=color, width=thickness,
        )

        # Advance hue a tiny step so the color cycles as you draw
        state.drawing_hue = (state.drawing_hue + 0.003) % 1.0

    state.drawing_cursor_x = new_x
    state.drawing_cursor_y = new_y
    state.drawing_dirty    = True
