# GPiBridge and GPiBridge Lite rev A: pinout

Written by `tools/make_docs.py` from `gen/pins.py`, the one source of truth. Both boards
use the same pins; on the Lite the bus lines meet the plug through 100 R each, not through
the transceivers, PE and the TE pins go nowhere, DC carries the board ID (R21: 1 k to
ground there, 10 k to 3.3 V on GPiBridge) and BUS_PWR_EN lights the green BUS LED.

## RP2354A GPIO

| GPIO | net | what it is |
|---|---|---|
| 0 | DIO5 | data, via SN75160B; GPIO0-3 carry DIO5-8 and GPIO4-7 DIO1-4, so no data wires cross |
| 1 | DIO6 | data, via SN75160B (the Lite: 100 R) |
| 2 | DIO7 | data, via SN75160B (the Lite: 100 R) |
| 3 | DIO8 | data, via SN75160B (the Lite: 100 R) |
| 4 | DIO1 | data, via SN75160B (the Lite: 100 R) |
| 5 | DIO2 | data, via SN75160B (the Lite: 100 R) |
| 6 | DIO3 | data, via SN75160B (the Lite: 100 R) |
| 7 | DIO4 | data, via SN75160B (the Lite: 100 R) |
| 8 | EOI | end or identify, via SN75161B |
| 9 | DAV | data valid |
| 10 | NRFD | not ready for data |
| 11 | NDAC | not data accepted |
| 12 | IFC | interface clear |
| 13 | REN | remote enable |
| 14 | ATN | attention |
| 15 | SRQ | service request |
| 16 | UART_TX | UART0 TX, to the debug connector |
| 17 | UART_RX | UART0 RX, from the debug connector |
| 18 | GP18 | spare |
| 19 | DC | SN75161B direction: low = controller (drives ATN, REN, IFC); also the board ID: 10 k up on GPiBridge, 1 k down on GPiBridge Lite |
| 20 | PE | SN75160B pull-up enable: high = totem-pole DIO, low = open collector |
| 21 | BUS_PWR_EN | high switches 5 V to the transceivers |
| 22 | LED_USB | yellow LED, high = on |
| 23 | LED_ERR | red LED, high = on |
| 24 | TE_DATA | SN75160B talk enable: high drives DIO onto the bus |
| 25 | TE_CTRL | SN75161B talk enable |
| 26 | GP26 | spare |
| 27 | GP27 | spare |
| 28 | GP28 | spare |
| 29 | GP29 | spare |

## The IEEE-488 plug (J2), by contact

| contact | signal | contact | signal |
|---|---|---|---|
| 1 | DIO1 | 13 | DIO5 |
| 2 | DIO2 | 14 | DIO6 |
| 3 | DIO3 | 15 | DIO7 |
| 4 | DIO4 | 16 | DIO8 |
| 5 | EOI | 17 | REN |
| 6 | DAV | 18 | GND (DAV) |
| 7 | NRFD | 19 | GND (NRFD) |
| 8 | NDAC | 20 | GND (NDAC) |
| 9 | IFC | 21 | GND (IFC) |
| 10 | SRQ | 22 | GND (SRQ) |
| 11 | ATN | 23 | GND (ATN) |
| 12 | shield | 24 | logic GND |

## Debug connectors (JST-SH 3-pin, Raspberry Pi debug pinout, pin 1 nearest the board's top edge)

| connector | pin 1 | pin 2 | pin 3 |
|---|---|---|---|
| J3 SWD | SWCLK | GND | SWDIO |
| J4 UART (115200 baud) | RX (into the RP2354A) | GND | TX |
