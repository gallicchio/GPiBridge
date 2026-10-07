#!/usr/bin/env python3
"""Write firmware/src/board_pins.h from gen/pins.py, so the firmware and the
board cannot disagree about which GPIO is which.

    python3 gen/firmware_pins.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pins as PINS
import board_info as BI

OUT = os.path.join(ROOT, "firmware", "src", "board_pins.h")


def main():
    g = PINS.GPIO_OF
    L = ["/* board_pins.h: which RP2354A GPIO does what on GPiBridge and GPiBridge Lite rev %s." % BI.REV,
         " * WRITTEN BY gen/firmware_pins.py FROM gen/pins.py: edit that, not this. */",
         "#pragma once", "",
         "/* The data byte: GPIO 0-7, nibbles swapped (GPIO0-3 carry DIO5-8, GPIO4-7 carry",
         " * DIO1-4) so that the sixteen data wires cross nowhere on the board.  bus_byte()",
         " * and wire_byte() convert. */",
         "#define PIN_DATA_BASE   %d" % min(g["DIO%d" % i] for i in range(1, 9))]
    for i in range(1, 9):
        L.append("#define PIN_DIO%d        %d" % (i, g["DIO%d" % i]))
    L.append("")
    for name in ("EOI", "DAV", "NRFD", "NDAC", "IFC", "REN", "ATN", "SRQ"):
        L.append("#define PIN_%-12s %d   /* %s */" % (name, g[name], PINS.GPIO[g[name]][1]))
    L.append("")
    for name in ("TE_DATA", "TE_CTRL", "DC", "PE", "BUS_PWR_EN", "LED_USB", "LED_ERR", "UART_TX", "UART_RX"):
        L.append("#define PIN_%-12s %d   /* %s */" % (name, g[name], PINS.GPIO[g[name]][1]))
    L += ["", "/* the bus lines' pins, for setting them up together */",
          "#define BUS_PIN_MASK    ((0xffu << PIN_DATA_BASE) | (1u << PIN_EOI) | (1u << PIN_DAV) | (1u << PIN_NRFD) | \\",
          "                         (1u << PIN_NDAC) | (1u << PIN_IFC) | (1u << PIN_REN) | (1u << PIN_ATN) | \\",
          "                         (1u << PIN_SRQ))",
          "",
          "/* the board's 10 k resistors, which hold these pins while the RP2354A is in reset */",
          "#define BOARD_PULL_UP_MASK    (%s)" % " | ".join("(1u << PIN_%s)" % n for n in PINS.PULL_UP),
          "#define BOARD_PULL_DOWN_MASK  (%s)" % " | ".join("(1u << PIN_%s)" % n for n in PINS.PULL_DOWN),
          "",
          "/* the data byte as the bus carries it (DIO1 = bit 0) <-> as GPIO 0-7 carry it */",
          "static inline unsigned wire_byte(unsigned b) { return ((b << 4) | (b >> 4)) & 0xffu; }",
          "static inline unsigned bus_byte(unsigned w) { return ((w << 4) | (w >> 4)) & 0xffu; }", ""]
    # a check that the nibble swap is what the header says
    for i in range(1, 9):
        gp = g["DIO%d" % i]
        bit = i - 1
        assert gp == ((bit + 4) % 8), "DIO%d on GPIO%d: not the swapped nibble order" % (i, gp)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write("\n".join(L))
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
