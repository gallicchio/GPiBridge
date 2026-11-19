/* sim_bus.h: the simulated bus and instrument (sim_bus.c) */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define SIM_ADDR 10

extern int sim_addr;
extern bool sim_present;
extern uint8_t sim_status;
extern char sim_last_message[256];
extern int sim_sdc_count, sim_get_count, sim_gtl_count;
extern bool sim_srq;                    /* it holds SRQ asserted until it is serial-polled */
extern unsigned long sim_bytes_in, sim_sum_in;   /* every data byte it took, and their sum */
extern bool sim_last_eoi;               /* its last message ended with EOI */
extern bool sim_lite;                   /* test_prologix: what hal_lite() answers */
extern bool sim_other_controller;       /* test_prologix: another controller holds REN */
extern int sim_power_offs;              /* times the board switched the transceivers' 5 V off */
extern bool sim_endless;                /* addressed to talk, it never stops and sends no EOI (an HP
                                           5316B, 2026-11-19: REVB.md 2.15) */
extern uint64_t sim_busy_us;            /* after a message's first byte it holds NRFD this long (the
                                           bench's 33120A, going from local to remote, held it over
                                           1 s, 2026-11-18) */

void sim_reset(void);
bool sim_ren(void);

/* built with -DSIM_NO_HAL (test_wire.c): one step of the instrument against
 * what our side asserts on the bus; what it asserts comes back */
#include "../src/gpib_hal.h"
void sim_wire_step(const bool our[L_COUNT], uint8_t our_data, bool bus_powered, bool out[L_COUNT],
                   uint8_t *out_data);
