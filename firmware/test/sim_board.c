/* sim_board.c: a GPiBridge that is not there.
 *
 * The firmware above the Pico SDK (prologix.c, gpib.c, bringup.c and the
 * board's own pin layer, hal_rp2350.c) on a PC, behind a pseudo-terminal that
 * stands for the adapter's USB serial port.  Below it the wires of
 * wire_model.c: the transceivers by their function tables, or the Lite's
 * pins on the bus.  So the bring-up scripts (bringup/), tools/gpibridge.py
 * and lab-instrument-control's own Link and drivers can be run, before any
 * board exists, against the code the board will run.
 *
 *   sim_board [lite] [--link PATH] [--serial NAME] [--instrument]
 *             [--bus FILE --slot N] [--fault WHAT] [--manual]
 *
 *   lite            GPiBridge Lite (R21 pulls DC down)
 *   --link PATH     a symbolic link to the pseudo-terminal, a name to open
 *   --serial NAME   the USB serial number it reports (++t info)
 *   --instrument    the simulated HP 33120A (sim_bus.c) on its plug, address 10
 *   --bus FILE      a bus shared with other sim_boards: each takes a --slot
 *                   (0-3) in FILE, and sees what the others assert, as boards
 *                   joined by a GPIB cable do
 *   --fault WHAT    a board fault: no5v, stuck5v, open=LINE, short=LINE,LINE,
 *                   turned (the plug soldered in turned round), no_r21 (R21 missing:
 *                   DC follows the pad's pull)
 *   --manual        start as after "++t autostart 0": off the bus
 *
 * It prints one JSON line with the pseudo-terminal's name when it is ready,
 * the firmware's log (the UART's lines) on stderr, and runs until killed.
 * Time is the PC's clock, so a 500 ms timeout takes 500 ms.
 *
 * What it does not simulate: USB itself, the flash, the LEDs, the watchdog
 * and core 1 (main.c and capture_rp2350.c, which only the board can run).
 * "++t capture" works: it records the model's pins.
 */
#include "../src/bringup.h"
#include "../src/capture.h"
#include "../src/gpib.h"
#include "../src/prologix.h"
#include "../src/version.h"
#include "sim_bus.h"
#include "wire_model.h"
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

/* ---- the bus between boards: a file every sim_board on it maps -------------- */
#define SLOTS 8                          /* boards in 0-3; the instrument on board n's plug in 4+n */
typedef struct {
    uint16_t low[SLOTS];                 /* the lines each asserts */
    uint16_t high[SLOTS];                /* the lines each drives high as well (totem-pole) */
    uint8_t terminates[SLOTS];           /* its terminations are on the bus */
    uint8_t present[SLOTS];              /* it is plugged in at all (and brings its ground contacts) */
    uint32_t fights[SLOTS];              /* times it began driving a line against another */
    uint32_t breaches[SLOTS];            /* its own pin rules broken (wire_model.h) */
} shared_bus;

static shared_bus private_bus, *bus = &private_bus;
static int slot;
static bool instrument, turned;
static const char *serial_number = "SIM0";

static unsigned bit_pin(unsigned bit) { return bit < 8 ? dio_pin[bit] : line_pin[bit - 8]; }

/* The plug soldered in turned round: contact n sits in the hole of contact
 * 25 - n.  What this board's DIO1 pad meets is then the bus's ground at
 * contact 24, and so on (docs/PINOUT.md).  A line that lands on a ground
 * contact reads asserted for ever; a ground pad that lands on a line holds
 * that line asserted.  (Contact 12, the shield, is ground on these boards and
 * at any instrument.) */
static const int8_t contact_bit[25] = {     /* IEEE-488 contact -> line bit; -1: ground or shield */
    [0] = -1, [1] = 0, [2] = 1, [3] = 2, [4] = 3, [5] = 8 + L_EOI, [6] = 8 + L_DAV, [7] = 8 + L_NRFD,
    [8] = 8 + L_NDAC, [9] = 8 + L_IFC, [10] = 8 + L_SRQ, [11] = 8 + L_ATN, [12] = -1,
    [13] = 4, [14] = 5, [15] = 6, [16] = 7, [17] = 8 + L_REN,
    [18] = -1, [19] = -1, [20] = -1, [21] = -1, [22] = -1, [23] = -1, [24] = -1,
};

/* our lines as the bus sees them through a turned plug (outward), and the bus
 * as our pads see it (inward; grounded: something out there has ground contacts) */
static uint16_t through_plug(uint16_t ours_or_bus, bool outward, bool grounded)
{
    if (!turned)
        return ours_or_bus;
    uint16_t v = 0;
    for (int c = 1; c <= 24; c++) {
        int pad = contact_bit[c], met = contact_bit[25 - c];    /* this pad's signal; the bus contact it meets */
        if (outward) {
            if (met >= 0 && (pad < 0 || (ours_or_bus >> pad & 1)))
                v |= (uint16_t)(1u << met);                     /* our line, or our ground pad, holds it low */
        } else if (pad >= 0) {
            if (met < 0 ? grounded : (ours_or_bus >> met & 1))
                v |= (uint16_t)(1u << pad);                     /* a ground contact, or the line it meets */
        }
    }
    return v;
}

/* ---- "++t capture": the model's pins, as core 1 would record them ----------- */
static capture_entry rec[CAPTURE_MAX];
static size_t n_rec;
static enum { C_IDLE, C_RUNNING, C_FULL, C_STOPPED } cap;
static uint64_t t0_us;

static uint64_t clock_us(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000u + (uint64_t)(t.tv_nsec / 1000);
}

uint64_t time_us_64(void) { return clock_us() - t0_us; }
void busy_wait_us_32(uint32_t us)
{
    if (us >= 500) {
        usleep(us);
    } else {
        uint64_t end = clock_us() + us;
        while (clock_us() < end)
            ;
    }
    wire_changed();
}
void usb_poll(void) {}

static void record(void)
{
    if (cap != C_RUNNING)
        return;
    uint32_t pins = 0;
    for (unsigned p = 0; p < 32; p++)
        if ((capture_mask() >> p & 1) && wire(p))
            pins |= 1u << p;
    if (n_rec && rec[n_rec - 1].pins == pins)
        return;
    if (n_rec == CAPTURE_MAX) {
        cap = C_FULL;
        return;
    }
    rec[n_rec++] = (capture_entry){(uint32_t)(time_us_64() * CAPTURE_TICKS_PER_US), pins};
}

/* ---- beyond the plug: the other boards, and the instrument ------------------ */
static bool fighting;

static void exchange(void)
{
    uint16_t low = 0, high = 0, others_low = 0, others_high = 0;
    bool terminated = false, company = instrument;
    for (unsigned bit = 0; bit < 16; bit++) {
        if (ours(bit_pin(bit)))
            low |= (uint16_t)(1u << bit);
        else if (xcvr_totem(bit_pin(bit)))
            high |= (uint16_t)(1u << bit);
    }
    low = through_plug(low, true, false);
    high = turned ? 0 : high;
    bus->present[slot] = 1;
    bus->low[slot] = low;
    bus->high[slot] = high;
    bus->terminates[slot] = !lite_board && powered();
    for (int s = 0; s < SLOTS; s++) {
        if (s == slot || s == slot + 4)
            continue;
        others_low |= bus->low[s];
        others_high |= bus->high[s];
        terminated |= bus->terminates[s];
        company |= bus->present[s];
    }
    if (instrument) {
        bool to_it[L_COUNT], from_it[L_COUNT];
        uint8_t data_from_it;
        uint16_t seen = low | others_low, it = 0;
        for (int l = 0; l < L_COUNT; l++)
            to_it[l] = seen >> (8 + l) & 1;
        sim_wire_step(to_it, (uint8_t)seen, true, from_it, &data_from_it);
        it = data_from_it;
        for (int l = 0; l < L_COUNT; l++)
            if (from_it[l])
                it |= (uint16_t)RAW_BIT(l);
        bus->low[slot + 4] = it;
        bus->terminates[slot + 4] = 1;
        others_low |= it;
        terminated = true;
    }
    uint16_t seen = through_plug(others_low, false, company);
    for (int l = 0; l < L_COUNT; l++)
        far[l] = seen >> (8 + l) & 1;
    far_data = (uint8_t)seen;
    bus_terminated = terminated;
    bool fight = (low & others_high) || (high & others_low);
    if (fight && !fighting)
        bus->fights[slot]++;
    fighting = fight;
}

static bool faulty;                      /* a fault is planted: the pin rules are a good board's */

void wire_changed(void)
{
    exchange();
    if (!faulty) {
        wire_check("sim_board");
        bus->breaches[slot] = (uint32_t)wire_breach_count();
    }
    record();
}
void wire_read(void) { wire_changed(); }

/* ---- what main.c does around the protocol code -------------------------------- */
static int master = -1;
static prologix_config saved;
static bool have_saved, manual;

static void host_write(const uint8_t *d, size_t n)
{
    while (n) {
        ssize_t k = write(master, d, n);
        if (k < 0) {
            if (errno == EAGAIN || errno == EINTR) {
                usleep(200);
                continue;
            }
            return;
        }
        d += k;
        n -= (size_t)k;
    }
}
static void host_flush(void) {}
static void host_text(const char *s, size_t n) { host_write((const uint8_t *)s, n); }
static void save(const prologix_config *c)
{
    saved = *c;
    have_saved = true;
}
static void uart(const char *json)
{
    fprintf(stderr, "%s\n", json);
    fflush(stderr);
}
static const char *board_name(void)
{
    if (!hal_board_known())
        return "unknown (R21 not read) " GPIBRIDGE_BOARD;   /* REVB.md 1.8 */
    return hal_lite() ? "GPiBridge Lite " GPIBRIDGE_BOARD : "GPiBridge " GPIBRIDGE_BOARD;
}
static const char *capture_name(void) { return (const char *[]){"idle", "running", "full", "stopped"}[cap]; }

static void status_extra(char *json, size_t n)
{
    snprintf(json, n, ",\"board\":\"%s\",\"usb_ready_ms\":180,\"console\":%d,\"capture\":\"%s\",\"changes\":%lu,"
             "\"settings_errors\":0,\"us\":%llu",
             board_name(), prologix_cfg.console_port, capture_name(), (unsigned long)(cap == C_RUNNING ? 0 : n_rec),
             (unsigned long long)time_us_64());
}
static void info(char *json, size_t n)
{
    snprintf(json, n, ",\"serial\":\"%s\",\"chip_rev\":4,\"chip_reset\":\"0x00010000\",\"vreg\":\"0x000000b0\","
             "\"watchdog_reset\":0,\"temp_raw\":868,\"sys_khz\":150000,\"flash_kb\":2048,\"uptime_ms\":%lu,"
             "\"sim\":true",
             serial_number, (unsigned long)(time_us_64() / 1000));
}
static void identify(int seconds)
{
    char j[80];
    snprintf(j, sizeof j, "{\"event\":\"identify\",\"seconds\":%d}", seconds);
    uart(j);
}
static void capture_command(const char *what)
{
    char s[96];
    if (!strcmp(what, "start")) {
        n_rec = 0;
        cap = C_RUNNING;
        record();
    } else if (!strcmp(what, "stop")) {
        if (cap == C_RUNNING)
            cap = C_STOPPED;
    } else if (!strcmp(what, "dump")) {
        char who[64];
        if (cap == C_RUNNING)
            cap = C_STOPPED;
        snprintf(who, sizeof who, "%s, firmware %s (simulated)", board_name(), GPIBRIDGE_VERSION);
        capture_vcd(rec, n_rec, CAPTURE_TICKS_PER_US, 10, who, host_text);
        return;
    } else if (strcmp(what, "status")) {
        host_text("++t capture start | stop | status | dump\r\n", 42);
        return;
    }
    snprintf(s, sizeof s, "{\"capture\":\"%s\",\"changes\":%lu}\r\n", capture_name(),
             (unsigned long)(cap == C_RUNNING ? 0 : n_rec));
    host_text(s, strlen(s));
}

static void start(void);
static void reboot(bool bootsel)
{
    uart(bootsel ? "{\"event\":\"reboot\",\"to\":\"bootsel\"}" : "{\"event\":\"reboot\"}");
    gpib_stop();
    start();                             /* a simulated board comes straight back, whichever it was */
}

static const prologix_io io = {
    .write = host_write, .flush = host_flush, .save = save, .reboot = reboot, .log = uart,
    .status_extra = status_extra, .capture = capture_command, .info = info, .identify = identify,
};

/* main() up to the host configuring the device (tud_mount_cb) */
static void start(void)
{
    char j[160];
    prologix_init(&io, have_saved ? &saved : NULL);
    if (manual && !have_saved)
        prologix_cfg.manual_start = true;
    gpib_stop();
    snprintf(j, sizeof j, "{\"event\":\"boot\",\"version\":\"%s\",\"board\":\"%s\",\"at_ms\":%lu}", GPIBRIDGE_VERSION,
             board_name(), (unsigned long)(time_us_64() / 1000));
    uart(j);
    if (prologix_cfg.manual_start) {
        uart("{\"event\":\"usb\",\"configured\":true,\"bus_power\":\"waits for ++t power 1\"}");
        return;
    }
    if (gpib_start(false))
        uart("{\"event\":\"bus_power\",\"on\":true}");
    else
        uart("{\"event\":\"bus\",\"error\":\"another controller holds ATN, REN or IFC: staying off the bus "
             "(++t power 2 takes it regardless)\"}");
}

static int line_bit(const char *name)
{
    static const char *const names[16] = {
        "DIO1", "DIO2", "DIO3", "DIO4", "DIO5", "DIO6", "DIO7", "DIO8",
        [8 + L_EOI] = "EOI", [8 + L_DAV] = "DAV", [8 + L_NRFD] = "NRFD", [8 + L_NDAC] = "NDAC",
        [8 + L_IFC] = "IFC", [8 + L_REN] = "REN", [8 + L_ATN] = "ATN", [8 + L_SRQ] = "SRQ",
    };
    for (int b = 0; b < 16; b++)
        if (!strcmp(name, names[b]))
            return b;
    fprintf(stderr, "sim_board: no line called %s\n", name);
    exit(2);
}

static const char *link_path;
static void bye(int sig)
{
    (void)sig;
    if (link_path)
        unlink(link_path);
    bus->low[slot] = bus->high[slot] = 0;
    bus->terminates[slot] = bus->present[slot] = 0;
    if (instrument) {
        bus->low[slot + 4] = 0;
        bus->terminates[slot + 4] = 0;
    }
    _exit(0);
}

int main(int argc, char **argv)
{
    const char *bus_path = NULL;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i], *v = i + 1 < argc ? argv[i + 1] : "";
        if (!strcmp(a, "lite")) {
            lite_board = true;
        } else if (!strcmp(a, "--instrument")) {
            instrument = true;
        } else if (!strcmp(a, "--manual")) {
            manual = true;
        } else if (!strcmp(a, "--link")) {
            link_path = v, i++;
        } else if (!strcmp(a, "--serial")) {
            serial_number = v, i++;
        } else if (!strcmp(a, "--bus")) {
            bus_path = v, i++;
        } else if (!strcmp(a, "--slot")) {
            slot = atoi(v) & 3, i++;
        } else if (!strcmp(a, "--fault")) {
            char *f = strdup(v), *comma;
            i++;
            faulty = true;
            if (!strcmp(f, "no5v")) {
                fault_no_5v = true;
            } else if (!strcmp(f, "stuck5v")) {
                fault_5v_stuck = true;
            } else if (!strcmp(f, "turned")) {
                turned = true;
            } else if (!strcmp(f, "no_r21")) {
                fault_no_r21 = true;
            } else if (!strncmp(f, "open=", 5)) {
                fault_open |= 1u << bit_pin((unsigned)line_bit(f + 5));
            } else if (!strncmp(f, "short=", 6) && (comma = strchr(f, ','))) {
                *comma = 0;
                fault_short_a = (int)bit_pin((unsigned)line_bit(f + 6));
                fault_short_b = (int)bit_pin((unsigned)line_bit(comma + 1));
            } else {
                fprintf(stderr, "sim_board: --fault no5v | stuck5v | turned | no_r21 | open=LINE | short=LINE,LINE\n");
                return 2;
            }
        } else {
            fprintf(stderr, "usage: sim_board [lite] [--link PATH] [--serial NAME] [--instrument] "
                            "[--bus FILE --slot N] [--fault WHAT] [--manual]\n");
            return 2;
        }
    }
    if (bus_path) {
        int fd = open(bus_path, O_RDWR | O_CREAT, 0600);
        if (fd < 0 || ftruncate(fd, sizeof(shared_bus)) < 0) {
            perror(bus_path);
            return 1;
        }
        bus = mmap(NULL, sizeof(shared_bus), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (bus == MAP_FAILED) {
            perror("mmap");
            return 1;
        }
        bus->fights[slot] = bus->breaches[slot] = 0;
    }
    t0_us = clock_us();
    wire_report = stderr;
    for (unsigned p = 0; p < 32; p++)
        pull[p] = -1;                    /* the pads after reset: pull-downs */
    sim_reset();
    bus_terminated = false;

    master = posix_openpt(O_RDWR | O_NOCTTY);
    if (master < 0 || grantpt(master) < 0 || unlockpt(master) < 0) {
        perror("pseudo-terminal");
        return 1;
    }
    const char *name = ptsname(master);
    /* Hold the other end open ourselves, raw: what we write is then never
     * echoed back to us as if typed, and a program that closes the port does
     * not hang up on us. */
    int slave = open(name, O_RDWR | O_NOCTTY);
    struct termios t;
    if (slave < 0 || tcgetattr(slave, &t) < 0) {
        perror(name);
        return 1;
    }
    cfmakeraw(&t);
    tcsetattr(slave, TCSANOW, &t);
    if (link_path) {
        unlink(link_path);
        if (symlink(name, link_path) < 0) {
            perror(link_path);
            return 1;
        }
    }
    signal(SIGTERM, bye);
    signal(SIGINT, bye);
    signal(SIGHUP, bye);

    start();
    printf("{\"sim_board\":\"ready\",\"port\":\"%s\",\"board\":\"%s\",\"serial\":\"%s\",\"slot\":%d}\n", name,
           board_name(), serial_number, slot);
    fflush(stdout);

    for (;;) {
        struct pollfd p = {.fd = master, .events = POLLIN};
        uint8_t buf[64];                 /* as USB brings it: a full-speed packet at a time */
        if (poll(&p, 1, 2) > 0 && (p.revents & POLLIN)) {
            ssize_t n = read(master, buf, sizeof buf);
            if (n > 0)
                prologix_input(buf, (size_t)n);
        }
        wire_changed();                  /* the others move the bus while we wait */
    }
}
