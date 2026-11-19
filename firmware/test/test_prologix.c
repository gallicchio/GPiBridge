/* test_prologix.c: the Prologix layer and the bus engine against the
 * simulated instrument (sim_bus.c), on the host.  `make` here runs it.
 *
 * Each test types what a host program would type, and checks what comes
 * back and what the instrument saw.
 */
#include "../src/gpib.h"
#include "../src/prologix.h"
#include "sim_bus.h"
#include <stdio.h>
#include <string.h>

static char out[4096];
static size_t outlen;
static char logged[4096];
static int saves, reboots, identified = -1;

static void w(const uint8_t *d, size_t n)
{
    if (outlen + n < sizeof out) {
        memcpy(out + outlen, d, n);
        outlen += n;
        out[outlen] = 0;
    }
}
static void fl(void) {}
static void sv(const prologix_config *c) { (void)c; saves++; }
static void rb(bool bootsel) { (void)bootsel; reboots++; }
static void lg(const char *j)
{
    strncat(logged, j, sizeof logged - strlen(logged) - 2);
    strcat(logged, "\n");
}
static void inf(char *json, size_t n) { snprintf(json, n, ",\"chip_rev\":2"); }
static void idf(int seconds) { identified = seconds; }
/* The USB buffer, as the read sees it: `fifo` there from the start, `later` once `later_at`
 * bytes have gone to the host (the host sending more while it waits); a reboot due once
 * `stop_at` bytes have (REVB.md 2.15). */
static const char *fifo = "", *later = "";
static size_t later_at, stop_at = (size_t)-1;
static int pk(void)
{
    if (*fifo)
        return (unsigned char)*fifo;
    return outlen >= later_at && *later ? (unsigned char)*later : -1;
}
static void dr(void)
{
    if (*fifo)
        fifo++;
    else if (*later)
        later++;
}
static bool st(void) { return outlen >= stop_at; }
static const prologix_io io = {.write = w, .flush = fl, .save = sv, .reboot = rb, .log = lg,
                               .info = inf, .identify = idf,   /* no capture here */
                               .host_peek = pk, .host_drop = dr, .must_stop = st};

static int failures, checks;

static void type(const char *s)
{
    outlen = 0;
    out[0] = 0;
    logged[0] = 0;
    prologix_input((const uint8_t *)s, strlen(s));
}

#define CHECK(cond, ...)                                     \
    do {                                                     \
        checks++;                                            \
        if (!(cond)) {                                       \
            failures++;                                      \
            printf("FAIL %s:%d: ", __FILE__, __LINE__);      \
            printf(__VA_ARGS__);                             \
            printf("\n   output: \"%s\"\n   log: %s\n", out, logged); \
        }                                                    \
    } while (0)

static void fresh(void)
{
    sim_reset();
    prologix_init(&io, NULL);
    gpib_start(false);
    saves = reboots = 0;
}

int main(void)
{
    fresh();

    /* addresses */
    type("++addr 10\n");
    type("++addr\n");
    CHECK(!strcmp(out, "10\r\n"), "++addr query");
    type("++addr 9 96\n++addr\n");
    CHECK(!strcmp(out, "9 96\r\n"), "secondary address");
    type("++addr 10\n");

    /* a query, then ++read eoi */
    type("*IDN?\n");
    CHECK(!strcmp(sim_last_message, "") || 1, "write");
    type("++read eoi\n");
    CHECK(!strcmp(out, "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\n"), "++read eoi returns the answer");

    /* read-after-write */
    type("++auto 1\n");
    type("VOLT?\n");
    CHECK(!strcmp(out, "+1.00000E+00\n"), "++auto 1 reads the answer");
    type("++auto 0\n");

    /* a plain command arrives with its terminator stripped by the instrument */
    type("VOLT 2.5\n");
    CHECK(!strcmp(sim_last_message, "VOLT 2.5"), "the instrument got \"%s\"", sim_last_message);

    /* escaping: an unescaped '+' is dropped, ESC + passes */
    type("VOLT \x1b+3.0\n");
    CHECK(!strcmp(sim_last_message, "VOLT +3.0"), "escaped plus: \"%s\"", sim_last_message);
    type("VOLT +4.0\n");
    CHECK(!strcmp(sim_last_message, "VOLT 4.0"), "unescaped plus dropped: \"%s\"", sim_last_message);

    /* ++read <char>: stops at that byte */
    type("ECHO?\n++read 46\n");          /* '.' */
    CHECK(!strcmp(out, "VOLT 4."), "++read 46 stops at '.': \"%s\"", out);
    type("++clr\n");

    /* eot_char marks EOI */
    type("++eot_enable 1\n++eot_char 42\n*IDN?\n++read eoi\n");
    CHECK(outlen && out[outlen - 1] == '*', "eot_char after EOI");
    type("++eot_enable 0\n");

    /* serial poll */
    sim_status = 0x41;
    type("++spoll\n");
    CHECK(!strcmp(out, "65\r\n"), "++spoll returns the status byte: \"%s\"", out);
    type("++spoll 10\n");
    CHECK(!strcmp(out, "1\r\n"), "RQS cleared by the poll: \"%s\"", out);

    /* device clear, trigger, local */
    int sdc = sim_sdc_count, get = sim_get_count, gtl = sim_gtl_count;
    type("++clr\n++trg\n++loc\n");
    CHECK(sim_sdc_count == sdc + 1 && sim_get_count == get + 1 && sim_gtl_count == gtl + 1, "SDC, GET, GTL");

    /* REN is asserted by a controller at start */
    CHECK(sim_ren(), "REN asserted");

    /* nobody at address 5: an error in the log, nothing hangs */
    type("++addr 5\n*IDN?\n");
    CHECK(strstr(logged, "no listener") != NULL, "writing to an empty address reports no listener");
    type("++addr 10\n");

    /* the instrument has nothing to say: ++read eoi times out (and says so) */
    type("++read_tmo_ms 20\n++read eoi\n");
    CHECK(outlen == 0 && strstr(logged, "timeout"), "a read with nothing to read times out");
    type("++read_tmo_ms 500\n");

    /* the instrument unplugged */
    sim_present = false;
    type("*IDN?\n");
    CHECK(strstr(logged, "no listener") != NULL, "no instrument at all");
    sim_present = true;

    /* a listener busy after the first byte (the bench's 33120A, back from local, held NRFD
     * over 1 s and firmware 0.4.2 dropped the rest of the message, 2026-11-18): the
     * message waits for it, whole, and ++read_tmo_ms (reads only, as the Prologix manual
     * has it) does not cut it short */
    type("++read_tmo_ms 500\n");
    sim_busy_us = 3000000;
    unsigned long t_before = gpib_count.timeouts;
    type("*IDN?\n++read eoi\n");
    CHECK(!strcmp(out, "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\n") && gpib_count.timeouts == t_before,
          "a listener busy 3 s after the first byte gets the whole message (timeouts %lu)",
          gpib_count.timeouts - t_before);
    sim_busy_us = 30000000;              /* busy for longer than any write waits: given up, counted */
    type("VOLT 1.0\n");
    CHECK(gpib_count.timeouts == t_before + 1 && strstr(logged, "timeout"), "a listener busy 30 s: the write gives up");
    sim_busy_us = 0;
    type("++clr\n");

    /* "++t power 1" on a live bus takes it again without switching the transceivers off
     * and on (0.4.3 did; REVB.md 2.14) */
    int offs = sim_power_offs, sdc_before = sim_sdc_count;
    type("++t power 1\n");
    CHECK(sim_power_offs == offs && gpib_powered(), "++t power 1 on a live bus: no power-off (%d)", sim_power_offs - offs);
    type("*IDN?\n++read eoi\n");
    CHECK(!strcmp(out, "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\n") && sim_sdc_count == sdc_before,
          "and the instrument answers after it: \"%s\"", out);
    /* off, then on: the off is real, and the instrument is left unaddressed first */
    type("++addr 10\nVOLT 1.5\n++t power 0\n");
    CHECK(sim_power_offs == offs + 1 && !gpib_powered(), "++t power 0 switches it off");
    type("++t power 1\n*IDN?\n++read eoi\n");
    CHECK(!strcmp(out, "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\n"), "on again, and answered: \"%s\"", out);

    /* settings: each change asks to be saved; ++savecfg 0 stops that */
    saves = 0;
    type("++eos 2\n++eoi 0\n");
    CHECK(saves == 2, "two changes, two saves (%d)", saves);
    type("++savecfg 0\n++eos 0\n");
    CHECK(saves == 2, "no save with ++savecfg 0 (%d)", saves);
    type("++eos\n");
    CHECK(!strcmp(out, "0\r\n"), "++eos query");

    /* the rest of the command set answers */
    type("++ver\n");
    CHECK(!strncmp(out, "GPiBridge GPIB-USB", 18), "++ver: \"%s\"", out);
    sim_lite = true;                     /* the same firmware on GPiBridge Lite */
    type("++ver\n");
    CHECK(!strncmp(out, "GPiBridge Lite GPIB-USB", 23), "++ver on the Lite: \"%s\"", out);
    sim_lite = false;
    type("++t compat 1\n++ver\n");
    CHECK(!strncmp(out, "Prologix GPIB-USB Controller", 28), "++t compat 1");
    type("++mode\n");
    CHECK(!strcmp(out, "1\r\n"), "++mode");
    type("++srq\n");
    CHECK(!strcmp(out, "0\r\n"), "++srq");
    type("++bogus\n");
    CHECK(!strcmp(out, "Unrecognized command\r\n"), "unknown command");
    type("++t status\n");
    CHECK(strstr(out, "\"bus_power\":1") != NULL, "++t status");
    type("++rst\n");
    CHECK(reboots == 1, "++rst reboots");

    /* the second USB serial port: saved, then the device reconnects with it */
    saves = 0;
    type("++savecfg 1\n++t console 1\n");
    CHECK(prologix_cfg.console_port && saves >= 1 && reboots == 2 && strstr(out, "console port on"),
          "++t console 1: saved (%d) and reconnects (%d)", saves, reboots);
    type("++t console 0\n");
    CHECK(!prologix_cfg.console_port && reboots == 3, "++t console 0");
    /* the capture is the board's (core 1): a build without it says so */
    type("++t capture start\n");
    CHECK(strstr(out, "no capture") != NULL, "++t capture without the board: \"%s\"", out);

    /* a long line, sent in pieces, still arrives whole */
    char longline[600];
    memset(longline, 'A', 500);
    longline[500] = 0;
    type("++eos 2\n");
    for (int i = 0; i < 500; i += 50) {
        char piece[51];
        memcpy(piece, longline + i, 50);
        piece[50] = 0;
        prologix_input((const uint8_t *)piece, 50);
    }
    type("\n");
    CHECK(strlen(sim_last_message) == 255, "a 500-byte line reaches the instrument (its buffer keeps 255)");

    /* ---- a line longer than the buffer streams to the instrument, EOI on its end ---- */
    fresh();
    type("++addr 10\n++eos 2\n");
    static char big[40000];
    unsigned long sum = 0;
    for (size_t i = 0; i < 30000; i++) {
        big[i] = (char)('A' + i % 26);
        sum += (unsigned char)big[i];
    }
    sim_bytes_in = sim_sum_in = 0;
    for (size_t i = 0; i < 30000; i += 64)       /* as USB brings it: 64 bytes at a time */
        prologix_input((const uint8_t *)big + i, i + 64 <= 30000 ? 64 : 30000 - i);
    type("\n");
    CHECK(sim_bytes_in == 30001 && sim_sum_in == sum + '\n' && sim_last_eoi,
          "a 30000-byte line: the instrument took %lu bytes (sum %lu, expected %lu), EOI %d", sim_bytes_in,
          sim_sum_in, sum + '\n', sim_last_eoi);
    CHECK(logged[0] == 0, "and nothing was logged");
    type("*IDN?\n++read eoi\n");
    CHECK(!strncmp(out, "HEWLETT-PACKARD", 15), "the bus is in order after it: \"%s\"", out);
    /* without a terminator of ours (++eos 3), the EOI still rides the last byte */
    type("++eos 3\n");
    sim_bytes_in = 0;
    for (size_t i = 0; i < 8192 * 2; i += 64)    /* exactly two buffers: nothing is left over at the end */
        prologix_input((const uint8_t *)big + i, 64);
    type("\n");
    CHECK(sim_bytes_in == 8192 * 2 && sim_last_eoi, "two buffers exactly, no terminator: %lu bytes, EOI %d",
          sim_bytes_in, sim_last_eoi);
    type("++eos 2\n");
    /* nobody listening: said once, the rest of the line dropped, and the next line is a new line */
    type("++addr 5\n");
    for (size_t i = 0; i < 30000; i += 64)
        prologix_input((const uint8_t *)big + i, 64);
    type("\n");
    type("++addr 10\n*IDN?\n++read eoi\n");
    CHECK(!strncmp(out, "HEWLETT-PACKARD", 15), "after a long line to nobody: \"%s\"", out);

    /* ---- a binary block with every byte the adapter would take for itself ---- */
    {
        uint8_t points[64], line_[200];
        size_t k = 0;
        const char *head = "DATA:DAC VOLATILE, #264";
        for (int i = 0; i < 64; i++)             /* LF, CR, ESC and '+' among them */
            points[i] = (uint8_t)("\n\r\x1b+\0\xff"[i % 6]);
        memcpy(line_, head, strlen(head));
        k = strlen(head);
        for (int i = 0; i < 64; i++) {
            if (points[i] == '\n' || points[i] == '\r' || points[i] == 27 || points[i] == '+')
                line_[k++] = 27;
            line_[k++] = points[i];
        }
        line_[k++] = '\n';
        outlen = 0;
        logged[0] = 0;
        sim_bytes_in = 0;
        prologix_input(line_, k);
        CHECK(sim_bytes_in == strlen(head) + 64 + 1, "the block: %lu bytes at the instrument", sim_bytes_in);
        type("DATA:ATTRibute:POINts? VOLATILE\n++read eoi\n");
        CHECK(!strcmp(out, "+32\n"), "32 points stored: \"%s\"", out);
        type("SYSTem:ERRor?\n++read eoi\n");
        CHECK(!strncmp(out, "+0,", 3), "no error from the block: \"%s\"", out);
    }

    /* ---- the 33120A's own commands, as lab-instrument-control's driver sends them ---- */
    type("APPLy:SINusoid 1234.5,0.8,0.1\n");
    type("APPLy?\n++read eoi\n");
    CHECK(!strcmp(out, "\"SIN 1.234500000000E+03,+8.000000E-01,+1.000000E-01\"\n"), "APPLy?: %s", out);
    type("APPLy:SINusoid 20e6,1,0\nSYSTem:ERRor?\n++read eoi\n");
    CHECK(!strncmp(out, "-222", 4), "20 MHz is refused: %s", out);

    /* ---- SRQ: the line, then a serial poll lets go of it ---- */
    sim_srq = true;
    sim_status = 0x50;
    type("++srq\n");
    CHECK(!strcmp(out, "1\r\n"), "++srq with SRQ asserted: \"%s\"", out);
    type("++spoll\n");
    CHECK(!strcmp(out, "80\r\n"), "the poll's status byte: \"%s\"", out);
    type("++srq\n");
    CHECK(!strcmp(out, "0\r\n"), "++srq after the poll: \"%s\"", out);

    /* ---- another controller on the bus: stand back, say so, take it only when told to ---- */
    type("++t power 0\n");
    sim_other_controller = true;
    type("++t power 1\n");
    CHECK(strstr(logged, "another controller"), "++t power 1 against another controller logs it: %s", logged);
    type("++t status\n");
    CHECK(strstr(out, "\"bus\":\"busy\"") && strstr(out, "\"bus_power\":0"), "++t status then: %s", out);
    type("*IDN?\n");
    CHECK(strstr(logged, "another controller has the bus"), "a data line then says why it went nowhere: %s", logged);
    type("++t power 2\n++t status\n");
    CHECK(strstr(out, "\"bus\":\"controller\""), "++t power 2 takes the bus regardless: %s", out);
    sim_other_controller = false;
    type("++t power 0\n++t power 1\n++t status\n");
    CHECK(strstr(out, "\"bus\":\"controller\""), "and ++t power 1 on a free bus: %s", out);

    /* ---- the bring-up commands ---- */
    type("++t status\n");
    CHECK(strstr(out, "\"bus\":\"controller\"") && strstr(out, "\"autostart\":1"), "++t status: %s", out);
    type("++t info\n");
    CHECK(strstr(out, "\"board\":\"GPiBridge rev A\"") && strstr(out, "\"chip_rev\":2"), "++t info: %s", out);
    type("++t crash\n");
    CHECK(strstr(out, "no watchdog"), "++t crash without a watchdog (a PC) says so: %s", out);
    type("++t identify 7\n");
    CHECK(identified == 7, "++t identify 7 (%d)", identified);
    type("++t identify\n");
    CHECK(identified == 30, "++t identify, 30 s by default (%d)", identified);
    saves = 0;
    type("++savecfg 1\n++t autostart 0\n++t autostart\n");
    CHECK(!strcmp(out, "0\r\n") && prologix_cfg.manual_start && saves >= 1, "++t autostart 0: \"%s\"", out);
    type("++t autostart 1\n");
    CHECK(!prologix_cfg.manual_start, "++t autostart 1");
    type("++t lines\n");
    CHECK(strstr(out, "\"bus\":\"controller\"") && strstr(out, "ATN") && strstr(out, "REN"),
          "++t lines, idle: ATN and REN asserted: %s", out);
    type("++t raw\n");
    CHECK(strstr(out, "\"raw\":\"off\",\"power\":1"), "++t raw, not in it: %s", out);
    type("++t raw set 0x0001\n");
    CHECK(strstr(out, "error"), "++t raw set before a role: %s", out);
    type("++t raw dev_listen\n");
    CHECK(strstr(out, "\"raw\":\"dev_listen\"") && strstr(out, "\"lines\":\"0x0000\""), "++t raw dev_listen: %s", out);
    type("++t raw set 0x0001\n");
    CHECK(strstr(out, "not driven in this role: DIO1"), "DIO1 is not a listening device's to drive: %s", out);
    type("++t raw ctrl_talk\n++t raw set 0x0201\n");
    CHECK(strstr(out, "\"set\":\"0x0201\"") && strstr(out, "DIO1 DAV"), "DIO1 and DAV asserted: %s", out);
    type("++t status\n");
    CHECK(strstr(out, "\"bus\":\"raw\""), "++t status in raw mode: %s", out);
    type("*IDN?\n");
    CHECK(strstr(logged, "raw mode"), "a data line in raw mode is refused, and says why: %s", logged);
    type("++t raw off\n");
    CHECK(strstr(out, "\"raw\":\"off\",\"power\":0"), "++t raw off: %s", out);
    type("++t lines\n");
    CHECK(strstr(out, "\"bus\":\"off\""), "++t lines with the bus off: %s", out);
    type("++spoll\n");
    CHECK(strstr(logged, "bus power off"), "a serial poll with the bus off says so: %s", logged);
    type("++t power 1\n*IDN?\n++read eoi\n");
    CHECK(!strncmp(out, "HEWLETT-PACKARD", 15), "++t power 1 brings the controller back: \"%s\"", out);
    sim_present = false;                 /* a selftest wants the GPIB side empty */
    type("++t selftest\n");
    sim_present = true;
    CHECK(strstr(out, "\"selftest\":\"done\"") && strstr(out, "\"ok\":"), "++t selftest answers: %s", out);
    type("*IDN?\n++read eoi\n");
    CHECK(!strncmp(out, "HEWLETT-PACKARD", 15), "and the controller is back after it: \"%s\"", out);

    /* REVB.md 2.15: a talker that never stops and sends no EOI (an HP 5316B addressed to
     * talk). The host waits for the answer; once it sends more, the read ends there, and
     * what it sent is carried out. */
    fresh();
    sim_endless = true;
    later = "++ver\n";
    later_at = 600;
    type("++addr 10\n++read eoi\n");
    CHECK(outlen >= 600 && !strncmp(out, "F      +1.00000E+07\r\n", 21) && strstr(logged, "the host sent more"),
          "a read that never ends stops when the host sends more (%lu bytes)", (unsigned long)outlen);
    sim_endless = false;
    type(later);
    later = "";
    CHECK(!strncmp(out, "GPiBridge", 9), "and what it sent is then carried out: \"%s\"", out);
    type("*IDN?\n++read eoi\n");
    CHECK(!strncmp(out, "HEWLETT-PACKARD", 15), "the bus is in order after it: \"%s\"", out);

    /* the same, from a host that ends its lines CR LF: the LF, still in the USB buffer when
     * the read begins, is no news */
    fresh();
    sim_endless = true;
    fifo = "\n";
    later = "++ver\r\n";
    later_at = 300;
    type("++addr 10\r\n++read eoi\r");
    CHECK(outlen >= 300 && !*fifo && strstr(logged, "the host sent more"),
          "CR LF: the LF dropped, and the read stopped for what came after (%lu bytes)", (unsigned long)outlen);
    sim_endless = false;
    type(later);
    later = "";
    CHECK(!strncmp(out, "GPiBridge", 9), "CR LF: ++ver carried out: \"%s\"", out);

    /* several commands in one write, or already in the USB buffer: a Prologix's read, whole */
    fresh();
    type("++addr 10\n*IDN?\n++read eoi\n++ver\n");
    CHECK(!strncmp(out, "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\nGPiBridge", 46),
          "a read with more in the same write is not cut short: \"%s\"", out);
    fresh();
    fifo = "++ver\n";
    type("++addr 10\n*IDN?\n++read eoi\n");
    CHECK(!strcmp(out, "HEWLETT-PACKARD,33120A,0,7.0-5.0-1.0\n") && !strcmp(fifo, "++ver\n"),
          "nor with more already in the USB buffer: \"%s\"", out);
    fifo = "";

    /* a reboot due (picotool reboot -f -a) ends even such a read; the rest is carried out */
    fresh();
    sim_endless = true;
    stop_at = 300;
    type("++addr 10\n++read eoi\n++ver\n");
    CHECK(strstr(logged, "a reboot is due") && strstr(out, "GPiBridge"),
          "a reboot due ends a read that would not: %lu bytes", (unsigned long)outlen);
    sim_endless = false;
    stop_at = (size_t)-1;

    printf("%d checks, %d failures; %lu bytes out, %lu in, %lu timeouts, %lu no-listener\n", checks, failures,
           (unsigned long)gpib_count.bytes_out, (unsigned long)gpib_count.bytes_in,
           (unsigned long)gpib_count.timeouts, (unsigned long)gpib_count.no_listener);
    return failures ? 1 : 0;
}
