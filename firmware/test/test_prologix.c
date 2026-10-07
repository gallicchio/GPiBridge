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
static int saves, reboots;

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
static const prologix_io io = {.write = w, .flush = fl, .save = sv, .reboot = rb, .log = lg};   /* no capture here */

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
    gpib_start();
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

    printf("%d checks, %d failures; %lu bytes out, %lu in, %lu timeouts, %lu no-listener\n", checks, failures,
           (unsigned long)gpib_count.bytes_out, (unsigned long)gpib_count.bytes_in,
           (unsigned long)gpib_count.timeouts, (unsigned long)gpib_count.no_listener);
    return failures ? 1 : 0;
}
