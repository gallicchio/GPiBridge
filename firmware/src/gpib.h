/* gpib.h: IEEE-488.1 as the system controller sees it.
 *
 * The three-wire handshake in C, line by line, over gpib_hal.h.  Every wait
 * has a timeout; nothing here can hang the firmware.  The engine is the
 * controller in charge and the only system controller on the bus (it owns
 * IFC and REN), as a Prologix in controller mode is.
 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    GPIB_OK = 0,
    GPIB_TIMEOUT,          /* a handshake line did not move in time */
    GPIB_NO_LISTENER,      /* we would talk, but nobody is listening (NRFD and NDAC both released) */
    GPIB_OFF,              /* the transceivers are unpowered */
} gpib_status;

const char *gpib_status_name(gpib_status s);

/* interface messages (IEEE 488.1 table, the bytes sent with ATN) */
enum {
    GPIB_GTL = 0x01, GPIB_SDC = 0x04, GPIB_PPC = 0x05, GPIB_GET = 0x08, GPIB_TCT = 0x09,
    GPIB_LLO = 0x11, GPIB_DCL = 0x14, GPIB_PPU = 0x15, GPIB_SPE = 0x18, GPIB_SPD = 0x19,
    GPIB_LAD = 0x20, GPIB_UNL = 0x3f, GPIB_TAD = 0x40, GPIB_UNT = 0x5f, GPIB_SAD = 0x60,
};

typedef struct {
    uint32_t bytes_out, bytes_in, timeouts, no_listener;
} gpib_counters;

extern gpib_counters gpib_count;
extern uint32_t gpib_timeout_us;        /* each handshake step's limit (++read_tmo_ms sets it) */
extern uint8_t gpib_my_address;         /* ours, when we address ourselves to talk or listen */

void gpib_start(void);                  /* power up released, become system controller, IFC */
void gpib_stop(void);                   /* release everything, power off */
bool gpib_powered(void);
void gpib_ifc(void);                    /* interface clear: 150 us, as a Prologix does */
void gpib_ren(bool on);
bool gpib_srq(void);

/* bytes with ATN asserted: addressing and interface messages */
gpib_status gpib_command(const uint8_t *cmd, size_t n);
/* streaming: address `pad` to listen and talk to it a byte at a time ... */
gpib_status gpib_talk_start(int pad, int sad);
gpib_status gpib_talk_byte(uint8_t b, bool eoi);
/* ... or address it to talk and listen a byte at a time; gpib_idle() ends either */
gpib_status gpib_listen_start(int pad, int sad);
gpib_status gpib_listen_byte(uint8_t *b, bool *eoi);
/* address `pad` (and `sad` if >= 0) to listen, us to talk; then send data */
gpib_status gpib_send_to(int pad, int sad, const uint8_t *data, size_t n, bool eoi_last);
/* address `pad` to talk, us to listen; read until EOI (if stop_eoi), the byte
 * `stop_char` (if >= 0), `max` bytes, or a timeout between bytes */
gpib_status gpib_receive_from(int pad, int sad, uint8_t *buf, size_t max, size_t *got,
                              bool stop_eoi, int stop_char, bool *eoi_seen);
/* serial poll one device: its status byte */
gpib_status gpib_serial_poll(int pad, int sad, uint8_t *status);
/* bring the bus to idle after a transfer: ATN asserted, untalk, unlisten */
void gpib_idle(void);
