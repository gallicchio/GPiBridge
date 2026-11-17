#!/usr/bin/env python3
"""The board's top, with every place the bring-up names numbered: docs/images/bringup_map.png
(GPIBRIDGE_VARIANT=lite: docs/images/lite_bringup_map.png).

    python3 tools/bringup_map.py

A person at a crowded bench finds "TP3" faster in a picture than in a sentence.  The
places come from the generators' own tables (gen/placement.py, gen/footprints.py), so
a part that moves takes its number with it.  The picture is KiCad's own 3D render,
drawn the way the board lies on the bench: USB-C to the left, the plug's pins up.
Needs KiCad 10 (tools/kienv.py) and Pillow.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "gen"))
sys.path.insert(0, HERE)

import board_info as BI          # noqa: E402
import footprints as FP          # noqa: E402
import kienv                     # noqa: E402
import placement as PL           # noqa: E402

from PIL import Image, ImageDraw, ImageFont      # noqa: E402

W, H = PL.BOARD["w"], PL.BOARD["h"]
PLACE = PL.lite_place() if BI.LITE and hasattr(PL, "lite_place") else PL.PLACE


def contact(c):
    """Board coordinates of IEEE-488 contact c: the plug is on the back, turned 180 degrees."""
    x, y = FP.contact_xy(c)
    return PL.XC - x, PL.YC + y


def spots():
    """(number, x, y, what it is, what to do there) in the order a bring-up meets them."""
    def at(ref):
        return PLACE[ref][0], PLACE[ref][1]
    out = [
        ("J1  USB-C: to the PC.  Its metal shell is ground: a scope's ground clip goes here", at("J1")),
        ("J3  SWD: the Debug Probe's D port", at("J3")),
        ("J4  UART: the Debug Probe's U port", at("J4")),
        ("TP3  1V1: the core supply, 1.05 to 1.15 V", at("TP3")),
        ("TP2  3V3: 3.20 to 3.40 V", at("TP2")),
        ("TP1  VBUS: 4.4 to 5.3 V", at("TP1")),
    ]
    if "TP4" in PLACE:
        out.append(("TP4  5V: the transceivers' supply, 4.75 to 5.25 V while the green LED is lit", at("TP4")))
    out += [
        ("TP5  GND", at("TP5")),
        ("USB LED, yellow: blinking, waiting for the PC; steady, configured", at("D1")),
        ("BUS LED, green: on the GPIB bus.  Lit: do not change GPIB cables", at("D2")),
        ("ERR LED, red: a bus error in the last second; yellow and red turn about: \"this one\"", at("D3")),
        ("BOOT: never needed (a paperclip through the lid, if all else fails)", at("SW1")),
        ("contact 1 (DIO1): the hole marked 1.  Tack this pin first", contact(1)),
        ("contact 24 (ground): the hole under 12.  Tack it second; it must read 0 ohms to TP5", contact(24)),
        ("contact 12 (shield)", contact(12)),
        ("contact 13 (DIO5)", contact(13)),
    ]
    return [(i + 1, x, y, text) for i, (text, (x, y)) in enumerate(out)]


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    scratch = os.path.join(BI.SCRATCH, "view")
    os.makedirs(scratch, exist_ok=True)
    raw = os.path.join(scratch, BI.IMAGE_PREFIX + "bringup_top.png")
    kienv.run_cli(["pcb", "render", "--side", "top", "--width", "2400", "--height", "1300", "--quality", "high",
                   "--background", "transparent", "-o", raw, BI.PCB])
    img = Image.open(raw).convert("RGBA")
    # the opaque area is the board (and J1's face, 1.2 mm past the left edge): the right,
    # top and bottom edges are the board's own, so they give the scale
    box = img.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()
    scale = (box[3] - box[1]) / H
    x0, y0 = box[2] - W * scale, box[1]

    def px(x, y):
        return x0 + x * scale, y0 + y * scale

    items = spots()
    pad, line_h = 40, 44
    legend_h = line_h * ((len(items) + 1) // 2) + 2 * pad
    crop = (max(0, int(x0 - 3 * scale)), max(0, int(y0 - 3 * scale)),
            min(img.width, int(box[2] + 3 * scale)), min(img.height, int(box[3] + 3 * scale)))
    # the render's soft shadow is half-transparent: keep the board, drop the shadow
    img.putalpha(img.getchannel("A").point(lambda v: 255 if v > 128 else 0))
    board = img.crop(crop)
    out = Image.new("RGBA", (board.width + 2 * pad, board.height + legend_h + pad), "white")
    out.alpha_composite(board, (pad, pad))
    d = ImageDraw.Draw(out)
    f, small = font(30), font(26)
    r = 21
    for n, x, y, _ in items:
        cx, cy = px(x, y)
        cx, cy = cx - crop[0] + pad, cy - crop[1] + pad
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 20, 20, 235), outline="white", width=3)
        t = str(n)
        tw = d.textlength(t, font=small)
        d.text((cx - tw / 2, cy - 16), t, fill="white", font=small)
    half = (len(items) + 1) // 2
    for i, (n, _, _, text) in enumerate(items):
        col, row = divmod(i, half)
        tx, ty = pad + col * (out.width // 2), board.height + 2 * pad + row * line_h
        d.ellipse((tx, ty, tx + 2 * r - 6, ty + 2 * r - 6), fill=(200, 20, 20, 255))
        t = str(n)
        d.text((tx + r - 3 - d.textlength(t, font=small) / 2, ty + 3), t, fill="white", font=small)
        d.text((tx + 2 * r + 8, ty + 1), text, fill="black", font=f)
    # the legend's lines must fit: widen the sheet if one does not
    need = max(d.textlength(text, font=f) for _, _, _, text in items) + 2 * r + 8 + pad
    if need > out.width // 2:
        wide = Image.new("RGBA", (int(2 * need) + 2 * pad, out.height), "white")
        wide.alpha_composite(out.crop((0, 0, out.width, board.height + 2 * pad)), ((wide.width - out.width) // 2, 0))
        d = ImageDraw.Draw(wide)
        for i, (n, _, _, text) in enumerate(items):
            col, row = divmod(i, half)
            tx, ty = pad + col * (wide.width // 2), board.height + 2 * pad + row * line_h
            d.ellipse((tx, ty, tx + 2 * r - 6, ty + 2 * r - 6), fill=(200, 20, 20, 255))
            t = str(n)
            d.text((tx + r - 3 - d.textlength(t, font=small) / 2, ty + 3), t, fill="white", font=small)
            d.text((tx + 2 * r + 8, ty + 1), text, fill="black", font=f)
        out = wide
    path = os.path.join(ROOT, "docs", "images", BI.IMAGE_PREFIX + "bringup_map.png")
    out.convert("RGB").save(path, optimize=True)
    print("wrote", os.path.relpath(path, ROOT), "%dx%d, %d places" % (out.width, out.height, len(items)))


if __name__ == "__main__":
    main()
