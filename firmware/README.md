# GPiBridge firmware

Version 0.3.0, for rev A of GPiBridge and GPiBridge Lite: one image runs both. C on the
Pico SDK 2.1.1 and TinyUSB. It builds and passes its host tests. It has not yet run on a
board.

**Which board.** `hal_init()` reads DC (GPIO19) once, before it drives anything. R21
holds it high on GPiBridge (10 k to 3.3 V) and low on the Lite (1 k to ground). On
GPiBridge the pin layer drives the transceivers' terminal pins and their TE, DC and PE;
on the Lite it drives the bus itself, open-drain: a line is asserted by enabling the
pin's output, whose value the pad holds low (OUTOVER), and released by making it an
input. `++ver`, `++t status` (`"board"`), the console's boot line and the USB product
string ("GPiBridge Lite USB-GPIB") say which. The serial port's name is the same on
both, so programs find either.

## Build, test, flash

```sh
./fetch_sdk.sh                             # once: the pinned Pico SDK into external/
cmake -S . -B build && cmake --build build -j
make -C test                               # the host tests, no hardware needed
python3 ../tools/gpibridge.py flash build/gpibridge.uf2
```

- **Needs:** CMake and `arm-none-eabi-gcc` (tested with 10.3). The SDK builds
  `picotool` itself, in `build/_deps/picotool/`.
- **A blank board** starts in the RP2354A's ROM bootloader. `picotool load -x
  build/gpibridge.uf2` loads it, or copy the `.uf2` onto the `RP2350` drive.
- **Linux:** `../tools/60-gpibridge.rules` gives `picotool` access without sudo.

## What the computer sees

One USB device, 1209:0001 (pid.codes' test PID until it has its own), asking for
300 mA. By default it is one serial port, as a Prologix is:

| interface | name | what |
|---|---|---|
| CDC 0 | GPiBridge GPIB | the Prologix "++" controller: `../HANDBOOK.md` §2 |
| vendor | Reset | Raspberry Pi's reset interface: `picotool reboot -f -u` |

- **`++t console 1`** adds a second serial port, "GPiBridge console". It carries JSON
  lines out, and takes `status`, `power on`, `power off`, `reboot` and `bootsel` in. The
  setting is saved, and the adapter reconnects with the new set of interfaces.
- **The UART** (J4, 115200 baud) always carries the same JSON lines, from the first one.
- **The USB serial number** is the RP2354A's unique ID.
- **Windows** binds its built-in drivers by itself: usbser to the serial ports, and
  WinUSB to the reset interface, through Microsoft OS 2.0 descriptors. So `picotool`
  works there with nothing installed.
- **Opening the console port at 1200 baud** reboots into BOOTSEL (the Arduino habit).

## The files

| file | what |
|---|---|
| `src/main.c` | USB callbacks, the console, settings in flash, LEDs, the failsafes |
| `src/capture.c`, `src/capture_rp2350.c` | the bus capture: core 1 records every change of the 16 bus lines and the direction pins (83 ns timestamps); `capture.c` writes it as a VCD |
| `src/prologix.c` | the "++" command set, escaping, the read and write loops |
| `src/gpib.c` | IEEE-488.1: source and acceptor handshakes, addressing, IFC, REN, serial poll; every wait has a timeout |
| `src/gpib_hal.h` | the bus as the engine sees it: lines asserted or released, whatever the wire's polarity |
| `src/hal_rp2350.c` | that interface on the board: GPIOs, transceiver directions, the 5 V switch |
| `src/board_pins.h` | which GPIO is which. **Generated** from `../gen/pins.py` by `../gen/firmware_pins.py`: edit those |
| `src/usb_descriptors.c`, `src/tusb_config.h` | the USB device: one or two serial ports, the reset interface, the Microsoft OS 2.0 descriptors |
| `boards/gpibridge.h` | the board for the SDK: RP2354A (RP2350A with 2 MB flash in the package), UART0 on GPIO16/17 |
| `test/` | the host tests and the simulated instrument |

## The rules the code keeps

- **Nothing on the bus until it is safe.** The transceivers stay unpowered until
  every pin is released and USB is configured. On unmount or suspend the firmware
  unwinds in reverse and powers them off.
- **No wire has two drivers.** When a transceiver changes direction, the pins that
  become its outputs are released first, and the pins that become its inputs are
  driven after (`hal_rp2350.c`).
- **Every wait ends.** A handshake wait gives up after `++read_tmo_ms` when reading
  (500 ms by default) and after 1 s when writing. It counts the timeout and leaves the
  bus idle. A 2 s watchdog catches anything else.
- **Never stuck in a bad image.** Three watchdog resets in a row restart in the ROM
  bootloader. A run of 10 s clears the count.
- **RP2350-E9.** While the transceivers are off, the bus pins rest on the pads'
  pull-downs with their input buffers off, the datasheet's workaround.
- **The Lite never drives a line high.** Its bus pins' output value is forced low in the
  pad, so the only thing software can do to a line is pull it low or let it go. Off the
  bus (USB unconfigured or suspended) every bus pin is an input with no pull and no
  input buffer, and the BUS LED is off; it lets go of the bus before it turns the LED off.
- **Core 1 only records.** It sleeps until `++t capture start`, then spins from RAM. It
  has called `flash_safe_execute_core_init()`, so settings writes pause it rather than
  crash it.

## The tests (`make -C test`)

- **`test_prologix`** (32 checks): what a host program types on the GPIB port, through
  `prologix.c` and `gpib.c`, against `sim_bus.c`. That is a simulated HP 33120A at
  address 10, doing both handshakes, `*IDN?`, `VOLT?`, `ECHO?`, SDC, GET, GTL and serial
  poll. It covers:
  - `++addr` with secondary addresses;
  - `++read eoi|n`, `++auto`, escaping, `++eot_*`, `++eos`, `++savecfg`;
  - `++spoll`, `++clr`, `++trg`, `++loc`;
  - a read timeout and an absent instrument;
  - `++t compat` and `++t console`;
  - `++ver` on each board.
- **`test_wire`**: the board's real pin layer too (`hal_rp2350.c`, with the SDK's GPIO
  calls stubbed in `test/stubs/`). The other end is a model of the SN75160B and SN75161B
  from their datasheets' function tables, with the board's pull resistors. After every
  pin change it checks two things:
  - the RP2354A and a transceiver never drive the same wire;
  - nothing is driven high into the unpowered transceivers.

  It also sends every byte value through the nibble-swapped data pins and back. Four
  planted bugs were each caught; `../DESIGN_NOTES.md` §2.3 lists them.

  `test_wire lite` runs the same against GPiBridge Lite: the pins on a wired-OR bus,
  R21 pulling DC down. After every pin change it checks that no bus pin drives its line
  high, that no bus pin's output is on without the pad's low override, and that nothing
  is asserted while the firmware is off the bus. Its first run caught the BUS LED going
  off a moment before NRFD and NDAC were released.
- **`sigrok_check.py`**: `test_wire` records the bus during `*IDN?` and the byte-value
  exchanges, both as the plug sees it and as the board's own capture sees it, through
  `capture.c`'s VCD writer. sigrok's IEEE-488 decoder, an independent implementation,
  must read back exactly the bytes that were sent: 12 of 12 recordings do, six for each
  board. It needs
  `sigrok-cli` (`apt install sigrok-cli`, or `$SIGROK_CLI`), and says "skipped" without
  it.

The C tests run under AddressSanitizer and UBSan. Add a test before changing the
protocol or the pin layer.

## Not yet

- **A PIO engine.** The pins were chosen for it: DIO1-8 and EOI on GPIO0-8, NRFD and
  NDAC adjacent.
- **Device mode** (`++mode 0`, `++lon`, `++status`): being an instrument, not the
  controller.
- **A USBTMC/USB488 interface.**
- **A/B images** with "try before you buy".
- **The plan's longer console command list** (`../PLAN.md` §3).
