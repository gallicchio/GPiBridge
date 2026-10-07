/* gpib_hal.h: the IEEE-488 bus as the engine (gpib.c) sees it.
 *
 * Every line is "asserted" (true) or "released" (false), whatever its polarity
 * on the wire (the bus is active low).  Two implementations:
 *   hal_rp2350.c     the boards: GPiBridge's GPIOs, SN75160B/SN75161B controls and
 *                    5 V switch, or GPiBridge Lite's open-drain pins (hal_lite())
 *   test/sim_bus.c   a simulated bus with scripted instruments, for the host tests
 *
 * Who drives what (SN75161B function table, DC and TE):
 *   controller (DC low):   we drive ATN, REN, IFC; SRQ is an input
 *   talking (TE high):     we drive DIO1-8, DAV, EOI; NRFD, NDAC are inputs
 *   listening (TE low):    we drive NRFD, NDAC; DIO1-8, DAV, EOI are inputs
 * hal_talk() changes direction in the order that never has the RP2354A and a
 * transceiver driving the same wire.
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef enum { L_EOI, L_DAV, L_NRFD, L_NDAC, L_IFC, L_REN, L_ATN, L_SRQ, L_COUNT } gpib_line;

bool hal_lite(void);                    /* GPiBridge Lite (no transceivers)? Read once from the board */
void hal_init(void);                    /* pins to their safe state; transceivers unpowered */
void hal_power(bool on);                /* 5 V to the transceivers (and the green BUS LED); the Lite: its BUS LED */
void hal_controller(bool on);           /* DC: controller drives ATN, REN, IFC */
void hal_talk(bool on);                 /* TE: talker drives DIO, DAV, EOI; listener NRFD, NDAC */
void hal_totem(bool on);                /* PE: DIO totem-pole (normal) or open collector (parallel poll) */
void hal_set(gpib_line line, bool asserted);
bool hal_get(gpib_line line);
void hal_data_out(uint8_t byte);        /* DIO1 = bit 0; a 1 bit is an asserted line */
uint8_t hal_data_in(void);
void hal_data_release(void);
uint64_t hal_us(void);                  /* microseconds since start */
void hal_delay_us(uint32_t us);
void hal_idle(void);                    /* while waiting on the bus: let USB run */
