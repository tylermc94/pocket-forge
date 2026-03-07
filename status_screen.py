#!/usr/bin/env python3
import time

import state
import hardware
import display
import menus
import party
import drawing


def _on_hat_button():
    """HAT button handler — exits Drawing mode; reserved for other states later."""
    if state.current_state == state.AppState.DRAWING:
        # Signal the main loop to exit drawing cleanly (display calls must stay
        # on the main thread to avoid I2C contention).
        state.drawing_exit_requested = True


hardware.board.on_button_press(_on_hat_button)

try:
    print("Starting main loop...")
    display.draw_main_screen()
    last_second              = int(time.time())
    button_was_down          = False
    drawing_long_press_done  = False  # True once the 1-s clear fires in a single press

    while True:
        if hardware.trackball_available:
            try:
                up, down, left, right, switch, _ = hardware.trackball.read()
            except Exception as e:
                up = down = left = right = switch = 0
                button_was_down = False
                state.scroll_accumulator = 0
                time.sleep(0.05)  # Brief backoff, let I2C bus recover

            # Button press tracking
            if switch and not button_was_down:
                button_was_down             = True
                state.click_start_time      = time.time()
                state.movement_during_click = 0
                print(f"[DEBUG] Button pressed, state={state.current_state}")

            elif not switch and button_was_down:
                button_was_down = False
                click_duration  = time.time() - state.click_start_time
                print(f"[DEBUG] Button released, duration={click_duration:.3f}s, movement={state.movement_during_click}, time_since_last={time.time() - state.last_click_time:.3f}s")

                if (click_duration < 0.5 and
                        state.movement_during_click < state.MOVEMENT_THRESHOLD and
                        time.time() - state.last_click_time > 0.3):

                    print(f"[DEBUG] Valid click registered, state={state.current_state}")
                    state.last_click_time = time.time()

                    if state.current_state == state.AppState.PARTY_MODE:
                        party.stop_party_mode()
                        menus.enter_submenu(state.AppState.GAMES_MENU, state.games_menu_items, "Games")

                    elif state.current_state == state.AppState.DRAWING:
                        # Short click: toggle draw / move (only if long-press clear
                        # didn't already fire during this press)
                        if not drawing_long_press_done:
                            drawing.toggle_mode()
                            display.draw_drawing_screen()

                    elif state.current_state == state.AppState.MAIN:
                        state.current_state      = state.AppState.MAIN_MENU
                        state.current_menu_items = state.main_menu_items
                        state.menu_index         = 0
                        state.prev_menu_index    = -1
                        display.draw_menu_full("Menu")

                    else:
                        menus.handle_menu_selection()
                else:
                    print(f"[DEBUG] Click rejected")

                # Reset long-press flag whenever button is released
                drawing_long_press_done = False

            if button_was_down:
                state.movement_during_click += abs(up) + abs(down) + abs(left) + abs(right)

                # Long-press (≥1 s) in drawing mode clears the canvas once per press
                if (state.current_state == state.AppState.DRAWING and
                        not drawing_long_press_done and
                        time.time() - state.click_start_time >= 1.0):
                    drawing_long_press_done = True
                    drawing.clear_canvas()
                    display.draw_drawing_screen()
                    print("[DEBUG] Drawing canvas cleared (long press)")

            # Drawing mode: handle all four axes before the general scroll logic
            if state.current_state == state.AppState.DRAWING:
                net_h = right - left
                net_v = down - up
                if abs(net_h) > 0 or abs(net_v) > 0:
                    drawing.handle_movement(net_h, net_v)
                    if state.drawing_dirty:
                        display.draw_drawing_screen()

            # Scroll handling
            net_movement = down - up
            if abs(net_movement) > 0:
                if state.current_state == state.AppState.PARTY_MODE:
                    with state.party_lock:
                        state.party_speed = max(10, min(100, state.party_speed + (2 if net_movement > 0 else -2)))

                elif state.current_state in (state.AppState.VOLUME, state.AppState.BRIGHTNESS, state.AppState.TRACKBALL_SENSITIVITY):
                    state.scroll_accumulator += net_movement
                    if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                        # scroll up (accumulator < 0) → value increases; scroll down → value decreases
                        if state.current_state == state.AppState.VOLUME:
                            delta = 5 if state.scroll_accumulator < 0 else -5
                            new_val = max(0, min(100, state.current_volume + delta))
                            if new_val != state.current_volume:
                                state.current_volume = new_val
                                display.draw_slider_screen("Volume", state.current_volume, "%")
                        elif state.current_state == state.AppState.BRIGHTNESS:
                            delta = 5 if state.scroll_accumulator < 0 else -5
                            new_val = max(10, min(100, state.current_brightness + delta))
                            if new_val != state.current_brightness:
                                state.current_brightness = new_val
                                hardware.board.set_backlight(state.current_brightness)
                                display.draw_slider_screen("Brightness", state.current_brightness, "%")
                        else:  # TRACKBALL_SENSITIVITY
                            delta = 1 if state.scroll_accumulator < 0 else -1
                            new_val = max(1, min(10, state.current_sensitivity + delta))
                            if new_val != state.current_sensitivity:
                                state.current_sensitivity = new_val
                                state.SCROLL_SENSITIVITY = 11 - state.current_sensitivity
                                display.draw_slider_screen("Sensitivity", state.current_sensitivity * 10, "%")
                        state.scroll_accumulator = 0

                elif state.current_state not in (
                    state.AppState.MAIN,
                    state.AppState.OTA_RESULT,
                    state.AppState.DRAWING,
                ):
                    state.scroll_accumulator += net_movement
                    if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                        item_count = 2 if state.current_state == state.AppState.OTA_CONFIRM else len(state.current_menu_items)

                        if state.scroll_accumulator > 0:
                            state.menu_index = (state.menu_index + 1) % item_count
                        else:
                            state.menu_index = (state.menu_index - 1) % item_count

                        print(f"[DEBUG] Scroll, state={state.current_state}, menu_index={state.menu_index}")

                        if state.current_state == state.AppState.OTA_CONFIRM:
                            display.draw_ota_confirm()
                        else:
                            display.draw_menu_full(menus.get_menu_title())
                        state.scroll_accumulator = 0

        # Drawing mode: HAT-button exit and deferred dirty redraws
        if state.current_state == state.AppState.DRAWING:
            if state.drawing_exit_requested:
                state.drawing_exit_requested = False
                drawing.stop_drawing()
            elif state.drawing_dirty:
                display.draw_drawing_screen()

        # Main screen clock update — only redraws when the second changes
        if state.current_state == state.AppState.MAIN:
            current_second = int(time.time())
            if current_second != last_second:
                last_second = current_second
                display.draw_main_screen()

        time.sleep(0.008)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    party.stop_party_mode()
    hardware.board.cleanup()
    hardware.set_trackball_color(0, 0, 0)