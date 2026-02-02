# Sonos Overlay

A macOS-style volume overlay for controlling Sonos speakers with Karabiner.

## Installation

### Prequisites

```bash
brew install font-fontawesome karabiner-element
```

```bash
# Install the package
pip install -e .
```

### Command Line

After installation, use the `sonos-overlay` command:

```bash
# Volume controls
sonos-overlay ${YOUR_SPEAKER_NAME} volume_up
sonos-overlay ${YOUR_SPEAKER_NAME} volume_down
sonos-overlay ${YOUR_SPEAKER_NAME} mute

# Playback controls
sonos-overlay ${YOUR_SPEAKER_NAME} playpause
sonos-overlay ${YOUR_SPEAKER_NAME} next
sonos-overlay ${YOUR_SPEAKER_NAME} prev
```

Or run as a module:

```bash
python3 -m sonos_overlay volume_up
```

### Karabiner Integration

```json
{
  "title": "Sonos Controls",
  "rules": [
    {
      "description": "Control Sonos with Media Keys",
      "manipulators": [
        {
          "type": "basic",
          "from": {"key_code": "volume_up"},
          "to": [{"shell_command": "sonos-overlay volume_up"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "volume_down"},
          "to": [{"shell_command": "sonos-overlay volume_down"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "mute"},
          "to": [{"shell_command": "sonos-overlay mute"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "play_or_pause"},
          "to": [{"shell_command": "sonos-overlay playpause"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "fastforward"},
          "to": [{"shell_command": "sonos-overlay next"}]
        },
        {
          "type": "basic",
          "from": {"key_code": "rewind"},
          "to": [{"shell_command": "sonos-overlay prev"}]
        }
      ]
    }
  ]
}
```

Enable in: Karabiner-Elements → Complex Modifications → Add rule
