# pokEPROM

A pocket-sized BIOS chip dumper, flasher, and library manager — no PC required.

Built around a Raspberry Pi Zero W, a CH341A SPI programmer, and a small TFT
display, pokEPROM lets you detect, read, write, and catalog BIOS/EEPROM chips
on the go. Think of it as a portable flashrom front-end with a chip library
built in.

## Status
🚧 Early prototype — UI and navigation logic built in pygame, running on PC
for now. Hardware integration (Pi + display + encoder) in progress.

## Planned
- [x] Screen navigation system (stack-based, encoder-friendly)
- [x] Detect / Read / Write / Bins screens
- [x] Chip-matched bin filtering before write
- [x] Auto-backup before write
- [ ] Physical hardware (Pi Zero W + TFT + rotary encoder)
- [ ] Bin search/filter screen
- [ ] Hex viewer
- [ ] Custom ESP32 standalone version
- [ ] Custom CH341A-alternative board (multi-voltage, all-in-one)

## Hardware (current prototype target)
- Raspberry Pi Zero W
- 2.2" TFT SPI display (ILI9341, 240x320)
- CH341A SPI programmer + SOIC8 clip
- Rotary encoder w/ push button

## Software
- Python 3 + pygame (runs on framebuffer, no desktop required)
- flashrom (CH341A driver/backend)
