"""
Configuration settings for Sonos Overlay
"""

from pathlib import Path
import os

# Speaker Configuration
SPEAKER_NAME = os.environ.get("SONOS_SPEAKER_NAME", "Living Room")

# Font Configuration
FONT_AWESOME_PATH = os.environ.get(
    "FONT_AWESOME_PATH",
    str(Path.home() / "Library/Fonts/Font Awesome 7 Free-Solid-900.otf")
)

# Volume Configuration
VOLUME_STEP = int(os.environ.get("SONOS_VOLUME_STEP", "2"))

# Overlay Display Configuration
OVERLAY_DURATION = int(os.environ.get("SONOS_OVERLAY_DURATION", "1500"))

# Font Awesome Unicode characters
FA_ICONS = {
    'volume_high': '\uf028',      # fa-volume-high
    'volume_low': '\uf027',       # fa-volume-low
    'volume_xmark': '\uf6a9',     # fa-volume-xmark
    'volume_off': '\uf026',       # fa-volume-off
    'play': '\uf04b',             # fa-play
    'pause': '\uf04c',            # fa-pause
    'forward_step': '\uf051',     # fa-forward-step
    'backward_step': '\uf048',    # fa-backward-step
}
