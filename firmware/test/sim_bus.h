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
extern bool sim_lite;                   /* test_prologix: what hal_lite() answers */

void sim_reset(void);
bool sim_ren(void);

/* built with -DSIM_NO_HAL (test_wire.c): one step of the instrument against
 * what our side asserts on the bus; what it asserts comes back */
#include "../src/gpib_hal.h"
void sim_wire_step(const bool our[L_COUNT], uint8_t our_data, bool bus_powered, bool out[L_COUNT],
                   uint8_t *out_data);
