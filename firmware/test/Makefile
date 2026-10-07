# The firmware on the host.  `make` builds and runs both tests, every time:
#   test_prologix  the "++" layer and the bus engine against a simulated instrument
#   test_wire      the board's pin layer too, against the transceivers' function
#                  tables: no two drivers on one wire, nothing into unpowered chips;
#                  and again as GPiBridge Lite (`test_wire lite`), its pins the bus:
#                  never driven high, nothing asserted off the bus; their recordings
#                  of the bus are then read by sigrok's own IEEE-488 decoder
#                  (sigrok_check.py; skipped without sigrok-cli)
CFLAGS = -std=c11 -Wall -Wextra -Wno-unused-parameter -g -I../src -fsanitize=address,undefined
HEADERS = ../src/*.h sim_bus.h

all: run_prologix run_wire

test_prologix: ../src/gpib.c ../src/prologix.c sim_bus.c test_prologix.c $(HEADERS)
	$(CC) $(CFLAGS) -o $@ ../src/gpib.c ../src/prologix.c sim_bus.c test_prologix.c

test_wire: ../src/gpib.c ../src/hal_rp2350.c ../src/capture.c sim_bus.c test_wire.c $(HEADERS) stubs/*/*.h
	$(CC) $(CFLAGS) -DSIM_NO_HAL -Istubs -o $@ ../src/gpib.c ../src/hal_rp2350.c ../src/capture.c sim_bus.c \
		test_wire.c

run_prologix: test_prologix
	./test_prologix

run_wire: test_wire
	mkdir -p out
	./test_wire
	./test_wire lite
	python3 sigrok_check.py

clean:
	rm -rf test_prologix test_wire out
.PHONY: all run_prologix run_wire clean
