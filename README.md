# Sonos Control Overlay

A macOS-style volume overlay for controlling Sonos speakers with Karabiner.

## Installation

### Prerequisites

```bash
brew install font-fontawesome karabiner-elements
```

```bash
mkdir -p ~/.local/{bin,opt}
python3 -m venv ~/.local/opt/sonos-ctl-overlay
~/.local/opt/sonos-ctl-overlay/bin/pip install git+https://github.com/mietzen/sonos-ctl-overlay.git
ln -s ~/.local/opt/sonos-ctl-overlay/bin/sonos-ctl-overlay ~/.local/bin/sonos-ctl-overlay
echo 'PATH=$PATH:$HOME/.local/bin' >> ~/.zshrc
```

## Configuration

Create `~/.sonos-ctl-overlay.yml`:

```yaml
speaker_ip: "192.168.1.100"
volume_step: 2
font_path: "~/Library/Fonts/Font Awesome 7 Free-Solid-900.otf"

style:
  background_color: "#D6D6D7"
  background_opacity: 0.8
  font_color: "#000000"
  corner_radius: 16
  duration_ms: 1500
```

## Usage

### Command Line

```bash
# With IP in config (recommended)
sonos-ctl-overlay volume_up
sonos-ctl-overlay volume_down
sonos-ctl-overlay mute
sonos-ctl-overlay playpause
sonos-ctl-overlay next
sonos-ctl-overlay prev

# Or specify IP directly
sonos-ctl-overlay 192.168.1.100 volume_up
```

### Karabiner Integration

Add to `~/.config/karabiner/assets/complex_modifications/sonos.json`:

```json
{
  "title": "Sonos Controls",
  "rules": [
    {
      "description": "Control Sonos with Media Keys",
      "manipulators": [
        {
          "type": "basic",
          "from": {"key_code": "F12"},
          "to": [{"shell_command": "~/.local/bin/sonos-ctl-overlay volume_up"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "F11"},
          "to": [{"shell_command": "~/.local/bin/sonos-ctl-overlay volume_down"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "F10"},
          "to": [{"shell_command": "~/.local/bin/sonos-ctl-overlay mute"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "F8"},
          "to": [{"shell_command": "~/.local/bin/sonos-ctl-overlay playpause"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "F9"},
          "to": [{"shell_command": "~/.local/bin/sonos-ctl-overlay next"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "F7"},
          "to": [{"shell_command": "~/.local/bin/sonos-ctl-overlay prev"}]
        }
      ]
    }
  ]
}
```

Enable in: Karabiner-Elements > Complex Modifications > Add rule
