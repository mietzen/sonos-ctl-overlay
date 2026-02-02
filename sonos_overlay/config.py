"""
Configuration loader for Sonos Control Overlay.
Loads settings from ~/.sonos-ctl-overlay.yml with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_PATH = Path.home() / ".sonos-ctl-overlay.yml"

# Font Awesome Unicode characters
FA_ICONS = {
    "volume_high": "\uf028",
    "volume_low": "\uf027",
    "volume_xmark": "\uf6a9",
    "volume_off": "\uf026",
    "play": "\uf04b",
    "pause": "\uf04c",
    "forward_step": "\uf051",
    "backward_step": "\uf048",
}


@dataclass
class OverlayStyle:
    """Overlay appearance settings."""

    background_color: str = "#D6D6D7"
    background_opacity: float = 0.5
    font_color: str = "#000000"
    corner_radius: int = 16
    duration_ms: int = 1500


@dataclass
class Config:
    """Application configuration."""

    speaker_ip: str | None = None
    volume_step: int = 2
    font_path: str = field(
        default_factory=lambda: str(Path.home() / "Library/Fonts/Font Awesome 7 Free-Solid-900.otf")
    )
    socket_path: str = "/tmp/sonos-ctl-overlay.sock"
    style: OverlayStyle = field(default_factory=OverlayStyle)


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b)


def load_config() -> Config:
    """Load configuration from YAML file, falling back to defaults."""
    config = Config()

    if not CONFIG_PATH.exists():
        return config

    try:
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return config

    # Top-level settings
    if "speaker_ip" in data:
        config.speaker_ip = data["speaker_ip"]
    if "volume_step" in data:
        config.volume_step = int(data["volume_step"])
    if "font_path" in data:
        config.font_path = os.path.expanduser(data["font_path"])
    if "socket_path" in data:
        config.socket_path = str(data["socket_path"])

    # Style settings
    style_data = data.get("style", {})
    if style_data:
        if "background_color" in style_data:
            config.style.background_color = style_data["background_color"]
        if "background_opacity" in style_data:
            config.style.background_opacity = float(style_data["background_opacity"])
        if "font_color" in style_data:
            config.style.font_color = style_data["font_color"]
        if "corner_radius" in style_data:
            config.style.corner_radius = int(style_data["corner_radius"])
        if "duration_ms" in style_data:
            config.style.duration_ms = int(style_data["duration_ms"])

    return config
