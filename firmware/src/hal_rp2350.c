/* hal_rp2350.c: gpib_hal.h on the board, both of them.
 *
 * Which board: R21 holds DC (GPIO19) high on GPiBridge (10 k to 3.3 V) and low
 * on GPiBridge Lite (1 k to ground).  hal_init() reads it once, before it
 * drives DC.
 *
 * GPiBridge.  The bus is active low and the transceivers do not invert, so a
 * line is asserted when its GPIO is low.  While the transceivers are
 * unpowered every bus GPIO is an input with its pull-down (no current into an
 * unpowered chip); once they are powered, inputs pull up, which the
 * transceivers read as "released".  Direction changes follow one rule: stop
 * driving the pins that are about to become the transceiver's outputs before
 * switching it, and start driving the pins that become its inputs after.  The
 * RP2354A and a transceiver never drive one wire against each other.
 *
 * GPiBridge Lite.  The pins are the bus (through 100 R), so each line is
 * open-drain: asserted by enabling the pin's output, released by making it an
 * input again.  The pad's output value is forced low in hardware (OUTOVER), so
 * whatever the software does, no pin can drive a line high against another
 * device; the instruments' terminations pull the lines up.  Off the bus (USB
 * not configured) every pin is an input with no pull and no input buffer.
 *
 * test/test_wire.c checks both, after every pin change: against the
 * transceivers' function tables, and against a wired-OR bus for the Lite.
 */
#include "gpib_hal.h"
#include "board_pins.h"
#include "hardware/gpio.h"
#include "pico/time.h"

void usb_poll(void);                     /* main.c: TinyUSB's task and the USB queues */

static const unsigned pin_of[L_COUNT] = {
    [L_EOI] = PIN_EOI, [L_DAV] = PIN_DAV, [L_NRFD] = PIN_NRFD, [L_NDAC] = PIN_NDAC,
    [L_IFC] = PIN_IFC, [L_REN] = PIN_REN, [L_ATN] = PIN_ATN, [L_SRQ] = PIN_SRQ,
};
#define DATA_MASK (0xffu << PIN_DATA_BASE)

static bool powered;
static bool detected, lite;

bool hal_lite(void)
{
    if (!detected) {
        gpio_init(PIN_DC);               /* an input: R21 alone sets its level */
        gpio_disable_pulls(PIN_DC);
        gpio_set_input_enabled(PIN_DC, true);
        busy_wait_us_32(10);
        lite = !gpio_get(PIN_DC);
        detected = true;
    }
    return lite;
}

static void release_input(unsigned pin)
{
    gpio_set_dir(pin, GPIO_IN);
    if (powered) {
        gpio_pull_up(pin);
        gpio_set_input_enabled(pin, true);
    } else if (lite) {
        gpio_disable_pulls(pin);         /* off the bus: nothing at all on the line */
        gpio_set_input_enabled(pin, false);
    } else {
        /* RP2350-E9 (A2 stepping): with its input buffer on, a pin held only by
         * the pad's pull-down can sit at 2.2 V.  Off, the pull-down works, and
         * nothing reads the bus while the transceivers are unpowered. */
        gpio_pull_down(pin);
        gpio_set_input_enabled(pin, false);
    }
}

/* GPiBridge: drive the transceiver's terminal input.  The Lite: assert by
 * enabling the (forced low) output, release by letting go. */
static void drive(unsigned pin, bool asserted)
{
    if (lite) {
        if (asserted)
            gpio_set_dir(pin, GPIO_OUT);
        else
            release_input(pin);
        return;
    }
    gpio_put(pin, !asserted);
    gpio_set_dir(pin, GPIO_OUT);
}

static void control(unsigned pin, bool level)
{
    gpio_init(pin);
    gpio_put(pin, level);
    gpio_set_dir(pin, GPIO_OUT);
}

void hal_init(void)
{
    hal_lite();
    powered = false;
    if (lite) {
        /* no transceivers: PE and the TE pins go nowhere (held low, not left
         * floating), DC is the board ID (left to R21), BUS_PWR_EN is the green LED */
        control(PIN_BUS_PWR_EN, 0);
        gpio_set_drive_strength(PIN_BUS_PWR_EN, GPIO_DRIVE_STRENGTH_12MA);
        control(PIN_PE, 0);
        control(PIN_TE_DATA, 0);
        control(PIN_TE_CTRL, 0);
        for (unsigned pin = 0; pin < 32; pin++)
            if (BUS_PIN_MASK & (1u << pin)) {
                gpio_init(pin);
                gpio_set_outover(pin, GPIO_OVERRIDE_LOW);       /* the pad can only pull low */
                gpio_set_drive_strength(pin, GPIO_DRIVE_STRENGTH_12MA);
                release_input(pin);
            }
        return;
    }
    /* what the board's own pulls hold at reset: device mode, listening, unpowered
     * (PE low until the power is on: nothing high into an unpowered chip that need not be) */
    control(PIN_BUS_PWR_EN, 0);
    control(PIN_DC, 1);
    control(PIN_TE_DATA, 0);
    control(PIN_TE_CTRL, 0);
    control(PIN_PE, 0);
    for (unsigned pin = 0; pin < 32; pin++)
        if (BUS_PIN_MASK & (1u << pin)) {
            gpio_init(pin);
            release_input(pin);
        }
}

void hal_power(bool on)
{
    if (on) {
        gpio_put(PIN_BUS_PWR_EN, 1);     /* GPiBridge: the transceivers' 5 V; the Lite: its BUS LED */
        powered = true;
    } else {
        if (lite)
            gpio_set_dir_in_masked(BUS_PIN_MASK);        /* the Lite lets go of the bus, then says so */
        powered = false;
        if (!lite) {
            gpio_put(PIN_DC, 1);
            gpio_put(PIN_TE_DATA, 0);
            gpio_put(PIN_TE_CTRL, 0);
            gpio_put(PIN_PE, 0);
        }
        gpio_put(PIN_BUS_PWR_EN, 0);
    }
    for (unsigned pin = 0; pin < 32; pin++)
        if (BUS_PIN_MASK & (1u << pin))
            release_input(pin);
}

void hal_controller(bool on)
{
    if (on) {
        release_input(PIN_SRQ);
        if (!lite)
            gpio_put(PIN_DC, 0);
        drive(PIN_ATN, false);
        drive(PIN_REN, false);
        drive(PIN_IFC, false);
    } else {
        release_input(PIN_ATN);
        release_input(PIN_REN);
        release_input(PIN_IFC);
        if (!lite)
            gpio_put(PIN_DC, 1);
    }
}

void hal_talk(bool on)
{
    if (on) {
        release_input(PIN_NRFD);
        release_input(PIN_NDAC);
        if (!lite) {
            gpio_put(PIN_TE_DATA, 1);
            gpio_put(PIN_TE_CTRL, 1);
        }
        drive(PIN_DAV, false);
        drive(PIN_EOI, false);
        if (lite) {
            hal_data_release();
        } else {
            gpio_put_masked(DATA_MASK, DATA_MASK);      /* released */
            gpio_set_dir_out_masked(DATA_MASK);
        }
    } else {
        gpio_set_dir_in_masked(DATA_MASK);
        for (unsigned i = 0; i < 8; i++)
            release_input(PIN_DATA_BASE + i);
        release_input(PIN_DAV);
        release_input(PIN_EOI);
        if (!lite) {
            gpio_put(PIN_TE_DATA, 0);
            gpio_put(PIN_TE_CTRL, 0);
        }
        drive(PIN_NRFD, true);                          /* hold the handshake */
        drive(PIN_NDAC, true);
    }
}

/* PE: the SN75160B's drivers totem-pole or open collector.  The Lite is always
 * open-drain. */
void hal_totem(bool on)
{
    if (!lite)
        gpio_put(PIN_PE, on);
}

void hal_set(gpib_line line, bool asserted)
{
    if (lite)
        drive(pin_of[line], asserted);
    else
        gpio_put(pin_of[line], !asserted);
}

bool hal_get(gpib_line line) { return !gpio_get(pin_of[line]); }

void hal_data_out(uint8_t byte)
{
    unsigned w = wire_byte(byte);
    if (lite) {                                         /* a 1 bit: output enabled, so low */
        gpio_set_dir_masked(DATA_MASK, w << PIN_DATA_BASE);
        return;
    }
    gpio_put_masked(DATA_MASK, (~w & 0xffu) << PIN_DATA_BASE);
}

uint8_t hal_data_in(void) { return (uint8_t)bus_byte((~gpio_get_all() >> PIN_DATA_BASE) & 0xffu); }

void hal_data_release(void)
{
    if (lite)
        gpio_set_dir_in_masked(DATA_MASK);
    else
        gpio_put_masked(DATA_MASK, DATA_MASK);
}

uint64_t hal_us(void) { return time_us_64(); }

void hal_delay_us(uint32_t us) { busy_wait_us_32(us); }

void hal_idle(void) { usb_poll(); }
