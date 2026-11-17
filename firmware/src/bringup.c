/* bringup.c: the board as sixteen wires.  See bringup.h. */
#include "bringup.h"
#include "gpib.h"
#include "gpib_hal.h"
#include <stdlib.h>
#include <string.h>

static const char *const role_name[RAW_ROLES] = {
    [RAW_DEV_LISTEN] = "dev_listen", [RAW_DEV_TALK] = "dev_talk",
    [RAW_CTRL_LISTEN] = "ctrl_listen", [RAW_CTRL_TALK] = "ctrl_talk",
};
static const char *const line_name[16] = {
    "DIO1", "DIO2", "DIO3", "DIO4", "DIO5", "DIO6", "DIO7", "DIO8",
    [8 + L_EOI] = "EOI", [8 + L_DAV] = "DAV", [8 + L_NRFD] = "NRFD", [8 + L_NDAC] = "NDAC",
    [8 + L_IFC] = "IFC", [8 + L_REN] = "REN", [8 + L_ATN] = "ATN", [8 + L_SRQ] = "SRQ",
};

static raw_role role;
static uint16_t set;                     /* what "raw set" last asserted */
static bool pe = true;

/* the names of the lines in a mask: "DAV NRFD" */
static const char *names(uint16_t mask)
{
    static char s[16 * 5 + 1];
    s[0] = 0;
    for (unsigned bit = 0; bit < 16; bit++)
        if (mask >> bit & 1) {
            if (s[0])
                strcat(s, " ");
            strcat(s, line_name[bit]);
        }
    return s;
}

static void enter(raw_role r)
{
    gpib_raw(r);
    hal_totem(pe);
    role = r;
    set = 0;
}

static void where(void (*say)(const char *fmt, ...), int pull)
{
    if (!gpib_is_raw()) {
        say("{\"raw\":\"off\",\"power\":%d}", gpib_powered());
        return;
    }
    uint16_t lines = hal_raw_get(pull);
    say("{\"raw\":\"%s\",\"drives\":\"0x%04x\",\"reads\":\"0x%04x\",\"set\":\"0x%04x\",\"lines\":\"0x%04x\","
        "\"pe\":%d,\"names\":\"%s\"}",
        role_name[role], hal_raw_drives(), hal_raw_reads(), set, lines, pe, names(lines));
}

static void raw_command(int argc, char **argv, void (*say)(const char *fmt, ...))
{
    const char *what = argc > 1 ? argv[1] : "";
    if (!what[0]) {
        where(say, 0);
        return;
    }
    if (!strcmp(what, "off")) {
        gpib_stop();
        where(say, 0);
        return;
    }
    for (int r = 0; r < RAW_ROLES; r++)
        if (!strcmp(what, role_name[r])) {
            enter((raw_role)r);
            where(say, 0);
            return;
        }
    if (!gpib_is_raw()) {
        say("{\"raw\":\"off\",\"error\":\"first a role: ++t raw dev_listen | dev_talk | ctrl_listen | ctrl_talk\"}");
        return;
    }
    if (!strcmp(what, "set") && argc > 2) {
        char *end;
        unsigned long m = strtoul(argv[2], &end, 0);
        if (end == argv[2] || *end || m > 0xffff) {
            say("{\"raw\":\"%s\",\"error\":\"a mask: 0x0000 to 0xffff\"}", role_name[role]);
        } else if (m & ~hal_raw_drives()) {
            say("{\"raw\":\"%s\",\"error\":\"not driven in this role: %s\"}", role_name[role],
                names((uint16_t)(m & ~hal_raw_drives())));
        } else {
            set = (uint16_t)m;
            hal_raw_set(set);
            where(say, 0);
        }
    } else if (!strcmp(what, "get")) {
        const char *p = argc > 2 ? argv[2] : "";
        where(say, !strcmp(p, "up") ? +1 : !strcmp(p, "down") ? -1 : 0);
    } else if (!strcmp(what, "pe") && argc > 2 && (argv[2][0] == '0' || argv[2][0] == '1') && !argv[2][1]) {
        pe = argv[2][0] == '1';
        hal_totem(pe);
        where(say, 0);
    } else {
        say("{\"raw\":\"%s\",\"error\":\"++t raw ROLE | set 0xMASK | get [up|down] | pe 0|1 | off\"}", role_name[role]);
    }
}

/* With nothing on the GPIB side.  GPiBridge: the transceivers' bus pins rest
 * on their own terminations, so every receive path must read "released"
 * whatever the pad's pull says (a pin that follows the pull is an open joint
 * or a dead channel), and with the 5 V off every pin must fall to its
 * pull-down (a pin that stays high says the switch never opened).  The Lite:
 * every pin follows the pulls, and asserting one line moves that line only. */
static void selftest(void (*say)(const char *fmt, ...), const char *board)
{
    bool was_on = gpib_powered(), was_raw = gpib_is_raw();
    raw_role was_role = role;
    bool ok = true;

    gpib_stop();
    if (hal_lite()) {
        enter(RAW_DEV_LISTEN);
        uint16_t up = hal_raw_get(+1), down = hal_raw_get(-1), bad = 0;
        for (unsigned bit = 0; bit < 16; bit++) {
            hal_raw_set((uint16_t)(1u << bit));
            uint16_t got = hal_raw_get(+1);
            hal_raw_set(0);
            if (got != (uint16_t)(1u << bit)) {
                bad |= (uint16_t)(1u << bit);
                say("{\"selftest\":\"walk\",\"line\":\"%s\",\"asserted\":\"0x%04x\",\"read\":\"0x%04x\"}",
                    line_name[bit], 1u << bit, got);
            }
        }
        say("{\"selftest\":\"float\",\"up\":\"0x%04x\",\"down\":\"0x%04x\"}", up, down);
        say("{\"selftest\":\"walk\",\"bad\":\"0x%04x\",\"names\":\"%s\"}", bad, names(bad));
        ok = !up && !bad;
    } else {
        uint16_t off = hal_raw_get(-1);      /* unpowered, on the pull-downs */
        say("{\"selftest\":\"off\",\"down\":\"0x%04x\"}", off);
        if (off != 0xffff)
            ok = false;
        for (int r = 0; r < RAW_ROLES; r++) {
            enter((raw_role)r);
            uint16_t reads = hal_raw_reads(), up = hal_raw_get(+1), down = hal_raw_get(-1);
            say("{\"selftest\":\"%s\",\"reads\":\"0x%04x\",\"up\":\"0x%04x\",\"down\":\"0x%04x\"}", role_name[r],
                reads, up, down);
            if ((up | down) & reads)
                ok = false;
        }
    }
    gpib_stop();
    if (was_raw)
        enter(was_role);
    else if (was_on)
        gpib_start(true);                /* we were the controller a moment ago: no need to look */
    say("{\"selftest\":\"done\",\"board\":\"%s\",\"ok\":%s}", board, ok ? "true" : "false");
}

void bringup_command(int argc, char **argv, void (*say)(const char *fmt, ...), const char *board)
{
    if (!strcmp(argv[0], "raw")) {
        raw_command(argc, argv, say);
    } else if (!strcmp(argv[0], "selftest")) {
        selftest(say, board);
    } else {                             /* "lines": whoever has the bus, as the pins read it */
        if (!gpib_powered()) {
            say("{\"lines\":null,\"bus\":\"off\"}");
            return;
        }
        uint16_t lines = hal_raw_get(0);
        say("{\"lines\":\"0x%04x\",\"bus\":\"%s\",\"names\":\"%s\"}", lines,
            gpib_is_raw() ? role_name[role] : "controller", names(lines));
    }
}
