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
 *   - SDC clears it; serial poll returns sim_status.
 */
#include "sim_bus.h"
#include "../src/gpib.h"
#include "../src/gpib_hal.h"
#include <stdio.h>
#include <string.h>

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
static enum { IDLE, LISTEN, TALK } role;
static bool spoll_mode, spoll_pending;
static char inbuf[256];
static size_t inlen;
static char outbuf[256];
static size_t outlen, outpos;
static enum { A_READY, A_WAIT_DAV_OFF } acc;
static enum { S_IDLE, S_WAIT_NRFD, S_WAIT_NDAC, S_WAIT_NDAC_ON } src;

static bool line(gpib_line l) { return ctl[l] || dev[l]; }
static uint8_t data(void) { return ctl_data | dev_data; }

static void answer(const char *msg)
{
    const char *a = NULL;
    static char buf[sizeof sim_last_message];
    if (!strcmp(msg, "*IDN?"))
        a = "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0";
    else if (!strcmp(msg, "VOLT?"))
        a = "+1.00000E+00";
    else if (!strcmp(msg, "ECHO?")) {
        snprintf(buf, sizeof buf, "%s", sim_last_message);
        a = buf;
    }
    if (a) {
        snprintf(outbuf, sizeof outbuf, "%s\n", a);
        outlen = strlen(outbuf);
        outpos = 0;
    } else if (msg[0]) {
        snprintf(sim_last_message, sizeof sim_last_message, "%s", msg);
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
        inlen = outlen = outpos = 0;
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
    if (inlen < sizeof inbuf - 1)
        inbuf[inlen++] = (char)b;
    if (b == '\n' || eoi) {
        while (inlen && (inbuf[inlen - 1] == '\n' || inbuf[inlen - 1] == '\r'))
            inlen--;
        inbuf[inlen] = 0;
        answer(inbuf);
        inlen = 0;
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
    return line(l);
}
void hal_data_out(uint8_t b) { ctl_data = b; }
uint8_t hal_data_in(void) { return data(); }
void hal_data_release(void) { ctl_data = 0; }
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
    inlen = outlen = outpos = 0;
    acc = A_READY;
    src = S_IDLE;
    sim_status = 0x40;
    sim_last_message[0] = 0;
    sim_sdc_count = sim_get_count = sim_gtl_count = 0;
    sim_present = true;
    sim_addr = SIM_ADDR;
}

bool sim_ren(void) { return line(L_REN); }
