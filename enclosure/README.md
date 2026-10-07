# The housing

Two parts for JLC3DP's MJF PA12 (nylon), drawn in FreeCAD's Python from the board's
own placement (`gen/placement.py`) and the plug's dimensions (`gen/footprints.py`, from
NorComp's drawing and 3D model). One base fits both boards; each has its own lid:

| part | what it does |
|---|---|
| `out/gpibridge_base.step`, `.stl` | the side toward the instrument. Its 3.5 mm front plate is what the plug's flange bears on, so plugging in pushes on the housing, not on the 24 solder joints. The board lies on the plate, inside 1.2 mm walls. The plug's body passes through it with 0.3 mm all round. |
| `out/gpibridge_lid.step`, `.stl` | GPiBridge's cover: the USB-C through the end wall (its face flush with the wall), openings over the two debug connectors (the cables plug in from above), holes over the three LEDs and over BOOT (press it with a paperclip), and two counterbored M2 screw holes. Labels engraved 0.5 mm deep. |
| `out/gpibridge_lite_lid.step`, `.stl` | the same cover for GPiBridge Lite, engraved "GPiBridge Lite" |

Outside: 62.6 x 28.2 mm, 11.0 mm from the flange to the lid's top; the plug's D shell
stands 8.5 mm out of the front, as on a GPIB cable.

```
python3 enclosure/build.py      the two parts, the board's 3D model, and CHECK.txt
python3 enclosure/render.py     pictures, by KiCad's renderer (out/render_*.png)
```

`build.py` exports each board with every part's 3D model (KiCad's STEP export) and
intersects it with the base and its lid. `out/CHECK.txt` must say *no overlap*. It does,
for both boards, with 0.38 mm over the tallest part (the debug connectors, 4.32 mm).
When `../reference/` has NorComp's own 3D model of the plug (`111-024-113L001.STEP`,
from Digi-Key; not committed), it is put in place too, its flange on the base's face:
no overlap, and 0.30 mm between its body and the opening at the closest.

## Ordering, or printing it yourself

It is drawn for 3D printing, not machining: JLC3DP's MJF (powder-bed nylon), which needs
no supports.

**From JLC3DP.** Upload the `.stl` files: one base for every adapter, of either kind, and
the lid for each board (for the first order, two of each board: four bases, two of each
lid). Choose MJF, PA12 (grey, or dyed black). The walls are 1.2 mm against their 0.8 mm
minimum, and the engraving is 0.5 mm deep. The title's strokes are 0.8 mm wide, but the
small labels' horizontal strokes are 0.35-0.42 mm, under JLC3DP's 0.5 mm guideline for
engraved detail, so those may come out faint.

**On an FDM printer** (a Bambu Lab, say) it prints without supports too:
- **PETG or ASA, not PLA.** PLA softens at about 55 °C and creeps under the screws
  below that; the back of a working instrument can run warm.
- **The base on its front face, the lid on its top face.** The only overhangs are then
  the 0.4 mm step in the plug's opening and a 1 mm ring where each lid boss starts over
  its counterbore.
- **0.12-0.16 mm layers.** The engraving faces the bed: the title prints well, the
  2-2.6 mm labels cleanly only from a 0.2 mm nozzle.
- **Fits.** The board has 0.15 mm all round in the base, and FDM prints inside edges
  about 0.1 mm small. If the board does not drop in, print again with the slicer's
  X-Y hole compensation at +0.1 mm. Try a plug in the base's opening (0.3 mm clear)
  before printing four.

Two **M2 x 8 thread-forming screws** (pan head up to 4.0 mm across, or cheese head) hold
it together. They pass through the lid and the board and cut their own thread in the
base's 1.7 mm pilot holes: 1.7 mm of thread, with the tip 1.3 mm short of the holes'
bottoms (`out/CHECK.txt` says so on every build). An M2 x 10 would bottom out in the
pilot hole before its head seated.

## Putting it together

The plug is soldered last, in the base, so that its height is the housing's (as on
UsbGpib):

1. JLCPCB fits every part except the plug.
2. Push the plug's rear body through the base's opening from the front. The flange
   lies against the base's front face, with **contact 1 on the same side as the
   board's silkscreen "1"**: the D's wide side toward the board's top edge.
3. Lay the board into the base, with the plug's 24 pins up through it, and press it
   down until it rests on the plug's standoff plate. The pins are 1.0 mm wide for their
   first 0.5 mm (NorComp's 3D model), so they grip the 1.00 mm holes. Solder two
   first, in the holes marked "1" and under "12", and measure at the plug's face:
   contact 24 reads 0 ohms to GND (TP5) and contact 1 does not. The pins fit either way
   round; turned round, the readings swap (`HANDBOOK.md`, step 5). Then solder the rest
   from the top.
4. Put the lid on, and drive the two screws in.

To take it out of an instrument, pull on the housing. The plug's flange cannot be
clamped from the front (the instrument's own flange sits there), so the pull goes
through the solder joints, as on every GPIB-to-USB adapter of this shape. Jack screws
cannot be fitted: the flange's holes fall over the board's USB and UART circuits.

## Fonts

`fonts/DejaVuSans-Bold.ttf` is DejaVu Sans Bold (Bitstream Vera licence, in
`fonts/DejaVu-LICENSE.txt`), kept here so that the labels come out the same on any
machine.
