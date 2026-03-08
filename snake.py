"""
Snake game for Pocket Forge.

Controls:
  Trackball direction — change snake direction (up/down/left/right)
  Hold click          — pause / resume
  Hold (game over)    — exit to Games menu

Grid: 24x24 cells (10px each), play area 240x240, HUD below.
"""

import random
import time

import state
import display
import logger


COLS = 24
ROWS = 24


def start_snake():
    """Initialise snake state and enter SNAKE mode."""
    state.snake_body      = [(12, 12), (11, 12), (10, 12)]
    state.snake_direction = (1, 0)
    state.snake_alive     = True
    state.snake_score     = 0
    state.snake_speed     = 6
    state.snake_last_move = time.time()
    state.snake_paused    = False
    _spawn_food()
    state.current_state = state.AppState.SNAKE
    display.draw_snake_screen()
    logger.debug_log("Snake game started")


def stop_snake():
    """Clean up and return to Games menu."""
    state.snake_body = []
    import menus
    menus.enter_submenu(state.AppState.GAMES_MENU, state.games_menu_items, "Games")
    logger.debug_log("Snake game exited")


def _spawn_food():
    """Place food at a random cell not occupied by the snake."""
    occupied = set(state.snake_body)
    attempts = 0
    while attempts < 200:
        pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if pos not in occupied:
            state.snake_food = pos
            return
        attempts += 1
    # Fallback: just place it somewhere
    state.snake_food = (0, 0)


def set_direction(dx, dy):
    """Set direction if not reversing into self."""
    cur_dx, cur_dy = state.snake_direction
    # Prevent 180-degree turn
    if (dx, dy) != (-cur_dx, -cur_dy):
        state.snake_direction = (dx, dy)


def tick():
    """Advance snake by one step. Returns True if display needs redraw."""
    if not state.snake_alive or state.snake_paused:
        return False

    now = time.time()
    interval = 1.0 / state.snake_speed
    if now - state.snake_last_move < interval:
        return False

    state.snake_last_move = now

    head_x, head_y = state.snake_body[0]
    dx, dy = state.snake_direction
    new_x = head_x + dx
    new_y = head_y + dy

    # Wall collision
    if new_x < 0 or new_x >= COLS or new_y < 0 or new_y >= ROWS:
        state.snake_alive = False
        logger.debug_log(f"Snake died: wall collision, score={state.snake_score}")
        return True

    # Self collision
    if (new_x, new_y) in state.snake_body:
        state.snake_alive = False
        logger.debug_log(f"Snake died: self collision, score={state.snake_score}")
        return True

    # Move head
    state.snake_body.insert(0, (new_x, new_y))

    # Check food
    if (new_x, new_y) == state.snake_food:
        state.snake_score += 1
        logger.debug_log(f"Snake ate food, score={state.snake_score}")
        # Speed up every 5 foods
        if state.snake_score % 5 == 0:
            state.snake_speed = min(20, state.snake_speed + 1)
            logger.debug_log(f"Snake speed increased to {state.snake_speed}")
        _spawn_food()
    else:
        # Remove tail
        state.snake_body.pop()

    return True
