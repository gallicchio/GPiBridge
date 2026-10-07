/* test_wire.c: the board's own pin layer (src/hal_rp2350.c) and bus engine
 * (src/gpib.c), against a model of the wires: the SN75160B and SN75161B by
 * their datasheets' function tables, the board's pull resistors
 * (board_pins.h), and the simulated instrument (sim_bus.c) on the far side
 * of the plug.  `make` here runs it twice: `./test_wire` for GPiBridge,
 * `./test_wire lite` for GPiBridge Lite, whose pins are the bus (wired-OR,
 * through 100 R) and whose R21 pulls DC down instead of up.
 *
 * After every change of any pin it checks, on GPiBridge:
 *   CONTENTION  the RP2354A and a transceiver never drive the same wire (a
 *               channel's terminal pin is the transceiver's output while
 *               that channel receives);
 *   BACK-POWER  while the transceivers are unpowered, the RP2354A drives
 *               none of their pins high (DC excepted: the board's own 10 k
 *               pull-up holds it high then too);
 * on the Lite:
 *   DRIVE-HIGH  no bus pin ever drives its line high (a released line is an
 *               input; the instruments' terminations pull it up);
 *   OVERRIDE    no bus pin enables its output without the pad's output forced
 *               low first (OUTOVER: the hardware's guarantee of the above);
 *   OFF-BUS     nothing is asserted while the firmware is off the bus;
 * and, on both, end to end through the active-low wires and the
 * nibble-swapped data pins, that every byte value reaches the instrument and
 * comes back.
 */
#include "../src/board_pins.h"
#include "../src/capture.h"
#include "../src/gpib.h"
#include "sim_bus.h"
#include "hardware/gpio.h"
#include "pico/time.h"
#include <stdio.h>
#include <string.h>

/* ---- the RP2354A's side of each wire ------------------------------------- */
static bool oe[32], ov[32], ie[32];     /* output enabled, output value, input enabled */
static bool outlow[32];                  /* the pad's output forced low (OUTOVER) */
static int pull[32];                     /* the pad's own pull: +1 up, -1 down, 0 none */
static uint64_t now;
static bool lite_board;                  /* ./test_wire lite */

static const unsigned line_pin[L_COUNT] = {
    [L_EOI] = PIN_EOI, [L_DAV] = PIN_DAV, [L_NRFD] = PIN_NRFD, [L_NDAC] = PIN_NDAC,
    [L_IFC] = PIN_IFC, [L_REN] = PIN_REN, [L_ATN] = PIN_ATN, [L_SRQ] = PIN_SRQ,
};
static const unsigned dio_pin[8] = {PIN_DIO1, PIN_DIO2, PIN_DIO3, PIN_DIO4,
                                    PIN_DIO5, PIN_DIO6, PIN_DIO7, PIN_DIO8};

/* the wire's level as the RP2354A and the resistors set it, the transceiver aside */
static bool mcu_level(unsigned pin)
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

static bool powered(void) { return mcu_level(PIN_BUS_PWR_EN); }

/* ---- the far side: the instrument's outputs on the bus ------------------- */
static bool dev[L_COUNT];
static uint8_t dev_data;

/* Does the transceiver drive this terminal pin (its channel receives)?
 * SN75160B: TE low receives.  SN75161B function table: DC high receives ATN,
 * REN and IFC and transmits SRQ; TE high transmits DAV and receives NRFD and
 * NDAC; EOI by DC, TE and ATN, whose level is the terminal's while DC is low
 * (ATN transmits) and the bus's while DC is high. */
static bool xcvr_drives(unsigned pin)
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
        bool atn_high = dc ? !dev[L_ATN] : mcu_level(PIN_ATN);
        return dc ? !atn_high : atn_high;
    }
    return false;
}

/* what our side asserts on the bus: a transmitting channel whose terminal pin
 * is low; on the Lite, a pin whose output is on (and low) */
static bool ours(unsigned pin)
{
    if (lite_board)
        return oe[pin] && !mcu_level(pin);
    return powered() && !xcvr_drives(pin) && !mcu_level(pin);
}

static bool asserted(unsigned pin)
{
    if (ours(pin))
        return true;
    for (int l = 0; l < L_COUNT; l++)
        if (line_pin[l] == pin)
            return dev[l];
    for (int i = 0; i < 8; i++)
        if (dio_pin[i] == pin)
            return dev_data >> i & 1;
    return false;
}

/* the level the RP2354A reads */
static bool wire(unsigned pin)
{
    if (lite_board && (BUS_PIN_MASK & (1u << pin)))
        return !asserted(pin);           /* the pin is the bus */
    if (oe[pin])
        return ov[pin];
    if (xcvr_drives(pin))
        return !asserted(pin);
    return mcu_level(pin);
}

/* ---- a record of the run, for sigrok's IEEE-488 decoder (sigrok_check.sh) ----
 * Two views of the same moments: the bus itself, as a logic analyser on the
 * plug would see it, and the RP2354A's pins, as the board's own capture
 * (capture.h) sees them.  Each change gets a distinct time: 16 ticks per
 * simulated microsecond, the later ones in a microsecond a tick apart. */
#define REC_MAX 200000
#define REC_TICKS_PER_US 16
static capture_entry rec_bus[REC_MAX], rec_pin[REC_MAX];
static size_t n_bus, n_pin;
static bool recording;
static uint64_t rec_now = ~0ull;
static uint32_t rec_sub;

static void record(void)
{
    if (!recording)
        return;
    uint32_t bus = 0, pin = 0;
    for (unsigned p = 0; p < 32; p++) {
        uint32_t bit = 1u << p;
        if (BUS_PIN_MASK & bit) {
            if (!asserted(p))
                bus |= bit;              /* the wire: high = released */
            if (wire(p))
                pin |= bit;              /* what the RP2354A's pin carries */
        } else if ((capture_mask() & bit) && mcu_level(p)) {
            bus |= bit;
            pin |= bit;
        }
    }
    if (now != rec_now) {
        rec_now = now;
        rec_sub = 0;
    } else if (rec_sub < REC_TICKS_PER_US - 1) {
        rec_sub++;
    }
    uint32_t t = (uint32_t)(now * REC_TICKS_PER_US + rec_sub);
    if ((!n_bus || bus != rec_bus[n_bus - 1].pins) && n_bus < REC_MAX)
        rec_bus[n_bus++] = (capture_entry){t, bus};
    if ((!n_pin || pin != rec_pin[n_pin - 1].pins) && n_pin < REC_MAX)
        rec_pin[n_pin++] = (capture_entry){t, pin};
}

static FILE *vcd_file;
static void vcd_out(const char *s, size_t n) { fwrite(s, 1, n, vcd_file); }

static void write_vcd(const char *path, const capture_entry *e, size_t n)
{
    vcd_file = fopen(path, "w");
    if (!vcd_file)
        return;
    capture_vcd(e, n, REC_TICKS_PER_US, 10, "test_wire", vcd_out);
    fclose(vcd_file);
}

static void record_start(void)
{
    n_bus = n_pin = 0;
    recording = true;
}

static void record_save(const char *name)
{
    char path[80];
    const char *board = lite_board ? "lite_" : "";
    recording = false;
    snprintf(path, sizeof path, "out/%s%s_bus.vcd", board, name);
    write_vcd(path, rec_bus, n_bus);
    snprintf(path, sizeof path, "out/%s%s_pins.vcd", board, name);
    write_vcd(path, rec_pin, n_pin);
}

/* ---- after every pin change: the instrument takes a step, then the checks */
static int changes, contention, backpower, drive_high, override, off_bus;
static const char *phase = "";

static void settle(void)
{
    bool our[L_COUNT];
    uint8_t our_data = 0;
    for (int l = 0; l < L_COUNT; l++)
        our[l] = ours(line_pin[l]);
    for (int i = 0; i < 8; i++)
        our_data |= (uint8_t)(ours(dio_pin[i]) << i);
    sim_wire_step(our, our_data, powered(), dev, &dev_data);
    changes++;
    for (unsigned p = 0; p < 32; p++) {
        bool bus = BUS_PIN_MASK & (1u << p);
        if (lite_board) {
            if (bus && oe[p] && mcu_level(p) && drive_high++ < 10)
                printf("DRIVE-HIGH: GPIO%u drives its bus line high during %s\n", p, phase);
            if (bus && oe[p] && !outlow[p] && override++ < 10)
                printf("OVERRIDE: GPIO%u's output on without the pad forced low during %s\n", p, phase);
            if (bus && oe[p] && !powered() && off_bus++ < 10)
                printf("OFF-BUS: GPIO%u asserted while the firmware is off the bus during %s\n", p, phase);
            continue;
        }
        bool chip_input = p == PIN_TE_DATA || p == PIN_TE_CTRL || p == PIN_PE;
        if (bus && oe[p] && xcvr_drives(p) && contention++ < 10)
            printf("CONTENTION on GPIO%u during %s\n", p, phase);
        if (!powered() && (bus || chip_input) && oe[p] && ov[p] && backpower++ < 10)
            printf("BACK-POWER: GPIO%u high into the unpowered transceivers during %s\n", p, phase);
    }
    record();
}

/* ---- the Pico SDK calls hal_rp2350.c makes (stubs/) ---------------------- */
void gpio_init(unsigned pin)
{
    oe[pin] = ov[pin] = false;
    outlow[pin] = false;                 /* the SDK rewrites the pin's whole control register */
    ie[pin] = true;
    settle();
}
void gpio_set_dir(unsigned pin, bool out)
{
    oe[pin] = out;
    settle();
}
void gpio_put(unsigned pin, bool value)
{
    ov[pin] = value;
    settle();
}
bool gpio_get(unsigned pin)
{
    now++;
    settle();
    return ie[pin] && wire(pin);
}
uint32_t gpio_get_all(void)
{
    now++;
    settle();
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
    settle();
}
void gpio_set_dir_out_masked(uint32_t mask)
{
    for (unsigned p = 0; p < 32; p++)
        if (mask >> p & 1)
            oe[p] = true;
    settle();
}
void gpio_set_dir_in_masked(uint32_t mask)
{
    for (unsigned p = 0; p < 32; p++)
        if (mask >> p & 1)
            oe[p] = false;
    settle();
}
void gpio_pull_up(unsigned pin)
{
    pull[pin] = +1;
    settle();
}
void gpio_pull_down(unsigned pin)
{
    pull[pin] = -1;
    settle();
}
void gpio_set_input_enabled(unsigned pin, bool enabled)
{
    ie[pin] = enabled;
    settle();
}
void gpio_disable_pulls(unsigned pin)
{
    pull[pin] = 0;
    settle();
}
void gpio_set_outover(unsigned pin, unsigned value)
{
    outlow[pin] = value == GPIO_OVERRIDE_LOW;
    settle();
}
void gpio_set_drive_strength(unsigned pin, enum gpio_drive_strength drive) {}
void gpio_set_dir_masked(uint32_t mask, uint32_t value)
{
    for (unsigned p = 0; p < 32; p++)
        if (mask >> p & 1)
            oe[p] = value >> p & 1;
    settle();
}
uint64_t time_us_64(void) { return ++now; }
void busy_wait_us_32(uint32_t us)
{
    now += us;
    settle();
}
void usb_poll(void) {}

/* ---- the tests ------------------------------------------------------------ */
static int failures;

#define CHECK(cond, ...)                                     \
    do {                                                     \
        if (!(cond)) {                                       \
            failures++;                                      \
            printf("FAIL %s:%d (%s): ", __FILE__, __LINE__, phase); \
            printf(__VA_ARGS__);                             \
            printf("\n");                                    \
        }                                                    \
    } while (0)

static void send(const uint8_t *msg, size_t n)
{
    gpib_status s = gpib_send_to(SIM_ADDR, -1, msg, n, true);
    CHECK(s == GPIB_OK, "send: %s", gpib_status_name(s));
    gpib_idle();
}

static size_t query(const char *q, uint8_t *buf, size_t max)
{
    send((const uint8_t *)q, strlen(q));
    size_t got;
    bool eoi;
    gpib_status s = gpib_receive_from(SIM_ADDR, -1, buf, max, &got, true, -1, &eoi);
    CHECK(s == GPIB_OK && eoi, "answer to %s: %s, EOI %d", q, gpib_status_name(s), eoi);
    return got;
}

int main(int argc, char **argv)
{
    static const char idn[] = "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\n";
    uint8_t buf[300];
    size_t n;

    lite_board = argc > 1 && !strcmp(argv[1], "lite");
    printf("%s: ", lite_board ? "GPiBridge Lite" : "GPiBridge");

    sim_reset();
    for (unsigned p = 0; p < 32; p++)
        pull[p] = -1;                    /* the pads after reset: pull-downs */

    phase = "boot";
    gpib_stop();                         /* what main() does first */
    CHECK(!powered(), "transceivers powered at boot");

    phase = "gpib_start";
    gpib_start();
    CHECK(hal_lite() == lite_board, "the board read as %s", hal_lite() ? "the Lite" : "GPiBridge");
    CHECK(powered() && gpib_powered(), "transceivers off after gpib_start");
    CHECK(!mcu_level(PIN_DC), "DC high: not the controller");
    CHECK(sim_ren(), "REN not asserted");
    if (lite_board)
        for (unsigned p = 0; p < 32; p++)
            if (BUS_PIN_MASK & (1u << p))
                CHECK(outlow[p] && pull[p] > 0 && ie[p], "GPIO%u: forced low %d, pull %d, input %d", p, outlow[p],
                      pull[p], ie[p]);

    phase = "*IDN?";
    record_start();
    n = query("*IDN?\n", buf, sizeof buf);
    record_save("idn");
    CHECK(n == strlen(idn) && !memcmp(buf, idn, n), "answered \"%.*s\"", (int)n, (const char *)buf);

    /* every byte value but NUL (the instrument keeps C strings) and CR, LF (which end its messages) */
    for (int half = 0; half < 2; half++) {
        uint8_t msg[130];
        size_t k = 0;
        for (int b = half ? 0x80 : 0x01; b < (half ? 0x100 : 0x80); b++)
            if (b != '\n' && b != '\r')
                msg[k++] = (uint8_t)b;
        msg[k++] = '\n';
        phase = half ? "bytes 0x80-0xff" : "bytes 0x01-0x7f";
        record_start();
        send(msg, k);
        n = query("ECHO?\n", buf, sizeof buf);
        record_save(half ? "bytes_high" : "bytes_low");
        CHECK(n == k && !memcmp(buf, msg, k), "%zu bytes sent, %zu came back", k, n);
    }

    phase = "serial poll";
    uint8_t status = 0;
    gpib_status s = gpib_serial_poll(SIM_ADDR, -1, &status);
    CHECK(s == GPIB_OK && status == 0x40, "%s, status 0x%02x", gpib_status_name(s), status);

    phase = "nobody there";
    sim_present = false;
    s = gpib_send_to(SIM_ADDR, -1, (const uint8_t *)"X\n", 2, true);
    CHECK(s == GPIB_NO_LISTENER, "%s", gpib_status_name(s));
    gpib_idle();
    sim_present = true;

    phase = "gpib_stop";
    gpib_stop();
    CHECK(!powered() && !gpib_powered(), "transceivers on after gpib_stop");
    for (unsigned p = 0; p < 32; p++)
        if (BUS_PIN_MASK & (1u << p))
            CHECK(!oe[p] && (lite_board ? pull[p] == 0 : pull[p] < 0) && !ie[p], "GPIO%u: output %d, pull %d, input %d",
                  p, oe[p], pull[p], ie[p]);

    phase = "gpib_start again";
    gpib_start();
    n = query("*IDN?\n", buf, sizeof buf);
    CHECK(n == strlen(idn) && !memcmp(buf, idn, n), "answered %zu bytes", n);
    gpib_stop();

    if (lite_board)
        printf("%d pin changes checked: %d driven high, %d without the override, %d off the bus; %d failures\n",
               changes, drive_high, override, off_bus, failures);
    else
        printf("%d pin changes checked: %d contention, %d back-power; %d failures\n", changes, contention, backpower,
               failures);
    return failures || contention || backpower || drive_high || override || off_bus;
}
