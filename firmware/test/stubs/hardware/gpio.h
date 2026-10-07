/* The Pico SDK GPIO calls src/hal_rp2350.c makes, for test_wire.c, which
 * implements them over its model of the board's wires. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

enum { GPIO_IN = 0, GPIO_OUT = 1 };
enum gpio_override { GPIO_OVERRIDE_NORMAL = 0, GPIO_OVERRIDE_INVERT = 1, GPIO_OVERRIDE_LOW = 2, GPIO_OVERRIDE_HIGH = 3 };
enum gpio_drive_strength { GPIO_DRIVE_STRENGTH_2MA = 0, GPIO_DRIVE_STRENGTH_4MA = 1, GPIO_DRIVE_STRENGTH_8MA = 2,
                           GPIO_DRIVE_STRENGTH_12MA = 3 };

void gpio_init(unsigned pin);
void gpio_set_dir(unsigned pin, bool out);
void gpio_put(unsigned pin, bool value);
bool gpio_get(unsigned pin);
uint32_t gpio_get_all(void);
void gpio_put_masked(uint32_t mask, uint32_t value);
void gpio_set_dir_out_masked(uint32_t mask);
void gpio_set_dir_in_masked(uint32_t mask);
void gpio_pull_up(unsigned pin);
void gpio_pull_down(unsigned pin);
void gpio_set_input_enabled(unsigned pin, bool enabled);
void gpio_disable_pulls(unsigned pin);
void gpio_set_outover(unsigned pin, unsigned value);
void gpio_set_drive_strength(unsigned pin, enum gpio_drive_strength drive);
void gpio_set_dir_masked(uint32_t mask, uint32_t value);
