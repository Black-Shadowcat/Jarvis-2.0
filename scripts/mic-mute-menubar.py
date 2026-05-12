#!/usr/bin/env /opt/homebrew/bin/python3.11
"""Menu bar button to mute/unmute microphone."""

import subprocess
import rumps


def get_mic_volume():
    result = subprocess.run(
        ["osascript", "-e", "input volume of (get volume settings)"],
        capture_output=True, text=True
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 75


def set_mic_volume(volume):
    subprocess.run(
        ["osascript", "-e", f"set volume input volume {volume}"],
        capture_output=True
    )


class MicMuteApp(rumps.App):
    def __init__(self):
        super().__init__("🎙️", quit_button=None)
        self.muted = False
        self.last_volume = get_mic_volume() or 75
        self.menu = ["Mikro stummschalten", None, "Beenden"]

    @rumps.clicked("Mikro stummschalten")
    def toggle_mute(self, sender):
        if self.muted:
            set_mic_volume(self.last_volume)
            self.title = "🎙️"
            sender.title = "Mikro stummschalten"
            self.muted = False
        else:
            self.last_volume = get_mic_volume() or 75
            set_mic_volume(0)
            self.title = "🔇"
            sender.title = "Mikro wieder aktivieren"
            self.muted = True

    @rumps.clicked("Beenden")
    def quit_app(self, _):
        if self.muted:
            set_mic_volume(self.last_volume)
        rumps.quit_application()


if __name__ == "__main__":
    MicMuteApp().run()
