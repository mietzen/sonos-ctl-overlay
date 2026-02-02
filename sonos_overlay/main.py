#!/usr/bin/env python3
"""
Sonos Control with Overlay
Direct control using SoCo library with macOS-style overlay
Non-blocking singleton pattern - can be called multiple times rapidly
"""

import sys
import os
import socket
import json
import subprocess
import soco
from pathlib import Path

# Defer Qt imports until needed (after fork check)
def get_qt_imports():
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar
    from PyQt5.QtCore import Qt, QTimer, QSocketNotifier
    from PyQt5.QtGui import QFont, QFontDatabase
    return QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, Qt, QTimer, QSocketNotifier, QFont, QFontDatabase

from .config import (
    FONT_AWESOME_PATH,
    VOLUME_STEP,
    OVERLAY_DURATION,
    SOCKET_PATH,
    FA_ICONS
)

# ============================================================================
# SONOS CONTROL FUNCTIONS
# ============================================================================

def get_speaker(ip):
    """Get speaker by IP address directly"""
    try:
        return soco.SoCo(ip)
    except Exception as e:
        print(f"Error connecting to speaker at {ip}: {e}", file=sys.stderr)
        return None

def get_volume_icon(volume, is_muted=False):
    """Return appropriate Font Awesome icon based on volume level"""
    if is_muted:
        return FA_ICONS['volume_xmark']
    elif volume == 0:
        return FA_ICONS['volume_off']
    elif volume < 33:
        return FA_ICONS['volume_low']
    else:
        return FA_ICONS['volume_high']

def get_playback_icon(state):
    """Return appropriate Font Awesome icon for playback state"""
    if state == 'PLAYING':
        return FA_ICONS['play']
    else:
        return FA_ICONS['pause']

def execute_action(speaker, action):
    """Execute the Sonos command and return current state info"""
    result = {'action': action}
    try:
        if action == 'volume_up':
            current = speaker.volume
            new_volume = min(100, current + VOLUME_STEP)
            speaker.volume = new_volume
            result['volume'] = new_volume
            result['muted'] = speaker.mute

        elif action == 'volume_down':
            current = speaker.volume
            new_volume = max(0, current - VOLUME_STEP)
            speaker.volume = new_volume
            result['volume'] = new_volume
            result['muted'] = speaker.mute

        elif action == 'mute':
            current_mute = speaker.mute
            speaker.mute = not current_mute
            result['volume'] = speaker.volume
            result['muted'] = not current_mute

        elif action == 'playpause':
            state = speaker.get_current_transport_info()['current_transport_state']
            if state == 'PLAYING':
                speaker.pause()
                result['state'] = 'PAUSED_PLAYBACK'
            else:
                speaker.play()
                result['state'] = 'PLAYING'

        elif action == 'next':
            speaker.next()
            result['state'] = 'PLAYING'

        elif action == 'prev':
            speaker.previous()
            result['state'] = 'PLAYING'

    except Exception as e:
        print(f"Error executing action: {e}", file=sys.stderr)

    return result

# ============================================================================
# OVERLAY WIDGET (created only when running as server)
# ============================================================================

def create_overlay_class():
    """Factory to create overlay class with Qt imports"""
    QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, Qt, QTimer, QSocketNotifier, QFont, QFontDatabase = get_qt_imports()

    class SonosOverlay(QWidget):
        def __init__(self):
            super().__init__()
            self.close_timer = None
            self.server_socket = None
            self.socket_notifier = None
            self.fa_family = None
            self.QTimer = QTimer
            self.QSocketNotifier = QSocketNotifier
            self.QFont = QFont
            self.Qt = Qt
            self.QLabel = QLabel
            self.QProgressBar = QProgressBar
            self.QVBoxLayout = QVBoxLayout
            self.init_ui_base(QFontDatabase)

        def init_ui_base(self, QFontDatabase):
            """Initialize the base UI without content"""
            Qt = self.Qt
            # Window flags for overlay
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool |
                Qt.X11BypassWindowManagerHint
            )
            self.setAttribute(Qt.WA_TranslucentBackground)

            # Load Font Awesome
            font_id = QFontDatabase.addApplicationFont(FONT_AWESOME_PATH)
            if font_id == -1:
                alt_paths = [
                    str(Path.home() / ".fonts/FontAwesome6Free-Solid-900.otf"),
                    "/usr/share/fonts/truetype/font-awesome/FontAwesome6Free-Solid-900.otf",
                ]
                for alt_path in alt_paths:
                    font_id = QFontDatabase.addApplicationFont(alt_path)
                    if font_id != -1:
                        break

                if font_id == -1:
                    print(f"Warning: Could not load Font Awesome from {FONT_AWESOME_PATH}", file=sys.stderr)
                    self.fa_family = "Arial"
                else:
                    fa_families = QFontDatabase.applicationFontFamilies(font_id)
                    self.fa_family = fa_families[0] if fa_families else "Arial"
            else:
                fa_families = QFontDatabase.applicationFontFamilies(font_id)
                self.fa_family = fa_families[0] if fa_families else "Arial"

            # Styling
            self.setStyleSheet("""
                QWidget {
                    background-color: rgba(44, 44, 44, 230);
                    border-radius: 12px;
                }
            """)
            self.setFixedSize(300, 100)

            # Position at lower-mid of screen
            self.position_overlay()

        def position_overlay(self):
            """Position overlay at lower-mid of screen"""
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.desktop().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = screen.height() - self.height() - 150  # 150px from bottom
            self.move(x, y)

        def update_display(self, state_info):
            """Update the overlay display with new state"""
            # Clear existing layout
            if self.layout():
                while self.layout().count():
                    item = self.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            else:
                layout = self.QVBoxLayout()
                layout.setContentsMargins(25, 20, 25, 20)
                layout.setSpacing(10)
                self.setLayout(layout)

            action = state_info.get('action', '')

            if action in ['volume_up', 'volume_down', 'mute']:
                self.show_volume_overlay(state_info)
            elif action == 'playpause':
                self.show_playback_overlay(state_info)
            elif action in ['next', 'prev']:
                self.show_track_overlay(state_info)

            # Reset close timer
            if self.close_timer:
                self.close_timer.stop()
            self.close_timer = self.QTimer()
            self.close_timer.setSingleShot(True)
            self.close_timer.timeout.connect(self.hide_overlay)
            self.close_timer.start(OVERLAY_DURATION)

            self.show()
            self.raise_()

        def hide_overlay(self):
            """Hide the overlay"""
            self.hide()

        def show_volume_overlay(self, state_info):
            """Show volume control overlay"""
            volume = state_info.get('volume', 0)
            is_muted = state_info.get('muted', False)

            layout = self.layout()

            # Icon
            icon_text = get_volume_icon(volume, is_muted)
            icon = self.QLabel(icon_text)
            icon.setFont(self.QFont(self.fa_family, 36))
            icon.setAlignment(self.Qt.AlignCenter)
            icon.setStyleSheet("color: white; background: transparent;")
            layout.addWidget(icon)

            # Progress bar
            progress = self.QProgressBar()
            progress.setValue(volume)
            progress.setTextVisible(False)
            progress.setFixedHeight(8)
            progress.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 4px;
                    background-color: rgba(255, 255, 255, 0.25);
                }
                QProgressBar::chunk {
                    background-color: white;
                    border-radius: 4px;
                }
            """)
            layout.addWidget(progress)

        def show_playback_overlay(self, state_info):
            """Show playback control overlay - icon only"""
            state = state_info.get('state', 'PAUSED_PLAYBACK')

            layout = self.layout()

            # Icon - show current state (play icon when playing, pause when paused)
            icon_text = get_playback_icon(state)
            icon = self.QLabel(icon_text)
            icon.setFont(self.QFont(self.fa_family, 48))
            icon.setAlignment(self.Qt.AlignCenter)
            icon.setStyleSheet("color: white; background: transparent;")
            layout.addWidget(icon)

        def show_track_overlay(self, state_info):
            """Show track skip overlay - icon only"""
            action = state_info.get('action', 'next')
            icon_text = FA_ICONS['forward_step'] if action == 'next' else FA_ICONS['backward_step']

            layout = self.layout()

            # Icon only
            icon = self.QLabel(icon_text)
            icon.setFont(self.QFont(self.fa_family, 48))
            icon.setAlignment(self.Qt.AlignCenter)
            icon.setStyleSheet("color: white; background: transparent;")
            layout.addWidget(icon)

        def setup_server(self):
            """Setup Unix socket server for receiving commands"""
            # Remove old socket if exists
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass

            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.server_socket.bind(SOCKET_PATH)
            self.server_socket.setblocking(False)

            # Use Qt socket notifier for async socket handling
            self.socket_notifier = self.QSocketNotifier(
                self.server_socket.fileno(),
                self.QSocketNotifier.Read
            )
            self.socket_notifier.activated.connect(self.handle_socket_data)

        def handle_socket_data(self):
            """Handle incoming data on the socket"""
            try:
                data = self.server_socket.recv(4096)
                if data:
                    msg = json.loads(data.decode())
                    self.update_display(msg)
            except Exception as e:
                print(f"Error handling socket data: {e}", file=sys.stderr)

        def cleanup(self):
            """Cleanup socket on exit"""
            if self.server_socket:
                self.server_socket.close()
            try:
                os.unlink(SOCKET_PATH)
            except OSError:
                pass

    return SonosOverlay, QApplication, QTimer

# ============================================================================
# CLIENT/SERVER COMMUNICATION
# ============================================================================

def send_to_server(state_info):
    """Send state info to running overlay server"""
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        client.sendto(json.dumps(state_info).encode(), SOCKET_PATH)
        client.close()
        return True
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        # Server not running or stale socket - clean up
        try:
            os.unlink(SOCKET_PATH)
        except OSError:
            pass
        return False

# ============================================================================
# MAIN
# ============================================================================

def run_overlay_server(state_info_json):
    """Run the overlay server (called in subprocess)"""
    state_info = json.loads(state_info_json)

    SonosOverlay, QApplication, QTimer = create_overlay_class()

    app = QApplication(sys.argv)
    overlay = SonosOverlay()
    overlay.setup_server()
    overlay.update_display(state_info)

    # Cleanup on exit
    app.aboutToQuit.connect(overlay.cleanup)

    # Auto-quit after longer idle (no commands for 10 seconds)
    idle_timer = QTimer()
    idle_timer.setSingleShot(True)
    idle_timer.timeout.connect(app.quit)
    idle_timer.start(10000)

    # Reset idle timer when overlay is updated
    original_update = overlay.update_display
    def update_with_idle_reset(si):
        original_update(si)
        idle_timer.start(10000)
    overlay.update_display = update_with_idle_reset

    app.exec_()


def main():
    # Check if running as overlay server (internal mode)
    if len(sys.argv) >= 3 and sys.argv[1] == '--server':
        run_overlay_server(sys.argv[2])
        return

    if len(sys.argv) < 3:
        print("Usage: sonos-overlay <speaker_ip> <action>", file=sys.stderr)
        print("Actions: volume_up, volume_down, mute, playpause, next, prev", file=sys.stderr)
        sys.exit(1)

    speaker_ip = sys.argv[1]
    action = sys.argv[2]

    # Validate action
    valid_actions = ['volume_up', 'volume_down', 'mute', 'playpause', 'next', 'prev']
    if action not in valid_actions:
        print(f"Invalid action: {action}", file=sys.stderr)
        print(f"Valid actions: {', '.join(valid_actions)}", file=sys.stderr)
        sys.exit(1)

    # Get speaker by IP
    speaker = get_speaker(speaker_ip)
    if not speaker:
        sys.exit(1)

    # Execute action and get state
    state_info = execute_action(speaker, action)

    # Try to send to existing server
    if send_to_server(state_info):
        # Successfully sent to existing overlay
        sys.exit(0)

    # Spawn subprocess to run overlay (non-blocking)
    state_json = json.dumps(state_info)
    subprocess.Popen(
        [sys.executable, '-m', 'sonos_overlay', '--server', state_json],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )


if __name__ == '__main__':
    main()
