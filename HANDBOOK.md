# GPiBridge handbook: bring-up, use, recovery

For GPiBridge and GPiBridge Lite alike: one firmware image runs both, and tells which
board it is on (`"board"` in `++t status`). Where the Lite differs, it says so.

## 1. Bring-up of a new board

**On Linux, once:** install `tools/60-gpibridge.rules`. It lets `picotool` reach the
adapter without sudo, and stops USB autosuspend from switching the bus off between
programs. The file says how. The serial ports need the `dialout` group.

Do these in order. Each step says what to see and what it rules out. Nothing here needs
an instrument until step 6.

**Before power.** JLCPCB has fitted every part but the GPIB plug. Look at:
- U1's pin 1 dot: the chip is turned 180 degrees, so its dot is at the bottom right,
  by the silk dot;
- L1's white dot, which must sit by the silk dot;
- D1-D3's cathodes, on the left;
- U2 and U3's pin 1, bottom left (silk triangles).

The parts most likely to be fitted the wrong way round are listed in
`mfg/release/PLACEMENT_CHECKS.txt`.

1. **USB current, transceivers off.** Plug into a USB port through a meter or a
   current-limited supply (5 V, 300 mA limit).
   - Blank (no firmware): about 20-40 mA. The RP2354A sits in its ROM bootloader and
     shows up as `RP2350 Boot` (2e8a:000f); `lsusb` shows it.
   - Probe the test points: VBUS on TP1, 3V3 on TP2 (3.25-3.35 V), 1V1 on TP3
     (1.05-1.15 V), 5V on TP4 (0 V: the transceivers are off), GND on TP5.
   - Green BUS LED: off.
2. **Load the firmware.** `picotool load -x firmware/build/gpibridge.uf2`, or copy the
   UF2 onto the `RP2350` drive. Its serial port appears: `python3 tools/gpibridge.py
   list`.
3. **Its status.** `python3 tools/gpibridge.py status` prints a JSON line with the
   version, `"bus_power":1` and `usb_ready_ms`. The firmware switches the transceivers on
   as soon as the host configures USB.
   - Green BUS LED: on. TP4: 4.7-5.1 V.
   - Current: up to about 270 mA with the drivers active (the datasheets' worst case);
     the typical figure is for this step to measure.
   - Yellow USB LED: steady (it blinks while waiting for the host).
4. **The debug connectors.** A Raspberry Pi Debug Probe, D port on J3 (SWD) and U port on
   J4 (UART, 115200 baud), is the way in when USB is broken (`BRINGUP.md` §5):
   - `openocd -f interface/cmsis-dap.cfg -f target/rp2350.cfg` attaches;
   - the UART prints the firmware's JSON log from its first line, with the start-up
     time (`at_ms`).
5. **The plug.** Solder the plug in the housing's base (`enclosure/README.md`), the
   board pressed down onto it: the pins' first 0.5 mm is 1.0 mm wide and grips the
   holes. Its 24 pins fit the board either way round, and turned round every signal is
   on the wrong contact. So solder two pins first: the one in the hole marked "1", and
   the one in the hole under "12" (contact 24's). Then measure at the plug's face, where the
   contact numbers are moulded:
   - contact 24 (the narrow side's end, diagonally opposite contact 1) reads 0 ohms to
     GND (TP5);
   - contact 1 does not.

   Turned round, the two pins sit in each other's holes and the readings swap. Then
   solder the rest, and check that contacts 1-11 and 13-17 are not shorted to each other
   or to GND, and that contacts 12 (the cable shield) and 18-24 read 0 ohms to GND.
6. **An instrument.** Plug into an instrument with a known GPIB address (for example
   the bench's HP 33120A at 10). Then `python3 tools/gpibridge.py test 10` prints its
   `*IDN?`, a serial-poll byte and the queries per second, and exits 0.

If step 6 fails:
- `++t status` counts `timeouts` and `no_listener`;
- `++t trace 1` logs every transfer (UART, and the console port if it is on);
- `python3 tools/gpibridge.py capture 10 "*IDN?" idn` records the bus during one query,
  for PulseView (`BRINGUP.md` §3);
- `no_listener` means nothing answered the address: the wrong address, the instrument
  off, the plug turned round (the D only fits one way into the instrument), or the
  transceivers unpowered.

## 2. Use

The adapter is one USB serial port, "GPiBridge GPIB", which speaks the Prologix
GPIB-USB controller's commands (controller mode, manual 6.0 in `datasheets/`). Port
settings (baud rate, flow control) do not matter: it is USB.

| command | does |
|---|---|
| `++addr N [SAD]` | the instrument's address (0-30; SAD 96-126) |
| any other line | sent to the instrument with the `++eos` terminator; EOI on its last byte if `++eoi 1` |
| `++read eoi` | read until the instrument sets EOI (or `++read_tmo_ms` passes with no byte) |
| `++read N`, `++read` | read until byte N, or until the timeout |
| `++auto 1` | read after every write |
| `++spoll [N]`, `++srq` | serial poll; the SRQ line |
| `++clr`, `++trg`, `++loc`, `++llo`, `++ifc` | SDC, GET, GTL, LLO, interface clear |
| `++eos 0-3`, `++eoi 0/1`, `++eot_enable`, `++eot_char` | terminators |
| `++savecfg 0/1` | settings kept in flash (written 2 s after the last change, only if changed) |
| `++ver`, `++help`, `++rst` | |

GPiBridge's own commands:

| command | does |
|---|---|
| `++t status` | JSON: version, board (`GPiBridge rev A` or `GPiBridge Lite rev A`), bus power, SRQ, byte and error counters, `usb_ready_ms` (reset to USB configured) |
| `++t trace 1` | log every transfer (UART, and the console port if it is on) |
| `++t capture start`, `stop`, `status`, `dump` | record the bus; `dump` sends a VCD for PulseView (`BRINGUP.md` §3) |
| `++t console 1` | add a second serial port, "GPiBridge console" (JSON log and commands); saved; the adapter reconnects. `0` removes it |
| `++t compat 1` | `++ver` answers with the Prologix string, for software that checks it (EZGPIB) |
| `++t power 0/1`, `++t ren 0/1` | on or off the bus (GPiBridge: the transceivers' 5 V); REN |
| `++t bootsel` | reboot into the ROM bootloader, for a firmware update |

In data lines, CR, LF, ESC and '+' must be escaped with ESC (27). An unescaped '+' is
dropped, as on a Prologix: `tools/gpibridge.py` escapes for you, and so does PyVISA-py's
Prologix driver.

### On each operating system

Nothing to install anywhere: every OS has the drivers built in.

| | Linux | macOS | Windows 10 and 11 |
|---|---|---|---|
| the port | `/dev/ttyACM0`, and `/dev/serial/by-id/usb-GPiBridge_..._GPIB_<serial>-if00` | `/dev/cu.usbmodem<serial>1` | `COMn`, "USB Serial Device" |
| driver | `cdc_acm` (kernel) | built in | `usbser` (built in) |
| to do once | the `dialout` group; `tools/60-gpibridge.rules` for `picotool` and against autosuspend | nothing | nothing |
| firmware update | `tools/gpibridge.py flash`, or `picotool`, or copy the `.uf2` to the `RP2350` drive | the same | the `RP2350` drive, or `picotool` (Windows binds WinUSB to the reset interface by itself) |

### Compared with a Prologix

- **The same.** The "++" command set and its escaping; no baud rate; no DTR needed.
  Programs that open a serial port and speak "++" work unchanged:
  - PyVISA-py: `PRLGX-ASRL0::/dev/ttyACM0::INTFC`, then `GPIB0::10::INSTR`;
  - EZGPIB, with `++t compat 1` once;
  - KE5FX's GPIB Toolkit;
  - `lab-instrument-control`.
- **Different:**
  - **The port's name.** A Prologix is an FTDI chip: `/dev/ttyUSB*` on Linux,
    `/dev/cu.usbserial-*` on macOS. This adapter is a standard USB serial port:
    `/dev/ttyACM*` and `/dev/cu.usbmodem*`. Scripts that hard-code the port name need
    the new one.
  - **The USB IDs**: 1209:0001, not FTDI's 0403:6001. Programs that look for the FTDI
    chip, or talk to it through FTDI's own D2XX library instead of a serial port, will
    not find it.
  - **`++ver`** says "GPiBridge ..." unless `++t compat 1`.
  - **Device mode** (`++mode 0`, `++lon`, `++status`) is not there yet: this firmware
    is a controller.
- **PyVISA-py's settings**: it sets `++read_tmo_ms 50`, too short for an instrument in
  local mode. Send `++read_tmo_ms 500` and raise the interface resource's timeout, as
  for a Prologix (`lab-instrument-control/gpib/gpib.md`).

### Firmware updates and Prologix programs

Updates use their own USB interface (Raspberry Pi's reset interface) or `++t bootsel`;
no Prologix program sends either. During an update the serial port disappears, and the
`RP2350` drive appears in its place. Then the adapter comes back with the same USB serial
number, so the same `COMn` on Windows and the same `/dev/serial/by-id/` name on Linux.
Settings saved with `++savecfg` survive updates.

## 3. Firmware updates and recovery

- **Normal update**: `python3 tools/gpibridge.py flash firmware/build/gpibridge.uf2`. It
  asks the firmware for BOOTSEL (`++t bootsel`), then runs `picotool load -x`. Or use
  `picotool reboot -f -u` then `picotool load -x FILE`: the reset interface does it.
- **Firmware that crashes**: after three watchdog resets in a row, it reboots into
  BOOTSEL by itself. Load a good image.
- **Firmware that runs but whose USB is broken**: load a new image over SWD (the Debug
  Probe on J3 works whatever the firmware does), or send `bootsel` on the console.
- **Nothing else works**: hold BOOT (a paperclip through the lid's small hole) while
  plugging in USB. The ROM bootloader always starts.

## 4. LEDs

| LED | colour | means |
|---|---|---|
| USB | yellow | blinking: waiting for the host; steady: configured; brief off: traffic |
| BUS | green | on the bus: on GPiBridge the transceivers have 5 V (lit by the switched supply itself); on the Lite the firmware lights it at the same moments |
| ERR | red | a bus error (timeout, no listener) in the last second |

## 5. GPiBridge Lite

- **Bring-up** is section 1, less what the Lite does not have: no TP4 (5 V), no U2 or U3
  to inspect, and its current in step 3 stays near the 20-40 mA of step 1. In step 3,
  `++t status` must say `"board":"GPiBridge Lite rev A"`: the firmware read R21 (1 k from
  DC to ground). If it says `GPiBridge`, R21 is missing or open, and the firmware would
  drive the transceiver controls instead of the bus: stop and look.
- **One instrument**, or up to three on a short cable: the RP2354A's pins sink 12 mA
  through 100 R each, against the 48 mA of IEEE 488.1's drivers (`DESIGN_NOTES.md` §7).
  For a full bus, use GPiBridge.
- **The plug** goes in as on GPiBridge, and the housing is the same, with the lid
  engraved "GPiBridge Lite".

## 6. Left plugged in with the USB unplugged

It is fine for either board on a working instrument; `DESIGN_NOTES.md` §8 has the
numbers. GPiBridge's transceivers do not load the bus while unpowered. The Lite's
RP2350 pins tolerate a standard bus's 3.4 V while unpowered (up to 3.63 V), and draw
almost nothing. A Prologix or UsbGpib left the same way is powered through its bus
pins and may sit half-awake; unplug those, or give them their USB, when other devices on
the bus are working.
