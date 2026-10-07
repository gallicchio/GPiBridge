# GPiBridge firmware: Pico SDK 2 + TinyUSB, for the RP2354A.
#
#   ./fetch_sdk.sh                         once: the pinned Pico SDK into external/
#   cmake -S . -B build && cmake --build build -j
#   picotool load -x build/gpibridge.uf2 -f    (or copy the .uf2 to the BOOTSEL drive)
#
# make -C test: the host tests (the Prologix layer and the bus engine against a
# simulated instrument; the pin layer against the transceivers' function
# tables), no hardware needed.  README.md says more.
cmake_minimum_required(VERSION 3.13)

set(PICO_SDK_PATH ${CMAKE_CURRENT_LIST_DIR}/external/pico-sdk CACHE PATH "the Pico SDK")
set(PICO_PLATFORM rp2350-arm-s)
set(PICO_BOARD gpibridge)
set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/boards)
include(${PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(gpibridge C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

add_executable(gpibridge
    src/main.c
    src/gpib.c
    src/hal_rp2350.c
    src/prologix.c
    src/usb_descriptors.c
    src/capture.c
    src/capture_rp2350.c
    # Raspberry Pi's reset interface (picotool reboot), without the rest of stdio_usb
    ${PICO_SDK_PATH}/src/rp2_common/pico_stdio_usb/reset_interface.c
)
target_include_directories(gpibridge PRIVATE src ${PICO_SDK_PATH}/src/rp2_common/pico_stdio_usb/include)
target_compile_definitions(gpibridge PRIVATE
    PICO_STDIO_USB_ENABLE_RESET_VIA_VENDOR_INTERFACE=1
    PICO_STDIO_USB_RESET_INTERFACE_SUPPORT_RESET_TO_BOOTSEL=1
    PICO_STDIO_USB_RESET_INTERFACE_SUPPORT_RESET_TO_FLASH_BOOT=1
    PICO_STDIO_USB_RESET_INTERFACE_SUPPORT_MS_OS_20_DESCRIPTOR=0
    PICO_STDIO_USB_RESET_BOOTSEL_INTERFACE_DISABLE_MASK=0
    PICO_STDIO_USB_RESET_RESET_TO_FLASH_DELAY_MS=100
    PICO_STDIO_USB_ENABLE_RESET_VIA_BAUD_RATE=0
)
target_compile_options(gpibridge PRIVATE -Wall -Wextra -Wno-unused-parameter)
target_link_libraries(gpibridge
    pico_stdlib
    pico_unique_id
    pico_usb_reset_interface
    pico_flash
    pico_multicore
    hardware_flash
    hardware_ticks
    hardware_watchdog
    tinyusb_device
    tinyusb_board
)
pico_enable_stdio_uart(gpibridge 1)
pico_enable_stdio_usb(gpibridge 0)
pico_add_extra_outputs(gpibridge)
