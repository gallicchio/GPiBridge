/* main.c: GPiBridge's firmware on the RP2354A.
 *
 *   USB serial "GPiBridge GPIB"     the Prologix "++" controller (prologix.c)
 *   USB serial "GPiBridge console"  optional (++t console 1): JSON lines,
 *                                   logs out, a few commands in; the same
 *                                   lines always go out on the UART (J4)
 *   USB reset interface              `picotool reboot -u -f` reaches BOOTSEL
 *   core 1                           the bus capture, when asked (capture.h)
 *
 * Failsafes:
 *   - the transceivers are switched on only after every pin is released,
 *     and only once the host has configured us (they draw more than the
 *     100 mA an unconfigured USB device may);
 *   - every wait on the bus has a timeout, and a watchdog catches the rest;
 *   - three watchdog resets in a row reboot into BOOTSEL, so a bad image
 *     can always be replaced over USB, with nobody pressing BOOT.
 *
 * LEDs: yellow (USB) blinks until the host has configured us, then stays on
 * and blinks off on traffic; red (ERR) lights for a second after a bus error;
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
#include "hardware/flash.h"
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
    if (flash_safe_execute(settings_write_now, NULL, 100) == PICO_OK)
        console_line("{\"event\":\"settings\",\"saved\":true}");
    else
        console_line("{\"event\":\"settings\",\"error\":\"flash busy\"}");
}

static void settings_poll(void)
{
    if (dirty && time_us_64() - dirty_at > 2000000)
        settings_flush();
}

/* ---- USB -------------------------------------------------------------------- */
static uint64_t traffic_at, error_at, usb_ready_us;

void usb_poll(void)
{
    tud_task();
    watchdog_update();
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

static const char *board_name(void) { return hal_lite() ? "GPiBridge Lite " GPIBRIDGE_BOARD : "GPiBridge " GPIBRIDGE_BOARD; }

/* the fields ++t status and the console's status add to the bus counters */
static void status_extra(char *json, size_t n)
{
    snprintf(json, n, ",\"board\":\"%s\",\"usb_ready_ms\":%lu,\"console\":%d,\"capture\":\"%s\",\"changes\":%lu",
             board_name(), (unsigned long)(usb_ready_us / 1000), prologix_cfg.console_port, capture_state(),
             (unsigned long)capture_count());
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

static const prologix_io io = {
    .write = gpib_write_host,
    .flush = gpib_flush_host,
    .save = settings_save,
    .reboot = do_reboot,
    .log = log_json,
    .status_extra = status_extra,
    .capture = capture_command,
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
        gpib_start();
        console_line("{\"event\":\"bus_power\",\"on\":true}");
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

/* The transceivers draw up to 220 mA (110 mA each, datasheets): more than the
 * 100 mA a USB device may take before the host configures it.  So their 5 V
 * goes on when the host configures us, and off when it lets go or suspends. */
void tud_mount_cb(void)
{
    if (!usb_ready_us)
        usb_ready_us = time_us_64();     /* from reset: how long the start took */
    gpib_start();
    console_line("{\"event\":\"bus_power\",\"on\":true}");
}

void tud_umount_cb(void) { gpib_stop(); }

void tud_suspend_cb(bool remote_wakeup_en)
{
    (void)remote_wakeup_en;
    gpib_stop();
}

void tud_resume_cb(void)
{
    if (tud_mounted())
        gpib_start();
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
    if (!tud_mounted())
        usb = (t / 250000) & 1;          /* blink: waiting for the host */
    else
        usb = t - traffic_at > 50000;    /* on, off for a moment on traffic */
    gpio_put(PIN_LED_USB, usb);
    gpio_put(PIN_LED_ERR, error_at && t - error_at < 1000000);
}

/* ---- start -------------------------------------------------------------------- */
int main(void)
{
    /* three watchdog resets in a row: something in this image crashes; go to
     * BOOTSEL so the next image can be loaded over USB */
    if (watchdog_caused_reboot()) {
        if (++watchdog_hw->scratch[0] >= CRASHES_TO_BOOTSEL) {
            watchdog_hw->scratch[0] = 0;
            rom_reset_usb_boot_extra(-1, 0, false);
        }
    } else {
        watchdog_hw->scratch[0] = 0;
    }
    stdio_init_all();                    /* printf to UART0, the debug connector */
    gpio_init(PIN_LED_USB);
    gpio_set_dir(PIN_LED_USB, GPIO_OUT);
    gpio_init(PIN_LED_ERR);
    gpio_set_dir(PIN_LED_ERR, GPIO_OUT);

    prologix_init(&io, settings_load());
    gpib_stop();                         /* pins released, transceivers off until USB is configured */
    usb_descriptors_init(prologix_cfg.console_port);
    tusb_init();
    watchdog_enable(2000, true);
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
        console_poll();
        settings_poll();
        leds();
        if (watchdog_hw->scratch[0] && time_us_64() - started > 10000000)
            watchdog_hw->scratch[0] = 0;     /* ran ten seconds: this image is fine */
    }
}
