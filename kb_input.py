"""
kb_input.py
Reads raw keyboard events from an evdev input device and injects them
into pygame's event queue as standard KEYDOWN / KEYUP events.

SDL in 'dummy' mode has no input pipeline, so we bypass it entirely
and feed events manually — your existing pygame.event.get() loop
picks them up with no changes needed.
"""

import threading
import pygame
from evdev import InputDevice, categorize, ecodes

# Map evdev key codes → pygame key constants.
# Add any keys your UI needs that aren't listed here.
KEYMAP: dict[int, int] = {
    ecodes.KEY_UP:        pygame.K_UP,
    ecodes.KEY_DOWN:      pygame.K_DOWN,
    ecodes.KEY_LEFT:      pygame.K_LEFT,
    ecodes.KEY_RIGHT:     pygame.K_RIGHT,
    ecodes.KEY_ENTER:     pygame.K_RETURN,
    ecodes.KEY_BACKSPACE: pygame.K_BACKSPACE,
    ecodes.KEY_SPACE:     pygame.K_SPACE,
    ecodes.KEY_ESC:       pygame.K_ESCAPE,
    ecodes.KEY_TAB:       pygame.K_TAB,
}

# Path to your wireless keyboard/dongle input device.
# Check with: ls /dev/input/by-id/
DEFAULT_KEYBOARD_DEVICE = '/dev/input/by-id/usb-1ea7_2.4G_Mouse-event-kbd'


class KeyboardBridge:
    """
    Spawns a daemon thread that reads evdev events and posts
    them into pygame's event queue.
    """

    def __init__(self, device_path: str = DEFAULT_KEYBOARD_DEVICE):
        self.device_path = device_path
        self._running = False
        self._thread = threading.Thread(target=self._listen, daemon=True)

    def start(self) -> None:
        """Start listening for keyboard events."""
        self._running = True
        self._thread.start()

    def stop(self) -> None:
        """Signal the listener thread to stop."""
        self._running = False

    def _listen(self) -> None:
        try:
            device = InputDevice(self.device_path)
        except FileNotFoundError:
            print(f"[kb_input] Device not found: {self.device_path}")
            return

        for event in device.read_loop():
            if not self._running:
                break
            if event.type != ecodes.EV_KEY:
                continue

            key_event = categorize(event)
            pg_key = KEYMAP.get(key_event.scancode)
            if pg_key is None:
                continue

            if key_event.keystate == key_event.key_down:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pg_key))
            elif key_event.keystate == key_event.key_up:
                pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pg_key))

