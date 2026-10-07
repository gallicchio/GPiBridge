/* prologix.c: the "++" command set over gpib.c.  See prologix.h. */
#include "prologix.h"
#include "gpib.h"
#include "gpib_hal.h"
#include "version.h"
#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LINE_MAX 8192            /* a data line: a whole waveform upload fits */
#define WRITE_TIMEOUT_US 1000000 /* a listener that holds NRFD this long is not coming back */
#define ESC 27

prologix_config prologix_cfg;
static const prologix_io *io;
static bool savecfg = true;     /* not saved itself; on at every start (the manual) */
static bool trace;

/* the line being gathered */
static uint8_t line[LINE_MAX + 2];
static size_t len;
static bool esc, overflow, command;
static int leading_plus;

/* output to the host, in chunks */
static uint8_t obuf[64];
static size_t olen;

static void out_flush(void)
{
    if (olen) {
        io->write(obuf, olen);
        olen = 0;
    }
    if (io->flush)
        io->flush();
}

static void out_byte(uint8_t b)
{
    obuf[olen++] = b;
    if (olen == sizeof obuf) {
        io->write(obuf, olen);
        olen = 0;
    }
}

static void reply(const char *fmt, ...)
{
    char s[320];          /* ++t status with its extra fields is the longest */
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(s, sizeof s - 2, fmt, ap);
    va_end(ap);
    if (n < 0)
        return;
    if (n > (int)sizeof s - 3)
        n = sizeof s - 3;
    s[n++] = '\r';
    s[n++] = '\n';
    for (int i = 0; i < n; i++)
        out_byte((uint8_t)s[i]);
    out_flush();
}

static void note(const char *what, gpib_status s)
{
    char j[160];
    snprintf(j, sizeof j, "{\"event\":\"%s\",\"status\":\"%s\",\"addr\":%d}", what, gpib_status_name(s),
             prologix_cfg.pad);
    if (io->log && (trace || s != GPIB_OK))
        io->log(j);
}

void prologix_defaults(prologix_config *c)
{
    memset(c, 0, sizeof *c);
    c->pad = 1;
    c->sad = -1;
    c->autoread = false;
    c->eoi = true;
    c->eos = 0;
    c->eot_enable = false;
    c->eot_char = '\n';
    c->read_tmo_ms = 500;
}

static void changed(void)
{
    if (savecfg && io->save)
        io->save(&prologix_cfg);
}

void prologix_init(const prologix_io *i, const prologix_config *saved)
{
    io = i;
    prologix_defaults(&prologix_cfg);
    if (saved)
        prologix_cfg = *saved;
    len = 0;
    esc = overflow = command = false;
    leading_plus = 0;
}

/* ---------------------------------------------------------------------------- */
static void read_until(bool stop_eoi, int stop_char)
{
    gpib_timeout_us = (uint32_t)prologix_cfg.read_tmo_ms * 1000u;
    gpib_status s = gpib_listen_start(prologix_cfg.pad, prologix_cfg.sad);
    while (s == GPIB_OK) {
        uint8_t b;
        bool eoi;
        s = gpib_listen_byte(&b, &eoi);
        if (s != GPIB_OK)
            break;
        out_byte(b);
        if (eoi && prologix_cfg.eot_enable)
            out_byte(prologix_cfg.eot_char);
        if ((eoi && stop_eoi) || (stop_char >= 0 && b == stop_char))
            break;
    }
    out_flush();
    gpib_idle();
    /* a read that ends in a timeout is how "++read" (no argument) is meant to end */
    if (s != GPIB_OK && !(s == GPIB_TIMEOUT && !stop_eoi && stop_char < 0))
        note("read", s);
}

static void send_line(void)
{
    static const char *eos[] = {"\r\n", "\r", "\n", ""};
    size_t n = len;
    for (const char *e = eos[prologix_cfg.eos & 3]; *e; e++)
        line[n++] = (uint8_t)*e;
    gpib_timeout_us = WRITE_TIMEOUT_US;
    gpib_status s = gpib_send_to(prologix_cfg.pad, prologix_cfg.sad, line, n, prologix_cfg.eoi);
    if (s != GPIB_OK) {
        note("write", s);
        gpib_idle();
        return;
    }
    if (trace)
        note("write", s);
    if (prologix_cfg.autoread)
        read_until(true, -1);
    else
        gpib_idle();
}

/* ---------------------------------------------------------------------------- */
static int argc;
static char *argv[34];

static bool number(const char *s, int lo, int hi, int *v)
{
    char *end;
    long x = strtol(s, &end, 10);
    if (end == s || *end || x < lo || x > hi)
        return false;
    *v = (int)x;
    return true;
}

static bool flag_arg(bool *f)
{
    int v;
    if (argc < 2) {
        reply("%d", *f ? 1 : 0);
        return false;
    }
    if (number(argv[1], 0, 1, &v)) {
        *f = v != 0;
        return true;
    }
    return false;
}

/* a (PAD [SAD]) pair from argv[i]; returns how many arguments it used */
static int pad_sad(int i, int *pad, int *sad)
{
    if (i >= argc || !number(argv[i], 0, 30, pad))
        return 0;
    if (i + 1 < argc && number(argv[i + 1], 96, 126, sad)) {
        *sad -= 96;
        return 2;
    }
    *sad = -1;
    return 1;
}

static void addressed_command(uint8_t msg)
{
    uint8_t cmd[4];
    size_t k = 0;
    cmd[k++] = GPIB_UNL;
    cmd[k++] = (uint8_t)(GPIB_LAD | prologix_cfg.pad);
    if (prologix_cfg.sad >= 0)
        cmd[k++] = (uint8_t)(GPIB_SAD | prologix_cfg.sad);
    cmd[k++] = msg;
    gpib_timeout_us = WRITE_TIMEOUT_US;
    gpib_status s = gpib_command(cmd, k);
    if (s != GPIB_OK)
        note("command", s);
    gpib_idle();
}

static void tether_command(void)
{
    const char *what = argc > 1 ? argv[1] : "help";
    int v;
    if (!strcmp(what, "status")) {
        char extra[128] = "";
        if (io->status_extra)
            io->status_extra(extra, sizeof extra);
        reply("{\"version\":\"%s\",\"bus_power\":%d,\"srq\":%d,\"addr\":%d,\"bytes_out\":%lu,\"bytes_in\":%lu,"
              "\"timeouts\":%lu,\"no_listener\":%lu%s}",
              GPIBRIDGE_VERSION, gpib_powered(), gpib_srq(), prologix_cfg.pad, (unsigned long)gpib_count.bytes_out,
              (unsigned long)gpib_count.bytes_in, (unsigned long)gpib_count.timeouts,
              (unsigned long)gpib_count.no_listener, extra);
    } else if (!strcmp(what, "console") && argc > 2 && number(argv[2], 0, 1, &v)) {
        /* the USB device changes shape: save, then reconnect with the new one */
        prologix_cfg.console_port = v;
        changed();
        reply("console port %s: reconnecting", v ? "on" : "off");
        out_flush();
        io->reboot(false);
    } else if (!strcmp(what, "capture")) {
        if (io->capture)
            io->capture(argc > 2 ? argv[2] : "status");
        else
            reply("no capture on this build");
    } else if (!strcmp(what, "power") && argc > 2 && number(argv[2], 0, 1, &v)) {
        if (v)
            gpib_start();
        else
            gpib_stop();
    } else if (!strcmp(what, "ren") && argc > 2 && number(argv[2], 0, 1, &v)) {
        gpib_ren(v);
    } else if (!strcmp(what, "compat") && argc > 2 && number(argv[2], 0, 1, &v)) {
        prologix_cfg.compat_ver = v;
        changed();
    } else if (!strcmp(what, "trace") && argc > 2 && number(argv[2], 0, 1, &v)) {
        trace = v;
    } else if (!strcmp(what, "bootsel")) {
        out_flush();
        io->reboot(true);
    } else {
        reply("++t status | power 0|1 | ren 0|1 | compat 0|1 | trace 0|1 | console 0|1 | "
              "capture start|stop|status|dump | bootsel");
    }
}

static void do_command(void)
{
    /* split "++word args" (the leading ++ already gone) at spaces */
    line[len] = 0;
    argc = 0;
    for (char *p = (char *)line; *p && argc < (int)(sizeof argv / sizeof argv[0]);) {
        while (*p == ' ' || *p == '\t')
            p++;
        if (!*p)
            break;
        argv[argc++] = p;
        while (*p && *p != ' ' && *p != '\t')
            p++;
        if (*p)
            *p++ = 0;
    }
    if (!argc)
        return;
    for (char *p = argv[0]; *p; p++)
        *p = (char)tolower((unsigned char)*p);
    const char *c = argv[0];
    int v, pad, sad;
    prologix_config *cfg = &prologix_cfg;

    if (!strcmp(c, "addr")) {
        if (argc == 1)
            cfg->sad >= 0 ? reply("%d %d", cfg->pad, cfg->sad + 96) : reply("%d", cfg->pad);
        else if (pad_sad(1, &pad, &sad)) {
            cfg->pad = (uint8_t)pad;
            cfg->sad = (int8_t)sad;
            changed();
        }
    } else if (!strcmp(c, "auto")) {
        if (flag_arg(&cfg->autoread))
            changed();
    } else if (!strcmp(c, "eoi")) {
        if (flag_arg(&cfg->eoi))
            changed();
    } else if (!strcmp(c, "eos")) {
        if (argc == 1)
            reply("%d", cfg->eos);
        else if (number(argv[1], 0, 3, &v)) {
            cfg->eos = (uint8_t)v;
            changed();
        }
    } else if (!strcmp(c, "eot_enable")) {
        if (flag_arg(&cfg->eot_enable))
            changed();
    } else if (!strcmp(c, "eot_char")) {
        if (argc == 1)
            reply("%d", cfg->eot_char);
        else if (number(argv[1], 0, 255, &v)) {
            cfg->eot_char = (uint8_t)v;
            changed();
        }
    } else if (!strcmp(c, "read_tmo_ms")) {
        if (argc == 1)
            reply("%d", cfg->read_tmo_ms);
        else if (number(argv[1], 1, 3000, &v)) {
            cfg->read_tmo_ms = (uint16_t)v;
            changed();
        }
    } else if (!strcmp(c, "read")) {
        if (argc == 1)
            read_until(false, -1);
        else if (!strcmp(argv[1], "eoi"))
            read_until(true, -1);
        else if (number(argv[1], 0, 255, &v))
            read_until(false, v);
    } else if (!strcmp(c, "spoll")) {
        if (!pad_sad(1, &pad, &sad)) {
            pad = cfg->pad;
            sad = cfg->sad;
        }
        uint8_t status = 0;
        gpib_timeout_us = (uint32_t)cfg->read_tmo_ms * 1000u;
        gpib_status s = gpib_serial_poll(pad, sad, &status);
        if (s == GPIB_OK)
            reply("%d", status);
        else
            note("spoll", s);
    } else if (!strcmp(c, "srq")) {
        reply("%d", gpib_srq() ? 1 : 0);
    } else if (!strcmp(c, "clr")) {
        addressed_command(GPIB_SDC);
    } else if (!strcmp(c, "loc")) {
        addressed_command(GPIB_GTL);
    } else if (!strcmp(c, "llo")) {
        addressed_command(GPIB_LLO);
    } else if (!strcmp(c, "trg")) {
        uint8_t cmd[2 + 2 * 15];
        size_t k = 0;
        cmd[k++] = GPIB_UNL;
        int i = 1, used;
        while ((used = pad_sad(i, &pad, &sad)) && k < sizeof cmd - 3) {
            cmd[k++] = (uint8_t)(GPIB_LAD | pad);
            if (sad >= 0)
                cmd[k++] = (uint8_t)(GPIB_SAD | sad);
            i += used;
        }
        if (k == 1) {
            cmd[k++] = (uint8_t)(GPIB_LAD | cfg->pad);
            if (cfg->sad >= 0)
                cmd[k++] = (uint8_t)(GPIB_SAD | cfg->sad);
        }
        cmd[k++] = GPIB_GET;
        gpib_timeout_us = WRITE_TIMEOUT_US;
        gpib_status s = gpib_command(cmd, k);
        if (s != GPIB_OK)
            note("trg", s);
        gpib_idle();
    } else if (!strcmp(c, "ifc")) {
        gpib_ifc();
    } else if (!strcmp(c, "mode")) {
        if (argc == 1)
            reply("1");
        else if (number(argv[1], 0, 1, &v) && v == 0 && io->log)
            io->log("{\"event\":\"mode\",\"error\":\"device mode is not supported; staying a controller\"}");
    } else if (!strcmp(c, "savecfg")) {
        if (flag_arg(&savecfg) && savecfg)
            changed();
    } else if (!strcmp(c, "rst")) {
        out_flush();
        io->reboot(false);
    } else if (!strcmp(c, "ver")) {
        if (cfg->compat_ver)
            reply("Prologix GPIB-USB Controller version 6.107");
        else
            reply("%s GPIB-USB controller version %s", hal_lite() ? "GPiBridge Lite" : "GPiBridge",
                  GPIBRIDGE_VERSION);
    } else if (!strcmp(c, "help")) {
        reply("++addr [pad [sad]] | ++auto [0|1] | ++clr | ++eoi [0|1] | ++eos [0-3] | ++eot_enable [0|1] | "
              "++eot_char [n] | ++ifc | ++llo | ++loc | ++mode | ++read [eoi|n] | ++read_tmo_ms [ms]");
        reply("++rst | ++savecfg [0|1] | ++spoll [pad [sad]] | ++srq | ++trg [pad ...] | ++ver | ++help | ++t help");
    } else if (!strcmp(c, "t")) {
        tether_command();
    } else if (!strcmp(c, "lon") || !strcmp(c, "status")) {
        if (io->log)
            io->log("{\"event\":\"command\",\"error\":\"device-mode command: not supported\"}");
    } else {
        reply("Unrecognized command");
    }
}

/* ---------------------------------------------------------------------------- */
static void end_of_line(void)
{
    if (overflow) {
        if (io->log)
            io->log("{\"event\":\"input\",\"error\":\"line too long: dropped\"}");
    } else if (command) {
        do_command();
    } else if (len) {
        send_line();
    }
    len = 0;
    esc = overflow = command = false;
    leading_plus = 0;
}

static void keep(uint8_t c)
{
    if (len < LINE_MAX)
        line[len++] = c;
    else
        overflow = true;
}

void prologix_input(const uint8_t *data, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        uint8_t c = data[i];
        if (esc) {                       /* the escaped byte, whatever it is */
            esc = false;
            keep(c);
            continue;
        }
        if (c == ESC) {
            esc = true;
        } else if (c == '\r' || c == '\n') {
            end_of_line();
        } else if (c == '+') {
            if (command) {
                keep(c);
            } else if (len == 0 && ++leading_plus == 2) {
                command = true;          /* an unescaped "++" starts the line */
            }
            /* any other unescaped '+' is dropped, as the manual says */
        } else {
            keep(c);
        }
    }
}
