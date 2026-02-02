#!/usr/bin/env python3
"""
Sonos Control with Overlay.
Direct control using SoCo library with macOS-style overlay.
Non-blocking singleton pattern - can be called multiple times rapidly.
"""

import atexit
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys

import soco

from .config import FA_ICONS, Config, hex_to_rgb, load_config


def get_speaker(ip: str) -> soco.SoCo | None:
    """Get speaker by IP address directly."""
    try:
        return soco.SoCo(ip)
    except Exception as e:
        print(f"Error connecting to speaker at {ip}: {e}", file=sys.stderr)
        return None


def get_volume_icon(volume: int, is_muted: bool = False) -> str:
    """Return appropriate Font Awesome icon based on volume level."""
    if is_muted:
        return FA_ICONS["volume_xmark"]
    if volume == 0:
        return FA_ICONS["volume_off"]
    if volume < 33:
        return FA_ICONS["volume_low"]
    return FA_ICONS["volume_high"]


def get_playback_icon(state: str) -> str:
    """Return appropriate Font Awesome icon for playback state."""
    if state == "PLAYING":
        return FA_ICONS["play"]
    return FA_ICONS["pause"]


def execute_action(speaker: soco.SoCo, action: str, volume_step: int) -> dict:
    """Execute the Sonos command and return current state info."""
    result = {"action": action}
    try:
        if action == "volume_up":
            current = speaker.volume
            new_volume = min(100, current + volume_step)
            speaker.volume = new_volume
            result["volume"] = new_volume
            result["muted"] = speaker.mute

        elif action == "volume_down":
            current = speaker.volume
            new_volume = max(0, current - volume_step)
            speaker.volume = new_volume
            result["volume"] = new_volume
            result["muted"] = speaker.mute

        elif action == "mute":
            current_mute = speaker.mute
            speaker.mute = not current_mute
            result["volume"] = speaker.volume
            result["muted"] = not current_mute

        elif action == "playpause":
            state = speaker.get_current_transport_info()["current_transport_state"]
            if state == "PLAYING":
                speaker.pause()
                result["state"] = "PAUSED_PLAYBACK"
            else:
                speaker.play()
                result["state"] = "PLAYING"

        elif action == "next":
            speaker.next()
            result["state"] = "PLAYING"

        elif action == "prev":
            speaker.previous()
            result["state"] = "PLAYING"

    except Exception as e:
        print(f"Error executing action: {e}", file=sys.stderr)

    return result


def run_overlay_server(state_info_json: str, config_json: str) -> None:
    """Run overlay using native macOS APIs - no focus stealing."""
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyProhibited,
        NSBackingStoreBuffered,
        NSColor,
        NSFont,
        NSMakeRect,
        NSScreen,
        NSTextField,
        NSTimer,
        NSView,
        NSWindow,
        NSWindowStyleMaskBorderless,
    )
    from CoreText import CTFontManagerRegisterFontsForURL, kCTFontManagerScopeProcess
    from Foundation import NSURL, NSFileHandle, NSNotificationCenter

    state_info = json.loads(state_info_json)
    config_data = json.loads(config_json)

    # Reconstruct style from config
    style = config_data["style"]
    font_path = config_data["font_path"]
    socket_path = config_data["socket_path"]

    # Parse style settings
    bg_r, bg_g, bg_b = hex_to_rgb(style["background_color"])
    bg_opacity = style["background_opacity"]
    fg_r, fg_g, fg_b = hex_to_rgb(style["font_color"])
    corner_radius = style["corner_radius"]
    duration_ms = style["duration_ms"]

    # Prevent app from appearing in dock or stealing focus
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

    # Load Font Awesome
    fa_font = None
    if os.path.exists(font_path):
        font_url = NSURL.fileURLWithPath_(font_path)
        CTFontManagerRegisterFontsForURL(font_url, kCTFontManagerScopeProcess, None)
        for font_name in [
            "Font Awesome 6 Free Solid",
            "FontAwesome6Free-Solid",
            "Font Awesome 6 Free",
        ]:
            fa_font = NSFont.fontWithName_size_(font_name, 48)
            if fa_font:
                break

    if not fa_font:
        fa_font = NSFont.boldSystemFontOfSize_(48)

    fa_font_small = NSFont.fontWithName_size_(fa_font.fontName(), 36)
    if not fa_font_small:
        fa_font_small = NSFont.boldSystemFontOfSize_(36)

    # Determine window size based on action type
    action = state_info.get("action", "")
    is_square = action in ["playpause", "next", "prev"]

    screen = NSScreen.mainScreen()
    screen_frame = screen.frame()

    if is_square:
        width, height = 120, 120
    else:
        width, height = 300, 100

    x = (screen_frame.size.width - width) / 2
    y = 150

    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, width, height),
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    window.setLevel_(2000)
    window.setOpaque_(False)
    window.setBackgroundColor_(NSColor.clearColor())
    window.setIgnoresMouseEvents_(True)
    window.setHasShadow_(False)

    # Create content view with rounded corners and background color
    content_view = window.contentView()
    content_view.setWantsLayer_(True)
    content_view.layer().setBackgroundColor_(
        NSColor.colorWithCalibratedRed_green_blue_alpha_(bg_r, bg_g, bg_b, bg_opacity).CGColor()
    )
    content_view.layer().setCornerRadius_(corner_radius)
    content_view.layer().setMasksToBounds_(True)

    # Font color
    font_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(fg_r, fg_g, fg_b, 1.0)

    # Icon label
    icon_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 35, width, 55))
    icon_label.setBezeled_(False)
    icon_label.setDrawsBackground_(False)
    icon_label.setEditable_(False)
    icon_label.setSelectable_(False)
    icon_label.setTextColor_(font_color)
    icon_label.setFont_(fa_font)
    icon_label.setAlignment_(1)
    content_view.addSubview_(icon_label)

    # Progress bar background (for volume)
    bar_bg = NSView.alloc().initWithFrame_(NSMakeRect(25, 20, 250, 8))
    bar_bg.setWantsLayer_(True)
    bar_bg.layer().setBackgroundColor_(
        NSColor.colorWithCalibratedRed_green_blue_alpha_(fg_r, fg_g, fg_b, 0.25).CGColor()
    )
    bar_bg.layer().setCornerRadius_(4)
    bar_bg.setHidden_(is_square)
    content_view.addSubview_(bar_bg)

    # Progress bar foreground
    bar_fg = NSView.alloc().initWithFrame_(NSMakeRect(25, 20, 0, 8))
    bar_fg.setWantsLayer_(True)
    bar_fg.layer().setBackgroundColor_(
        NSColor.colorWithCalibratedRed_green_blue_alpha_(fg_r, fg_g, fg_b, 1.0).CGColor()
    )
    bar_fg.layer().setCornerRadius_(4)
    bar_fg.setHidden_(is_square)
    content_view.addSubview_(bar_fg)

    # State to track
    overlay_state = {"hide_timer": None, "idle_timer": None}

    def update_display(state: dict) -> None:
        action = state.get("action", "")

        if action in ["volume_up", "volume_down", "mute"]:
            volume = state.get("volume", 0)
            is_muted = state.get("muted", False)
            icon_label.setFont_(fa_font_small)
            icon_label.setFrame_(NSMakeRect(0, 45, 300, 45))
            icon_label.setStringValue_(get_volume_icon(volume, is_muted))
            bar_bg.setHidden_(False)
            bar_fg.setHidden_(False)
            bar_fg.setFrame_(NSMakeRect(25, 20, 250 * volume / 100, 8))
        elif action == "playpause":
            playback_state = state.get("state", "PAUSED_PLAYBACK")
            icon_label.setFont_(fa_font)
            icon_label.setFrame_(NSMakeRect(0, 36, 120, 48))
            icon_label.setStringValue_(get_playback_icon(playback_state))
            bar_bg.setHidden_(True)
            bar_fg.setHidden_(True)
        elif action in ["next", "prev"]:
            icon = FA_ICONS["forward_step"] if action == "next" else FA_ICONS["backward_step"]
            icon_label.setFont_(fa_font)
            icon_label.setFrame_(NSMakeRect(0, 36, 120, 48))
            icon_label.setStringValue_(icon)
            bar_bg.setHidden_(True)
            bar_fg.setHidden_(True)

        # Cancel existing hide timer
        if overlay_state["hide_timer"]:
            overlay_state["hide_timer"].invalidate()

        # Show window and set hide timer
        window.orderFrontRegardless()

        def hide_window() -> None:
            window.orderOut_(None)

        overlay_state["hide_timer"] = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            duration_ms / 1000.0, False, lambda t: hide_window()
        )

        # Reset idle timer
        if overlay_state["idle_timer"]:
            overlay_state["idle_timer"].invalidate()
        overlay_state["idle_timer"] = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            10.0, False, lambda t: app.terminate_(None)
        )

    # Setup socket server
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    with contextlib.suppress(OSError):
        os.unlink(socket_path)
    server_socket.bind(socket_path)
    server_socket.setblocking(False)

    # Socket notification handling
    file_handle = NSFileHandle.alloc().initWithFileDescriptor_(server_socket.fileno())

    def handle_socket_data(_notification: object) -> None:
        try:
            data = server_socket.recv(4096)
            if data:
                msg = json.loads(data.decode())
                update_display(msg)
        except Exception:
            pass
        file_handle.waitForDataInBackgroundAndNotify()

    NSNotificationCenter.defaultCenter().addObserverForName_object_queue_usingBlock_(
        "NSFileHandleDataAvailableNotification",
        file_handle,
        None,
        handle_socket_data,
    )
    file_handle.waitForDataInBackgroundAndNotify()

    # Show initial state
    update_display(state_info)

    # Cleanup on exit
    def cleanup() -> None:
        server_socket.close()
        with contextlib.suppress(OSError):
            os.unlink(socket_path)

    atexit.register(cleanup)

    def sigterm_handler(_signum: int, _frame: object) -> None:
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    # Run the app
    app.run()


def send_to_server(state_info: dict, socket_path: str) -> bool:
    """Send state info to running overlay server."""
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        client.sendto(json.dumps(state_info).encode(), socket_path)
        client.close()
        return True
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        with contextlib.suppress(OSError):
            os.unlink(socket_path)
        return False


def config_to_dict(config: Config) -> dict:
    """Convert config to JSON-serializable dict for subprocess."""
    return {
        "font_path": config.font_path,
        "socket_path": config.socket_path,
        "style": {
            "background_color": config.style.background_color,
            "background_opacity": config.style.background_opacity,
            "font_color": config.style.font_color,
            "corner_radius": config.style.corner_radius,
            "duration_ms": config.style.duration_ms,
        },
    }


def main() -> None:
    """Main entry point."""
    config = load_config()

    # Check if running as overlay server (internal mode)
    if len(sys.argv) >= 4 and sys.argv[1] == "--server":
        run_overlay_server(sys.argv[2], sys.argv[3])
        return

    # Parse CLI arguments
    valid_actions = ["volume_up", "volume_down", "mute", "playpause", "next", "prev"]

    if len(sys.argv) == 2:
        # Just action provided, use IP from config
        action = sys.argv[1]
        speaker_ip = config.speaker_ip
    elif len(sys.argv) == 3:
        # IP and action provided
        speaker_ip = sys.argv[1]
        action = sys.argv[2]
    else:
        print("Usage: sonos-overlay <action>", file=sys.stderr)
        print("       sonos-overlay <speaker_ip> <action>", file=sys.stderr)
        print(f"Actions: {', '.join(valid_actions)}", file=sys.stderr)
        print("\nSet speaker_ip in ~/.sonos-overlay.yml to omit IP from CLI", file=sys.stderr)
        sys.exit(1)

    if not speaker_ip:
        print("Error: No speaker IP provided", file=sys.stderr)
        print("Set speaker_ip in ~/.sonos-overlay.yml or pass as argument", file=sys.stderr)
        sys.exit(1)

    if action not in valid_actions:
        print(f"Invalid action: {action}", file=sys.stderr)
        print(f"Valid actions: {', '.join(valid_actions)}", file=sys.stderr)
        sys.exit(1)

    speaker = get_speaker(speaker_ip)
    if not speaker:
        sys.exit(1)

    state_info = execute_action(speaker, action, config.volume_step)

    if send_to_server(state_info, config.socket_path):
        sys.exit(0)

    # Start new overlay server
    state_json = json.dumps(state_info)
    config_json = json.dumps(config_to_dict(config))
    subprocess.Popen(
        [sys.executable, "-m", "sonos_overlay", "--server", state_json, config_json],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
