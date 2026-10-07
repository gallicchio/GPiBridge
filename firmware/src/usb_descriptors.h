/* usb_descriptors.h: the one choice the USB descriptors make at start-up. */
#pragma once
#include <stdbool.h>

/* before tusb_init(): one serial port (as a Prologix), or two with the console */
void usb_descriptors_init(bool with_console);
