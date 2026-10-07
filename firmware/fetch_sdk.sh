#!/bin/sh
# Fetch the pinned Pico SDK (and only its TinyUSB submodule) into external/.
# external/ is not committed: run this once on a fresh clone.
set -e
cd "$(dirname "$0")"
SDK_TAG=2.1.1
if [ ! -d external/pico-sdk ]; then
    mkdir -p external
    git clone --depth 1 --branch "$SDK_TAG" https://github.com/raspberrypi/pico-sdk.git external/pico-sdk
    git -C external/pico-sdk submodule update --init --depth 1 lib/tinyusb
fi
echo "Pico SDK $SDK_TAG in external/pico-sdk"
