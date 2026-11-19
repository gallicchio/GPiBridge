/* test_wire.c: the board's own pin layer (src/hal_rp2350.c) and bus engine
 * (src/gpib.c), against a model of the wires (wire_model.c: the SN75160B and
 * SN75161B by their datasheets' function tables, the board's pull resistors)
 * and the simulated instrument (sim_bus.c) on the far side of the plug.  `make` here runs it twice: `./test_wire` for GPiBridge,
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
 *
 * Then, with another controller holding REN, ATN or IFC: the board looks,
 * asserts nothing, and stays off the bus.
 *
 * Then the bring-up commands (src/bringup.c), under the same rules: every
 * line of every "++t raw" role reaches the bus and comes back from it, and
 * "++t selftest" passes a good board and fails each planted fault (no 5 V, a
 * 5 V switch stuck on, an open joint, two lines bridged).
 */
#include "../src/board_pins.h"
#include "../src/bringup.h"
#include "../src/capture.h"
#include "../src/gpib.h"
#include "sim_bus.h"
#include "wire_model.h"
#include "hardware/gpio.h"
#include "pico/time.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static uint64_t now;

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
static int changes;
static const char *phase = "";
static bool ext[L_COUNT];                /* lines the test itself asserts from beyond the plug */
static uint8_t ext_data;
static bool checking = true;             /* off while a fault is planted: the rules are a good board's */
static bool watching, we_asserted;       /* while watching: did this board assert any line at all? */

static void settle(void)
{
    bool our[L_COUNT];
    uint8_t our_data = 0;
    for (int l = 0; l < L_COUNT; l++)
        our[l] = ours(line_pin[l]);
    for (int i = 0; i < 8; i++)
        our_data |= (uint8_t)(ours(dio_pin[i]) << i);
    sim_wire_step(our, our_data, powered(), far, &far_data);
    for (int l = 0; l < L_COUNT; l++)
        far[l] |= ext[l];
    far_data |= ext_data;
    for (unsigned bit = 0; bit < 16 && watching; bit++)
        if (ours(bit < 8 ? dio_pin[bit] : line_pin[bit - 8]))
            we_asserted = true;
    changes++;
    if (checking)
        wire_check(phase);
    record();
}

void wire_changed(void) { settle(); }
void wire_read(void)
{
    now++;
    settle();
}

/* ---- the Pico SDK's clock (stubs/): a microsecond a call ------------------ */
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

/* what a bring-up command said, a line each */
static char said[4096];
static void say(const char *fmt, ...)
{
    size_t n = strlen(said);
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(said + n, sizeof said - n - 2, fmt, ap);
    va_end(ap);
    strcat(said, "\n");
}

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
    fault_no_r21 = argc > 1 && !strcmp(argv[1], "no_r21");
    printf("%s: ", lite_board ? "GPiBridge Lite" : fault_no_r21 ? "GPiBridge with R21 missing" : "GPiBridge");

    sim_reset();
    for (unsigned p = 0; p < 32; p++)
        pull[p] = -1;                    /* the pads after reset: pull-downs */

    if (fault_no_r21) {
        /* R21 missing or open (REVB.md 1.8): DC follows the pad's pull, so it reads low
         * with the pull-down and high with the pull-up.  The board must read as unknown,
         * get the pin layer that drives nothing high, and stay off the bus, whatever is
         * asked of it.  (Until 0.4.5 a floating DC was read once: high meant GPiBridge.) */
        phase = "boot";
        gpib_stop();
        phase = "board ID";
        CHECK(!hal_board_known(), "R21 missing, yet the board read as %s", hal_lite() ? "the Lite" : "GPiBridge");
        CHECK(hal_lite(), "an unknown board given the transceivers' pin layer");
        phase = "bus refused";
        CHECK(!gpib_start(false) && !gpib_start(true), "on the bus with R21 missing");
        gpib_raw(RAW_CTRL_TALK);
        CHECK(!gpib_powered() && !gpib_is_raw() && !powered(), "powered or raw with R21 missing");
        char *argv_[] = {"selftest"};
        said[0] = 0;
        bringup_command(1, argv_, say, "test");
        CHECK(strstr(said, "\"refused\"") && !gpib_powered(), "selftest with R21 missing: %s", said);
        for (unsigned p = 0; p < 32; p++)
            CHECK(!(oe[p] && ov[p] && !outlow[p] && (BUS_PIN_MASK & (1u << p))), "bus GPIO%u driven high", p);
        printf("%d pin changes checked; %d failures\n", changes, failures);
        return failures || wire_breach_count();
    }

    phase = "boot";
    gpib_stop();                         /* what main() does first */
    CHECK(!powered(), "transceivers powered at boot");

    phase = "gpib_start";
    gpib_start(false);
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
    gpib_start(false);
    n = query("*IDN?\n", buf, sizeof buf);
    CHECK(n == strlen(idn) && !memcmp(buf, idn, n), "answered %zu bytes", n);
    gpib_stop();

    /* ---- with the bus off, nothing moves: every transfer says so --------- */
    phase = "bus off";
    s = gpib_serial_poll(SIM_ADDR, -1, &status);
    CHECK(s == GPIB_OFF, "serial poll with the bus off: %s", gpib_status_name(s));
    s = gpib_send_to(SIM_ADDR, -1, (const uint8_t *)"X\n", 2, true);
    CHECK(s == GPIB_OFF, "send with the bus off: %s", gpib_status_name(s));
    gpib_ifc();
    gpib_ren(true);
    gpib_idle();
    CHECK(!powered(), "something switched the bus on");

    /* ---- somebody else is the controller: we look, touch nothing, and stand back ---- */
    static const gpib_line theirs[] = {L_REN, L_ATN, L_IFC};
    for (size_t i = 0; i < sizeof theirs / sizeof theirs[0]; i++) {
        phase = "another controller";
        ext[theirs[i]] = true;
        watching = true;
        we_asserted = false;
        bool started = gpib_start(false);
        watching = false;
        CHECK(!started && gpib_busy() && !gpib_powered() && !powered(), "started against another controller (line %d)",
              (int)theirs[i]);
        CHECK(!we_asserted, "asserted a line while looking for another controller (line %d)", (int)theirs[i]);
        s = gpib_send_to(SIM_ADDR, -1, (const uint8_t *)"X\n", 2, true);
        CHECK(s == GPIB_OFF && strstr(gpib_status_name(s), "another controller"), "a send then: %s",
              gpib_status_name(s));
        ext[theirs[i]] = false;
    }
    CHECK(gpib_count.refused == 3, "three starts refused (%lu)", (unsigned long)gpib_count.refused);
    phase = "the bus free again";
    CHECK(gpib_start(false) && !gpib_busy(), "did not start on a free bus");
    n = query("*IDN?\n", buf, sizeof buf);
    CHECK(n == strlen(idn) && !memcmp(buf, idn, n), "on a free bus, answered %zu bytes", n);
    gpib_stop();
    ext[L_REN] = true;                   /* a line stuck low is not a controller: forced, we start */
    CHECK(gpib_start(true) && gpib_powered(), "a forced start");
    ext[L_REN] = false;
    gpib_stop();

    /* ---- "++t raw": each role, each line, out to the bus and back -------- */
    sim_present = false;                 /* nothing beyond the plug but this test */
    static const char *const role_name[RAW_ROLES] = {"dev_listen", "dev_talk", "ctrl_listen", "ctrl_talk"};
    for (int r = 0; r < RAW_ROLES; r++) {
        phase = role_name[r];
        gpib_raw((raw_role)r);
        uint16_t drives = hal_raw_drives(), reads = hal_raw_reads(), bus = 0;
        CHECK(powered() && gpib_is_raw(), "raw mode did not power the bus");
        CHECK(lite_board || !(drives & reads), "a line both driven and read: 0x%04x", drives & reads);
        for (unsigned bit = 0; bit < 16; bit++)
            bus |= (uint16_t)(asserted(bit < 8 ? dio_pin[bit] : line_pin[bit - 8]) << bit);
        CHECK(!bus && !(hal_raw_get(0) & reads), "entering the role asserted 0x%04x", bus);
        for (unsigned bit = 0; bit < 16; bit++) {
            if (drives >> bit & 1) {     /* out: exactly this line on the bus */
                hal_raw_set((uint16_t)(1u << bit));
                bus = 0;
                for (unsigned k = 0; k < 16; k++)
                    bus |= (uint16_t)(ours(k < 8 ? dio_pin[k] : line_pin[k - 8]) << k);
                CHECK(bus == 1u << bit, "set 0x%04x put 0x%04x on the bus", 1u << bit, bus);
                hal_raw_set(0);
            }
            if (reads >> bit & 1) {      /* back: exactly this line read, whatever the pads' pulls */
                if (bit < 8)
                    ext_data = (uint8_t)(1u << bit);
                else
                    ext[bit - 8] = true;
                for (int pl = -1; pl <= 1; pl++) {
                    uint16_t got = hal_raw_get(pl) & reads;
                    CHECK(got == 1u << bit, "0x%04x asserted beyond the plug read as 0x%04x (pull %d)", 1u << bit,
                          got, pl);
                }
                ext_data = 0;
                memset(ext, 0, sizeof ext);
            }
        }
    }
    phase = "raw off";
    gpib_stop();
    CHECK(!powered() && !gpib_is_raw(), "raw mode left the bus on");

    /* ---- "++t selftest": a good board passes, each planted fault fails ---- */
    static const struct {
        const char *what;
        bool lite, full;                 /* which board it can happen to */
        uint32_t open;
        bool no_5v, stuck_5v;
        int short_a, short_b;
    } fault[] = {
        {"a good board", true, true, 0, false, false, -1, -1},
        {"the 5 V switch never closes", false, true, 0, true, false, -1, -1},
        {"the 5 V switch never opens", false, true, 0, false, true, -1, -1},
        {"DAV's joint open", false, true, 1u << PIN_DAV, false, false, -1, -1},
        {"DIO8's joint open", false, true, 1u << PIN_DIO8, false, false, -1, -1},
        {"SRQ's joint open", false, true, 1u << PIN_SRQ, false, false, -1, -1},
        {"NRFD's joint open", false, true, 1u << PIN_NRFD, false, false, -1, -1},
        {"DAV bridged to NRFD", true, false, 0, false, false, PIN_DAV, PIN_NRFD},
    };
    /* (An open joint on the Lite is out of a lone board's sight: the pad still
     * follows its own pull and reads its own low.  The two-board walk finds it:
     * bringup/, against sim_board.) */
    bus_terminated = false;              /* nothing on the GPIB side: the Lite's pins float */
    for (size_t i = 0; i < sizeof fault / sizeof fault[0]; i++) {
        if (!(lite_board ? fault[i].lite : fault[i].full))
            continue;
        phase = fault[i].what;
        fault_open = fault[i].open;
        fault_no_5v = fault[i].no_5v;
        fault_5v_stuck = fault[i].stuck_5v;
        fault_short_a = fault[i].short_a;
        fault_short_b = fault[i].short_b;
        checking = i == 0;               /* the rules are for a good board */
        said[0] = 0;
        char *argv_[] = {"selftest"};
        bringup_command(1, argv_, say, "test");
        bool passed = strstr(said, "\"ok\":true") != NULL;
        CHECK(passed == (i == 0), "selftest said %s:\n%s", passed ? "ok" : "not ok", said);
        CHECK(!gpib_powered(), "selftest left the bus on");
    }
    fault_open = 0;
    fault_no_5v = fault_5v_stuck = false;
    fault_short_a = fault_short_b = -1;
    checking = true;
    bus_terminated = true;
    sim_present = true;

    /* ---- and the engine takes the bus back, as before --------------------- */
    phase = "after raw";
    gpib_raw(RAW_CTRL_TALK);
    hal_raw_set(RAW_DATA);               /* leave it mid-test, lines asserted */
    gpib_start(false);
    n = query("*IDN?\n", buf, sizeof buf);
    CHECK(n == strlen(idn) && !memcmp(buf, idn, n), "after raw mode, answered %zu bytes", n);
    said[0] = 0;
    char *argv_[] = {"selftest"};
    sim_present = false;
    bus_terminated = false;
    bringup_command(1, argv_, say, "test");
    sim_present = true;
    bus_terminated = true;
    CHECK(strstr(said, "\"ok\":true") && gpib_powered() && !gpib_is_raw(), "selftest from a running bus: %s", said);
    n = query("*IDN?\n", buf, sizeof buf);
    CHECK(n == strlen(idn) && !memcmp(buf, idn, n), "after a selftest, answered %zu bytes", n);
    gpib_stop();

    if (lite_board)
        printf("%d pin changes checked: %d driven high, %d without the override, %d off the bus; %d failures\n",
               changes, wire_found.drive_high, wire_found.override, wire_found.off_bus, failures);
    else
        printf("%d pin changes checked: %d contention, %d back-power; %d failures\n", changes, wire_found.contention,
               wire_found.backpower, failures);
    return failures || wire_breach_count();
}
