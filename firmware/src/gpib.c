/* gpib.c: the IEEE-488.1 three-wire handshake and the controller's
 * addressing, in C over gpib_hal.h.  See gpib.h.
 *
 * Source handshake (we talk), one byte:
 *   1. NRFD and NDAC both released: nobody is listening, stop.
 *   2. wait for NRFD released (every listener ready);
 *   3. data and EOI on the lines, 2 us to settle (T1 for any driver type);
 *   4. assert DAV;
 *   5. wait for NDAC released (every listener has it);
 *   6. release DAV, EOI and the data.
 * Acceptor handshake (we listen), one byte, entered with NRFD and NDAC asserted:
 *   1. release NRFD (ready);  2. wait for DAV;  3. assert NRFD, read data and EOI;
 *   4. release NDAC (accepted);  5. wait for DAV released;  6. assert NDAC.
 */
#include "gpib.h"
#include "gpib_hal.h"

gpib_counters gpib_count;
uint32_t gpib_timeout_us = 500000;      /* Prologix's default ++read_tmo_ms is 500 */
uint8_t gpib_my_address = 21;           /* an HP controller's habit; never an instrument's */

static bool powered;
static bool talking;                     /* our transceivers' direction */
static bool raw;                         /* bring-up has the lines (gpib_raw): the engine stands down */
static bool busy;                        /* the last start found another controller, and stood back */

/* the engine may use the bus: powered, and not lent to "++t raw" */
static bool ready(void) { return powered && !raw; }

const char *gpib_status_name(gpib_status s)
{
    switch (s) {
    case GPIB_OK: return "ok";
    case GPIB_TIMEOUT: return "timeout";
    case GPIB_NO_LISTENER: return "no listener";
    case GPIB_OFF: return raw ? "raw mode" : busy ? "another controller has the bus" : "bus power off";
    }
    return "?";
}

/* wait until a line reaches `state`; USB keeps running about every millisecond */
static bool wait_line(gpib_line line, bool state, uint32_t limit_us)
{
    uint64_t t0 = hal_us(), next_idle = t0 + 1000;
    while (hal_get(line) != state) {
        uint64_t t = hal_us();
        if (t - t0 > limit_us)
            return false;
        if (t >= next_idle) {
            hal_idle();
            next_idle = t + 1000;
        }
    }
    return true;
}

static void become_talker(void)
{
    if (!talking) {
        hal_talk(true);
        talking = true;
    }
}

static void become_listener(void)
{
    if (talking) {
        hal_talk(false);                 /* holds NRFD and NDAC asserted */
        talking = false;
    }
}

static gpib_status send_byte(uint8_t b, bool eoi)
{
    if (!hal_get(L_NRFD) && !hal_get(L_NDAC)) {
        gpib_count.no_listener++;
        return GPIB_NO_LISTENER;
    }
    if (!wait_line(L_NRFD, false, gpib_timeout_us)) {
        gpib_count.timeouts++;
        return GPIB_TIMEOUT;
    }
    hal_data_out(b);
    hal_set(L_EOI, eoi);
    hal_delay_us(2);
    hal_set(L_DAV, true);
    bool ok = wait_line(L_NDAC, false, gpib_timeout_us);
    hal_set(L_DAV, false);
    hal_set(L_EOI, false);
    hal_data_release();
    if (!ok) {
        gpib_count.timeouts++;
        return GPIB_TIMEOUT;
    }
    gpib_count.bytes_out++;
    return GPIB_OK;
}

static gpib_status receive_byte(uint8_t *b, bool *eoi)
{
    hal_set(L_NRFD, false);
    if (!wait_line(L_DAV, true, gpib_timeout_us)) {
        hal_set(L_NRFD, true);
        gpib_count.timeouts++;
        return GPIB_TIMEOUT;
    }
    hal_set(L_NRFD, true);
    *b = hal_data_in();
    *eoi = hal_get(L_EOI);
    hal_set(L_NDAC, false);
    bool ok = wait_line(L_DAV, false, gpib_timeout_us);
    hal_set(L_NDAC, true);
    if (!ok) {
        gpib_count.timeouts++;
        return GPIB_TIMEOUT;
    }
    gpib_count.bytes_in++;
    return GPIB_OK;
}

/* ---------------------------------------------------------------------------- */
/* Is somebody else running this bus?  Only a controller asserts ATN, REN or
 * IFC, and one in charge holds REN (a Prologix, an NI board and this firmware
 * all do) or ATN.  Called with the transceivers powered as a listening device
 * and nothing of ours asserted: we look for a millisecond and touch nothing. */
static bool another_controller(void)
{
    uint64_t t0 = hal_us();
    do {
        if (hal_get(L_REN) || hal_get(L_ATN) || hal_get(L_IFC))
            return true;
    } while (hal_us() - t0 < 1000);
    return false;
}

bool gpib_start(bool force)
{
    if (!hal_board_known())
        return false;                    /* R21 not read: which pin layer is not known (REVB.md 1.8) */
    if (powered && !raw) {
        /* On the bus already ("++t power 1" again): take it again without switching the
         * transceivers off and on, as a Prologix never does either.  Until 0.4.4 this was
         * gpib_stop() and a new start.  Suspected on 2026-11-18 of stopping a 33120A; the
         * scope then showed the lines clean through both, and that unit stopping on its
         * own (REVB.md 2.14).  Not switching the 5 V is still the better restart. */
        gpib_ifc();
        gpib_ren(true);
        gpib_idle();
        return true;
    }
    if (powered)
        gpib_stop();                     /* never hal_init() with pins driven */
    hal_init();                          /* everything released, transceivers off */
    hal_power(true);
    hal_delay_us(5000);                  /* the 5 V settles and the transceivers wake */
    talking = false;
    busy = !force && another_controller();
    if (busy) {
        /* Two controllers on one bus drive ATN, REN and IFC against each other,
         * 48 mA drivers both.  Stand back: off the bus again, and say so. */
        hal_power(false);
        gpib_count.refused++;
        return false;
    }
    hal_talk(false);                     /* our listener outputs to a known state */
    hal_controller(true);                /* DC low: ATN, REN, IFC are ours (released) */
    hal_totem(true);
    powered = true;
    raw = false;
    gpib_ifc();                          /* we are controller in charge */
    gpib_ren(true);                      /* instruments go remote when addressed, as with a Prologix */
    gpib_idle();
    return true;
}

void gpib_stop(void)
{
    busy = false;
    if (!powered) {
        hal_init();                      /* still: every pin to its safe state */
        return;
    }
    if (raw) {
        hal_raw_end();                   /* nothing driven, a listening device */
        hal_power(false);
        powered = raw = false;
        return;
    }
    uint32_t limit = gpib_timeout_us;
    gpib_timeout_us = 50000;             /* (a stuck instrument does not hold the stop up) */
    gpib_idle();                         /* nobody left addressed when ATN goes and the 5 V with it */
    gpib_timeout_us = limit;
    hal_set(L_REN, false);
    hal_set(L_ATN, false);
    hal_set(L_IFC, false);
    become_listener();
    hal_controller(false);
    hal_power(false);
    powered = false;
}

bool gpib_powered(void) { return powered; }
bool gpib_busy(void) { return busy; }

/* ---- bring-up: the board as sixteen wires ------------------------------------
 * The engine lets go of the bus and lends it to "++t raw" until gpib_start()
 * or gpib_stop().  From off, the bus powers up straight into the role: no
 * IFC, no REN, nothing asserted. */
void gpib_raw(raw_role role)
{
    if (!hal_board_known())
        return;                          /* bringup.c says why */
    busy = false;
    if (!powered) {
        hal_init();
        hal_power(true);
        hal_delay_us(5000);
        powered = true;
        hal_totem(true);
    } else if (!raw) {
        hal_set(L_REN, false);
        hal_set(L_ATN, false);
        hal_set(L_IFC, false);
        become_listener();
        hal_controller(false);
    }
    talking = false;
    raw = true;
    hal_raw_role(role);
}

bool gpib_is_raw(void) { return raw; }

void gpib_ifc(void)
{
    if (!ready())
        return;
    hal_set(L_IFC, true);
    hal_delay_us(150);                   /* as long as a Prologix holds it (IEEE 488.1: >= 100 us) */
    hal_set(L_IFC, false);
}

void gpib_ren(bool on)
{
    if (ready())
        hal_set(L_REN, on);
}

bool gpib_srq(void) { return ready() && hal_get(L_SRQ); }

gpib_status gpib_command(const uint8_t *cmd, size_t n)
{
    if (!ready())
        return GPIB_OFF;
    hal_set(L_ATN, true);                /* every device stops and listens to commands */
    become_talker();
    hal_delay_us(2);                     /* they answer ATN within 200 ns: NDAC asserted */
    for (size_t i = 0; i < n; i++) {
        gpib_status s = send_byte(cmd[i], false);   /* never EOI with ATN: that is a parallel poll */
        if (s != GPIB_OK)
            return s;
    }
    return GPIB_OK;
}

static size_t address(uint8_t *cmd, uint8_t talker_byte, uint8_t listener_byte, int sad, bool sad_follows_talker)
{
    size_t k = 0;
    cmd[k++] = GPIB_UNL;
    cmd[k++] = talker_byte;
    if (sad >= 0 && sad_follows_talker)
        cmd[k++] = (uint8_t)(GPIB_SAD | sad);
    cmd[k++] = listener_byte;
    if (sad >= 0 && !sad_follows_talker)
        cmd[k++] = (uint8_t)(GPIB_SAD | sad);
    return k;
}

gpib_status gpib_talk_start(int pad, int sad)
{
    uint8_t cmd[5];
    size_t k = address(cmd, (uint8_t)(GPIB_TAD | gpib_my_address), (uint8_t)(GPIB_LAD | pad), sad, false);
    gpib_status s = gpib_command(cmd, k);
    if (s != GPIB_OK)
        return s;
    hal_set(L_ATN, false);               /* data: the addressed device listens to us */
    hal_delay_us(2);
    return GPIB_OK;
}

gpib_status gpib_talk_byte(uint8_t b, bool eoi) { return ready() ? send_byte(b, eoi) : GPIB_OFF; }

gpib_status gpib_listen_start(int pad, int sad)
{
    uint8_t cmd[5];
    size_t k = address(cmd, (uint8_t)(GPIB_TAD | pad), (uint8_t)(GPIB_LAD | gpib_my_address), sad, true);
    gpib_status s = gpib_command(cmd, k);
    if (s != GPIB_OK)
        return s;
    become_listener();                   /* NRFD, NDAC asserted before ATN goes */
    hal_set(L_ATN, false);               /* data: the addressed device talks */
    return GPIB_OK;
}

gpib_status gpib_listen_byte(uint8_t *b, bool *eoi) { return ready() ? receive_byte(b, eoi) : GPIB_OFF; }

gpib_status gpib_serial_poll(int pad, int sad, uint8_t *status)
{
    uint8_t cmd[6];
    size_t k = 0;
    if (!ready())
        return GPIB_OFF;                 /* and no pin moves: the lines below would drive an unpowered bus */
    cmd[k++] = GPIB_UNL;
    cmd[k++] = (uint8_t)(GPIB_LAD | gpib_my_address);
    cmd[k++] = GPIB_SPE;
    cmd[k++] = (uint8_t)(GPIB_TAD | pad);
    if (sad >= 0)
        cmd[k++] = (uint8_t)(GPIB_SAD | sad);
    gpib_status s = gpib_command(cmd, k);
    if (s == GPIB_OK) {
        bool eoi;
        become_listener();
        hal_set(L_ATN, false);
        s = receive_byte(status, &eoi);
    }
    hal_set(L_ATN, true);
    become_talker();
    uint8_t done[2] = {GPIB_SPD, GPIB_UNT};
    gpib_status s2 = gpib_command(done, 2);
    return s != GPIB_OK ? s : s2;
}

void gpib_idle(void)
{
    if (!ready())
        return;
    uint8_t cmd[2] = {GPIB_UNT, GPIB_UNL};
    uint32_t nobody = gpib_count.no_listener;
    gpib_command(cmd, 2);                /* ATN stays asserted: every device waits for commands */
    gpib_count.no_listener = nobody;     /* an empty bus is no news here: the transfer before this counted it */
}

gpib_status gpib_send_to(int pad, int sad, const uint8_t *data, size_t n, bool eoi_last)
{
    gpib_status s = gpib_talk_start(pad, sad);
    for (size_t i = 0; s == GPIB_OK && i < n; i++)
        s = send_byte(data[i], eoi_last && i + 1 == n);
    return s;
}

gpib_status gpib_receive_from(int pad, int sad, uint8_t *buf, size_t max, size_t *got,
                              bool stop_eoi, int stop_char, bool *eoi_seen)
{
    *got = 0;
    *eoi_seen = false;
    gpib_status s = gpib_listen_start(pad, sad);
    while (s == GPIB_OK && *got < max) {
        uint8_t b;
        bool eoi;
        s = receive_byte(&b, &eoi);
        if (s != GPIB_OK)
            break;
        buf[(*got)++] = b;
        if (eoi)
            *eoi_seen = true;
        if ((eoi && stop_eoi) || (stop_char >= 0 && b == stop_char))
            break;
    }
    gpib_idle();
    return s;
}
