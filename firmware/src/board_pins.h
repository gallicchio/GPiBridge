/* board_pins.h: which RP2354A GPIO does what on GPiBridge and GPiBridge Lite rev A.
 * WRITTEN BY gen/firmware_pins.py FROM gen/pins.py: edit that, not this. */
#pragma once

/* The data byte: GPIO 0-7, nibbles swapped (GPIO0-3 carry DIO5-8, GPIO4-7 carry
 * DIO1-4) so that the sixteen data wires cross nowhere on the board.  bus_byte()
 * and wire_byte() convert. */
#define PIN_DATA_BASE   0
#define PIN_DIO1        4
#define PIN_DIO2        5
#define PIN_DIO3        6
#define PIN_DIO4        7
#define PIN_DIO5        0
#define PIN_DIO6        1
#define PIN_DIO7        2
#define PIN_DIO8        3

#define PIN_EOI          8   /* end or identify, via SN75161B */
#define PIN_DAV          9   /* data valid */
#define PIN_NRFD         10   /* not ready for data */
#define PIN_NDAC         11   /* not data accepted */
#define PIN_IFC          12   /* interface clear */
#define PIN_REN          13   /* remote enable */
#define PIN_ATN          14   /* attention */
#define PIN_SRQ          15   /* service request */

#define PIN_TE_DATA      24   /* SN75160B talk enable: high drives DIO onto the bus */
#define PIN_TE_CTRL      25   /* SN75161B talk enable */
#define PIN_DC           19   /* SN75161B direction: low = controller (drives ATN, REN, IFC); also the board ID: 10 k up on GPiBridge, 1 k down on GPiBridge Lite */
#define PIN_PE           20   /* SN75160B pull-up enable: high = totem-pole DIO, low = open collector */
#define PIN_BUS_PWR_EN   21   /* high switches 5 V to the transceivers */
#define PIN_LED_USB      22   /* yellow LED, high = on */
#define PIN_LED_ERR      23   /* red LED, high = on */
#define PIN_UART_TX      16   /* UART0 TX, to the debug connector */
#define PIN_UART_RX      17   /* UART0 RX, from the debug connector */

/* the bus lines' pins, for setting them up together */
#define BUS_PIN_MASK    ((0xffu << PIN_DATA_BASE) | (1u << PIN_EOI) | (1u << PIN_DAV) | (1u << PIN_NRFD) | \
                         (1u << PIN_NDAC) | (1u << PIN_IFC) | (1u << PIN_REN) | (1u << PIN_ATN) | \
                         (1u << PIN_SRQ))

/* the board's 10 k resistors, which hold these pins while the RP2354A is in reset */
#define BOARD_PULL_UP_MASK    ((1u << PIN_DC))
#define BOARD_PULL_DOWN_MASK  ((1u << PIN_TE_DATA) | (1u << PIN_TE_CTRL) | (1u << PIN_BUS_PWR_EN))

/* the data byte as the bus carries it (DIO1 = bit 0) <-> as GPIO 0-7 carry it */
static inline unsigned wire_byte(unsigned b) { return ((b << 4) | (b >> 4)) & 0xffu; }
static inline unsigned bus_byte(unsigned w) { return ((w << 4) | (w >> 4)) & 0xffu; }
