/* prologix.h: the Prologix GPIB-USB "++" command set, controller mode, over
 * a byte stream (the USB serial port "GPiBridge GPIB").
 *
 * As the Prologix manual (6.0, datasheets/) describes it: input is gathered
 * into lines ended by an unescaped CR or LF; ESC escapes CR, LF, ESC and '+'
 * (and unescaped ones are dropped); a line starting with "++" is a command,
 * any other line goes to the instrument at ++addr with the ++eos terminator,
 * EOI on its last byte if ++eoi is 1, and, with ++auto 1, is followed by a
 * read until EOI.
 *
 * GPiBridge's own commands start "++t " (++t help lists them); ++ver says
 * "GPiBridge", or Prologix's string after "++t compat 1" for software that
 * insists.  "++t console 1" adds the second USB serial port (JSON console)
 * and reconnects; by default there is one port, as on a Prologix.
 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint8_t pad;            /* 0-30 */
    int8_t sad;             /* -1 none, else 0-30 (++addr takes 96-126) */
    bool autoread;
    bool eoi;
    uint8_t eos;            /* 0 CR LF, 1 CR, 2 LF, 3 none */
    bool eot_enable;
    uint8_t eot_char;
    uint16_t read_tmo_ms;   /* 1-3000 */
    bool compat_ver;        /* ++ver answers as a Prologix */
    bool console_port;      /* a second USB serial port, "console" (++t console 1); off: one port, as a Prologix */
} prologix_config;

typedef struct {
    void (*write)(const uint8_t *data, size_t n);   /* to the host */
    void (*flush)(void);
    void (*save)(const prologix_config *cfg);       /* ++savecfg: to flash */
    void (*reboot)(bool bootsel);                    /* ++rst, ++t bootsel */
    void (*log)(const char *json);                   /* the console, for ++t trace */
    void (*status_extra)(char *json, size_t n);      /* more ++t status fields: ',"key":value...' */
    void (*capture)(const char *what);               /* ++t capture start|stop|status|dump */
} prologix_io;

extern prologix_config prologix_cfg;

void prologix_init(const prologix_io *io, const prologix_config *saved);   /* saved may be NULL */
void prologix_input(const uint8_t *data, size_t n);
void prologix_defaults(prologix_config *cfg);
