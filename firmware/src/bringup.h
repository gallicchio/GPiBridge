/* bringup.h: the bring-up commands, "++t raw", "++t lines" and "++t selftest".
 *
 * They treat the board as sixteen wires, below the bus engine, so a new board
 * can be checked joint by joint with nothing but a second board, a cable, or
 * nothing at all:
 *
 *   ++t lines                 the sixteen lines as the pins read them now
 *   ++t raw ROLE              take the lines from the engine, in one of the
 *                             transceivers' roles: dev_listen, dev_talk,
 *                             ctrl_listen, ctrl_talk (gpib_hal.h); from off, the
 *                             bus powers up straight into the role, with no IFC
 *                             and no REN
 *   ++t raw set 0xMASK        assert exactly these of the lines the role drives
 *   ++t raw get [up|down]     read every line, the pads' pulls up or down on
 *                             the pins this board does not drive
 *   ++t raw pe 0|1            the SN75160B's drivers open-collector or totem-pole
 *   ++t raw                   where it stands
 *   ++t raw off               let go and power the bus off; "++t power 1" is the
 *                             way back to being a controller
 *   ++t crash                 hang, so the watchdog restarts the board: three in a
 *                             row land in the ROM bootloader (the failsafe's test)
 *   ++t selftest              with nothing plugged into the GPIB side: every
 *                             receive path, the 5 V switch and every joint
 *                             between the RP2354A and the transceivers; on the
 *                             Lite, every pin against every other
 *
 * Every answer is one JSON line.  Masks are 16 bits, 1 = asserted (the pin
 * low): DIO1-8 in bits 0-7, then EOI, DAV, NRFD, NDAC, IFC, REN, ATN, SRQ.
 */
#pragma once

/* argv[0] is "raw", "lines" or "selftest"; say() sends one line to the host */
void bringup_command(int argc, char **argv, void (*say)(const char *fmt, ...), const char *board);
