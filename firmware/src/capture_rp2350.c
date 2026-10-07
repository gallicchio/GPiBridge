/* capture_rp2350.c: core 1 records the bus (see capture.h).
 *
 * Core 1 does nothing else.  It sleeps until a capture starts, then spins on
 * the GPIO input register, from RAM, writing down each change with TIMER1's
 * count.  TIMER1 is otherwise unused; its tick generator is set to every
 * clk_ref cycle (12 MHz) while a capture runs.  A spin of a few cycles samples
 * at some tens of MHz: far finer than any GPIB handshake.
 *
 * Settings writes stop core 1 for their ~45 ms (flash_safe_execute's lockout:
 * flash_safe_execute_core_init() below); a capture then has a gap.
 */
#include "capture.h"
#include "hardware/structs/sio.h"
#include "hardware/structs/timer.h"
#include "hardware/ticks.h"
#include "hardware/sync.h"
#include "pico/flash.h"
#include "pico/multicore.h"

capture_entry capture_buf[CAPTURE_MAX];

enum { IDLE, RUNNING, FULL, STOPPED };
static volatile int state = IDLE;
static volatile bool stop_request;
static volatile size_t count;
static bool core1_running;

static void __not_in_flash_func(sample)(void)
{
    const uint32_t mask = capture_mask();
    uint32_t last = ~0u;
    size_t n = 0;
    while (!stop_request) {
        uint32_t v = sio_hw->gpio_in & mask;
        if (v != last) {
            if (n == CAPTURE_MAX) {
                state = FULL;
                break;
            }
            capture_buf[n].t = timer1_hw->timerawl;
            capture_buf[n].pins = v;
            last = v;
            n++;
        }
    }
    count = n;
    __dmb();
    if (state == RUNNING)
        state = STOPPED;
}

static void core1_main(void)
{
    flash_safe_execute_core_init();          /* let core 0 write flash while we run */
    for (;;) {
        while (state != RUNNING)
            __wfe();
        sample();
    }
}

void capture_start(void)
{
    capture_stop();
    tick_start(TICK_TIMER1, 1);              /* 12 MHz: one tick per clk_ref cycle */
    count = 0;
    stop_request = false;
    __dmb();
    state = RUNNING;
    if (!core1_running) {
        multicore_launch_core1(core1_main);
        core1_running = true;
    }
    __sev();
}

void capture_stop(void)
{
    if (state == RUNNING) {
        stop_request = true;
        while (state == RUNNING)
            tight_loop_contents();
    }
    __dmb();
}

size_t capture_count(void) { return state == RUNNING ? 0 : count; }

const char *capture_state(void)
{
    static const char *name[] = {"idle", "running", "full", "stopped"};
    return name[state];
}

const capture_entry *capture_entries(void) { return capture_buf; }
