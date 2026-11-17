/* sim_bus.c: gpib_hal.h on the host, with a simulated IEEE-488 bus and one
 * instrument on it, so gpib.c and prologix.c run unchanged against something
 * that answers.  Every hal_get() lets the instrument take a step, and the
 * clock advances a microsecond, so every timeout in gpib.c is exercised.
 *
 * The instrument (address SIM_ADDR) is an IEEE 488.2-ish source and sink:
 *   - it acceptor-handshakes every command byte while ATN is asserted, and
 *     data bytes while addressed to listen;
 *   - a message ending in LF or EOI is a "program message": a query (ending
 *     in '?') queues its answer, anything else is stored;
 *   - addressed to talk with an answer queued, it source-handshakes it, EOI
 *     on the last byte;
 *   - SDC clears it; serial poll returns sim_status, and sim_srq holds SRQ
 *     asserted until then.
 *
 * It answers enough of an HP 33120A's SCPI (scpi(), below) for
 * lab-instrument-control's driver to run against it: APPLy and its limits,
 * the error queue, and a binary arbitrary-waveform upload, whose block may
 * hold any byte, so the message ends at the block's length or at EOI, not at
 * a line feed inside it.
 */
#include "sim_bus.h"
#include "../src/gpib.h"
#include "../src/gpib_hal.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

/* what each side drives: index L_xxx, true = asserted */
static bool ctl[L_COUNT], dev[L_COUNT];
static uint8_t ctl_data, dev_data;
static bool powered;

/* the instrument */
int sim_addr = SIM_ADDR;
bool sim_present = true;
uint8_t sim_status = 0x40;
char sim_last_message[256];
int sim_sdc_count, sim_get_count, sim_gtl_count;
bool sim_srq;
unsigned long sim_bytes_in, sim_sum_in;  /* every data byte it took, and their sum */
bool sim_last_eoi;                       /* the last message ended with EOI */
static enum { IDLE, LISTEN, TALK } role;
static bool spoll_mode, spoll_pending;
static char inbuf[40000];                /* a 16,000-point waveform is 32 kB */
static size_t inlen, block_end;
static char outbuf[320];
static size_t outlen, outpos;
static enum { A_READY, A_WAIT_DAV_OFF } acc;
static enum { S_IDLE, S_WAIT_NRFD, S_WAIT_NDAC, S_WAIT_NDAC_ON } src;

static bool line(gpib_line l) { return ctl[l] || dev[l]; }
static uint8_t data(void) { return ctl_data | dev_data; }

/* ---- a little of an HP 33120A --------------------------------------------- */
static struct {
    char func[8];
    double freq, vpp, offset, load, duty;
    int points;
    double average;
    char errors[4][48];
    int n_errors;
} gen;

static void gen_reset(void)
{
    memset(&gen, 0, sizeof gen);
    strcpy(gen.func, "SIN");
    gen.freq = 1000;
    gen.vpp = 0.1;
    gen.load = 50;
    gen.duty = 50;
}

static void gen_error(const char *e)
{
    if (gen.n_errors < 4)
        snprintf(gen.errors[gen.n_errors++], sizeof gen.errors[0], "%s", e);
}

/* Does msg start with the SCPI header `pat` ("SYSTem:ERRor?": capitals are
 * the short form)?  Returns what follows it, or NULL. */
static const char *scpi_is(const char *msg, const char *pat)
{
    for (;;) {
        size_t full = strcspn(pat, ":? "), brief = 0, got = 0;
        while (brief < full && !islower((unsigned char)pat[brief]))
            brief++;
        while (isalnum((unsigned char)msg[got]) || msg[got] == '*')
            got++;
        if ((got != full && got != brief) || strncasecmp(msg, pat, got))
            return NULL;
        msg += got;
        pat += full;
        if (*pat == ':') {
            if (*msg != ':')
                return NULL;
            msg++;
            pat++;
            continue;
        }
        if (*pat == '?') {
            if (*msg != '?')
                return NULL;
            msg++;
        } else if (*msg == '?' || *msg == ':') {
            return NULL;
        }
        while (*msg == ' ')
            msg++;
        return msg;
    }
}

static const char *scpi(const char *msg, size_t len)
{
    static char a[96];
    static const struct { const char *pat, *name; double top; } shape[] = {
        {"APPLy:SINusoid", "SIN", 15e6}, {"APPLy:SQUare", "SQU", 15e6}, {"APPLy:TRIangle", "TRI", 100e3},
        {"APPLy:RAMP", "RAMP", 100e3}, {"APPLy:NOISe", "NOIS", 0}, {"APPLy:DC", "DC", 0}, {"APPLy:USER", "USER", 5e6},
    };
    const char *r;
    if (scpi_is(msg, "*IDN?"))
        return "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0";
    if (scpi_is(msg, "*OPC?"))
        return "1";
    if (scpi_is(msg, "VOLT?"))
        return "+1.00000E+00";
    if (scpi_is(msg, "SYSTem:ERRor?")) {
        if (!gen.n_errors)
            return "+0,\"No error\"";
        snprintf(a, sizeof a, "%s", gen.errors[0]);
        memmove(gen.errors[0], gen.errors[1], sizeof gen.errors[0] * 3);
        gen.n_errors--;
        return a;
    }
    if (scpi_is(msg, "APPLy?")) {
        snprintf(a, sizeof a, "\"%s %.12E,%+.6E,%+.6E\"", gen.func, gen.freq, gen.vpp, gen.offset);
        return a;
    }
    for (size_t i = 0; i < sizeof shape / sizeof shape[0]; i++)
        if ((r = scpi_is(msg, shape[i].pat))) {
            char f[24] = "DEF", v[24] = "DEF", o[24] = "0";
            sscanf(r, "%23[^,],%23[^,],%23s", f, v, o);
            double freq = strcmp(f, "DEF") ? atof(f) : gen.freq, vpp = strcmp(v, "DEF") ? atof(v) : gen.vpp;
            if (shape[i].top && freq > shape[i].top) {
                gen_error("-222,\"Data out of range\"");
                freq = shape[i].top;
            }
            strcpy(gen.func, shape[i].name);
            gen.freq = freq;
            gen.vpp = vpp;
            gen.offset = atof(o);
            return NULL;
        }
    if (scpi_is(msg, "OUTPut:LOAD?")) {
        snprintf(a, sizeof a, "%+.5E", gen.load);
        return a;
    }
    if ((r = scpi_is(msg, "OUTPut:LOAD"))) {
        gen.load = !strncasecmp(r, "INF", 3) ? 9.9e37 : atof(r);
        return NULL;
    }
    if (scpi_is(msg, "PULSe:DCYCle?")) {
        snprintf(a, sizeof a, "%+.5E", gen.duty);
        return a;
    }
    if ((r = scpi_is(msg, "PULSe:DCYCle"))) {
        gen.duty = atof(r);
        return NULL;
    }
    if ((r = scpi_is(msg, "DATA:DAC"))) {
        /* VOLATILE, #<digits><bytes><16-bit points, least significant byte first> */
        const char *h = memchr(r, '#', len - (size_t)(r - msg));
        if (!h || !isdigit((unsigned char)h[1])) {
            gen_error("-161,\"Invalid block data\"");
            return NULL;
        }
        int nd = h[1] - '0';
        char digits[10] = "";
        memcpy(digits, h + 2, (size_t)nd);
        long bytes = atol(digits);
        const unsigned char *d = (const unsigned char *)h + 2 + nd;
        if (d + bytes > (const unsigned char *)msg + len) {
            gen_error("-161,\"Invalid block data\"");
            return NULL;
        }
        double sum = 0;
        for (long i = 0; i + 1 < bytes; i += 2)
            sum += (int16_t)(d[i] | d[i + 1] << 8);
        gen.points = (int)(bytes / 2);
        gen.average = gen.points ? sum / gen.points / 2047.0 : 0;
        return NULL;
    }
    if (scpi_is(msg, "DATA:ATTRibute:POINts?")) {
        snprintf(a, sizeof a, "+%d", gen.points);
        return a;
    }
    if (scpi_is(msg, "DATA:ATTRibute:AVERage?")) {
        snprintf(a, sizeof a, "%+.6E", gen.average);
        return a;
    }
    if (scpi_is(msg, "VOLTage:UNIT") || scpi_is(msg, "FORMat:BORDer") || scpi_is(msg, "FUNCtion:USER")
        || scpi_is(msg, "OUTPut:SYNC") || scpi_is(msg, "DISPlay:TEXT") || scpi_is(msg, "DISPlay:TEXT:CLEar"))
        return NULL;
    return msg;                          /* not one of the 33120A's: as before, kept for ECHO? */
}

static void answer(const char *msg, size_t len)
{
    const char *a;
    static char buf[sizeof sim_last_message];
    if (!strcmp(msg, "ECHO?")) {
        snprintf(buf, sizeof buf, "%s", sim_last_message);
        a = buf;
    } else {
        a = scpi(msg, len);
        if (a == msg) {                  /* nothing it knows: a query goes unanswered */
            a = NULL;
            if (msg[0])
                snprintf(sim_last_message, sizeof sim_last_message, "%.255s", msg);
        } else if (!a && msg[0]) {
            snprintf(sim_last_message, sizeof sim_last_message, "%.255s", msg);
        }
    }
    if (a) {
        snprintf(outbuf, sizeof outbuf, "%s\n", a);
        outlen = strlen(outbuf);
        outpos = 0;
    }
}

static void command_byte(uint8_t b)
{
    uint8_t m = b & 0x7f;
    if (m == GPIB_UNL) {
        if (role == LISTEN)
            role = IDLE;
    } else if (m == GPIB_UNT) {
        if (role == TALK)
            role = IDLE;
    } else if ((m & 0x60) == GPIB_LAD) {
        if ((m & 0x1f) == sim_addr)
            role = LISTEN;
    } else if ((m & 0x60) == GPIB_TAD) {
        if ((m & 0x1f) == sim_addr)
            role = TALK;
        else if (role == TALK)
            role = IDLE;                 /* another talker addressed: we stop */
    } else if (m == GPIB_SPE) {
        spoll_mode = true;
    } else if (m == GPIB_SPD) {
        spoll_mode = false;
    } else if (m == GPIB_SDC && role == LISTEN) {
        sim_sdc_count++;
        inlen = outlen = outpos = block_end = 0;
    } else if (m == GPIB_GET && role == LISTEN) {
        sim_get_count++;
    } else if (m == GPIB_GTL && role == LISTEN) {
        sim_gtl_count++;
    }
    if (spoll_mode && role == TALK)
        spoll_pending = true;
}

static void data_byte(uint8_t b, bool eoi)
{
    sim_bytes_in++;
    sim_sum_in += b;
    if (inlen < sizeof inbuf - 1)
        inbuf[inlen++] = (char)b;
    /* a DATA:DAC block may hold line feeds: inside it only its length (or EOI) ends the message */
    if (!block_end && b == '#' && inlen > 9 && !strncasecmp(inbuf, "DATA:DAC", 8))
        block_end = inlen;               /* the '#' is at block_end - 1; its length is not known yet */
    bool in_block = false;
    size_t block_total = 0;              /* where the block ends in inbuf, once its header is in */
    if (block_end) {
        size_t have = inlen - block_end; /* bytes after the '#' */
        int nd = have ? inbuf[block_end] - '0' : -1;
        if (nd == -1 || (nd >= 1 && nd <= 9 && have < (size_t)(1 + nd))) {
            in_block = true;             /* still in its header */
        } else if (nd >= 1 && nd <= 9) {
            char digits[10] = "";
            memcpy(digits, inbuf + block_end + 1, (size_t)nd);
            block_total = block_end + 1 + (size_t)nd + (size_t)atol(digits);
            in_block = inlen <= block_total;     /* this byte is one of the block's */
        }
    }
    if ((b == '\n' && !in_block) || eoi) {
        sim_last_eoi = eoi;
        size_t n = inlen;
        while (n > block_total && (inbuf[n - 1] == '\n' || inbuf[n - 1] == '\r'))
            n--;
        inbuf[n] = 0;
        answer(inbuf, n);
        inlen = block_end = 0;
    }
}

/* one step of the instrument's acceptor and source handshakes */
static void step(void)
{
    if (!powered || !sim_present) {
        memset(dev, 0, sizeof dev);
        dev_data = 0;
        return;
    }
    dev[L_SRQ] = sim_srq;
    bool atn = line(L_ATN);
    bool accepting = atn || role == LISTEN;
    bool sourcing = !atn && role == TALK;
    if (accepting) {
        dev[L_DAV] = false;
        dev[L_EOI] = false;
        dev_data = 0;
        src = S_IDLE;
        if (acc == A_READY) {
            dev[L_NDAC] = true;
            if (line(L_DAV)) {
                dev[L_NRFD] = true;      /* not ready for more */
                uint8_t b = data();
                if (atn)
                    command_byte(b);
                else
                    data_byte(b, line(L_EOI));
                dev[L_NDAC] = false;     /* accepted */
                acc = A_WAIT_DAV_OFF;
            } else {
                dev[L_NRFD] = false;     /* ready */
            }
        } else if (!line(L_DAV)) {
            dev[L_NDAC] = true;
            acc = A_READY;
        }
        return;
    }
    acc = A_READY;
    dev[L_NRFD] = dev[L_NDAC] = false;   /* not a listener: out of the handshake */
    if (!sourcing) {
        dev[L_DAV] = dev[L_EOI] = false;
        dev_data = 0;
        src = S_IDLE;
        return;
    }
    switch (src) {
    case S_IDLE:
        if (spoll_pending || outpos < outlen)
            src = S_WAIT_NRFD;
        break;
    case S_WAIT_NRFD:
        if (!line(L_NRFD) && line(L_NDAC)) {
            if (spoll_pending) {
                dev_data = sim_status;
                dev[L_EOI] = false;
            } else {
                dev_data = (uint8_t)outbuf[outpos];
                dev[L_EOI] = outpos + 1 == outlen;
            }
            dev[L_DAV] = true;
            src = S_WAIT_NDAC;
        }
        break;
    case S_WAIT_NDAC:
        if (!line(L_NDAC)) {
            dev[L_DAV] = dev[L_EOI] = false;
            dev_data = 0;
            if (spoll_pending) {
                spoll_pending = false;
                sim_status &= (uint8_t)~0x40;    /* RQS clears when polled */
                sim_srq = false;                 /* and it lets go of SRQ */
            } else {
                outpos++;
            }
            src = S_WAIT_NDAC_ON;
        }
        break;
    case S_WAIT_NDAC_ON:
        if (line(L_NDAC))
            src = S_IDLE;
        break;
    }
}

#ifdef SIM_NO_HAL
/* test_wire.c has its own model of the board's wires: it says what our side
 * asserts on the bus, the instrument takes a step, and what the instrument
 * asserts comes back */
void sim_wire_step(const bool our[L_COUNT], uint8_t our_data, bool bus_powered, bool out[L_COUNT],
                   uint8_t *out_data)
{
    memcpy(ctl, our, sizeof ctl);
    ctl_data = our_data;
    powered = bus_powered;
    step();
    memcpy(out, dev, sizeof dev);
    *out_data = dev_data;
}
#else
/* ---- gpib_hal.h ------------------------------------------------------------- */
static bool controller, talking;
static uint64_t now;
bool sim_lite;

bool hal_lite(void) { return sim_lite; }

void hal_init(void)
{
    memset(ctl, 0, sizeof ctl);
    ctl_data = 0;
    powered = controller = talking = false;
}
void hal_power(bool on) { powered = on; }
void hal_controller(bool on) { controller = on; }
void hal_talk(bool on)
{
    talking = on;
    if (on) {
        ctl[L_NRFD] = ctl[L_NDAC] = false;
    } else {
        ctl[L_DAV] = ctl[L_EOI] = false;
        ctl_data = 0;
        ctl[L_NRFD] = ctl[L_NDAC] = true;
    }
}
void hal_totem(bool on) { (void)on; }
void hal_set(gpib_line l, bool asserted)
{
    ctl[l] = asserted;
    step();
}
bool hal_get(gpib_line l)
{
    now++;
    step();
    return line(l) || (l == L_REN && sim_other_controller);
}
void hal_data_out(uint8_t b) { ctl_data = b; }
uint8_t hal_data_in(void) { return data(); }
void hal_data_release(void) { ctl_data = 0; }
/* "++t raw" on the abstract bus: the same roles, no pins.  test_wire.c runs
 * the real ones against the transceivers' tables. */
static raw_role raw;
static uint16_t raw_set;
#define RAW_HS (RAW_BIT(L_NRFD) | RAW_BIT(L_NDAC))
#define RAW_MAN (RAW_BIT(L_ATN) | RAW_BIT(L_REN) | RAW_BIT(L_IFC))
uint16_t hal_raw_drives(void)
{
    static const uint16_t d[RAW_ROLES] = {
        [RAW_DEV_LISTEN] = RAW_HS | RAW_BIT(L_SRQ), [RAW_DEV_TALK] = RAW_DATA | RAW_BIT(L_DAV) | RAW_BIT(L_SRQ),
        [RAW_CTRL_LISTEN] = RAW_HS | RAW_MAN, [RAW_CTRL_TALK] = RAW_DATA | RAW_BIT(L_DAV) | RAW_BIT(L_EOI) | RAW_MAN,
    };
    return sim_lite ? 0xffff : d[raw];
}
uint16_t hal_raw_reads(void) { return sim_lite ? 0xffff : (uint16_t)~hal_raw_drives() & (uint16_t)~(raw == RAW_DEV_TALK || raw == RAW_CTRL_LISTEN ? RAW_BIT(L_EOI) : 0); }
void hal_raw_set(uint16_t asserted)
{
    raw_set = asserted & hal_raw_drives();
    for (int l = 0; l < L_COUNT; l++)
        ctl[l] = raw_set >> (8 + l) & 1;
    ctl_data = (uint8_t)raw_set;
    step();
}
void hal_raw_role(raw_role r)
{
    raw = r;
    hal_raw_set(0);
}
void hal_raw_end(void) { hal_raw_role(RAW_DEV_LISTEN); }
bool sim_other_controller;               /* somebody else holds REN */
uint16_t hal_raw_get(int pull_)
{
    (void)pull_;
    step();
    uint16_t v = data();
    for (int l = 0; l < L_COUNT; l++)
        if (line(l))
            v |= (uint16_t)RAW_BIT(l);
    return powered ? v : 0xffff;
}
uint64_t hal_us(void) { return now; }
void hal_delay_us(uint32_t us)
{
    now += us;
    step();
}
void hal_idle(void) {}
#endif

void sim_reset(void)
{
    role = IDLE;
    spoll_mode = spoll_pending = false;
    inlen = outlen = outpos = block_end = 0;
    acc = A_READY;
    src = S_IDLE;
    sim_status = 0x40;
    sim_srq = false;
    sim_bytes_in = sim_sum_in = 0;
    gen_reset();
    sim_last_message[0] = 0;
    sim_sdc_count = sim_get_count = sim_gtl_count = 0;
    sim_present = true;
    sim_addr = SIM_ADDR;
}

bool sim_ren(void) { return line(L_REN); }
