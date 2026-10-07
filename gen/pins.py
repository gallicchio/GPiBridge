"""Which RP2354A pin does what: the one source of truth.

The schematic, the MCU symbol's pin order, the firmware's pin header
(firmware/src/board_pins.h, written by gen/firmware_pins.py) and the pinout
document are all made from this file.

The bus lines are active low on the wire.  The SN7516x transceivers do not
invert, so a terminal pin is low when its bus line is asserted.  The firmware
inverts them (in C, firmware/src/hal_rp2350.c; a PIO engine would use the
pads' INOVER/OUTOVER), so the bus engine sees 1 = asserted.

PIO needs:
  * the eight data lines and EOI on consecutive pins (GPIO0-8): one `in` or
    `out` of 9 bits;
  * NRFD and NDAC consecutive (GPIO10-11): one 2-bit side-set for the listener;
  * DAV on its own pin (GPIO9): a 1-bit side-set for the talker.

The data byte sits on GPIO0-7 with its nibbles swapped: GPIO0-3 carry DIO5-8
and GPIO4-7 carry DIO1-4.  That order lets all sixteen data wires (MCU to
SN75160B, SN75160B to the plug) run on the top copper layer without one
crossing: the RP2354A's pins meet the transceiver's in that order, and the
transceiver's bus pins then meet the plug's two rows in order.  The firmware
swaps the nibbles on the way in and out (byte = (b << 4 | b >> 4) & 0xFF).
"""

# GPIO -> (net, what it is)
GPIO = {
    0: ("DIO5", "data, via SN75160B; GPIO0-3 carry DIO5-8 and GPIO4-7 DIO1-4, so no data wires cross"),
    1: ("DIO6", ""), 2: ("DIO7", ""),
    3: ("DIO8", ""), 4: ("DIO1", ""), 5: ("DIO2", ""), 6: ("DIO3", ""), 7: ("DIO4", ""),
    8: ("EOI", "end or identify, via SN75161B"), 9: ("DAV", "data valid"),
    10: ("NRFD", "not ready for data"), 11: ("NDAC", "not data accepted"),
    12: ("IFC", "interface clear"), 13: ("REN", "remote enable"), 14: ("ATN", "attention"),
    15: ("SRQ", "service request"),
    16: ("UART_TX", "UART0 TX, to the debug connector"), 17: ("UART_RX", "UART0 RX, from the debug connector"),
    18: ("GP18", "spare"),
    19: ("DC", "SN75161B direction: low = controller (drives ATN, REN, IFC); also the board ID: "
               "10 k up on GPiBridge, 1 k down on GPiBridge Lite"),
    20: ("PE", "SN75160B pull-up enable: high = totem-pole DIO, low = open collector"),
    21: ("BUS_PWR_EN", "high switches 5 V to the transceivers"),
    22: ("LED_USB", "yellow LED, high = on"), 23: ("LED_ERR", "red LED, high = on"),
    24: ("TE_DATA", "SN75160B talk enable: high drives DIO onto the bus"),
    25: ("TE_CTRL", "SN75161B talk enable"),
    26: ("GP26", "spare"), 27: ("GP27", "spare"), 28: ("GP28", "spare"), 29: ("GP29", "spare"),
}

NET = {g: n for g, (n, _) in GPIO.items()}
GPIO_OF = {n: g for g, n in NET.items()}

# The order of the MCU symbol's right side, top to bottom (None = an empty
# row).  It is the order of the transceivers' rows, so every bus line runs
# straight across the sheet.  Lines with a pull-up get five empty rows above
# them, room for the resistor and its 3.3 V flag to hang from their own line
# without crossing another; DC, first, has the gap above U3.
GAP_U2_U3 = 16         # rows between the two transceivers: U2's GND, U3's VCC, notes
RIGHT_ROWS = (["BUS_PWR_EN", None, None]
              + ["DIO1", "DIO2", "DIO3", "DIO4", None, "DIO5", "DIO6", "DIO7", "DIO8"] + [None, "PE", "TE_DATA"]
              + [None] * GAP_U2_U3
              + ["DC"] + [None] * 5 + ["NRFD"] + [None] * 5 + ["NDAC"] + [None] * 5
              + ["SRQ", "EOI", None, "DAV", "ATN", "IFC", "REN", "TE_CTRL"])
# The 10 k pulls that set the transceivers' state while the RP2354A is in
# reset or blank.  (No series resistors: the transceivers' terminal outputs
# are short-circuit limited, and the firmware changes direction in one
# place, TE before the pins when talking, the pins before TE when listening.)
PULL_R = {"DC": "R21", "TE_DATA": "R19", "TE_CTRL": "R20", "BUS_PWR_EN": "R15"}

# Which of the SN75160B's eight identical channels carries each data line
# (channel c: bus pin Bc = pin c + 1, terminal pin Dc = pin 20 - c).  The
# channels are interchangeable, so they are assigned to suit the board.  U2
# lies above contacts 1-4 (upper row) and 13-16 (lower row), its bus pins
# B1..B8 left to right: B1-B4 run straight down to contacts 4, 3, 2, 1, and
# B5-B8 pass right of contact 1 into the gap between the rows and on to
# contacts 16, 15, 14, 13, all on the top layer.  The terminal pins D1..D8
# then read DIO4, 3, 2, 1, 8, 7, 6, 5, the order of GPIO7..GPIO0 as they
# leave the RP2354A.
U2_CHANNEL = {"DIO1": 4, "DIO2": 3, "DIO3": 2, "DIO4": 1, "DIO5": 8, "DIO6": 7, "DIO7": 6, "DIO8": 5}
# The left side, top to bottom: fixed-function pins by name, GPIOs by net.
LEFT_ROWS = (["USB_DM", "USB_DP"] + [None] * 5
             + ["XIN"] + [None] * 4 + ["XOUT"] + [None] * 6
             + ["SWCLK", "SWDIO"] + [None] * 4
             + ["RUN"] + [None] * 4 + ["QSPI_SS"] + [None] * 3
             + ["QSPI_SCLK", "QSPI_SD0", "QSPI_SD1", "QSPI_SD2", "QSPI_SD3"] + [None] * 3
             + ["UART_RX", "UART_TX"] + [None] * 3
             + ["LED_USB"] + [None] * 3 + ["LED_ERR"] + [None] * 2
             + ["GP18", "GP26", "GP27", "GP28", "GP29"])

# Only DC needs a pull-up.  After an RP2354A reset its pins pull down, and
# the 5 V switch takes about 1 ms to open; DC high in that time keeps the
# SN75161B a device, so it can never drive ATN, REN or IFC (an IFC that long
# would reset every instrument's interface).  NRFD, NDAC and SRQ may assert
# for that 1 ms: NRFD and NDAC only pause a handshake (the three-wire
# handshake waits for every listener), SRQ is at worst a spurious service
# request.
PULL_UP = ["DC"]                                 # 10 k to 3.3 V: device mode
PULL_DOWN = ["TE_DATA", "TE_CTRL", "BUS_PWR_EN"]  # 10 k to ground: receive, transceivers off

# GPiBridge Lite has no transceivers, so DC, PE, TE_DATA and TE_CTRL go
# nowhere, except that DC carries the board's identity: R21 is 10 k to 3.3 V
# here and 1 k to ground on the Lite, in the same place.  The firmware reads
# DC before it drives anything: high, the transceiver pin layer; low, the
# Lite's.  (A spare pin with a strap would need an escape, and GP26-29 are
# walled in by the decoupling capacitors' copper.)  BUS_PWR_EN lights the
# Lite's green BUS LED directly.
LITE_PULL_DOWN = {"DC": "R21"}                   # 1 k to ground: the Lite's board ID
LITE_UNUSED = ["PE", "TE_DATA", "TE_CTRL"]
