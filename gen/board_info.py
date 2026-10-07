"""The board's identity, in one place: the schematic's title block, the
silkscreen, the release files and the firmware's version string read it.

Two boards come out of these generators.  GPiBridge drives the bus through
TI's transceivers; GPiBridge Lite has none, and its RP2354A's pins meet the
bus through 100 R each.  GPIBRIDGE_VARIANT=lite in the environment selects the
Lite; ./build.py makes both.  Every path a step reads or writes for one board
comes from here, so the two never overwrite each other.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANT = os.environ.get("GPIBRIDGE_VARIANT", "full")
if VARIANT not in ("full", "lite"):
    raise SystemExit("GPIBRIDGE_VARIANT must be 'full' or 'lite', not %r" % VARIANT)
LITE = VARIANT == "lite"

FAMILY = "GPiBridge"
NAME = "GPiBridgeLite" if LITE else "GPiBridge"       # its files' name
TITLE = "GPiBridge Lite" if LITE else "GPiBridge"     # what it calls itself
TAGLINE = "USB-C to IEEE-488 (GPIB)"
REV = "A"
DATE = "2026-10-06"          # the design date; a release made before it is ordered is a DRAFT
AUTHORS = "Jason Gallicchio and Claude"
URL = "github.com/gallicchio/GPiBridge"   # where it will live, as its own repository (Jason, 2026-10-06)
LICENCE = "Hardware CERN-OHL-P-2.0, software MIT"

# where this board's files go (the library in hardware/lib is shared)
HW = os.path.join(ROOT, "hardware")
PCB = os.path.join(HW, NAME + ".kicad_pcb")
SCH = os.path.join(HW, NAME + ".kicad_sch")
CHECKS = os.path.join(HW, "checks", "lite") if LITE else os.path.join(HW, "checks")
NETLIST = os.path.join(CHECKS, "netlist.net")
RELEASE = os.path.join(ROOT, "mfg", "release-lite" if LITE else "release")
IMAGE_PREFIX = "lite_" if LITE else ""                # docs/images/<prefix>board_top.png
SCRATCH = os.path.join(ROOT, "build", NAME)           # this board's intermediates
