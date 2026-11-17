"""Every number the bring-up steps compare a board against, with where it comes from.

Many are from datasheets and the design notes, not from a board: after the first board,
replace an estimate with what it read, and say so beside it.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# the firmware the steps expect to find: the version in the source tree
VERSION = re.search(r'GPIBRIDGE_VERSION "([^"]+)"', (ROOT / 'firmware/src/version.h').read_text()).group(1)

# "++t info" -------------------------------------------------------------------------
# The RP2350's temperature sensor is a diode drop read by the 12-bit ADC, whose reference
# is the 3.3 V rail: V = 0.706 V - 1.721 mV/K * (T - 27 C) (RP2350 datasheet, 12.4.6
# "Temperature Sensor").  So the raw count says what the rail is, to a few percent:
# 876 at 3.30 V and 27 C.  The die runs 5 to 25 K above the room.
TEMP_V27, TEMP_SLOPE = 0.706, -0.001721
DIE_C = (25.0, 60.0)                      # the die temperatures we will believe
RAIL_3V3 = (3.20, 3.40)                   # XC6206P332MR: 3.3 V +-2 %, and a percent for the ADC


def temp_raw_window():
    """The raw counts a good 3.3 V rail gives over DIE_C, with 3 % for the sensor's own spread
    (the datasheet calls it uncalibrated)."""
    lo = (TEMP_V27 + TEMP_SLOPE * (DIE_C[1] - 27)) / RAIL_3V3[1] * 4096 * 0.97
    hi = (TEMP_V27 + TEMP_SLOPE * (DIE_C[0] - 27)) / RAIL_3V3[0] * 4096 * 1.03
    return int(lo), int(hi) + 1


def rail_from_temp_raw(raw, die_c=40.0):
    """The 3.3 V rail a raw count implies, if the die is at die_c."""
    return (TEMP_V27 + TEMP_SLOPE * (die_c - 27)) * 4096 / raw


SYS_KHZ = 150000                          # the SDK's default for an RP2350: 150 MHz from the 12 MHz crystal
FLASH_KB = 2048                           # the RP2354A's flash (boards/gpibridge.h)

# "++t status" -----------------------------------------------------------------------
USB_READY_MS = (20, 2000)                 # reset to configured: BRINGUP.md section 6 expects 150-300 ms on Linux
# The crystal against this PC's clock.  An ABM8-272-T3 is +-30 ppm with its 15 pF; USB
# full speed tolerates 2500.  Over 100 means wrong load capacitors or a wrong crystal.
CRYSTAL_PPM = 100.0

# the capture ------------------------------------------------------------------------
IFC_US = (140.0, 400.0)                   # gpib_ifc() holds IFC for 150 us (IEEE 488.1 wants 100 or more)

# the rails, at the test points (HANDBOOK.md section 1) ---------------------------------
# name: (test point, lowest, highest); a scope's DC accuracy (3 %) is inside the windows
RAILS = {
    '+1V1': ('TP3', 1.05, 1.15),          # the RP2354A's core regulator (DVDD 1.1 V +-5 %)
    '+3V3': ('TP2', 3.20, 3.40),          # XC6206 3.3 V
    'VBUS': ('TP1', 4.40, 5.30),          # USB: 4.40 V is the lowest a low-power port may show (USB 2.0, 7.2.2)
    '+5V_GPIB': ('TP4', 4.75, 5.25),      # the SN75160B/161B's supply range; under 4.75 V the port or cable is weak
}
# Rev A's L1 is JLCPCB's substitute, an unpolarised TDK (DESIGN_NOTES.md risk 8).  The
# question is the ripple on +1V1 at the regulator's switching rate, bus off and on.
# Raspberry Pi's own boards show some 10-30 mV peak to peak there; 60 mV is the alarm.
RIPPLE_1V1_MVPP = 60.0
