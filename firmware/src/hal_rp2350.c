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
static bool detected, lite, known;

/* Which board, read once, before any pin is driven: DC with the pad's pull-down, then
 * with its pull-up (about 50 k each).  R21 outvotes both: 10 k to 3.3 V (GPiBridge)
 * reads high both times, 1 k to ground (the Lite) low both times.  A pin that follows
 * the pull has no R21 (missing or open): the board is unknown.  Its pins then get the
 * Lite's layer, which drives nothing high, and gpib.c keeps it off the bus (REVB.md
 * 1.8; until 0.4.5 a floating DC was read once, and high meant GPiBridge).  The
 * pull-down goes first, its input buffer off while it settles: with the buffer on, a
 * pin held only by the pull-down can sit at 2.2 V (RP2350-E9). */
static void read_board(void)
{
    gpio_init(PIN_DC);
    gpio_set_input_enabled(PIN_DC, false);
    gpio_pull_down(PIN_DC);
    busy_wait_us_32(200);
    gpio_set_input_enabled(PIN_DC, true);
    busy_wait_us_32(10);
    bool with_pull_down = gpio_get(PIN_DC);
    gpio_pull_up(PIN_DC);
    busy_wait_us_32(200);
    bool with_pull_up = gpio_get(PIN_DC);
    gpio_disable_pulls(PIN_DC);          /* R21 alone from here on */
    known = with_pull_down == with_pull_up;
    lite = !known || !with_pull_up;
}

bool hal_lite(void)
{
    if (!detected) {
        read_board();
        detected = true;
    }
    return lite;
}

bool hal_board_known(void)
{
    hal_lite();
    return known;
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

/* How long the transceivers' 5 V takes to fall once Q1 opens: 2.6 uF into the
 * two chips and the BUS LED.  Measured on A1: below 1 V in 0.36 ms, 0.2 V in 2.9 ms. */
#define RAIL_FALL_US 3000

static void release_all(void)
{
    for (unsigned pin = 0; pin < 32; pin++)
        if (BUS_PIN_MASK & (1u << pin))
            release_input(pin);
}

/* GPiBridge: while the transceivers have power, a terminal input that is not
 * driven must rest on a pull-up, which reads as "released": on a pull-down a
 * listening device's SN75161B asserts NRFD, NDAC and SRQ.  So the pull-ups go
 * on before the 5 V does, and stay until it has gone.  A pull-up into the
 * unpowered chips is some 50 uA a pin, for the moment the 5 V takes to rise or
 * fall.  With this, a board that powers up only to find another controller
 * on the bus (gpib.c) leaves again without a mark on any line. */
/* And never on again within 0.5 s of going off.  A margin, not a need: measured on A1
 * (2026-11-18, REVB.md 2.14) the 5 V is below 0.2 V 2.9 ms after Q1 opens, and the bus
 * lines stay clean through the fall and the next rise.  Added while a 33120A that stops
 * on its own was blamed on fast restarts. */
#define MIN_OFF_US 500000
static uint64_t off_at;                  /* when it was last switched off; 0: not since reset */

void hal_power(bool on)
{
    if (on) {
        while (off_at && time_us_64() - off_at < MIN_OFF_US)
            usb_poll();                  /* USB and the watchdog still served */
        powered = true;
        release_all();                   /* pull-ups, input buffers on */
        gpio_put(PIN_BUS_PWR_EN, 1);     /* GPiBridge: the transceivers' 5 V; the Lite: its BUS LED */
        return;
    }
    if (lite) {
        gpio_set_dir_in_masked(BUS_PIN_MASK);            /* the Lite lets go of the bus, then says so */
    } else if (powered) {
        release_all();                   /* whatever we still drove, let go while they can still hear it */
        gpio_put(PIN_DC, 1);
        gpio_put(PIN_TE_DATA, 0);
        gpio_put(PIN_TE_CTRL, 0);
        gpio_put(PIN_PE, 0);
        gpio_put(PIN_BUS_PWR_EN, 0);
        busy_wait_us_32(RAIL_FALL_US);
    }
    if (powered && !lite)
        off_at = time_us_64();
    powered = false;
    gpio_put(PIN_BUS_PWR_EN, 0);
    release_all();                       /* GPiBridge: pull-downs, input buffers off (E9); the Lite: nothing at all */
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

/* ---- bring-up: the board as sixteen wires (gpib_hal.h) ------------------------ */
static raw_role raw = RAW_DEV_LISTEN;
static const unsigned dio_pin[8] = {PIN_DIO1, PIN_DIO2, PIN_DIO3, PIN_DIO4, PIN_DIO5, PIN_DIO6, PIN_DIO7, PIN_DIO8};

static unsigned raw_pin(unsigned bit) { return bit < 8 ? dio_pin[bit] : pin_of[bit - 8]; }

#define RAW_HANDSHAKE (RAW_BIT(L_NRFD) | RAW_BIT(L_NDAC))
#define RAW_MANAGE (RAW_BIT(L_ATN) | RAW_BIT(L_REN) | RAW_BIT(L_IFC))

uint16_t hal_raw_drives(void)
{
    static const uint16_t drives[RAW_ROLES] = {
        [RAW_DEV_LISTEN] = RAW_HANDSHAKE | RAW_BIT(L_SRQ),
        [RAW_DEV_TALK] = RAW_DATA | RAW_BIT(L_DAV) | RAW_BIT(L_SRQ),
        [RAW_CTRL_LISTEN] = RAW_HANDSHAKE | RAW_MANAGE,
        [RAW_CTRL_TALK] = RAW_DATA | RAW_BIT(L_DAV) | RAW_BIT(L_EOI) | RAW_MANAGE,
    };
    return lite ? 0xffffu : drives[raw];
}

uint16_t hal_raw_reads(void)
{
    static const uint16_t reads[RAW_ROLES] = {
        [RAW_DEV_LISTEN] = RAW_DATA | RAW_BIT(L_DAV) | RAW_BIT(L_EOI) | RAW_MANAGE,
        [RAW_DEV_TALK] = RAW_MANAGE | RAW_HANDSHAKE,
        [RAW_CTRL_LISTEN] = RAW_DATA | RAW_BIT(L_DAV) | RAW_BIT(L_SRQ),
        [RAW_CTRL_TALK] = RAW_HANDSHAKE | RAW_BIT(L_SRQ),
    };
    return lite ? 0xffffu : reads[raw];
}

static void raw_release_all(void)
{
    for (unsigned bit = 0; bit < 16; bit++)
        release_input(raw_pin(bit));
}

/* The same rule as hal_talk(): no pin of ours drives while the transceivers
 * turn.  Released pins rest on their pull-ups, which a terminal input reads
 * as "released", so the bus sees nothing asserted on the way. */
void hal_raw_role(raw_role role)
{
    if (!powered)
        return;
    raw_release_all();
    raw = role;
    if (lite)
        return;
    bool talk = role == RAW_DEV_TALK || role == RAW_CTRL_TALK;
    bool ctrl = role == RAW_CTRL_LISTEN || role == RAW_CTRL_TALK;
    gpio_put(PIN_TE_DATA, talk);
    gpio_put(PIN_TE_CTRL, talk);
    gpio_put(PIN_DC, !ctrl);
    uint16_t d = hal_raw_drives();
    for (unsigned bit = 0; bit < 16; bit++)
        if (d >> bit & 1)
            drive(raw_pin(bit), false);
}

void hal_raw_end(void)
{
    raw_release_all();
    raw = RAW_DEV_LISTEN;
    if (!lite) {
        gpio_put(PIN_TE_DATA, 0);
        gpio_put(PIN_TE_CTRL, 0);
        gpio_put(PIN_DC, 1);
    }
}

void hal_raw_set(uint16_t asserted)
{
    if (!powered)
        return;
    uint16_t d = hal_raw_drives();
    for (unsigned bit = 0; bit < 16; bit++)
        if (d >> bit & 1)
            drive(raw_pin(bit), asserted >> bit & 1);
}

/* RP2350-E9 (A2 stepping): a pin with its input buffer on, held only by the
 * pad's pull-down, drifts up to about 2.2 V and reads high.  So a pull-down
 * reading keeps the buffers off while the pull settles the pin, and switches
 * each one on only for its own read, as the datasheet's workaround has it. */
uint16_t hal_raw_get(int pull)
{
    uint16_t ours = lite ? 0 : hal_raw_drives(), v = 0;
    if (!powered) {
        ours = 0;
        if (!lite && pull >= 0)
            pull = -1;                   /* never a pull-up into the unpowered transceivers */
    }
    if (!pull) {                         /* as the pins stand */
        uint32_t pins = gpio_get_all();
        for (unsigned bit = 0; bit < 16; bit++)
            if (!(pins >> raw_pin(bit) & 1))
                v |= (uint16_t)(1u << bit);
        return v;
    }
    for (unsigned bit = 0; bit < 16; bit++) {
        unsigned pin = raw_pin(bit);
        if (ours >> bit & 1)
            continue;
        if (pull > 0) {
            gpio_pull_up(pin);
            gpio_set_input_enabled(pin, true);
        } else {
            gpio_set_input_enabled(pin, false);
            gpio_pull_down(pin);
        }
    }
    busy_wait_us_32(50);                 /* a pad's 50-80 k against a pin, or against a cable on the Lite */
    for (unsigned bit = 0; bit < 16; bit++) {
        unsigned pin = raw_pin(bit);
        bool low;
        if (pull < 0 && !(ours >> bit & 1)) {
            gpio_set_input_enabled(pin, true);
            low = !gpio_get(pin);
            gpio_set_input_enabled(pin, false);
        } else {
            low = !gpio_get(pin);
        }
        if (low)
            v |= (uint16_t)(1u << bit);
    }
    for (unsigned bit = 0; bit < 16; bit++)     /* back to what release_input() leaves */
        if (!(ours >> bit & 1))
            release_input(raw_pin(bit));
    return v;
}

uint64_t hal_us(void) { return time_us_64(); }

void hal_delay_us(uint32_t us) { busy_wait_us_32(us); }

void hal_idle(void) { usb_poll(); }
