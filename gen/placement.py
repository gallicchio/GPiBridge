"""Where every part goes: millimetres from the board's top-left corner, x right,
y down; rotation in degrees counter-clockwise (KiCad's); side F or B.

The floorplan, seen from the top of the board (the instrument is underneath):

  * The IEEE-488 plug (J2) hangs under the board; its 24 pins come up through
    the lower half.  Contacts 1-12 run along the upper row (contact 1 at the
    right), 13-24 along the lower one.  Its steel flange, 3.5 mm below the
    board, lies inside the board's outline.
  * The two transceivers sit above the plug's pins, side by side, their bus
    pins facing the pins they drive: U3 (control lines) over contacts 5-11,
    U2 (data) over contacts 1-4 and 13-16.  Their terminal pins face the top
    edge, and the lines from the RP2354A reach them under the chips' bodies.
  * The RP2354A at the top left, turned 180 degrees: GPIO0-11 leave its right
    side straight towards the transceivers, the crystal sits above it, and
    Raspberry Pi's regulator and USB layout (turned with it) below it, next
    to the USB-C.
  * The left end: the USB-C (J1) at the bottom, its face out of the end; the
    5 V switch for the transceivers above it.
  * The right end: the two debug connectors (top entry, under openings in
    the housing's lid).
  * Along the bottom edge, under the plug's pins: the three LEDs and the
    BOOT button, in a row that shows through the lid.
  * Two M2 screw holes in the top corners, outside the plug's flange, hold
    the housing together.
"""

BOARD = dict(w=60.0, h=25.5, r=1.5)

# the bottom layer is two supply pours: 3.3 V left of this x, the
# transceivers' 5 V right of it
SUPPLY_SPLIT = 22.0

# the plug: the centre of its pin field
XC, YC = 32.0, 17.5
FLANGE = dict(x0=XC - 27.35, x1=XC + 27.35, y0=YC - 7.65, y1=YC + 7.65)


def contact_x(c):
    """x of IEEE-488 contact c on the board (the plug turned 180 degrees on the back)."""
    k = c if c <= 12 else c - 12
    return XC + (6.5 - k) * 2.16


ROW_UP, ROW_LO = YC - 2.145, YC + 2.145

# the transceivers: U3's NRFD pin (pin 5) over contact 7; U2 1.6 mm to its
# right (room for its VCC capacitors), its bus pins B1-B4 then over contacts 4-1
U_Y = 7.0
U3_X = contact_x(7) + 0.635
SOIC_W = 13.39                     # SOIC-20W courtyard across the pins, turned 90 degrees
U2_X = U3_X + SOIC_W + 1.6

# the RP2354A, turned 180 degrees: GPIO0-11 up its right side, GPIO12-18, the
# crystal, SWD and RUN along its top, USB and the regulator along its bottom
U1_X, U1_Y = 15.0, 10.0


def rpi(dx, dy, rot=0):
    """A part of Raspberry Pi's layout (their U1 at 0 degrees, centre at
    (0, 0)) for our U1 at 180 degrees: (x, y) -> (-x, -y), rotation + 180."""
    return (round(U1_X - dx, 4), round(U1_Y - dy, 4), (rot + 180) % 360, "F")


def at(x, y, rot=0, side="F"):
    return (x, y, rot, side)


# the USB-C: its face 1.2 mm past the board edge, flush with the housing's end
# wall (the HRO's face is 0.99 mm past the board edge when its datum, 2.66 mm
# behind the face, sits on the edge)
J1_X, J1_Y = 2.66 - (1.2 - 0.99), 20.0

PLACE = {
    "J2": at(XC, YC, 180, "B"),
    "U3": at(U3_X, U_Y, 90),
    "U2": at(U2_X, U_Y, 90),
    "U1": at(U1_X, U1_Y, 180),
    # Raspberry Pi's regulator, USB resistors and the decoupling they place
    "L1": rpi(2.0, -7.2, 0),
    "C7": rpi(2.0, -5.55, 0),
    "C6": rpi(2.0, -4.61, 0),
    "C9": rpi(4.2, -5.05, -90),
    "R3": rpi(4.2, -6.9, -90),
    "R1": rpi(-0.1, -7.4, -90),        # their R8, USB_D-
    "R2": rpi(-1.15, -7.4, -90),       # their R7, USB_D+
    "C19": rpi(-2.2, -7.4, 90),        # their C12 (at -2.1, a hair right for our 0402s' courtyards):
                                       # QSPI_IOVDD pin 54, their copper joins pin 53
    "C20": rpi(-3.25, -7.4, 90),       # USB_OTP_VDD pin 53 (ours: one capacitor per supply pin)
    # the other supply pins' capacitors: at the pin where the pin can reach
    # out, else beside the chip on its 3.3 V or 1.1 V ring
    "C16": at(11.4, 4.4, 180),         # IOVDD pin 30
    # (the column stops 0.4 mm above Raspberry Pi's ground via at the chip's corner)
    "C17": at(9.9, 10.3, 180),         # IOVDD pin 38
    "C12": at(9.9, 11.35, 180),        # DVDD pin 39
    "C21": at(9.9, 12.4, 180),         # ADC_AVDD pin 44
    "C18": at(9.9, 13.45, 180),        # IOVDD pin 45
    # a row below the ribbon, their supply pads on one line with pin 1
    "C13": at(19.6, 13.28, 270),       # IOVDD pin 1
    "C14": at(20.65, 13.28, 270),      # IOVDD pin 11 (through the ring)
    "C15": at(21.7, 13.28, 270),       # IOVDD pin 20 (through the ring)
    "C10": at(22.75, 13.28, 270),      # DVDD pin 6 (through the ring and In2)
    "C11": at(18.6, 2.35, 90),          # DVDD pin 23 (on the ring)
    "TP3": at(22.3, 10.8),             # +1V1
    # the crystal block above the RP2354A
    "Y1": at(14.95, 2.2, 90),
    "C4": at(17.3, 3.3, 270),
    "C5": at(11.55, 2.2, 90),
    "R6": at(12.6, 2.2, 270),
    # USB-C, its CC resistors and VBUS capacitor; the 3.3 V regulator
    "J1": at(J1_X, J1_Y, 270),
    "R4": at(9.1, 17.95, 0),
    "R5": at(9.4, 21.05, 0),
    "C1": at(9.1, 15.9, 90),
    "U4": at(12.0, 23.4, 180),
    "C2": at(9.4, 23.55, 270),         # VBUS pad up, on the VBUS line
    "C3": at(14.7, 23.4, 270),         # 3.3 V pad up, toward the regulator's output
    "TP1": at(13.0, 20.6),             # VBUS
    "TP2": at(16.4, 22.45),            # +3V3, on the regulator's output line
    # the left end: the transceivers' 5 V switch
    "H1": at(2.6, 2.6),
    # in a column, as drawn: Q2 pulls Q1's gate down through R17; R16 and C8
    # hold the gate at VBUS (C8 slows the turn-on); VBUS runs under Q1
    "Q2": at(3.763, 7.1, 270),
    "R17": at(3.763, 10.05, 90),
    "Q1": at(4.7, 12.78, 0),
    "R16": at(1.0, 12.78, 90),
    "C8": at(2.1, 12.78, 90),
    "R15": at(6.05, 7.3, 90),          # BUS_PWR_EN down
    # the transceivers' supply capacitors, at their VCC pins (top left of each)
    "C24": at(U3_X - 7.75, 2.35, 270),
    "C25": at(U3_X - 8.8, 2.35, 270),
    "C22": at(U2_X - 7.5, 2.2, 90),
    "C23": at(U2_X - 7.5, 4.35, 90),
    # the pulls that keep the transceivers off the bus while the RP2354A is in reset
    "R21": at(7.69, 5.3, 0),           # DC up, over DC's via
    "R20": at(24.0, 12.6, 90),          # TE_CTRL down
    "R19": at(U2_X - 7.5, 10.83, 90),  # TE_DATA down
    # the right end: both debug connectors (top entry) and their 100 R, each
    # in line with its pin, pad 1 toward the connector
    # (between U2 and J3 a resistor fits only upright: its connector pad on
    # the pin's line; below U2 they lie in line with the pins)
    "J3": at(57.3, 8.8, 270),
    "R7": at(53.95, 7.29, 90),         # SWCLK, J3 pin 1
    "R8": at(53.95, 10.31, 270),       # SWDIO, J3 pin 3
    "J4": at(57.3, 16.4, 270),
    "R11": at(53.68, 15.4, 180),       # RX, J4 pin 1
    "R12": at(53.68, 17.4, 180),       # TX, J4 pin 3
    "H2": at(57.5, 2.5),
    # along the bottom edge: BOOT, ground, the three LEDs
    "SW1": at(21.0, 23.0, 180),
    "R10": at(18.7, 20.1, 90),
    "TP4": at(26.6, 23.2),             # +5V_GPIB
    "TP5": at(29.0, 23.2),             # GND
    "D1": at(32.0, 23.2, 0),
    "R13": at(34.7, 23.2, 0),
    "D2": at(38.0, 23.2, 0),
    "R18": at(40.7, 23.2, 180),
    "D3": at(44.0, 23.2, 0),
    "R14": at(46.7, 23.2, 0),
}


# ---------------------------------------------------------------------------
# GPiBridge Lite: the same board without the transceivers and their 5 V.
# Everything the two share sits where it sits on GPiBridge, so the same
# housing fits both.  The ribbon from the RP2354A runs as on GPiBridge, and
# rises at the top edge into a row of 100 R, one per bus line, where the
# transceivers' terminal pins were; a via above each takes the line to the
# bottom layer and straight down to its contact (gen/routes.py).  Each
# resistor stands over its contact; REN's between contacts 9 and 10 (it
# crosses to the lower row there), and DIO5-8's past contact 1 (they reach the
# lower row round the end of the upper one).
LITE_GONE = ("U2", "U3", "Q1", "Q2", "R15", "R16", "R17", "R19", "R20", "C8", "C22", "C23", "C24", "C25", "TP4")
LITE_RES_Y = 2.0                   # the resistor row's centre; pad 1 (the RP2354A's side) below
LITE_VIA_Y = 0.8                   # the via above each resistor, to the bottom layer
LITE_RES_X = {"ATN": contact_x(11), "SRQ": contact_x(10), "REN": (contact_x(10) + contact_x(9)) / 2,
              "IFC": contact_x(9), "NDAC": contact_x(8), "NRFD": contact_x(7), "DAV": contact_x(6),
              "EOI": contact_x(5), "DIO4": contact_x(4), "DIO3": contact_x(3), "DIO2": contact_x(2),
              "DIO1": contact_x(1)}
LITE_RES_X.update({n: round(contact_x(1) + 1.12 + 1.1 * k, 3) for k, n in enumerate(("DIO8", "DIO7", "DIO6", "DIO5"))})


def lite_place():
    import pins as PINS
    place = {ref: at for ref, at in PLACE.items() if ref not in LITE_GONE}
    for net, x in LITE_RES_X.items():
        place["R%d" % (30 + PINS.GPIO_OF[net])] = at(round(x, 3), LITE_RES_Y, 90)
    # R21, DC's resistor: in GPiBridge's place, turned round, because here its
    # pad 1 is the DC end (a pull-down drawn hanging from the line)
    x, y, rot, side = place["R21"]
    place["R21"] = at(x, y, (rot + 180) % 360, side)
    return place


import board_info as _BI
if _BI.LITE:
    PLACE = lite_place()
