#!/usr/bin/env python3
import time

import state
import hardware
import display
import menus
import party


hardware.board.on_button_press(lambda: print("Recording mode TODO"))

try:
    print("Starting main loop...")
    display.draw_main_screen()
    last_second     = int(time.time())
    button_was_down = False

    while True:
        if hardware.trackball_available:
            try:
                up, down, left, right, switch, _ = hardware.trackball.read()
            except Exception as e:
                print(f"Trackball read error: {e}")
                up = down = left = right = switch = 0

            # Button press tracking
            if switch and not button_was_down:
                button_was_down           = True
                state.click_start_time    = time.time()
                state.movement_during_click = 0

            elif not switch and button_was_down:
                button_was_down = False
                click_duration  = time.time() - state.click_start_time

                if (click_duration < 0.5 and
                        state.movement_during_click < state.MOVEMENT_THRESHOLD and
                        time.time() - state.last_click_time > 0.3):

                    state.last_click_time = time.time()

                    if state.current_state == state.AppState.PARTY_MODE:
                        # Stop thread first, then redraw menu
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

            if button_was_down:
                state.movement_during_click += abs(up) + abs(down) + abs(left) + abs(right)

            # Scroll handling
            net_movement = down - up
            if abs(net_movement) > 0:
                if state.current_state == state.AppState.PARTY_MODE:
                    with state.party_lock:
                        state.party_speed = max(10, min(100, state.party_speed + (2 if net_movement > 0 else -2)))

                elif state.current_state not in (state.AppState.MAIN, state.AppState.OTA_RESULT):
                    state.scroll_accumulator += net_movement
                    if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                        item_count = 2 if state.current_state == state.AppState.OTA_CONFIRM else len(state.current_menu_items)

                        if state.scroll_accumulator > 0:
                            state.menu_index = (state.menu_index + 1) % item_count
                        else:
                            state.menu_index = (state.menu_index - 1) % item_count

                        if state.current_state == state.AppState.OTA_CONFIRM:
                            display.draw_ota_confirm()
                        else:
                            display.draw_menu_full(menus.get_menu_title())
                        state.scroll_accumulator = 0

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