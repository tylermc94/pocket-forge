import time
import state
import display
import hardware
import ota
import party


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
    # Handle OTA states first — before touching current_menu_items,
    # which still points to the Settings list during OTA confirmation flow
    if state.current_state == state.AppState.OTA_CONFIRM:
        if state.menu_index == 0:  # Yes
            display.draw_ota_result("Applying update...", color=(200, 200, 200))
            success, message = ota.apply_update()
            if not success:
                state.current_state = state.AppState.OTA_RESULT
                display.draw_ota_result(message, color=(255, 100, 100))
        else:  # No
            enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        return

    if state.current_state == state.AppState.OTA_RESULT:
        enter_submenu(state.AppState.SETTINGS_MENU, state.settings_menu_items, "Settings")
        return

    selected = state.current_menu_items[state.menu_index]
    print(f"Selected: {selected}")

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

    elif state.current_state == state.AppState.SETTINGS_MENU:
        if selected == "< Back":
            enter_submenu(state.AppState.MAIN_MENU, state.main_menu_items, "Menu")
        elif selected == "Software Update":
            ota.handle_ota()
        else:
            hardware.set_trackball_color(255, 0, 255)
            time.sleep(0.15)
            hardware.set_trackball_color(0, 0, 0)

    elif state.current_state == state.AppState.GAMES_MENU:
        if selected == "< Back":
            enter_submenu(state.AppState.MAIN_MENU, state.main_menu_items, "Menu")
        elif selected == "Party Mode":
            state.current_state = state.AppState.PARTY_MODE
            state.party_speed   = 30
            party.start_party_mode()
        else:
            hardware.set_trackball_color(0, 0, 255)
            time.sleep(0.15)
            hardware.set_trackball_color(0, 0, 0)

    elif state.current_state == state.AppState.POWER_MENU:
        if selected == "< Back":
            enter_submenu(state.AppState.MAIN_MENU, state.main_menu_items, "Menu")
        else:
            hardware.set_trackball_color(255, 0, 0)
            time.sleep(0.15)
            hardware.set_trackball_color(0, 0, 0)