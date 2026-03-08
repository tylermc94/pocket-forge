import time
import subprocess

import state
import display
import hardware
import ota
import party
from logger import debug_log


def enter_submenu(new_state, items, title):
    state.current_state      = new_state
    state.current_menu_items = items
    state.menu_index         = 0
    state.prev_menu_index    = -1
    display.draw_menu_full(title)


def get_menu_title():
    titles = {
        state.AppState.MAIN_MENU:     "Menu",
        state.AppState.SETTINGS_MENU: "Settings",
        state.AppState.GAMES_MENU:    "Games",
        state.AppState.POWER_MENU:    "Power",
    }
    return titles.get(state.current_state, "Menu")


def handle_menu_selection():
    debug_log(f"handle_menu_selection state={state.current_state} idx={state.menu_index}")

    # --- Slider confirmations ---
    if state.current_state == state.AppState.VOLUME:
        subprocess.run(['amixer', 'sset', 'Speaker',   f'{state.current_volume}%'], capture_output=True)
        subprocess.run(['amixer', 'sset', 'Headphone', f'{state.current_volume}%'], capture_output=True)
        enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        return

    if state.current_state == state.AppState.BRIGHTNESS:
        enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        return

    if state.current_state == state.AppState.SENSITIVITY:
        # Apply sensitivity: SCROLL_SENSITIVITY = 11 - value (inverse: higher value = lower threshold)
        state.SCROLL_SENSITIVITY = max(1, 11 - state.trackball_sensitivity)
        debug_log(f"Sensitivity set to {state.trackball_sensitivity} -> threshold={state.SCROLL_SENSITIVITY}")
        enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        return

    # --- OTA confirm ---
    if state.current_state == state.AppState.OTA_CONFIRM:
        debug_log(f"OTA_CONFIRM branch, idx={state.menu_index}")
        if state.menu_index == 0:  # Yes
            debug_log("Applying update")
            display.draw_ota_result("Applying update...", color=(200, 200, 200))
            success, message = ota.apply_update()
            if not success:
                state.current_state = state.AppState.OTA_RESULT
                display.draw_ota_result(message, color=(255, 100, 100))
        else:  # No
            debug_log("Update cancelled")
            enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        return

    if state.current_state == state.AppState.OTA_RESULT:
        enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        return

    # --- About screen ---
    if state.current_state == state.AppState.ABOUT:
        has_update = getattr(state, 'about_has_update', None)
        if has_update:
            # "Update available" selected — apply update
            display.draw_ota_result("Applying update...", color=(200, 200, 200))
            success, message = ota.apply_update()
            if not success:
                state.current_state = state.AppState.OTA_RESULT
                display.draw_ota_result(message, color=(255, 100, 100))
        else:
            # Up to date or error — go back to main menu
            enter_submenu(state.AppState.MAIN_MENU, state.main_menu_items, "Menu")
        return

    # --- Power confirm ---
    if state.current_state == state.AppState.POWER_CONFIRM:
        if state.menu_index == 0:  # Yes
            action = state.power_confirm_action
            if action == "poweroff":
                display.draw_ota_result("Powering off...", color=(200, 200, 200))
                time.sleep(1)
                display.draw_blank_screen()
                hardware.set_trackball_color(0, 0, 0)
                subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
            else:
                display.draw_ota_result("Restarting...", color=(200, 200, 200))
                time.sleep(1)
                display.draw_blank_screen()
                hardware.set_trackball_color(0, 0, 0)
                subprocess.Popen(['sudo', 'reboot'])
        else:  # No
            enter_submenu(state.AppState.POWER_MENU, state.power_menu_items, "Power")
        return

    selected = state.current_menu_items[state.menu_index]
    debug_log(f"Selected: {selected}")

    # --- Main menu ---
    if state.current_state == state.AppState.MAIN_MENU:
        if selected == "Status":
            state.current_state = state.AppState.MAIN
            display.draw_main_screen()
        elif selected == "Settings":
            enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        elif selected == "Games":
            enter_submenu(state.AppState.GAMES_MENU, state.games_menu_items, "Games")
        elif selected == "Power":
            enter_submenu(state.AppState.POWER_MENU, state.power_menu_items, "Power")
        elif selected == "About":
            ota.handle_about()

    # --- Settings menu ---
    elif state.current_state == state.AppState.SETTINGS_MENU:
        if selected == "< Back":
            enter_submenu(state.AppState.MAIN_MENU, state.main_menu_items, "Menu")
        elif selected == "Volume":
            try:
                result = subprocess.run(['amixer', 'sget', 'Speaker'], capture_output=True, text=True)
                for part in result.stdout.split():
                    if part.startswith('[') and part.endswith('%]'):
                        state.current_volume = round(int(part[1:-2]) / 5) * 5
                        break
            except Exception:
                pass
            state.current_state = state.AppState.VOLUME
            display.draw_slider_screen("Volume", state.current_volume, "%")
        elif selected == "Brightness":
            state.current_state = state.AppState.BRIGHTNESS
            display.draw_slider_screen("Brightness", state.current_brightness, "%")
        elif selected == "Trackball Sensitivity":
            state.current_state = state.AppState.SENSITIVITY
            display.draw_sensitivity_screen(state.trackball_sensitivity)
        elif selected == "Screen Timeout":
            # Cycle through options: 1, 2, 5, Never
            options = [1, 2, 5, 0]
            idx = options.index(state.screen_timeout_minutes) if state.screen_timeout_minutes in options else 0
            state.screen_timeout_minutes = options[(idx + 1) % len(options)]
            label = "Never" if state.screen_timeout_minutes == 0 else f"{state.screen_timeout_minutes}m"
            debug_log(f"Screen timeout set to {label}")
            display.draw_ota_result(f"Timeout: {label}", color=(0, 200, 100), pause=1)
            enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        else:
            # Developer Options or unimplemented — flash LED
            hardware.set_trackball_color(255, 0, 255)
            time.sleep(0.15)
            hardware.set_trackball_color(0, 0, 0)

    # --- Games menu ---
    elif state.current_state == state.AppState.GAMES_MENU:
        if selected == "< Back":
            enter_submenu(state.AppState.MAIN_MENU, state.main_menu_items, "Menu")
        elif selected == "Party Mode":
            state.current_state = state.AppState.PARTY_MODE
            state.party_speed   = 30
            party.start_party_mode()
        elif selected == "Drawing":
            _start_drawing()
        elif selected == "Snake":
            _start_snake()
        else:
            hardware.set_trackball_color(0, 0, 255)
            time.sleep(0.15)
            hardware.set_trackball_color(0, 0, 0)

    # --- Power menu ---
    elif state.current_state == state.AppState.POWER_MENU:
        if selected == "< Back":
            enter_submenu(state.AppState.MAIN_MENU, state.main_menu_items, "Menu")
        elif selected == "Sleep":
            state.sleeping   = True
            state.sleep_time = time.time()
            # led_color is preserved so wake can restore it
            hardware.set_trackball_color(0, 0, 0)
            display.draw_blank_screen()
            hardware.board.set_backlight(0)
        elif selected == "Power Off":
            state.power_confirm_action = "poweroff"
            state.current_state        = state.AppState.POWER_CONFIRM
            state.menu_index           = 0
            display.draw_power_confirm("poweroff")
        elif selected == "Restart":
            state.power_confirm_action = "reboot"
            state.current_state        = state.AppState.POWER_CONFIRM
            state.menu_index           = 0
            display.draw_power_confirm("reboot")
        else:
            hardware.set_trackball_color(255, 0, 0)
            time.sleep(0.15)
            hardware.set_trackball_color(0, 0, 0)


def _start_drawing():
    state.current_state      = state.AppState.DRAWING
    state.drawing_cursor_x   = 120
    state.drawing_cursor_y   = 140
    state.drawing_pixels     = []
    display.draw_drawing_screen()


def _start_snake():
    import random

    CELL   = 12
    BORDER = 4
    PLAY_W = 240 - BORDER * 2
    PLAY_H = 260 - BORDER * 2
    COLS   = PLAY_W // CELL
    ROWS   = PLAY_H // CELL

    cx = COLS // 2
    cy = ROWS // 2
    state.snake_body       = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
    state.snake_dir        = (1, 0)
    state.snake_food       = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
    state.snake_score      = 0
    state.snake_speed      = 0.15
    state.snake_last_step  = time.time()
    state.snake_paused     = False
    state.snake_dead       = False
    state.snake_foods_eaten = 0
    state.current_state    = state.AppState.SNAKE
    display.draw_snake_screen()
