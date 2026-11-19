/* main.c: GPiBridge's firmware on the RP2354A.
 *
 *   USB serial "GPiBridge GPIB"     the Prologix "++" controller (prologix.c)
 *   USB serial "GPiBridge console"  optional (++t console 1): JSON lines,
 *                                   logs out, a few commands in; the same
 *                                   lines always go out on the UART (J4)
 *   USB reset interface              `picotool reboot -u -f --vid 0x1209 --pid 0x0001` reaches BOOTSEL
 *   core 1                           the bus capture, when asked (capture.h)
 *
 * Failsafes:
 *   - the transceivers are switched on only after every pin is released,
 *     and only once the host has configured us (they draw more than the
 *     100 mA an unconfigured USB device may);
 *   - every wait on the bus has a timeout, and a watchdog catches the rest;
 *   - three watchdog timeouts in a row reboot into BOOTSEL, so a bad image
 *     can always be replaced over USB, with nobody pressing BOOT.  Only a
 *     timeout counts (watchdog_enable_caused_reboot): on the RP2350
 *     watchdog_caused_reboot() is also true after a deliberate reboot
 *     (++rst, ++t console), and three of those in ten seconds sent rev A's
 *     first board to BOOTSEL on its first day (bringup/REVB.md 2.8).
 *
 * LEDs: yellow (USB) blinks until the host has configured us, then stays on
 * and blinks off on traffic; red (ERR) lights for a second after a bus error;
 * "++t identify" flashes the two against each other, to tell boards apart;
 * green (BUS) is lit by the transceivers' own 5 V (on GPiBridge Lite, by the
 * same signal, BUS_PWR_EN: while the firmware is on the bus).
 *
 * One image runs both boards: hal_rp2350.c reads which at start-up (R21 on
 * DC) and drives the transceivers or, on the Lite, the bus pins themselves.
 */
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/bootrom.h"
#include "pico/flash.h"
#include "pico/unique_id.h"
#include "hardware/adc.h"
#include "hardware/clocks.h"
#include "hardware/flash.h"
#include "hardware/structs/powman.h"
#include "hardware/structs/ticks.h"
#include "hardware/sync.h"
#include "hardware/watchdog.h"
#include "tusb.h"
#include "board_pins.h"
#include "capture.h"
#include "gpib.h"
#include "gpib_hal.h"
#include "prologix.h"
#include "usb_descriptors.h"
#include "version.h"

#define CDC_GPIB 0
#define CDC_CONSOLE 1
#define SETTINGS_OFFSET (PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE)
#define SETTINGS_MAGIC 0x47506942u      /* "GPiB" */
#define CRASHES_TO_BOOTSEL 3

static void bus_start(void);

/* ---- the console ------------------------------------------------------------ */
static void console_line(const char *s)
{
    printf("%s\n", s);                   /* the UART (J4) */
    if (tud_cdc_n_connected(CDC_CONSOLE)) {
        tud_cdc_n_write_str(CDC_CONSOLE, s);
        tud_cdc_n_write_str(CDC_CONSOLE, "\r\n");
        tud_cdc_n_write_flush(CDC_CONSOLE);
    }
}

/* ---- settings in the flash's last sector ---------------------------------- */
typedef struct {
    uint32_t magic;
    uint32_t size;
    prologix_config cfg;
    uint32_t check;
} settings;

static uint32_t checksum(const settings *s)
{
    const uint8_t *p = (const uint8_t *)&s->cfg;
    uint32_t h = 2166136261u;            /* FNV-1a */
    for (size_t i = 0; i < sizeof s->cfg; i++)
        h = (h ^ p[i]) * 16777619u;
    return h;
}

static const prologix_config *settings_load(void)
{
    const settings *s = (const settings *)(XIP_BASE + SETTINGS_OFFSET);
    if (s->magic != SETTINGS_MAGIC || s->size != sizeof(settings) || s->check != checksum(s))
        return NULL;
    return &s->cfg;
}

static prologix_config pending;
static bool dirty;
static uint32_t settings_errors;         /* settings writes the flash refused */
static uint64_t dirty_at;

static void settings_write_now(void *arg)
{
    (void)arg;
    static uint8_t page[FLASH_PAGE_SIZE * 2];   /* the struct rounded up to pages */
    memset(page, 0xff, sizeof page);
    settings s = {.magic = SETTINGS_MAGIC, .size = sizeof(settings), .cfg = pending};
    s.check = checksum(&s);
    memcpy(page, &s, sizeof s);
    flash_range_erase(SETTINGS_OFFSET, FLASH_SECTOR_SIZE);
    flash_range_program(SETTINGS_OFFSET, page, sizeof page);
}

/* ++savecfg: only when something changed, and once things have settled for 2 s,
 * so a script that sets ++addr before every query does not wear the flash */
static void settings_save(const prologix_config *cfg)
{
    const prologix_config *now = settings_load();
    if (now && !memcmp(now, cfg, sizeof *cfg)) {
        dirty = false;
        return;
    }
    pending = *cfg;
    dirty = true;
    dirty_at = time_us_64();
}

static void settings_flush(void)
{
    dirty = false;
    int rc = flash_safe_execute(settings_write_now, NULL, 100);
    char s[80];
    if (rc == PICO_OK) {
        console_line("{\"event\":\"settings\",\"saved\":true}");
    } else {
        settings_errors++;
        snprintf(s, sizeof s, "{\"event\":\"settings\",\"error\":\"flash_safe_execute %d\"}", rc);
        console_line(s);
    }
}

static void settings_poll(void)
{
    if (dirty && time_us_64() - dirty_at > 2000000)
        settings_flush();
}

/* ---- USB -------------------------------------------------------------------- */
static uint64_t traffic_at, error_at, usb_ready_us, identify_until;
static bool crashed_before;              /* this start followed a watchdog timeout: a hang or a fault */
static uint32_t boot_reason, boot_scratch4; /* WATCHDOG REASON (1 timer, 2 force) and SCRATCH4 as this start found them */

#define WATCHDOG_MS 2000
static bool reboot_asked;                /* by the reset interface: "reboot from flash" */
static bool watching;                    /* our watchdog is running (main(), after USB starts) */

void usb_poll(void)
{
    tud_task();
    watchdog_update();
    /* The Pico SDK's reset interface takes "reboot from flash" (picotool reboot -f -a) as
     * watchdog_reboot(0, 0, 100 ms), and the feed above would reload those 100 ms for ever:
     * the board never rebooted (A1, 2026-11-19; REVB.md 2.15).  Seen as a load under ours,
     * it becomes our own orderly reboot, from the main loop; a read under way ends for it. */
    if (watching && !reboot_asked && (watchdog_hw->ctrl & WATCHDOG_CTRL_TIME_BITS) < WATCHDOG_MS * 500u) {
        reboot_asked = true;
        watchdog_enable(WATCHDOG_MS, true);   /* our 2 s again, until then */
    }
}

static void gpib_write_host(const uint8_t *data, size_t n)
{
    uint64_t t0 = time_us_64();
    traffic_at = t0;
    while (n) {
        /* not tud_cdc_n_connected(): that needs DTR, which a Prologix (an FTDI
         * chip) never asked for, so some programs never raise it */
        if (!tud_mounted())
            return;
        uint32_t k = tud_cdc_n_write(CDC_GPIB, data, n);
        data += k;
        n -= k;
        if (n) {
            tud_cdc_n_write_flush(CDC_GPIB);
            usb_poll();
            if (time_us_64() - t0 > 2000000)
                return;                  /* the host stopped reading */
        }
    }
}

static void gpib_flush_host(void) { tud_cdc_n_write_flush(CDC_GPIB); }

static void host_text(const char *s, size_t n) { gpib_write_host((const uint8_t *)s, n); }

static void host_line(const char *s)
{
    host_text(s, strlen(s));
    host_text("\r\n", 2);
    gpib_flush_host();
}

static void do_reboot(bool bootsel)
{
    console_line(bootsel ? "{\"event\":\"reboot\",\"to\":\"bootsel\"}" : "{\"event\":\"reboot\"}");
    if (dirty)
        settings_flush();                /* a setting that asked for the reboot (++t console) */
    sleep_ms(50);
    gpib_stop();
    if (bootsel)
        rom_reset_usb_boot_extra(-1, 0, false);
    watchdog_reboot(0, 0, 10);
    for (;;)
        tight_loop_contents();
}

static void log_json(const char *json)
{
    if (strstr(json, "\"status\":\"ok\"") == NULL)
        error_at = time_us_64();
    console_line(json);
}

static const char *board_name(void)
{
    if (!hal_board_known())
        return "unknown (R21 not read) " GPIBRIDGE_BOARD;   /* REVB.md 1.8 */
    return hal_lite() ? "GPiBridge Lite " GPIBRIDGE_BOARD : "GPiBridge " GPIBRIDGE_BOARD;
}

/* the fields ++t status and the console's status add to the bus counters */
static void status_extra(char *json, size_t n)
{
    snprintf(json, n, ",\"board\":\"%s\",\"usb_ready_ms\":%lu,\"console\":%d,\"capture\":\"%s\",\"changes\":%lu,"
             "\"settings_errors\":%lu,\"us\":%llu",
             board_name(), (unsigned long)(usb_ready_us / 1000), prologix_cfg.console_port, capture_state(),
             (unsigned long)capture_count(), (unsigned long)settings_errors, (unsigned long long)time_us_64());
}

/* ++t info: what the chip says about itself.  Nothing here needs a probe:
 *   chip_rev    the RP2350's stepping (2 = A2, which has erratum E9);
 *   chip_reset  POWMAN's record of why the chip last reset (datasheet: CHIP_RESET);
 *   vreg        the core regulator's control word (POWMAN VREG);
 *   temp_raw    the temperature sensor through the 12-bit ADC, whose reference
 *               is the 3.3 V rail: a diode drop of about 0.7 V over the rail,
 *               so a rail that is far off shows here (876 at 3.30 V and 27 C);
 *   sys_khz     the system clock, from the 12 MHz crystal. */
static void info(char *json, size_t n)
{
    static bool adc_ready;
    char id[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
    pico_get_unique_board_id_string(id, sizeof id);
    if (!adc_ready) {
        adc_init();
        adc_set_temp_sensor_enabled(true);
        adc_ready = true;
    }
    adc_select_input(ADC_TEMPERATURE_CHANNEL_NUM);
    uint32_t sum = 0;
    for (int i = 0; i < 64; i++)
        sum += adc_read();
    /* the watchdog, measured: its count just after a feed, and how far it falls in 1 ms
     * (expected 2,000,000 and 1000: a 2 s timeout in 1 us ticks) */
    uint32_t irq = save_and_disable_interrupts();
    watchdog_update();
    uint32_t wd0 = watchdog_hw->ctrl & WATCHDOG_CTRL_TIME_BITS;
    busy_wait_us_32(1000);
    uint32_t wd1 = watchdog_hw->ctrl & WATCHDOG_CTRL_TIME_BITS;
    watchdog_update();
    restore_interrupts(irq);
    snprintf(json, n, ",\"serial\":\"%s\",\"chip_rev\":%u,\"chip_reset\":\"0x%08lx\",\"vreg\":\"0x%08lx\","
             "\"watchdog_reset\":%d,\"temp_raw\":%lu,\"sys_khz\":%lu,\"flash_kb\":%u,\"uptime_ms\":%lu,"
             "\"wd_load\":%lu,\"wd_per_ms\":%ld,\"wd_tick\":\"0x%lx/%lu\",\"boot_reason\":%lu,\"boot_scratch4\":\"0x%08lx\"",
             id, (unsigned)rp2350_chip_version(), (unsigned long)powman_hw->chip_reset, (unsigned long)powman_hw->vreg,
             crashed_before, (unsigned long)(sum / 64), (unsigned long)(clock_get_hz(clk_sys) / 1000),
             (unsigned)(PICO_FLASH_SIZE_BYTES / 1024), (unsigned long)(time_us_64() / 1000), (unsigned long)wd0,
             (long)wd0 - (long)wd1, (unsigned long)ticks_hw->ticks[TICK_WATCHDOG].ctrl,
             (unsigned long)ticks_hw->ticks[TICK_WATCHDOG].cycles, (unsigned long)boot_reason,
             (unsigned long)boot_scratch4);
}

static void identify(int seconds) { identify_until = seconds ? time_us_64() + (uint64_t)seconds * 1000000u : 0; }

/* ++t crash: hang with interrupts off, as a fault would; the watchdog bites
 * 2 s later.  The bus first goes off, as the watchdog would leave it. */
static void crash(void)
{
    console_line("{\"event\":\"crash\",\"by\":\"++t crash\"}");
    gpib_stop();
    (void)save_and_disable_interrupts();
    for (;;)
        tight_loop_contents();
}

/* ++t capture start|stop|status|dump */
static void capture_command(const char *what)
{
    char s[96];
    if (!strcmp(what, "start")) {
        capture_start();
    } else if (!strcmp(what, "stop")) {
        capture_stop();
    } else if (!strcmp(what, "dump")) {
        capture_stop();
        char who[48];
        snprintf(who, sizeof who, "%s, firmware %s", board_name(), GPIBRIDGE_VERSION);
        capture_vcd(capture_entries(), capture_count(), CAPTURE_TICKS_PER_US, 10, who, host_text);
        gpib_flush_host();
        return;
    } else if (strcmp(what, "status")) {
        host_line("++t capture start | stop | status | dump");
        return;
    }
    snprintf(s, sizeof s, "{\"capture\":\"%s\",\"changes\":%lu}", capture_state(), (unsigned long)capture_count());
    host_line(s);
}

static int host_peek(void)
{
    uint8_t c;
    return tud_cdc_n_peek(CDC_GPIB, &c) ? c : -1;
}

static void host_drop(void)
{
    uint8_t c;
    tud_cdc_n_read(CDC_GPIB, &c, 1);
}

static bool must_stop(void) { return reboot_asked; }

static const prologix_io io = {
    .write = gpib_write_host,
    .flush = gpib_flush_host,
    .save = settings_save,
    .reboot = do_reboot,
    .log = log_json,
    .status_extra = status_extra,
    .capture = capture_command,
    .info = info,
    .identify = identify,
    .crash = crash,
    .host_peek = host_peek,
    .host_drop = host_drop,
    .must_stop = must_stop,
};

/* the console's commands: one word a line */
static void console_command(char *cmd)
{
    char s[300], extra[128];
    if (!strcmp(cmd, "status")) {
        status_extra(extra, sizeof extra);
        snprintf(s, sizeof s,
                 "{\"version\":\"%s\",\"bus_power\":%d,\"srq\":%d,\"addr\":%d,"
                 "\"bytes_out\":%lu,\"bytes_in\":%lu,\"timeouts\":%lu,\"no_listener\":%lu,\"uptime_s\":%lu%s}",
                 GPIBRIDGE_VERSION, gpib_powered(), gpib_srq(), prologix_cfg.pad,
                 (unsigned long)gpib_count.bytes_out, (unsigned long)gpib_count.bytes_in,
                 (unsigned long)gpib_count.timeouts, (unsigned long)gpib_count.no_listener,
                 (unsigned long)(time_us_64() / 1000000), extra);
        console_line(s);
    } else if (!strcmp(cmd, "bootsel")) {
        do_reboot(true);
    } else if (!strcmp(cmd, "reboot")) {
        do_reboot(false);
    } else if (!strcmp(cmd, "power on")) {
        bus_start();
    } else if (!strcmp(cmd, "power off")) {
        gpib_stop();
        console_line("{\"event\":\"bus_power\",\"on\":false}");
    } else if (cmd[0]) {
        console_line("{\"help\":\"status | power on | power off | reboot | bootsel\"}");
    }
}

static void console_poll(void)
{
    static char line[64];
    static size_t n;
    while (tud_cdc_n_available(CDC_CONSOLE)) {
        int c = tud_cdc_n_read_char(CDC_CONSOLE);
        if (c == '\r' || c == '\n') {
            line[n] = 0;
            console_command(line);
            n = 0;
        } else if (n < sizeof line - 1) {
            line[n++] = (char)c;
        }
    }
}

/* On the bus as its controller, unless another controller is running it: then
 * off again, the red LED lit, and the reason on the log. */
static void bus_start(void)
{
    if (gpib_start(false)) {
        console_line("{\"event\":\"bus_power\",\"on\":true}");
        return;
    }
    error_at = time_us_64();
    if (!hal_board_known()) {
        console_line("{\"event\":\"bus\",\"error\":\"R21 (DC) read neither high nor low: which board is not "
                     "known, so staying off the bus (REVB.md 1.8)\"}");
        return;
    }
    console_line("{\"event\":\"bus\",\"error\":\"another controller holds ATN, REN or IFC: staying off the bus "
                 "(++t power 2 takes it regardless)\"}");
}

/* The transceivers draw up to 220 mA (110 mA each, datasheets): more than the
 * 100 mA a USB device may take before the host configures it.  So their 5 V
 * goes on when the host configures us, and off when it lets go or suspends. */
void tud_mount_cb(void)
{
    if (!usb_ready_us)
        usb_ready_us = time_us_64();     /* from reset: how long the start took */
    if (prologix_cfg.manual_start) {     /* ++t autostart 0: the host says when */
        console_line("{\"event\":\"usb\",\"configured\":true,\"bus_power\":\"waits for ++t power 1\"}");
        return;
    }
    bus_start();
}

void tud_umount_cb(void) { gpib_stop(); }

void tud_suspend_cb(bool remote_wakeup_en)
{
    (void)remote_wakeup_en;
    gpib_stop();
}

void tud_resume_cb(void)
{
    if (tud_mounted() && !prologix_cfg.manual_start)
        bus_start();
}

/* the console port at 1200 baud: the Arduino habit for "go to BOOTSEL" */
void tud_cdc_line_coding_cb(uint8_t itf, cdc_line_coding_t const *coding)
{
    if (itf == CDC_CONSOLE && coding->bit_rate == 1200)
        do_reboot(true);
}

/* ---- LEDs ----------------------------------------------------------------- */
static void leds(void)
{
    uint64_t t = time_us_64();
    bool usb;
    if (t < identify_until) {            /* ++t identify: yellow and red, turn about, 4 a second */
        bool phase = (t / 125000) & 1;
        gpio_put(PIN_LED_USB, phase);
        gpio_put(PIN_LED_ERR, !phase);
        return;
    }
    if (!tud_mounted())
        usb = (t / 250000) & 1;          /* blink: waiting for the host */
    else
        usb = t - traffic_at > 50000;    /* on, off for a moment on traffic */
    gpio_put(PIN_LED_USB, usb);
    gpio_put(PIN_LED_ERR, !hal_board_known() || (error_at && t - error_at < 1000000));   /* steady: R21 not read */
}

/* ---- start -------------------------------------------------------------------- */
int main(void)
{
    /* three watchdog resets in a row: something in this image crashes; go to
     * BOOTSEL so the next image can be loaded over USB */
    boot_reason = watchdog_hw->reason;
    boot_scratch4 = watchdog_hw->scratch[4];
    if (watchdog_enable_caused_reboot()) {
        crashed_before = true;
        if (++watchdog_hw->scratch[0] >= CRASHES_TO_BOOTSEL) {
            watchdog_hw->scratch[0] = 0;
            rom_reset_usb_boot_extra(-1, 0, false);
        }
    } else {
        watchdog_hw->scratch[0] = 0;
    }
    stdio_init_all();                    /* printf to UART0, the debug connector */
    capture_init();                      /* core 1, asleep: flash_safe_execute can then lock it out */
    gpio_init(PIN_LED_USB);
    gpio_set_dir(PIN_LED_USB, GPIO_OUT);
    gpio_init(PIN_LED_ERR);
    gpio_set_dir(PIN_LED_ERR, GPIO_OUT);

    prologix_init(&io, settings_load());
    gpib_stop();                         /* pins released, transceivers off until USB is configured */
    usb_descriptors_init(prologix_cfg.console_port);
    tusb_init();
    watchdog_enable(WATCHDOG_MS, true);
    watching = true;                     /* before this, usb_poll() runs with no watchdog of ours */
    printf("{\"event\":\"boot\",\"version\":\"%s\",\"board\":\"%s\",\"at_ms\":%lu}\n", GPIBRIDGE_VERSION,
           board_name(), (unsigned long)(time_us_64() / 1000));

    uint64_t started = time_us_64();
    uint8_t buf[64];
    for (;;) {
        usb_poll();
        if (tud_cdc_n_available(CDC_GPIB)) {
            uint32_t n = tud_cdc_n_read(CDC_GPIB, buf, sizeof buf);
            traffic_at = time_us_64();
            prologix_input(buf, n);
        }
        if (reboot_asked)
            do_reboot(false);            /* picotool reboot -f -a, seen in usb_poll() */
        console_poll();
        settings_poll();
        leds();
        if (watchdog_hw->scratch[0] && time_us_64() - started > 10000000)
            watchdog_hw->scratch[0] = 0;     /* ran ten seconds: this image is fine */
    }
}
