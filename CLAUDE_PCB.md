# CLAUDE_PCB.md: how to design a board Jason will be proud of

> **This is a public snapshot. The authoritative copy is elsewhere.**
>
> The working version of this file is `CLAUDE_PCB.md` at the top of Jason Gallicchio's
> private OpticsPCBs repository (`~/OpticsPCBs` on his machines, which is
> `../../OpticsPCBs` from his clone of this repository). It is the one that gets updated
> as Claude makes and fixes more PCBs with him, and this copy is not kept in step. **If
> you are working with access to OpticsPCBs, read and update that file, not this one.**
>
> This copy was taken on 2026-10-06, when GPiBridge moved out of OpticsPCBs into its own
> repository, and edited for publication. It leaves out what only works inside that
> repository: its other boards' file paths and prompt numbers, its private scripts, and
> paths on Jason's machines. The lessons are all here.

Read this before starting or changing a PCB with Claude. It distils what went right and
wrong on six Claude-generated boards: GPiBridge, and five in Jason's private repository
(a GPSDO for a PYNQ-Z2, built and brought up; a rebuild of the Icepi Zero for JLCPCB, built
after a wrong switch stopped the line; an analog Lorenz-attractor board, "AI UNLEASHES
CHAOS", built and working first time; an ECP5 board with two ADCs and two DACs, designed
and reviewed; and an ECP5 ADC/DAC board for the Icepi Zero, abandoned when its BGA would
not escape with an autorouter). Every rule here is something Jason had to ask for, or a
fault that a fab, a reviewer or a working board found. Examples name those boards as
GPSDO, Icepi, Lorenz and ECP5.

---

## 1. How Jason works with you

- **Log everything.** Each prompt goes verbatim, with minor typos fixed, into the
  project's `CLAUDE_CODE_CHAT.md`, followed by your response. Head each response with the
  real time range of the work. Put decision tables **in the response**, not only in a
  README. Responses show the renders as they were then, so the next prompt makes sense;
  include images only when they changed.
- **Questions.** Ask in the chat and in a temporary `QUESTIONS.md`; he answers in
  `ANSWERS.md`. Both are gitignored. Check them when you can.
- **"Go all night".** Keep going, log progress in the chat as you go, and write findings
  down before a session or the power could die. Do not stop to ask what you
  can decide; record the decision and why.
- **Be opinionated.** Recommend, with the trade-off stated; do not survey options you
  will not pursue.
- **Self-critical review.** End with the most likely causes of a dead-on-arrival board
  and what mitigates each ("If I got these back and told you they didn't
  work, what would be the most likely cause?").
- **Rev A until ordered.** It stays "rev A" until Jason pays a fab. Then:
  - lock it: a git tag, a `<board>-revA.zip` of the project and `mfg/release/`, and
    SHA-256 sums;
  - start `REVB_CHANGES.md`, applied all at once.
- **Outside reviews.** When the board is ready, write a `DESIGN_REVIEW_PROMPT.md` for
  other LLMs, each writing only into its own `design_review_<Name>/` directory. Then
  reconcile them by evidence (datasheet numbers), not by majority.
- **Git.** Do not commit or push unless Jason asks. Where a repository holds several
  projects and other agents work in it too, never commit another project's files.

## 2. Build system and sources of truth

- **One command makes everything:** schematic, PCB, checks, manufacturing files,
  renders, documents and cost estimate. `--clean` removes exactly what it generates, so
  it is obvious what lives in git.
- **Reproducible from a fresh clone** on another machine:
  - Vendor every symbol, footprint and 3D model the board uses into the project's own
    library. A fresh KiCad AppImage has an empty `~/.local/share/kicad/10.0/symbols`.
  - Relative paths only: the next rule.
  - The KiCad AppImage path comes from an environment variable with a default.
- **All paths are relative** (Jason, 2026-10-06: "In general, *all* paths should be
  relative"). Nothing committed may name a place on one machine: no `/home/<user>/`,
  `/Users/`, `/tmp/` or mount point.
  - Inside a repository, a path is relative to the file that holds it or to the
    project: `os.path.dirname(__file__)` in scripts, `${KIPRJMOD}` in KiCad's library
    tables and 3D model paths, `${workspaceFolder}` in editor settings, plain relative
    links in documents.
  - A tool outside the repository (KiCad, oss-cad-suite, a bench library) comes from
    `PATH` or one environment variable, whose default may be under `~`. One module
    finds it for every script (GPiBridge's `tools/kienv.py`).
  - Scratch files go in a gitignored build directory inside the project, or come from
    `tempfile`; never a fixed name in `/tmp`.
  - Generated files count. A KiCad netlist records its schematic's absolute path in
    `(source …)`, and plotting from the GUI stores the output directory in
    `.kicad_pcb` (`outputdirectory`) and `.kicad_pro` (`last_paths`). Rewrite them
    as relative in the step that writes them. CMake build directories, compiled host
    tests and KiCad's `fp-info-cache` stay out of git.
  - Before every commit: `git grep -I -n -E '/home/|/Users/|/tmp/|/mnt/'`, and with
    `-a` instead of `-I` for the binary files (STEP, PDF, PNG, executables).
  - An audit of the older projects found about 100 committed files that broke it:
    library tables and 3D model paths into other people's home directories (those
    boards open without their libraries and models anywhere else), netlists, a plot
    directory inherited from an upstream project, analysis scripts that read data from
    outside the repository, and caches committed by mistake (`fp-info-cache`,
    `temp-freerouting.dsn`).
- **One source of truth per fact**, and everything else derived from it:
  - pin assignments drive the schematic, the firmware constraints and the pinout
    document;
  - part numbers live in one parts table;
  - the revision and date live in one place, and the silkscreen reads them;
  - placement drives the silkscreen labels that belong to parts (hand-placed
    "H"/"T" markers drifted away from their heaters).
- **Generated documents.** From the source of truth, generate:
  - the pinout (ASCII art), a bring-up handbook and the end-user guide;
  - PDFs and PNGs of every sheet, layer plots cropped to the board outline,
    and 3D renders from several sides.
- **Look at the output.** Export the schematic to PDF/PNG, render the board, and look,
  as Jason will. Most of his corrections were visible in one glance at a render.
  - **To look at one corner as the fab prints it**, plot F.SilkS, F.Mask and Edge.Cuts
    one at a time (`kicad-cli pcb export svg --mode-single --page-size-mode 0`). Crop
    each by rewriting the SVG's `viewBox` in board millimetres, recolour it and stack
    the three.
  - One plot of all the top layers buries the silkscreen under copper fill
    and Fab text.
- **Every page fits what is on it: sized to it, centred, filling it** (Jason, 2026-10-29: "In
  general, the schematics, PCBs, and PDFs should be sized and centered properly. I've seen
  many examples of things hanging off of the page or the page being far too big for the thing
  on it.").
  - Schematic sheets, board plots, assembly drawings and figures. The drawing spans the paper
    less a margin of about half an inch (12.7 mm), in whichever orientation suits it, with its
    centre at the page's. Nothing hangs off an edge; nothing sits in a corner of a page
    several times its size.
  - **kicad-cli does not do this.** It plots a board 1:1 where the board lies on its A4
    sheet, and its `--scale 0` autoscale stays on A4, off centre.
    - Fit each page after export with OpticsPCBs' `CostasLink-PYNQ-Z2/tools/fit_pdf.py`. It
      measures the drawn box with Ghostscript's bbox device and scales it onto Letter.
    - Print the scale in the margin.
    - Plot paper drawings `--black-and-white`, because KiCad's yellow and pink silkscreen
      colours hardly print.
  - **A schematic's sheet size is chosen for its content**, so the content fills the frame.
  - **Check by rendering every page whole** (`pdftoppm`), and with `fit_pdf.py check`.
- **Datasheets** go in `datasheets/`, gitignored for copyright. Fetch all of them: every
  IC, connector and mechanical part. Read pinouts from the datasheet's **pin figure**,
  not only its table.
- **Pad checks.** Check pad positions against KiCad's own pcbnew (load the board in its
  Python and read the pads back), because rotation conventions have bitten every board.
- **A second board from the same pipeline** (GPiBridge Lite, 2026-10-06): one
  environment variable selects it, and one module holds every path that differs
  (project, checks, release folder, image names), so the two never overwrite each other.
  Refactor the shared code into functions first, and after each step check that the
  first board's schematic and board files come out **byte for byte** the same: with
  deterministic builds that is a free regression test, and it caught a refactor that
  had silently run a whole drawing section five times.
- **Board IDs.** To tell variants apart in one firmware image, look first for a
  resistor that both boards already have in the same place, and fit it with a different
  value or to the other rail (GPiBridge's DC pull-up, 10 k up, became the Lite's 1 k
  down). The spare pin first chosen for a strap turned out to be walled in by
  decoupling copper.

## 3. Parts and sourcing (JLCPCB)

- **One-step order.**
  - Every machine-placed part must be in JLCPCB's stock, deep enough to survive a week,
    and active at Digi-Key and Mouser too.
  - Consign only when Jason agrees and it saves real cost or complexity.
  - Prefer Basic parts: each distinct Extended part costs a setup fee (about $3).
- **Query stock and price** through JLCPCB's parts API (GPiBridge's `tools/jlc_api.py`,
  which caches each answer with its timestamp). Never trust memory: "in stock" is a
  statement about a moment, and their search web page does not render for an agent.
- **Every code is checked against its description.** Eight ECP5 codes typed from memory
  named the wrong part: a 2.2 pF capacitor was a 180 kΩ 1206 resistor, a 24.9 Ω load
  470 kΩ. Every check that existed passed. The release must fail if:
  - any LCSC code's JLCPCB description lacks the schematic's value and package;
  - any SMD part has no code. Eleven codeless parts silently became "hand-solder" on
    ECP5.
- **The part must fit the copper.** Compare every ordered code's EasyEDA land pattern
  with the board (GPiBridge's `mfg/footprint_check.py`: HOLE, PADS, LAND, datum). A
  substituted switch with two locating posts and no holes stopped JLCPCB's line.
  - An MPN search can return a zero-stock code first; read the stock column.
  - Family variants differ mechanically.
- **Ratings.** Read voltage, current and power off the code's own description:
  - a 50 mA chip inductor was drawn where a 600 mA power inductor was required;
  - check resistor power at the worst-case input.
- **BOM.** One line per LCSC code. "51R1%" and "51R" mapped to one part produced
  JLCPCB's "multiple lines matched to the same part".
- **Packages.** 0805 or 0603 for hand rework and probing, unless the datasheet or the
  density says otherwise. Prefer solderable packages that are
  common everywhere.
- **Annotated BOM.** Price per item and for N boards, stock with the time of the query,
  Basic/Extended/consigned, and a note for anything to look at.
- **Landed cost.** The US has no de minimis exemption any more. JLCPCB pre-collects duty
  under DDP, which they band at 35-90% of the goods' value. Price boards with shipping
  and duty.

* **A line can run out AFTER the order is placed.** GPiBridge's L1 (Abracon AOTA 3.3 µH,
  C42411119): 347 on JLCPCB's shelf when the release was costed (2026-10-08), the order placed
  2026-10-06 with "stock >= the order" passing, and on 2026-10-18 an email: "Due to insufficient
  stock of C42411119, we have enabled the 'Replace Parts' function for your order"; 3 left for 4
  boards.  The fix is in Order History (Replace Parts: pick one, or leave it unpopulated); nothing
  is re-uploaded.  Before answering, `tools/jlc_api.py` with a free-text search ("3.3uH 2016")
  lists the shelf with stock, Isat, DCR and package in a minute, and the datasheet or the
  vendor's design guide says what the part has to be (here: 3.3 µH, 2016 land, Isat > 1 A; the
  AOTA's only special property was a polarity dot).  Keep the design's part and record the
  substitution where the part is named (gen/parts, the design notes' risk list, the bring-up's
  check of what the part affects, the README's status), so the next order expects it.

## 4. Schematics: the Art of Electronics standard

Jason worked with Paul Horowitz. The bar is a schematic drawn so that every question a
reader would ask is answered at the place they would ask it.

- **Flow.**
  - Signals go left to right and power comes from the top.
  - Series parts are horizontal on the signal line; shunts are vertical, hanging off
    the node.
  - Draw it as the circuit is understood, not as the netlist happens to connect.
- **No disappearing labels.** A label that vanishes and reappears elsewhere is allowed
  only for power and ground. Wire it if you can ("connect it with a wire
  rather than a label").
- **Notes at the node.**
  - Put voltage ranges, frequencies, rise times and impedances **right at the node**
    they describe, in small boxes with small arrows to the probe point.
  - Wrap note boxes like a newspaper column, about 80 characters.
- **Why boxes.** Explain why a part was chosen ("74LVC1GU04: U = unbuffered; LVC =
  5.5 V tolerant at 3.3 V"), and when to fit each jumper ("50 Ω: fit for all but the
  ZED-F9T").
- **Limits at every connector:** maximum DC, Vpp before clipping, Vpp before damage,
  and output ranges.
- **Nothing overlaps anything.** No text, reference or value overlaps a symbol, wire,
  box or other text, and everything stays inside the page border.
  - Check it in code and by looking at the exported PDF.
  - The usual offenders: references on vertical R/C, GND flags on decoupling caps,
    notes next to GND symbols.
- **Symbols the right way up.** No upside-down GND flags or `+3V3` arrows pointing down
  with upside-down text. No PWR_FLAG left floating in a corner.
- **Hierarchical and global arrows** are justified so they do not overlap boxes. They
  point the way the signal goes (bidirectional only when it is), and their names say
  where they go ("…_FPGA").
- **Do not split ICs into many sub-symbols.**
  - The power pins stay on the IC; never a separate rectangle that looks like another
    chip.
  - Big multi-function parts are the exception. The ADC/DAC is drawn as one trapezoid
    per channel plus a common box, with a dashed box around all of them, and so are
    multi-unit symbols such as the PHY and the FTDI.
- **Decoupling.** One capacitor per supply pin, drawn **at that pin**, never bunched off
  to the side. The PCB then places each one at its pin.
- **Repeated blocks** are identical pages or identical tiles, differing only in names, so
  paging through the PDF shows the pattern. A missing 13th copy leaves a blank in the
  same place.
- **Net names.** Sensible, especially on long runs and anything leaving a page. Avoid
  names that read like other buses (`FPGA_SCLK_OUT` looked like I²C's SCL).
- **Comments must not go stale.** A note that names "U112", or a part that is no longer
  there, is a bug. Say "the LM27761 here", and regenerate notes from data.
- **No four-way junctions.** Fix the ERC warnings that matter, refresh cached symbols,
  and save in KiCad 10's own format (`kicad-cli sch upgrade`) so opening the file asks
  nothing.
- **Pins.** Check every pin of every generated symbol against the datasheet's pin
  **figure**. ECP5 found, all with checks passing:
  - an FDA's output pair swapped, making positive feedback;
  - a mini-HDMI with type-A numbering;
  - a SOT-23-6 EEPROM numbered like a SOIC;
  - a bit-reversed DAC port;
  - a TCXO's ground drawn as an enable;
  - a photodiode whose LCSC footprint has pad 1 = anode where KiCad's symbol has pin 1 =
    cathode;
  - three header pin-name lists printed in reverse.
- **Trace every path** with a netlist walk: signal paths end to end, power from the
  input to every pin, every configuration and strap pin, every clock.

## 5. Placement and routing

- **Floorplan first.**
  - Decide where the connectors and blocks go.
  - Run each signal path through its chips in the order the schematic draws it.
  - Then hang each chip's passives directly off its pins.
  - Leave room for labels from the start: spread out rather than bunch into a corner.
- **Orientation.** Placement follows the schematic: a horizontal series resistor is
  horizontal on the board, along the trace; a vertical shunt is vertical ("I
  even specifically asked that the 100R resistors be horizontal").
- **Rotation.** Verify what 0/90/180/270 actually do to each footprint's pads before
  relying on them. "0 = horizontal" was wrong more than once.
- **Decoupling** at the pins: straight to a ground via, on the back if that is closer.
- **Blocks.** Each functional block sits in a silkscreen box. Everything that belongs to
  it, part and label, lies inside its box; nothing else does.
  - Check it in code. Rev A of GPSDO printed 71 designators in the wrong box.
  - Identical channels are laid out identically.
- **Power.** Distribute it in pours or wide traces. GPSDO's +3V3_A lost 109 mV in 1.4 m
  of 0.5 mm track because the "plane" was never poured.
  - Check the regulator's dropout from the **worst** input. A USB port can give 4.75 V,
    less a fuse and a diode.
- **Ground.** Keep an unbroken ground reference under every fast signal. A layer change
  gets a ground via within about 1.5 mm. Keep analog and digital apart physically, and
  keep switch nodes small.
- **Plan the copper.** On GPiBridge the maze router was left only the ground vias:
  every other connection, down to each decoupling capacitor's 1 mm stub, is written as
  coordinates computed from the pads. The router's versions wandered (VBUS through
  three layers, a UART line along the board edge); the planned ones look like a person
  drew them and are no more work to write than the fixes they replaced.
- **Router.**
  - The Java autorouter (Freerouting) made things worse.
  - A simple maze router plus hand-planned routes worked. River-routing buses
    first worked.
  - When routing fails, look at postage stamps of the router's own obstacle grid around
    one failed connection. Three looks found what a day of blind rebuilds did not.
- **Clean traces.** No zig-zags, loops or detours around a part's own pins. If a resistor
  is in the way of its own trace, rotate the resistor.
- **Order reversals need a layer change.** When a chip's pins leave it in the reverse
  of a connector's contact order (GPiBridge Lite: the RP2354A against the GPIB plug),
  no single-layer routing exists, however the lines bend. Find the one place where the
  lines run in the connector's order and change layer there, once per line: on the
  Lite, where the ribbon rises into a row of series resistors, a via above each takes
  it to the bottom layer and straight down to its contact.
- **No vias in holes.** Keep vias out of through-hole drills, including the routing
  net's own. GPSDO shipped a via drilled inside a header pin.
- **Fill zones in the file you ship.** GPSDO's committed board had **no pours**: zones
  were filled into a copy for DRC, and the original went to the gerbers.
  Count `filled_polygon` in the shipped `.kicad_pcb` and fail on zero.

## 6. Silkscreen: the board explains itself

The board should be usable without the schematic. It must be obvious how *not* to make a
mistake with an input level or a plug direction.

- **Identity:** the board name; "by Jason Gallicchio and Claude"; the URL; the date; and
  "rev A", the least prominent of these. Add a QR code with
  its URL printed under it when there is a web page.
- **Connectors.**
  - Names are **big**, right next to the connector they name, never between two
    connectors.
  - Every connector that leaves the board is labelled with what it is for and its
    limits: "±1 V MAX", "15 V DC, 1 A MIN".
  - The label sits by **that** connector, not the neighbour's.
- **Header pins.** Every pin is labelled next to itself: the top row's labels above it,
  the bottom row's below. Never all on one side, which makes people probe the wrong pin.
  - Rotate the labels with the header.
  - Name the colours and signals of screw-terminal wires at the screw.
    - Centre each label under its pin, in the strip just outside the
      terminal's outline.
    - Reserve that strip before placing the terminal's own resistors, and keep
      the designator out of it.
    - A placer that slides a label sideways to clear a part makes it read as
      the neighbouring pin's. Rev A's `red` sat nearer GND than VCC.
- **Jumpers.** Say what each does. A 3-pin selector gets two labels split by a line
  aligned exactly with the centre pin. A jumper that cannot select what its
  label says is a bug Jason will find.
- **Test points.** Labelled at the pad with the rail or the expected reading ("3V3",
  "In 10 MHz 0.7-8 Vpp"). If a legend is used, it must be legible and aligned, and the
  letters unambiguous (an "I" read as a "1").
- **ICs.** Name them by function and part number ("MPY634 multiplier", "op-amp
  LF412"), along with the component values.
- **Region labels.** Boxes interrupted by their label. A label for a box must not look
  like a label for one part inside it.
- **Overlap.** Nothing overlaps anything: silk on silk, silk on pads, silk over the
  edge. A label that will not fit goes to F.Fab, not on top of something.
  - The checks must cover labels as well as components.
  - Leave out "MountingHole" and its reference.
- **Printable sizes.** At least 0.8 mm text height and 0.15 mm line width at JLCPCB.
  KiCad checks text height but **not the width of graphic lines**: stock footprints draw
  0.12 mm.
- **Pin-1 marks.** Add one only where the pad pattern is symmetric under a half turn
  **and** the library prints nothing. A second dot next to the library's triangle is one
  more dot to confuse with JLCPCB's purple one. Oscillators
  and crystals with only an "L" for a cue need a big dot.
- **Prose on the silkscreen.** Left-justified, broken at sentence boundaries, and
  checked for grammar.

## 7. Mechanical: connectors, cables, enclosure

- **Connectors point out.** Check the **3D render**, not the footprint's rotation (an RJ45 faced into the board; SMAs sideways).
- **Flush at the edge, or a little past it.**
  - USB-C must sit where its drawing says, so a fat moulded plug can seat.
  - For the **HRO TYPE-C-31-M-12 (C165948)** the board edge is 5.79 mm past the upper
    shell tab, with the mating face 0.99 mm past the laminate. Do not let a
    silkscreen-to-edge DRC rule move a connector; trim the silkscreen instead.
  - Behind an end plate, faces must stand past the board edge by the plate's thickness.
- **Cables.** Leave room for fat plugs beside each other: USB next to HDMI next to RJ45. Space SMAs for fingers and wrenches, and spread them evenly along one edge.
- **Holes.** M3 mounting holes in the corners, clear of headers (a hole through
  the 2x20 header). Leave a keep-out where cards and plugs slide in, checked in code
  (ECP5's microSD).
- **Enclosures.**
  - Design for a real one and check it against its **drawing**. ECP5 was 8 mm short of
    its Hammond extrusion, so the SMAs would not have reached the end plate.
  - Check part heights against the floor and slot positions.
  - **Ask for the vendor's 3D model, and slice it** (FreeCAD: `shape.common()` with thin
    boxes; a `BoundBox` of curved faces is loose, `distToShape` is exact). NorComp's
    plug model showed what its drawing does not: pins 1.0 mm wide for their first
    0.5 mm (a press fit in the recommended 1.00 mm hole), and the insulator flaring out
    in the last 0.1 mm under the flange, 0.13 mm from a housing opening drawn from the
    body's nominal size. Then put the vendor's model in the housing check itself, in the
    position assembly gives it, when the file is present.
  - **Follow the force through the screws.** A plate made 0.2 mm thinner than a plug's
    flange height, "so the flange always bears", left the board resting on the plug
    0.2 mm up, which the lid's screws would have pressed down, bending the board. Make
    the stack-up nominally exact and let the tolerances fall either way.
  - **Check each screw's length against its stack** (GPiBridge, 2026-10-06): from the
    head's seat, through every part it passes, to the tip, which must stop inside its
    pilot hole with thread enough to hold. The M2 x 10 first specified would have
    bottomed out 0.7 mm early in a 3.5 mm plate; M2 x 8 leaves 1.7 mm of thread and
    1.3 mm to spare. Compute it in the housing script and fail the build on a bad
    length. Size counterbores for the widest head that will be bought (an M2 pan head
    is up to 4.0 mm), as printed.
  - **Measure engraved text's strokes**, not its height. DejaVu Sans Bold at 2.6 mm has
    0.42 mm horizontal bars, under MJF's 0.5 mm guideline for engraved detail.
- **3D models.** Every part has one; missing ones were noticed every time.
- **Gender and orientation** of anything that plugs in. Label header pins 1, 2, 39, 40
  as the mating module prints them, so a module that flips upside down goes in right.

## 8. Manufacturing package (JLCPCB)

- **Upload files:** gerbers zip, BOM (one line per LCSC code), CPL (KiCad native), CPL
  JLC-corrected, assembly notes to paste, and a cost estimate. Write `release/` so that
  Jason uploads exactly that folder.
  - **CPL file names** (Jason, 2026-10-08): `<board>_cpl_jlcpcb_upload.csv` is the one he
    uploads, with JLCPCB's rotations and positions; `<board>_cpl_kicad_native.csv` is
    KiCad's own numbers, for reference. The names say which file goes to JLCPCB, which
    `_cpl.csv` beside `_cpl_native.csv` did not.
- **DRC.**
  - At least as strict as JLCPCB's rules for the chosen stackup, at every severity, 0
    errors, with schematic parity.
  - Fill the zones and save them first.
  - Count unconnected items yourself: GPSDO printed a false "UNROUTED" caption while
    DRC said 0.
- **CPL rotations.** KiCad's zero and JLCPCB's zero differ by a property of **their**
  drawing of each LCSC part. Apply two things, in this order:
  1. **Bottom-side mirror:** `rot -> 180 - rot` (fixed points 90 and 270; confirmed on 10
     placements).
  2. **Per-footprint correction**, taken only from a real "Confirm parts placement"
     preview. Absent from the table means nobody has looked; zero means somebody looked.
     Known so far:

| footprint / part | correction | evidence |
|---|---|---|
| `SOT-23-5` | +180 | GPSDO, 59 placements |
| `VSSOP-8_2.3x2mm_P0.5mm` | +180 | Icepi rebuild |
| `Texas_DRT-3` | +270 | Icepi rebuild (top side) |
| `TSOP-II-54_22.2x10.16mm_P0.8mm` | +270 | Icepi rebuild |
| `SOIC-8_5.3x5.3mm_P1.27mm` | +270 | Icepi rebuild, read twice |
| `QFN-20-1EP_4x4mm_P0.5mm` | +270 | Icepi rebuild, read twice |
| `Oscillator_SMD_SiT_PQFN-4Pin_2.5x2.0mm` | 0 | Icepi rebuild, read twice |
| `D_SOD-523` | 0 | Icepi rebuild |
| LF412 SOIC-8 (C15322), MPY634 SOIC-16W (C1523457) | +270 | Lorenz preview |
| 6-way DIP switch C54952 | +270 | Lorenz preview |
| 78L12 / 79L12 SOT-89 (C8615, C8626) | +180 | Lorenz preview |
| BNC C41416668 | +90 | Lorenz preview |
| USB-C HRO TYPE-C-31-M-12 C165948 | 0 | Lorenz (built), GPiBridge preview. Its *position* needs moving 1.572 mm: see "Part positions" below |
| GPiBridge's eleven: RP2354A 0, SN75160B +270, SN75161B 0, AO3401A, 2N7002, XC6206 +180, BM03B +180, AOTA inductor +180, KT-0805Y/G and NCD0805R1 LEDs 0 | as predicted | GPiBridge rev A preview, 2026-10-06: "all of the rotations were correct" |

  Third-party rotation tables disagree with each other: GPSDO took one and got two wrong,
  one of them on 59 placements. List every unverified footprint in a
  `PLACEMENT_CHECKS.txt` for the day of ordering.
- **Predict the corrections from JLCPCB's own drawings** (GPiBridge, 2026-10-06).
  - The EasyEDA land pattern of each LCSC part (`footprint_check.py` fetches it), turned
    until its pads lie on ours *by pin number*, predicts the correction: minus that
    turn. It reproduces every top-side correction in the table above (7 footprints),
    for all 14 part numbers that use them on the Icepi, GPSDO and ECP5 boards.
  - It must be **per part, not per footprint**: JLCPCB draws the SN75160B lying down and
    the SN75161B upright, on the same SOIC-20W.
  - For two-pad polarized parts, use the **polarity mark** in their drawing, not the pad
    numbers. JLCPCB's KT-0805 LEDs call the cathode pad 2, and their AOTA inductor has
    its dot at pad 2 where Raspberry Pi's has it at pad 1.
  - It is untested on the bottom side. ECP5-2ADC-2DAC stores its bottom SOT-23-5s
    mirrored left-right, while the Icepi parts behind `BOTTOM_FLIP` are mirrored
    top-bottom. Look hardest at those in the preview.
  - Put predictions in the CPL, marked "predicted", and still list them in
    `PLACEMENT_CHECKS.txt`.
  - **Confirmed:** all eleven of GPiBridge's predictions (12 placements, including the
    SN75160B's 270 beside the SN75161B's 0 on one footprint, and the LEDs and inductor
    read by polarity mark) were right in its preview (2026-10-06).
- **Preview checkerboards.** JLCPCB's preview shows an "unknown part" checkerboard where
  their library has no drawing, so those rotations cannot be read there. The Lorenz RGB
  LED went in right from the plain CPL; say so in the notes.
- **Part positions: JLCPCB places THEIR origin.** The CPL's Mid X/Y is where JLCPCB
  puts the origin of *their* library drawing of the part. Where that is not KiCad's
  origin, the part lands off its pads by the difference, whatever the rotation.
  - Every USB-C so far has done it. JLCPCB's drawing of the HRO TYPE-C-31-M-12
    (C165948) has its origin 1.572 mm from KiCad's, towards the pad row. So the preview
    showed it hanging off the board edge with its pads beside ours, and Jason moved it
    by hand on every board (GPiBridge, 2026-10-06).
  - The Lorenz board's answer, that nothing in a CPL can address their model's origin,
    was wrong. The JLCPCB CPL is read by JLCPCB alone (the native CPL stays as KiCad
    wrote it), so put each part where their origin goes.
  - `footprint_check.py` fits their land pattern onto ours and reports where their
    origin sits in our footprint (its "datum"); GPiBridge's `make_release.py` adds it,
    turned with the part, to the JLCPCB CPL, and `PLACEMENT_CHECKS.txt` lists what
    moved. Check in the preview that each moved part sits on its pads.
  - Through-hole parts with keyed hole patterns go in one way only; note them.
- **Through-hole parts.** Say which are assembled and which are left for hand soldering.
  JLCPCB's THT labour is per order (about $3.58) plus per joint.
- **Fab review.** JLCPCB may return a "gerbers_Y11" set to confirm. Compare it with what
  was sent: hole counts, NPTH, outline.
- **Cost estimate:** board, parts, setup, stencil, Extended fees, SMT and THT joints,
  shipping and duty, for 1, 2, 5 and 20 boards. Note the quantity break where
  panelising pays.
  - Calibrate against JLCPCB's cart. GPiBridge (5 boards, 2 assembled, 4 layers, ENIG,
    60 x 25.5 mm): $24.80 PCBs + $60.56 assembly; GPiBridge Lite $25.85 + $40.18
    (2026-10-06). The estimate was about $5 low on each: it left out the through-hole
    labour that the USB-C's soldered shell legs bring. ENIG is most of the PCB price at
    this size.

## 9. Bring-up and debuggability

- **Plug in; don't solder or hold.** Jason does not want to solder wires or hold probes
  to debug. Provide labelled test points with ground clips nearby, U.FL monitor taps for
  signals worth scoping, and headers that take standard probes.
  He has many USB scopes, and wants to plug one in and walk away. So: **lots** of taps,
  on every analog node worth a look.
- **A monitor tap's series resistor is its divider and its load**.
  - 450 Ω is a 10× probe into a 50 Ω scope, and loads the node with 500 Ω.
  - 1 kΩ is ÷21, and loads it with 1 kΩ.
  - A series capacitor keeps a biased node's DC (and keeps a 50 Ω scope from
    pulling current out of a rail).
  - **Never tap a node whose amplitude sets a timing**, such as a comparator's or
    squarer's input behind a series resistor. Plugging the scope in would move the
    thing measured. Tap the low-impedance side.
  - U.FL is rated for 30 matings, MMCX for about 500.
- **Read the DNP flag before saying what is fitted.**
  - A part drawn on the schematic is not a part on the board.
  - GPSDO's pps jacks draw a 51 Ω terminator, marked DNP. A review round called the
    inputs terminated and dropped a test that works.
  - `excluded_from_assembly.csv` answers the question in one grep.
- **Try a new bench source as an aggressor before trusting it as a channel.** A
  USB-powered CircuitGear's DDS 10 MHz on one GPSDO input made every other channel's
  beat chatter (common mode: the pair differences stayed clean). It brings its ground
  and its spurs with it.
- **Rails at a glance.** An LED per rail, and an "in range" indication where it matters. Drive the LEDs so that they do not load a quiet rail.
- **Bring-up order** in a `HANDBOOK.md`: current-limited bench supply first, then each
  rail, then the programmer, then the first firmware, then the interfaces.
- **Bench instruments are scriptable.** Jason's lab drives its instruments from Python
  (`lab-instrument-control`: Siglent scopes and generators, an HP 33120A over GPIB, an
  ADALM2000), so the agent can take its own measurements once a board is cabled. Design
  tests that use them.
- **Firmware is part of the design.** A board with an MCU or FPGA needs its first
  firmware written and building before the board is ordered. That shakes out pin and
  clock choices: the GPSDO's I²C driver could not *read* until bring-up.
- **Test the pin layer against the datasheets on a PC** (GPiBridge `test_wire.c`). Stub
  the SDK's GPIO calls and model the chips on the other side from their function
  tables. Then check, after every pin change, that no wire has two drivers and nothing
  is driven into an unpowered chip. Plant a bug or two to prove the test can fail.
- **Symmetric connectors need a check, not just a mark.** A 2 × 12 grid solders in
  turned round as easily as right. Give a meter check after two pins are tacked (one
  contact must read 0 ohms to GND).
- **Say exactly what to buy and what plugs where** (GPiBridge `BRINGUP.md`). Name the
  probe and its cables, give each stage's connections and what the agent does then, and
  start with a partner both ends of which are scriptable: a Prologix in device mode for a
  GPIB board. Jason asked "what do I buy, and how do I connect it" before anything was
  built.
- **Check the protocol with somebody else's decoder.** Record the simulated bus as a VCD
  and have sigrok-cli's decoder read it back (GPiBridge `firmware/test/sigrok_check.py`).
  An engine and a simulator written by the same author share their misunderstandings; an
  independent decoder does not.
- **Give the board a way to see itself.** A spare core sampling its own pins into a VCD
  is a logic analyser with no wires, and it answers "how do I probe this?" for most
  problems.
- **Check a product name against trademark rules, not just search results.** Raspberry
  Pi's rules forbid "Raspberry" as a brand for hardware; "RaspberryGPiB" was proposed and
  had to be declined.

- **Open-drain on an RP2350** (GPiBridge Lite): assert by enabling the pin's output,
  release by making it an input, and set the pad's output override to LOW
  (`gpio_set_outover(pin, GPIO_OVERRIDE_LOW)`) so no software path can ever drive the
  line high. `gpio_init()` rewrites the pin's whole control register and clears the
  override: set it after. A host test that checks, after every pin change, that no
  output is on without the override makes the order a tested fact.

## 10. Verification gates (run them every build)

Before calling a schematic, PCB or release done:

1. ERC clean (the warnings understood), with the netlist exported.
2. Every symbol pin checked against the datasheet figure.
3. A path trace of every signal, power rail, clock and strap.
4. No overlaps on schematic sheets, checked in code and by eye on the PDF.
5. DRC at least as strict as the fab's: 0 errors and 0 unconnected, on the shipped file,
   with its zones filled.
6. Pads where KiCad puts them; connectors pointing out in the 3D render; every part with
   a 3D model.
7. Silkscreen:
   - no overlaps;
   - every label inside its box;
   - text at least 0.8 mm high and lines at least 0.15 mm wide;
   - nothing printed off the board.
8. Parts:
   - every SMD part with an LCSC code;
   - every code's description matching its value and package;
   - every ordered land pattern fitting the board (no HOLE);
   - stock and price fetched with a timestamp.
9. CPL native plus JLC-corrected, with `PLACEMENT_CHECKS.txt`.
10. The revision and date on the silkscreen match the source of truth. A release is
    stamped DRAFT until the date is a real date.
11. Every PDF page is sized to what is on it, centred, and filled less a half-inch margin.
    This covers schematic sheets and assembly drawings (§2, "Every page fits what is on it").

## 11. KiCad 10 and tooling quirks

- **Running KiCad.** From the AppImage, `kicad-cli` is a subcommand. For its Python,
  extract the AppImage once (`--appimage-extract`) and run `AppDir/AppRun python3.11
  script.py`: calling `usr/bin/python3.11` directly with `LD_LIBRARY_PATH` set
  segfaults on `import pcbnew` (10.0.6). GPiBridge's `tools/kienv.py` finds either,
  from environment variables with defaults under `~/.local`.
- **pcbnew from a script** (GPiBridge, 2026-10-06):
  - `board.Save()` also rewrites the `.kicad_pro` with default net classes and rules.
    Write the project file again after saving.
  - A board built in memory has no connectivity until `board.BuildConnectivity()`.
    Without it, `ZONE_FILLER` judges islands unconnected and silently drops pours (the
    ground under a USB-C vanished).
  - `FOOTPRINT.SetField()` with a new name (LCSC, MPN) creates a **visible field on
    F.SilkS**. Hide it and move it to F.Fab, or 400 silkscreen DRC errors appear.
  - `SetBold(False)` resets a text's stroke to size/8. Call it before
    `SetTextThickness()`.
  - KiCad's stroke font is wide: capitals advance about 0.9 x the size. Measure a
    text's real extent with `GetEffectiveTextShape().BBox()`; `GetBoundingBox()` adds
    margins.
  - **Deterministic boards.** Every item gets a random UUID, so each rebuild of an
    unchanged board diffs by about 20 000 lines. Call `pcbnew.KIID.SeedGenerator(n)`
    before creating anything, and run the script with `PYTHONHASHSEED=0` so set
    iteration (creation order) repeats: the file then comes out byte for byte the same.
    Seed once and a change to one footprint (more graphics, say) shifts every later
    UUID and reorders the file; reseed before each footprint (from a hash of its
    reference) and before each later stage, so a change shows up only where it is.
- **DRC findings that a script's own checks miss:**
  - `connection_width`: a track that ends exactly on a pad's corner (end the track at
    least half its width inside the pad); and two same-net vias whose pads touch on a
    layer neither uses (remove unconnected inner pads, or bridge them on the outer
    layer).
  - `track_dangling` points at a track's *start*, even when its other end is the
    loose one.
  - A track that ends inside a via's pad but outside its drill does not connect it
    on a layer whose unused pads are removed: end tracks at the via's centre.
- **The GUI under Wayland** (no middle-drag, layers not repainting until a zoom): it is
  the native Wayland canvas, not the file. Start KiCad with `GDK_BACKEND=x11` set (a
  two-line wrapper script).
- **Schematic quirks:**
  - A field's justification is mirrored when the symbol's rotation plus the field's
    angle is 180.
  - A footprint field's angle is **absolute**.
  - Pins that touch a wire's interior do not connect.
  - Text bounding boxes are about 2.0x the text size high, not 1.6x.
- **easyeda2kicad footprints** are in the old format (run `kicad-cli fp upgrade`), and
  their courtyards exclude the pads.
- **DRC rule trap.** A custom `silk_clearance` rule on text makes KiCad 10 report every
  designator against Fab text and courtyards as `silk_overlap`.
- **Inkscape 1.x** hangs with `DISPLAY`/`WAYLAND_DISPLAY` and a session bus. Run it with
  those unset and `DBUS_SESSION_BUS_ADDRESS=/dev/null`.
- **Scratch space.** An agent's scratchpad directory can vanish between sessions. Keep
  build scratch inside the project's gitignored `build/`.
