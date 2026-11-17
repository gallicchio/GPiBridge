/* wire_model.c: the board's wires on a PC.  See wire_model.h. */
#include "wire_model.h"
#include "hardware/gpio.h"
#include <stdio.h>

bool oe[32], ov[32], ie[32];
bool outlow[32];
int pull[32];
bool lite_board;
bool far[L_COUNT];
uint8_t far_data;
bool bus_terminated = true;
uint32_t fault_open;
bool fault_no_5v, fault_5v_stuck;
int fault_short_a = -1, fault_short_b = -1;

const unsigned line_pin[L_COUNT] = {
    [L_EOI] = PIN_EOI, [L_DAV] = PIN_DAV, [L_NRFD] = PIN_NRFD, [L_NDAC] = PIN_NDAC,
    [L_IFC] = PIN_IFC, [L_REN] = PIN_REN, [L_ATN] = PIN_ATN, [L_SRQ] = PIN_SRQ,
};
const unsigned dio_pin[8] = {PIN_DIO1, PIN_DIO2, PIN_DIO3, PIN_DIO4,
                             PIN_DIO5, PIN_DIO6, PIN_DIO7, PIN_DIO8};

bool mcu_level(unsigned pin)
{
    if (oe[pin])
        return ov[pin] && !outlow[pin];
    if (lite_board) {
        if (pin == PIN_DC)
            return false;                /* the Lite's R21: 1 k to ground, the board ID */
    } else {
        if (BOARD_PULL_UP_MASK & (1u << pin))
            return true;
        if (BOARD_PULL_DOWN_MASK & (1u << pin))
            return false;
    }
    return pull[pin] > 0;
}

bool powered(void)
{
    if (!lite_board && fault_no_5v)
        return false;
    if (!lite_board && fault_5v_stuck)
        return true;
    return mcu_level(PIN_BUS_PWR_EN);
}

/* Does the transceiver drive this terminal pin (its channel receives)?
 * SN75160B: TE low receives.  SN75161B function table: DC high receives ATN,
 * REN and IFC and transmits SRQ; TE high transmits DAV and receives NRFD and
 * NDAC; EOI by DC, TE and ATN, whose level is the terminal's while DC is low
 * (ATN transmits) and the bus's while DC is high. */
bool xcvr_drives(unsigned pin)
{
    if (lite_board || !powered())
        return false;
    bool dc = mcu_level(PIN_DC), te = mcu_level(PIN_TE_CTRL);
    for (int i = 0; i < 8; i++)
        if (pin == dio_pin[i])
            return !mcu_level(PIN_TE_DATA);
    if (pin == PIN_ATN || pin == PIN_REN || pin == PIN_IFC)
        return dc;
    if (pin == PIN_SRQ)
        return !dc;
    if (pin == PIN_DAV)
        return !te;
    if (pin == PIN_NRFD || pin == PIN_NDAC)
        return te;
    if (pin == PIN_EOI) {
        if (dc != te)
            return dc;                   /* DC H, TE L: receives; DC L, TE H: transmits */
        bool atn_high = dc ? !far[L_ATN] : mcu_level(PIN_ATN);
        return dc ? !atn_high : atn_high;
    }
    return false;
}

/* A transmitting channel's bus driver that pulls up as well as down: DIO with
 * PE high, and DAV, EOI, ATN, REN and IFC always (SN75161B: NRFD, NDAC and SRQ
 * are open-collector).  Two of these against each other is a bus fight. */
bool xcvr_totem(unsigned pin)
{
    if (lite_board || !powered() || xcvr_drives(pin) || !(BUS_PIN_MASK & (1u << pin)))
        return false;
    for (int i = 0; i < 8; i++)
        if (pin == dio_pin[i])
            return mcu_level(PIN_PE);
    return pin != PIN_NRFD && pin != PIN_NDAC && pin != PIN_SRQ;
}

/* the terminal pin as the transceiver's input sees it: an open joint floats
 * high, which a TTL input reads as "released" */
static bool terminal_low(unsigned pin)
{
    if (fault_open & (1u << pin))
        return false;
    return !mcu_level(pin);
}

bool ours(unsigned pin)
{
    if (lite_board)
        return oe[pin] && !mcu_level(pin) && !(fault_open & (1u << pin));
    return powered() && !xcvr_drives(pin) && terminal_low(pin);
}

static bool far_asserts(unsigned pin)
{
    for (int l = 0; l < L_COUNT; l++)
        if (line_pin[l] == pin)
            return far[l];
    for (int i = 0; i < 8; i++)
        if (dio_pin[i] == pin)
            return far_data >> i & 1;
    return false;
}

bool asserted(unsigned pin)
{
    if (ours(pin) || far_asserts(pin))
        return true;
    /* a solder bridge between two contacts: either line asserted pulls both */
    unsigned other = pin == (unsigned)fault_short_a ? (unsigned)fault_short_b
                     : pin == (unsigned)fault_short_b ? (unsigned)fault_short_a : 32;
    return other < 32 && (ours(other) || far_asserts(other));
}

bool wire(unsigned pin)
{
    if (fault_open & (1u << pin))
        return oe[pin] ? ov[pin] : pull[pin] > 0;   /* nothing but the pad on it */
    if (lite_board && (BUS_PIN_MASK & (1u << pin))) {
        if (asserted(pin))
            return false;
        return bus_terminated || pull[pin] > 0;   /* released: the terminations, or else the pad's pull */
    }
    if (oe[pin])
        return ov[pin];
    if (xcvr_drives(pin))
        return !asserted(pin);
    return mcu_level(pin);
}

/* ---- the rules ------------------------------------------------------------ */
wire_breaches wire_found;
FILE *wire_report;

void wire_check(const char *phase)
{
    FILE *f = wire_report ? wire_report : stdout;
    for (unsigned p = 0; p < 32; p++) {
        bool bus = BUS_PIN_MASK & (1u << p);
        if (lite_board) {
            if (bus && oe[p] && mcu_level(p) && wire_found.drive_high++ < 10)
                fprintf(f, "DRIVE-HIGH: GPIO%u drives its bus line high during %s\n", p, phase);
            if (bus && oe[p] && !outlow[p] && wire_found.override++ < 10)
                fprintf(f, "OVERRIDE: GPIO%u's output on without the pad forced low during %s\n", p, phase);
            if (bus && oe[p] && !powered() && wire_found.off_bus++ < 10)
                fprintf(f, "OFF-BUS: GPIO%u asserted while the firmware is off the bus during %s\n", p, phase);
            continue;
        }
        bool chip_input = p == PIN_TE_DATA || p == PIN_TE_CTRL || p == PIN_PE;
        if (bus && oe[p] && xcvr_drives(p) && wire_found.contention++ < 10)
            fprintf(f, "CONTENTION on GPIO%u during %s\n", p, phase);
        if (!powered() && (bus || chip_input) && oe[p] && ov[p] && wire_found.backpower++ < 10)
            fprintf(f, "BACK-POWER: GPIO%u high into the unpowered transceivers during %s\n", p, phase);
    }
}

int wire_breach_count(void)
{
    return wire_found.contention + wire_found.backpower + wire_found.drive_high + wire_found.override
           + wire_found.off_bus;
}

/* ---- the Pico SDK calls hal_rp2350.c makes (stubs/) ---------------------- */
void gpio_init(unsigned pin)
{
    oe[pin] = ov[pin] = false;
    outlow[pin] = false;                 /* the SDK rewrites the pin's whole control register */
    ie[pin] = true;
    wire_changed();
}
void gpio_set_dir(unsigned pin, bool out)
{
    oe[pin] = out;
    wire_changed();
}
void gpio_put(unsigned pin, bool value)
{
    ov[pin] = value;
    wire_changed();
}
bool gpio_get(unsigned pin)
{
    wire_read();
    return ie[pin] && wire(pin);
}
uint32_t gpio_get_all(void)
{
    wire_read();
    uint32_t v = 0;
    for (unsigned p = 0; p < 32; p++)
        if (ie[p] && wire(p))
            v |= 1u << p;
    return v;
}
void gpio_put_masked(uint32_t mask, uint32_t value)
{
    for (unsigned p = 0; p < 32; p++)
        if (mask >> p & 1)
            ov[p] = value >> p & 1;
    wire_changed();
}
void gpio_set_dir_out_masked(uint32_t mask)
{
    for (unsigned p = 0; p < 32; p++)
        if (mask >> p & 1)
            oe[p] = true;
    wire_changed();
}
void gpio_set_dir_in_masked(uint32_t mask)
{
    for (unsigned p = 0; p < 32; p++)
        if (mask >> p & 1)
            oe[p] = false;
    wire_changed();
}
void gpio_pull_up(unsigned pin)
{
    pull[pin] = +1;
    wire_changed();
}
void gpio_pull_down(unsigned pin)
{
    pull[pin] = -1;
    wire_changed();
}
void gpio_set_input_enabled(unsigned pin, bool enabled)
{
    ie[pin] = enabled;
    wire_changed();
}
void gpio_disable_pulls(unsigned pin)
{
    pull[pin] = 0;
    wire_changed();
}
void gpio_set_outover(unsigned pin, unsigned value)
{
    outlow[pin] = value == GPIO_OVERRIDE_LOW;
    wire_changed();
}
void gpio_set_drive_strength(unsigned pin, enum gpio_drive_strength drive) {}
void gpio_set_dir_masked(uint32_t mask, uint32_t value)
{
    for (unsigned p = 0; p < 32; p++)
        if (mask >> p & 1)
            oe[p] = value >> p & 1;
    wire_changed();
}
