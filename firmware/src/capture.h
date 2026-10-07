/* capture.h: the bus, recorded by the board itself: a 21-channel logic
 * analyser that needs no wires.
 *
 * Core 1 watches GPIO0-15, the sixteen bus lines at the transceivers'
 * terminal pins, and the transceivers' direction pins (TE, DC, PE and the 5 V
 * switch), and writes down every change with a timestamp from TIMER1 at
 * 12 MHz (83 ns).  capture_vcd() turns the record into a Value Change Dump,
 * which PulseView or sigrok-cli opens; their "ieee488" decoder then shows the
 * commands, addresses, data and EOI.
 *
 * The levels are the wire's: low = asserted, as on the bus, which is what the
 * decoder expects.  While a transceiver channel transmits, its pin shows what
 * the RP2354A sends; while it receives, what the bus carries.  So the record
 * shows both sides of every handshake this board takes part in.
 *
 *   ++t capture start      arm and start (the buffer holds CAPTURE_MAX changes)
 *   ++t capture stop       stop
 *   ++t capture status     {"capture":"running","changes":123}
 *   ++t capture dump       stop, then the VCD, ending with a line "$comment end $end"
 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t t;             /* timer ticks since the capture started */
    uint32_t pins;          /* GPIO levels, bit n = GPIOn */
} capture_entry;

#define CAPTURE_MAX 24576   /* 192 KB of the RP2354A's 520 KB */
#define CAPTURE_TICKS_PER_US 12

/* the GPIOs recorded */
uint32_t capture_mask(void);

/* Write n entries as a VCD.  ticks_per_us converts the timestamps;
 * timescale_ns is the VCD's time unit (10 keeps 83 ns ticks and stays small). */
void capture_vcd(const capture_entry *e, size_t n, uint32_t ticks_per_us, uint32_t timescale_ns,
                 const char *version, void (*out)(const char *s, size_t len));

/* on the board (capture_rp2350.c) */
void capture_start(void);
void capture_stop(void);
size_t capture_count(void);
const char *capture_state(void);           /* "idle", "running", "full", "stopped" */
const capture_entry *capture_entries(void);
