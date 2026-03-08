#!/usr/bin/env python3
import os
import time
import wave
import subprocess
from datetime import datetime

import numpy as np

import state
import hardware
import display
import menus
import party
import drawing
import snake
import logger
import queries

try:
    import sounddevice as sd
except ImportError:
    sd = None
    print("sounddevice not installed — recording unavailable")


def _do_wake():
    logger.debug_log("Waking: enabling WiFi, restarting battery thread")
    subprocess.run(['sudo', 'iwconfig', 'wlan0', 'txpower', 'auto'], capture_output=True)
    hardware.start_battery_thread()
    state.sleeping         = False
    state.screen_on        = True
    state.last_activity_time = time.time()
    state.current_state    = state.AppState.MAIN
    hardware.board.set_backlight(state.current_brightness)
    display.draw_main_screen()


def _on_hat_button_press():
    """HAT button pressed — start recording (hold to record)."""
    if state.sleeping:
        _do_wake()
        return

    if not state.screen_on:
        state.screen_on = True
        state.last_activity_time = time.time()
        hardware.board.set_backlight(state.current_brightness)

    if state.current_state in (state.AppState.RECORDING, state.AppState.TRANSCRIBING):
        return

    state.hat_button_held = True
    state.hat_button_press_time = time.time()


def _on_hat_button_release():
    """HAT button released — stop recording and transcribe."""
    state.hat_button_held = False

hardware.board.on_button_press(_on_hat_button_press)
hardware.board.on_button_release(_on_hat_button_release)

# Recording runtime state
_recording_stream = None
_recording_frames = []
_last_record_anim = 0.0


def _audio_callback(indata, frames, time_info, status):
    _recording_frames.append(indata.copy())


def _redraw_current_state():
    """Redraw whatever screen was showing before recording started."""
    s = state.current_state
    if s == state.AppState.MAIN:
        display.draw_main_screen()
    elif s in (state.AppState.MAIN_MENU, state.AppState.SETTINGS_MENU,
               state.AppState.GAMES_MENU, state.AppState.POWER_MENU,
               state.AppState.DEV_OPTIONS):
        display.draw_menu_full(menus.get_menu_title())
    elif s == state.AppState.DRAWING:
        state.drawing_dirty = True
    elif s == state.AppState.ABOUT:
        display.draw_about_screen()
    elif s == state.AppState.POWER_CONFIRM:
        display.draw_power_confirm(state.power_confirm_action)
    elif s == state.AppState.VOLUME:
        display.draw_slider_screen("Volume", state.current_volume, "%")
    elif s == state.AppState.BRIGHTNESS:
        display.draw_slider_screen("Brightness", state.current_brightness, "%")
    elif s == state.AppState.TRACKBALL_SENSITIVITY:
        display.draw_slider_screen("Sensitivity", state.current_sensitivity * 10, "%")
    elif s == state.AppState.SCREEN_TIMEOUT:
        pct = int((state.screen_timeout - 15) / (300 - 15) * 100)
        display.draw_slider_screen("Screen Timeout", pct, "", f"{state.screen_timeout}s")


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
                logger.debug_log(f"Trackball read error: {e}")
                up = down = left = right = switch = 0
                button_was_down = False
                state.scroll_accumulator = 0
                time.sleep(0.05)  # Brief backoff, let I2C bus recover

            any_input = bool(switch or up or down or left or right)

            if state.sleeping:
                if any_input and time.time() - state.sleep_enter_time > 1.5:
                    _do_wake()
                    button_was_down = False
                time.sleep(0.008)
                continue

            if not state.screen_on:
                # Screen is off — wake on any input, consume all of it
                if any_input:
                    state.screen_on          = True
                    state.last_activity_time = time.time()
                    hardware.board.set_backlight(state.current_brightness)
                    # If this wake was from a button press edge, mark it as held
                    # with a stale timestamp so the release edge won't register
                    # as a valid click.
                    if switch:
                        button_was_down             = True
                        state.click_start_time      = time.time() - 1.0
                        state.movement_during_click = 0
                    # Redraw current screen (framebuffer may hold stale content)
                    if state.current_state == state.AppState.MAIN:
                        display.draw_main_screen()
                    elif state.current_state in (state.AppState.MAIN_MENU,
                                                  state.AppState.SETTINGS_MENU,
                                                  state.AppState.GAMES_MENU,
                                                  state.AppState.POWER_MENU):
                        display.draw_menu_full(menus.get_menu_title())
                    elif state.current_state == state.AppState.ABOUT:
                        display.draw_about_screen()
                # Consume all input so the code below doesn't act on it
                up = down = left = right = switch = 0

            else:
                # Screen is on — update activity time and process normally
                if any_input:
                    state.last_activity_time = time.time()

                # Block all trackball input during recording/transcribing
                if state.current_state in (state.AppState.RECORDING, state.AppState.TRANSCRIBING):
                    up = down = left = right = switch = 0

                # Button tracking — switch is an edge event (1 on press AND release),
                # not a level.  Toggle button_was_down on each edge.
                if switch:
                    if not button_was_down:
                        # Press edge
                        button_was_down             = True
                        state.click_start_time      = time.time()
                        state.movement_during_click = 0
                        logger.debug_log(f"Button pressed, state={state.current_state}")
                    else:
                        # Release edge
                        button_was_down = False
                        click_duration  = time.time() - state.click_start_time
                        logger.debug_log(f"Button released, duration={click_duration:.3f}s, movement={state.movement_during_click}, time_since_last={time.time() - state.last_click_time:.3f}s")

                        # Long press actions (hold > 0.8s)
                        if click_duration > 0.8:
                            if state.current_state == state.AppState.DRAWING:
                                logger.debug_log("Drawing: hold to exit")
                                drawing.stop_drawing()
                            elif state.current_state == state.AppState.SNAKE:
                                if state.snake_alive and not state.snake_paused:
                                    logger.debug_log("Snake: hold to pause")
                                    state.snake_paused = True
                                    display.draw_snake_screen()
                                elif not state.snake_alive:
                                    logger.debug_log("Snake: hold to exit (dead)")
                                    snake.stop_snake()

                        elif (click_duration < 0.5 and
                                state.movement_during_click < state.MOVEMENT_THRESHOLD and
                                time.time() - state.last_click_time > 0.3):

                            logger.debug_log(f"Valid click registered, state={state.current_state}")
                            state.last_click_time = time.time()

                            if state.current_state == state.AppState.DRAWING:
                                drawing.toggle_mode()
                                state.drawing_dirty = True

                            elif state.current_state == state.AppState.SNAKE:
                                if state.snake_paused:
                                    logger.debug_log("Snake: click to resume")
                                    state.snake_paused = False
                                    state.snake_last_move = time.time()
                                    display.draw_snake_screen()

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
                            logger.debug_log("Click rejected")

                if button_was_down:
                    state.movement_during_click += abs(up) + abs(down) + abs(left) + abs(right)

                # Drawing game — trackball moves cursor and draws
                if state.current_state == state.AppState.DRAWING:
                    if up or down or left or right:
                        drawing.handle_movement(right - left, down - up)

                # Snake game — trackball sets direction
                if state.current_state == state.AppState.SNAKE and state.snake_alive and not state.snake_paused:
                    if up or down or left or right:
                        # Use dominant axis
                        dx = right - left
                        dy = down - up
                        if abs(dx) >= abs(dy) and dx != 0:
                            snake.set_direction(1 if dx > 0 else -1, 0)
                        elif dy != 0:
                            snake.set_direction(0, 1 if dy > 0 else -1)

                # Scroll handling
                net_movement = down - up
                if abs(net_movement) > 0:
                    if state.current_state == state.AppState.PARTY_MODE:
                        with state.party_lock:
                            state.party_speed = max(10, min(100, state.party_speed + (2 if net_movement > 0 else -2)))

                    elif state.current_state == state.AppState.POWER_CONFIRM:
                        state.scroll_accumulator += net_movement
                        if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                            state.menu_index = 1 if state.menu_index == 0 else 0
                            display.draw_power_confirm(state.power_confirm_action)
                            state.scroll_accumulator = 0

                    elif state.current_state in (state.AppState.VOLUME,
                                                  state.AppState.BRIGHTNESS,
                                                  state.AppState.TRACKBALL_SENSITIVITY,
                                                  state.AppState.SCREEN_TIMEOUT):
                        state.scroll_accumulator += net_movement
                        if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                            # scroll up (accumulator < 0) → value increases; scroll down → decreases
                            if state.current_state == state.AppState.VOLUME:
                                delta   = 5 if state.scroll_accumulator < 0 else -5
                                new_val = max(0, min(100, state.current_volume + delta))
                                if new_val != state.current_volume:
                                    state.current_volume = new_val
                                    display.draw_slider_screen("Volume", state.current_volume, "%")
                            elif state.current_state == state.AppState.BRIGHTNESS:
                                delta   = 5 if state.scroll_accumulator < 0 else -5
                                new_val = max(10, min(100, state.current_brightness + delta))
                                if new_val != state.current_brightness:
                                    state.current_brightness = new_val
                                    hardware.board.set_backlight(state.current_brightness)
                                    display.draw_slider_screen("Brightness", state.current_brightness, "%")
                            elif state.current_state == state.AppState.TRACKBALL_SENSITIVITY:
                                delta   = 1 if state.scroll_accumulator < 0 else -1
                                new_val = max(1, min(10, state.current_sensitivity + delta))
                                if new_val != state.current_sensitivity:
                                    state.current_sensitivity = new_val
                                    state.SCROLL_SENSITIVITY  = 21 - state.current_sensitivity * 2
                                    display.draw_slider_screen("Sensitivity", state.current_sensitivity * 10, "%")
                            else:  # SCREEN_TIMEOUT
                                delta   = 15 if state.scroll_accumulator < 0 else -15
                                new_val = max(15, min(300, state.screen_timeout + delta))
                                if new_val != state.screen_timeout:
                                    state.screen_timeout = new_val
                                    pct = int((state.screen_timeout - 15) / (300 - 15) * 100)
                                    display.draw_slider_screen("Screen Timeout", pct, "",
                                                               f"{state.screen_timeout}s")
                            state.scroll_accumulator = 0

                    elif state.current_state not in (state.AppState.MAIN,
                                                      state.AppState.ABOUT,
                                                      state.AppState.DRAWING,
                                                      state.AppState.SNAKE,
                                                      state.AppState.POWER_CONFIRM,
                                                      state.AppState.RECORDING,
                                                      state.AppState.TRANSCRIBING):
                        state.scroll_accumulator += net_movement
                        if abs(state.scroll_accumulator) >= state.SCROLL_SENSITIVITY:
                            item_count = len(state.current_menu_items)

                            if state.scroll_accumulator > 0:
                                state.menu_index = (state.menu_index + 1) % item_count
                            else:
                                state.menu_index = (state.menu_index - 1) % item_count

                            logger.debug_log(f"Scroll, state={state.current_state}, menu_index={state.menu_index}")

                            display.draw_menu_full(menus.get_menu_title())
                            state.scroll_accumulator = 0

        # === Voice recording: detect button press → start recording ===
        if (state.hat_button_held and state.hat_button_press_time > 0
                and state.current_state not in (state.AppState.RECORDING,
                                                state.AppState.TRANSCRIBING)):
            if state.whisper_model is None or sd is None:
                display.draw_stt_unavailable_screen()
                time.sleep(2)
                state.hat_button_press_time = 0  # Prevent re-trigger
                _redraw_current_state()
            else:
                state.pre_record_state = state.current_state
                state.current_state = state.AppState.RECORDING
                state.last_activity_time = time.time()
                _recording_frames.clear()
                _recording_stream = sd.InputStream(
                    samplerate=16000, channels=1, dtype='float32',
                    callback=_audio_callback)
                _recording_stream.start()
                display.draw_recording_screen(True)
                _last_record_anim = time.time()

        # === Voice recording: animation + release detection ===
        if state.current_state == state.AppState.RECORDING:
            now = time.time()
            if now - _last_record_anim >= 0.5:
                phase = int((now - state.hat_button_press_time) / 0.5) % 2 == 0
                display.draw_recording_screen(phase)
                _last_record_anim = now

            if not state.hat_button_held:
                # Button released — stop recording
                if _recording_stream:
                    _recording_stream.stop()
                    _recording_stream.close()
                    _recording_stream = None

                duration = time.time() - state.hat_button_press_time

                if duration < 0.5:
                    # Too short — discard silently
                    state.current_state = state.pre_record_state
                    _redraw_current_state()
                else:
                    # Transcribe
                    state.current_state = state.AppState.TRANSCRIBING
                    display.draw_transcribing_screen()

                    audio = (np.concatenate(_recording_frames, axis=0).flatten()
                             if _recording_frames
                             else np.array([], dtype=np.float32))

                    # Write temp WAV for whisper.cpp
                    wav_path = "/tmp/pf_recording.wav"
                    audio_int16 = (audio * 32767).astype(np.int16)
                    with wave.open(wav_path, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(audio_int16.tobytes())

                    t_start = time.time()
                    _wcmd = [state.whisper_cpp_bin,
                             '-m', state.whisper_cpp_model,
                             '-f', wav_path,
                             '--no-timestamps',
                             '-t', '4']
                    # English-only model doesn't need -l flag; set it for multilingual
                    if not state.whisper_model.endswith('.en'):
                        _wcmd += ['-l', 'en']
                    wresult = subprocess.run(
                        _wcmd, capture_output=True, text=True, timeout=120)
                    t_elapsed = time.time() - t_start
                    text = wresult.stdout.strip()

                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass

                    # Benchmark output (always printed)
                    print(f"Transcribed {duration:.1f}s audio in {t_elapsed:.1f}s | Result: {text}")
                    logger.debug_log(f"Transcription time: {t_elapsed:.1f}s, audio duration: {duration:.1f}s")

                    queries.log_query({
                        "timestamp": datetime.now().isoformat(timespec='seconds'),
                        "transcript": text,
                        "duration_seconds": round(duration, 1),
                        "transcription_time_seconds": round(t_elapsed, 1),
                        "whisper_model": state.whisper_model,
                        "audio_file": None,
                    })

                    display.draw_transcript_screen(text)
                    time.sleep(3)

                    state.current_state = state.pre_record_state
                    _redraw_current_state()

                _recording_frames.clear()

        # Main screen clock update — only redraws when the second changes and screen is on
        if state.current_state == state.AppState.MAIN and state.screen_on:
            current_second = int(time.time())
            if current_second != last_second:
                last_second = current_second
                display.draw_main_screen()

        # Drawing game — redraw when dirty
        if state.current_state == state.AppState.DRAWING and state.drawing_dirty:
            state.drawing_dirty = False
            display.draw_drawing_screen()

        # Snake game — tick and redraw
        if state.current_state == state.AppState.SNAKE:
            if snake.tick():
                if state.snake_alive:
                    display.draw_snake_screen()
                else:
                    display.draw_snake_dead_screen()

        # About screen background update check
        if state.current_state == state.AppState.ABOUT and state.ota_status_changed:
            state.ota_status_changed = False
            display.draw_about_status()

        # Screen timeout check — disabled in Party Mode, Drawing, Snake, and Recording
        if state.screen_on and state.current_state not in (state.AppState.PARTY_MODE,
                                                             state.AppState.DRAWING,
                                                             state.AppState.SNAKE,
                                                             state.AppState.RECORDING,
                                                             state.AppState.TRANSCRIBING):
            if time.time() - state.last_activity_time > state.screen_timeout:
                state.screen_on = False
                hardware.board.set_backlight(0)

        time.sleep(0.008)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    party.stop_party_mode()
    hardware.board.cleanup()
    hardware.set_trackball_color(0, 0, 0)
