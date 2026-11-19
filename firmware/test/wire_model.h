/* wire_model.h: the board's wires on a PC.
 *
 * The RP2354A's pads (the Pico SDK GPIO calls src/hal_rp2350.c makes, stubs/),
 * the board's pull resistors (board_pins.h), and the SN75160B and SN75161B by
 * their datasheets' function tables; or, for GPiBridge Lite, the pins on the
 * bus itself, wired-OR through 100 R.  Two programs stand on it:
 *
 *   test_wire.c   the pin layer and the bus engine, checked after every pin
 *                 change, against the simulated instrument;
 *   sim_board.c   the whole firmware above the SDK behind a pseudo-terminal,
 *                 several boards sharing one bus, for the bring-up scripts.
 *
 * Each supplies what lies beyond the plug: wire_changed() is called after
 * every pin change and wire_read() before every read; they set far[] and
 * far_data, what everything else on the bus asserts.
 */
#pragma once
#include "../src/board_pins.h"
#include "../src/gpib_hal.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

/* ---- the RP2354A's side of each wire ------------------------------------- */
extern bool oe[32], ov[32], ie[32];      /* output enabled, output value, input enabled */
extern bool outlow[32];                  /* the pad's output forced low (OUTOVER) */
extern int pull[32];                     /* the pad's own pull: +1 up, -1 down, 0 none */
extern bool lite_board;                  /* GPiBridge Lite: no transceivers, R21 pulls DC down */

extern const unsigned line_pin[L_COUNT];
extern const unsigned dio_pin[8];

/* ---- the far side: what the rest of the bus asserts ---------------------- */
extern bool far[L_COUNT];
extern uint8_t far_data;
extern bool bus_terminated;              /* something out there has terminations: a released line is high.  It only
                                            matters to the Lite, whose own pins have none */

/* ---- faults, to show that a check can fail ------------------------------- */
extern uint32_t fault_open;              /* these GPIOs' joints to the board are open */
extern bool fault_no_5v;                 /* the 5 V switch never closes */
extern bool fault_5v_stuck;              /* the 5 V switch never opens */
extern int fault_short_a, fault_short_b; /* two bus lines bridged at the plug (GPIO numbers; -1: none) */
extern bool fault_no_r21;                /* R21 missing or open: DC follows the pad's own pull */

bool mcu_level(unsigned pin);            /* the wire as the RP2354A and the resistors set it, the transceiver aside */
bool powered(void);                      /* the transceivers have 5 V (the Lite: BUS_PWR_EN, its LED) */
bool xcvr_drives(unsigned pin);          /* the transceiver drives this terminal pin (its channel receives) */
bool xcvr_totem(unsigned pin);           /* a transmitting channel that also drives its line high */
bool ours(unsigned pin);                 /* this board asserts the pin's bus line */
bool asserted(unsigned pin);             /* the bus line is asserted, by anyone */
bool wire(unsigned pin);                 /* the level the RP2354A reads */

/* The rules, checked after a pin change; each count is of breaches so far, and
 * the first few are printed with `phase`.  GPiBridge: the RP2354A and a
 * transceiver never drive one wire (contention), and nothing is driven high
 * into the unpowered transceivers (backpower).  The Lite: no bus pin drives
 * its line high, none enables its output without the pad forced low
 * (override), nothing is asserted off the bus. */
typedef struct {
    int contention, backpower, drive_high, override, off_bus;
} wire_breaches;
extern wire_breaches wire_found;
extern FILE *wire_report;                /* where the first few are printed (NULL: standard output) */
void wire_check(const char *phase);
int wire_breach_count(void);

void wire_changed(void);                 /* the program's: after every pin change */
void wire_read(void);                    /* the program's: before every read */
