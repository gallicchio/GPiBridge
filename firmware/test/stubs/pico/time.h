/* The Pico SDK time calls src/hal_rp2350.c makes, for test_wire.c. */
#pragma once
#include <stdint.h>

uint64_t time_us_64(void);
void busy_wait_us_32(uint32_t us);
