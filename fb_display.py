"""
fb_display.py
Handles pushing pygame surfaces to the physical TFT framebuffer.
SDL is set to 'dummy' mode so it never tries to open a real display —
we write pixels manually to /dev/fb1 in RGB565 format.
"""

import numpy as np

FB_DEVICE  = '/dev/fb1'
FB_WIDTH   = 320
FB_HEIGHT  = 240

_fb_handle = None


def fb_init(device: str = FB_DEVICE) -> None:
    """Open the framebuffer device. Call once at startup."""
    global _fb_handle
    _fb_handle = open(device, 'wb')


def fb_push(surface) -> None:
    """
    Convert a pygame Surface (RGB888) to RGB565 and write it to the framebuffer.
    Call this every frame instead of pygame.display.flip().
    """
    if _fb_handle is None:
        raise RuntimeError("fb_display not initialised — call fb_init() first")

    # surfarray gives (width, height, 3) in RGB order — transpose to (height, width, 3)
    import pygame
    arr = pygame.surfarray.array3d(surface)
    arr = arr.transpose(1, 0, 2)

    # Pack RGB888 → RGB565
    r = (arr[:, :, 0] >> 3).astype(np.uint16)
    g = (arr[:, :, 1] >> 2).astype(np.uint16)
    b = (arr[:, :, 2] >> 3).astype(np.uint16)
    rgb565 = (r << 11) | (g << 5) | b

    _fb_handle.seek(0)
    _fb_handle.write(rgb565.tobytes())
    _fb_handle.flush()


def fb_clear() -> None:
    """
    Blank the framebuffer to black.
    Call this on exit so the TFT doesn't freeze on the last pygame frame.
    """
    if _fb_handle is None:
        return
    blank = np.zeros((FB_HEIGHT, FB_WIDTH), dtype=np.uint16)
    _fb_handle.seek(0)
    _fb_handle.write(blank.tobytes())
    _fb_handle.flush()


def fb_close() -> None:
    """Blank the screen and release the framebuffer handle."""
    fb_clear()
    if _fb_handle is not None:
        _fb_handle.close()
