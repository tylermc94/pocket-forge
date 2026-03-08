#!/usr/bin/env python3
import time
import random

import state
import hardware
import display
import menus
import party
from logger import debug_log

# Snake grid constants (must match display.py)
_SNAKE_CELL   = 12
_SNAKE_BORDER = 4
_SNAKE_COLS   = (240 - _SNAKE_BORDER * 2) // _SNAKE_CELL
_SNAKE_ROWS   = (260 - _SNAKE_BORDER * 2) // _SNAKE_CELL

hardware.board.on_button_press(lambda: debug_log("Recording mode TODO"))

# ── helpers ──────────────────────────────────────────────────────────────────

def _set_led(r, g, b):
    """Set LED and record colour in state so it can be restored later."""
    state.led_color = (r, g, b)
    hardware.set_trackball_color(r, g, b)


def _sleep_device():
    """Blank display, kill LED, enter sleeping state."""
    state.sleeping   = True
    state.sleep_time = time.time()
    hardware.set_trackball_color(0, 0, 0)
    display.draw_blank_screen()
    hardware.board.set_backlight(0)
    debug_log("Device sleeping")


def _wake_device():
    """Restore display and LED from sleep/timeout."""
    state.sleeping = False
    hardware.board.set_backlight(state.current_brightness)
    r, g, b = state.led_color
    hardware.set_trackball_color(r, g, b)
    display.draw_main_screen()
    state.current_state = state.AppState.MAIN
    debug_log("Device woke")


def _snake_step():
    """Advance snake by one step. Handles collision, food, and speed."""
    dx, dy = state.snake_dir
    hx, hy = state.snake_body[0]
    nx, ny = hx + dx, hy + dy

    # Wall collision
    if nx < 0 or nx >= _SNAKE_COLS or ny < 0 or ny >= _SNAKE_ROWS:
        state.snake_dead = True
        display.draw_snake_dead_screen()
        return

    # Self collision
    if (nx, ny) in state.snake_body[:-1]:
        state.snake_dead = True
        display.draw_snake_dead_screen()
        return

    state.snake_body.insert(0, (nx, ny))

    # Food eaten
    if (nx, ny) == state.snake_food:
        state.snake_score      += 1
        state.snake_foods_eaten += 1
        # Speed up every 5 foods
        if state.snake_foods_eaten % 5 == 0:
            state.snake_speed = max(0.05, state.snake_speed - 0.01)
        # Spawn new food not on snake
        while True:
            fx = random.randint(0, _SNAKE_COLS - 1)
            fy = random.randint(0, _SNAKE_ROWS - 1)
            if (fx, fy) not in state.snake_body:
                break
        state.snake_food = (fx, fy)
    else:
        state.snake_body.pop()

    display.draw_snake_screen()


# ── main loop ─────────────────────────────────────────────────────────────────

try:
    debug_log("Starting main loop...")
    display.draw_main_screen()
    last_second     = int(time.time())
    button_was_down = False

    # Apply initial sensitivity
    state.SCROLL_SENSITIVITY = max(1, 11 - state.trackball_sensitivity)

    while True:
        now = time.time()

        # ── Sleep / screen timeout ────────────────────────────────────────────
        if state.sleeping:
            # Only process input after 2-second wake guard
            if hardware.trackball_available:
                try:
                    up, down, left, right, switch, _ = hardware.trackball.read()
                except Exception:
                    up = down = left = right = switch = 0
                    time.sleep(0.05)

                any_input = up or down or left or right or switch
                if any_input and (now - state.sleep_time) > 2.0:
                    debug_log(f"Wake detected after {now - state.sleep_time:.2f}s")
                    _wake_device()
                    state.last_activity_time = now
            time.sleep(0.05)
            continue

        # ── Screen timeout check ─────────────────────────────────────────────
        if state.screen_timeout_minutes > 0:
            timeout_secs = state.screen_timeout_minutes * 60
            if now - state.last_activity_time > timeout_secs:
                debug_log("Screen timeout — sleeping")
                _sleep_device()
                continue

        # ── Trackball input ──────────────────────────────────────────────────
        if hardware.trackball_available:
            try:
                up, down, left, right, switch, _ = hardware.trackball.read()
            except Exception as e:
                up = down = left = right = switch = 0
                button_was_down = False
                state.scroll_accumulator = 0
                time.sleep(0.05)
                continue

            any_movement = up or down or left or right or switch
            if any_movement:
                state.last_activity_time = now
                debug_log(f"TB: u={up} d={down} l={left} r={right} sw={switch} sens={state.trackball_sensitivity} threshold={state.SCROLL_SENSITIVITY}")

            # ── Button press tracking ─────────────────────────────────────────
            if switch and not button_was_down:
                button_was_down             = True
                state.click_start_time      = now
                state.movement_during_click = 0
                debug_log(f"Button pressed, state={state.current_state}")

            elif not switch and button_was_down:
                button_was_down = False
                click_duration  = now - state.click_start_time
                debug_log(f"Button released, duration={click_duration:.3f}s, movement={state.movement_during_click}")

                is_hold  = click_duration > 0.8
                is_click = (click_duration < 0.5 and
                            state.movement_during_click < state.MOVEMENT_THRESHOLD and
                            now - state.last_click_time > 0.3)

                # ── Drawing game hold = exit ──────────────────────────────────
                if state.current_state == state.AppState.DRAWING and is_hold:
                    debug_log("Drawing: hold to exit")
                    menus.enter_submenu(state.AppState.GAMES_MENU, state.games_menu_items, "Games")

                # ── Snake: hold on dead screen = exit ────────────────────────
                elif state.current_state == state.AppState.SNAKE and state.snake_dead and is_hold:
                    debug_log("Snake: hold to exit from dead screen")
                    menus.enter_submenu(state.AppState.GAMES_MENU, state.games_menu_items, "Games")

                # ── Snake: hold during play = pause; click while paused = resume
                elif state.current_state == state.AppState.SNAKE and not state.snake_dead:
                    if is_hold and not state.snake_paused:
                        state.snake_paused = True
                        debug_log("Snake: paused")
                        display.draw_snake_screen()
                    elif is_click and state.snake_paused:
                        state.snake_paused = False
                        state.snake_last_step = now
                        debug_log("Snake: resumed")
                        display.draw_snake_screen()

                elif is_click:
                    debug_log(f"Valid click, state={state.current_state}")
                    state.last_click_time = now

                    if state.current_state == state.AppState.DRAWING:
                        # Place a pixel at cursor
                        px = state.drawing_cursor_x
                        py = state.drawing_cursor_y
                        if (px, py) not in state.drawing_pixels:
                            state.drawing_pixels.append((px, py))
                        display.draw_drawing_screen()

                    elif state.current_state == state.AppState.PARTY_MODE:
                        party.stop_party_mode()
                        menus.enter_submenu(state.AppState.GAMES_MENU, state.games_menu_items, "Games")

                    elif state.current_state == state.AppState.MAIN:
                        state.current_state      = state.AppState.MAIN_MENU
                        state.current_menu_items = state.main_menu_items
                        state.menu_index         = 0
                        state.prev_menu_index    = -1
                        display.draw_menu_full("Menu")

                    else:
                        menus.handle_menu_selection()
                else:
                    debug_log("Click rejected")

            if button_was_down:
                state.movement_during_click += abs(up) + abs(down) + abs(left) + abs(right)

            # ── Drawing game trackball movement ───────────────────────────────
            if state.current_state == state.AppState.DRAWING and not button_was_down:
                moved = False
                SPEED = 3
                if up:
                    state.drawing_cursor_y = max(5, state.drawing_cursor_y - up * SPEED)
                    moved = True
                if down:
                    state.drawing_cursor_y = min(254, state.drawing_cursor_y + down * SPEED)
                    moved = True
                if left:
                    state.drawing_cursor_x = max(5, state.drawing_cursor_x - left * SPEED)
                    moved = True
                if right:
                    state.drawing_cursor_x = min(235, state.drawing_cursor_x + right * SPEED)
                    moved = True
                if moved:
                    display.draw_drawing_screen()

            # ── Snake direction control ───────────────────────────────────────
            elif state.current_state == state.AppState.SNAKE and not state.snake_dead and not state.snake_paused:
                dx, dy = state.snake_dir
                # Largest axis wins; ignore reversal
                if up > down and up > left and up > right and dy != 1:
                    state.snake_dir = (0, -1)
                elif down > up and down > left and down > right and dy != -1:
                    state.snake_dir = (0, 1)
                elif left > right and left > up and left > down and dx != 1:
                    state.snake_dir = (-1, 0)
                elif right > left and right > up and right > down and dx != -1:
                    state.snake_dir = (1, 0)

            # ── Scroll: party mode speed ──────────────────────────────────────
            net_movement = down - up
            if abs(net_movement) > 0:
                if state.current_state == state.AppState.PARTY_MODE:
                    with state.party_lock:
                        state.party_speed = max(10, min(100, state.party_speed + (2 if net_movement > 0 else -2)))

                elif state.current_state in (state.AppState.VOLUME, state.AppState.BRIGHTNESS):
                    state.scroll_accumulator += net_movement
                    if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                        delta = 5 if state.scroll_accumulator < 0 else -5
                        if state.current_state == state.AppState.VOLUME:
                            new_val = max(0, min(100, state.current_volume + delta))
                            if new_val != state.current_volume:
                                state.current_volume = new_val
                                display.draw_slider_screen("Volume", state.current_volume, "%")
                        else:
                            new_val = max(10, min(100, state.current_brightness + delta))
                            if new_val != state.current_brightness:
                                state.current_brightness = new_val
                                hardware.board.set_backlight(state.current_brightness)
                                display.draw_slider_screen("Brightness", state.current_brightness, "%")
                        state.scroll_accumulator = 0

                elif state.current_state == state.AppState.SENSITIVITY:
                    state.scroll_accumulator += net_movement
                    if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                        delta = 1 if state.scroll_accumulator < 0 else -1
                        new_val = max(1, min(10, state.trackball_sensitivity + delta))
                        if new_val != state.trackball_sensitivity:
                            state.trackball_sensitivity = new_val
                            state.SCROLL_SENSITIVITY    = max(1, 11 - new_val)
                            debug_log(f"Sensitivity preview: {new_val} -> threshold={state.SCROLL_SENSITIVITY}")
                            display.draw_sensitivity_screen(state.trackball_sensitivity)
                        state.scroll_accumulator = 0

                elif state.current_state == state.AppState.POWER_CONFIRM:
                    state.scroll_accumulator += net_movement
                    if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                        state.menu_index = (state.menu_index + (1 if state.scroll_accumulator > 0 else -1)) % 2
                        display.draw_power_confirm(state.power_confirm_action)
                        state.scroll_accumulator = 0

                elif state.current_state not in (
                    state.AppState.MAIN,
                    state.AppState.OTA_RESULT,
                    state.AppState.DRAWING,
                    state.AppState.SNAKE,
                    state.AppState.ABOUT,
                ):
                    state.scroll_accumulator += net_movement
                    if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                        item_count = 2 if state.current_state == state.AppState.OTA_CONFIRM else len(state.current_menu_items)

                        if state.scroll_accumulator > 0:
                            state.menu_index = (state.menu_index + 1) % item_count
                        else:
                            state.menu_index = (state.menu_index - 1) % item_count

                        debug_log(f"Scroll state={state.current_state} idx={state.menu_index}")

                        if state.current_state == state.AppState.OTA_CONFIRM:
                            display.draw_ota_confirm()
                        else:
                            display.draw_menu_full(menus.get_menu_title())
                        state.scroll_accumulator = 0

        # ── Snake step tick ───────────────────────────────────────────────────
        if (state.current_state == state.AppState.SNAKE and
                not state.snake_dead and
                not state.snake_paused and
                now - state.snake_last_step >= state.snake_speed):
            state.snake_last_step = now
            _snake_step()

        # ── Main screen clock update ──────────────────────────────────────────
        if state.current_state == state.AppState.MAIN:
            current_second = int(now)
            if current_second != last_second:
                last_second = current_second
                display.draw_main_screen()

        time.sleep(0.008)

except KeyboardInterrupt:
    debug_log("Exiting...")
finally:
    party.stop_party_mode()
    hardware.board.cleanup()
    hardware.set_trackball_color(0, 0, 0)
