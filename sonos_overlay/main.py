#!/usr/bin/env python3
"""
Sonos Control with Overlay
Direct control using SoCo library with macOS-style overlay
"""

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QFontDatabase
import sys
import soco
from pathlib import Path

from .config import (
    SPEAKER_NAME,
    FONT_AWESOME_PATH,
    VOLUME_STEP,
    OVERLAY_DURATION,
    FA_ICONS
)

# ============================================================================
# SONOS CONTROL FUNCTIONS
# ============================================================================

def discover_speaker(speaker_name):
    """Find speaker by name using SoCo discovery"""
    try:
        # Try to discover all speakers
        speakers = soco.discover(timeout=2)
        if not speakers:
            print(f"No Sonos speakers found on network", file=sys.stderr)
            return None
        
        # Find speaker by name
        for speaker in speakers:
            if speaker.player_name == speaker_name:
                return speaker
        
        # If not found, list available speakers
        print(f"Speaker '{speaker_name}' not found.", file=sys.stderr)
        print(f"Available speakers:", file=sys.stderr)
        for speaker in speakers:
            print(f"  - {speaker.player_name}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error discovering speakers: {e}", file=sys.stderr)
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
        return FA_ICONS['pause']
    else:
        return FA_ICONS['play']

# ============================================================================
# OVERLAY WIDGET
# ============================================================================

class SonosOverlay(QWidget):
    def __init__(self, speaker, action):
        super().__init__()
        self.speaker = speaker
        self.action = action
        
        if not self.speaker:
            print("No speaker available", file=sys.stderr)
            QTimer.singleShot(0, QApplication.instance().quit)
            return
            
        # Execute action before showing overlay
        self.execute_action()
        self.init_ui()
        
    def execute_action(self):
        """Execute the Sonos command"""
        try:
            if self.action == 'volume_up':
                current = self.speaker.volume
                new_volume = min(100, current + VOLUME_STEP)
                self.speaker.volume = new_volume
                
            elif self.action == 'volume_down':
                current = self.speaker.volume
                new_volume = max(0, current - VOLUME_STEP)
                self.speaker.volume = new_volume
                
            elif self.action == 'mute':
                current_mute = self.speaker.mute
                self.speaker.mute = not current_mute
                
            elif self.action == 'playpause':
                state = self.speaker.get_current_transport_info()['current_transport_state']
                if state == 'PLAYING':
                    self.speaker.pause()
                else:
                    self.speaker.play()
                    
            elif self.action == 'next':
                self.speaker.next()
                
            elif self.action == 'prev':
                self.speaker.previous()
                
        except Exception as e:
            print(f"Error executing action: {e}", file=sys.stderr)
        
    def init_ui(self):
        """Initialize the UI"""
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
            # Try alternative paths
            alt_paths = [
                str(Path.home() / ".fonts/FontAwesome6Free-Solid-900.otf"),
                "/usr/share/fonts/truetype/font-awesome/FontAwesome6Free-Solid-900.otf",
                "/System/Library/Fonts/FontAwesome.otf",
            ]
            for alt_path in alt_paths:
                font_id = QFontDatabase.addApplicationFont(alt_path)
                if font_id != -1:
                    break
            
            if font_id == -1:
                print(f"Warning: Could not load Font Awesome", file=sys.stderr)
                print(f"Tried: {FONT_AWESOME_PATH}", file=sys.stderr)
                for path in alt_paths:
                    print(f"       {path}", file=sys.stderr)
                fa_family = "Arial"
            else:
                fa_families = QFontDatabase.applicationFontFamilies(font_id)
                fa_family = fa_families[0] if fa_families else "Arial"
        else:
            fa_families = QFontDatabase.applicationFontFamilies(font_id)
            fa_family = fa_families[0] if fa_families else "Arial"
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # Determine what to display based on action
        if self.action in ['volume_up', 'volume_down', 'mute']:
            self.show_volume_overlay(layout, fa_family)
        elif self.action == 'playpause':
            self.show_playback_overlay(layout, fa_family)
        elif self.action in ['next', 'prev']:
            self.show_track_overlay(layout, fa_family)
        
        self.setLayout(layout)
        
        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(44, 44, 44, 230);
                border-radius: 12px;
            }
        """)
        self.setFixedSize(300, 120)
        
        # Position at top center
        screen = QApplication.desktop().screenGeometry()
        self.move((screen.width() - self.width()) // 2, 100)
        
        # Auto-close timer
        QTimer.singleShot(OVERLAY_DURATION, QApplication.instance().quit)
    
    def show_volume_overlay(self, layout, fa_family):
        """Show volume control overlay"""
        try:
            volume = self.speaker.volume
            is_muted = self.speaker.mute
        except Exception as e:
            print(f"Error getting volume info: {e}", file=sys.stderr)
            volume = 0
            is_muted = False
        
        # Icon
        icon_text = get_volume_icon(volume, is_muted)
        icon = QLabel(icon_text)
        icon.setFont(QFont(fa_family, 36))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(icon)
        
        # Progress bar
        progress = QProgressBar()
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
    
    def show_playback_overlay(self, layout, fa_family):
        """Show playback control overlay"""
        try:
            transport_info = self.speaker.get_current_transport_info()
            state = transport_info['current_transport_state']
        except Exception as e:
            print(f"Error getting playback state: {e}", file=sys.stderr)
            state = 'PAUSED_PLAYBACK'
        
        # Icon
        icon_text = get_playback_icon(state)
        icon = QLabel(icon_text)
        icon.setFont(QFont(fa_family, 48))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(icon)
        
        # State text
        state_text = "Playing" if state == 'PLAYING' else "Paused"
        label = QLabel(state_text)
        label.setFont(QFont('Arial', 14))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(label)
    
    def show_track_overlay(self, layout, fa_family):
        """Show track skip overlay"""
        icon_text = FA_ICONS['forward_step'] if self.action == 'next' else FA_ICONS['backward_step']
        
        # Icon
        icon = QLabel(icon_text)
        icon.setFont(QFont(fa_family, 48))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(icon)
        
        # Action text
        action_text = "Next Track" if self.action == 'next' else "Previous Track"
        label = QLabel(action_text)
        label.setFont(QFont('Arial', 14))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(label)

# ============================================================================
# MAIN
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: sonos-control.py <action>", file=sys.stderr)
        print("Actions: volume_up, volume_down, mute, playpause, next, prev", file=sys.stderr)
        sys.exit(1)
    
    action = sys.argv[1]
    
    # Validate action
    valid_actions = ['volume_up', 'volume_down', 'mute', 'playpause', 'next', 'prev']
    if action not in valid_actions:
        print(f"Invalid action: {action}", file=sys.stderr)
        print(f"Valid actions: {', '.join(valid_actions)}", file=sys.stderr)
        sys.exit(1)
    
    # Discover speaker
    speaker = discover_speaker(SPEAKER_NAME)
    if not speaker:
        sys.exit(1)
    
    # Create and show overlay
    app = QApplication(sys.argv)
    overlay = SonosOverlay(speaker, action)
    overlay.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

# Allow running as: python -m sonos_overlay
# and as installed script: sonos-overlay
