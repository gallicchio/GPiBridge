/* capture.c: the record of the bus as a Value Change Dump (see capture.h).
 * Plain C, so the host tests can run it against the simulated bus. */
#include "capture.h"
#include "board_pins.h"
#include <stdio.h>
#include <string.h>

/* The channels, named as sigrok's ieee488 decoder names them, then the
 * transceivers' direction pins, which show who drives what. */
static const struct {
    const char *name;
    uint8_t gpio;
} SIGNAL[] = {
    {"DIO1", PIN_DIO1}, {"DIO2", PIN_DIO2}, {"DIO3", PIN_DIO3}, {"DIO4", PIN_DIO4},
    {"DIO5", PIN_DIO5}, {"DIO6", PIN_DIO6}, {"DIO7", PIN_DIO7}, {"DIO8", PIN_DIO8},
    {"EOI", PIN_EOI}, {"DAV", PIN_DAV}, {"NRFD", PIN_NRFD}, {"NDAC", PIN_NDAC},
    {"IFC", PIN_IFC}, {"REN", PIN_REN}, {"ATN", PIN_ATN}, {"SRQ", PIN_SRQ},
    {"TE_DATA", PIN_TE_DATA}, {"TE_CTRL", PIN_TE_CTRL}, {"DC", PIN_DC}, {"PE", PIN_PE},
    {"BUS_PWR_EN", PIN_BUS_PWR_EN},
};
#define N_SIGNAL (sizeof SIGNAL / sizeof SIGNAL[0])

uint32_t capture_mask(void)
{
    uint32_t m = 0;
    for (size_t i = 0; i < N_SIGNAL; i++)
        m |= 1u << SIGNAL[i].gpio;
    return m;
}

static void put(void (*out)(const char *, size_t), const char *s) { out(s, strlen(s)); }

void capture_vcd(const capture_entry *e, size_t n, uint32_t ticks_per_us, uint32_t timescale_ns,
                 const char *version, void (*out)(const char *s, size_t len))
{
    char line[160];
    snprintf(line, sizeof line, "$comment %s: GPIB at the RP2354A's bus pins, low = asserted $end\n", version);
    put(out, line);
    snprintf(line, sizeof line, "$timescale %lu ns $end\n$scope module gpib $end\n", (unsigned long)timescale_ns);
    put(out, line);
    for (size_t i = 0; i < N_SIGNAL; i++) {
        snprintf(line, sizeof line, "$var wire 1 %c %s $end\n", (char)('!' + i), SIGNAL[i].name);
        put(out, line);
    }
    put(out, "$upscope $end\n$enddefinitions $end\n");
    if (!n) {
        put(out, "$comment end $end\n");
        return;
    }
    uint32_t prev = 0;
    uint64_t last_t = 0;
    for (size_t k = 0; k < n; k++) {
        /* ticks -> the VCD's unit, in 64 bits: 2^32 ticks at 12 MHz is 358 s.
         * Changes that round to one time share its "#t" line: times only rise. */
        uint64_t t = (uint64_t)(e[k].t - e[0].t) * 1000u / ticks_per_us / timescale_ns;
        if (k == 0 || t > last_t) {
            snprintf(line, sizeof line, "#%llu\n", (unsigned long long)t);
            put(out, line);
            last_t = t;
        }
        if (k == 0)
            put(out, "$dumpvars\n");
        for (size_t i = 0; i < N_SIGNAL; i++) {
            uint32_t bit = 1u << SIGNAL[i].gpio;
            if (k == 0 || ((e[k].pins ^ prev) & bit)) {
                line[0] = (e[k].pins & bit) ? '1' : '0';
                line[1] = (char)('!' + i);
                line[2] = '\n';
                out(line, 3);
            }
        }
        if (k == 0)
            put(out, "$end\n");
        prev = e[k].pins;
    }
    put(out, "$comment end $end\n");
}
