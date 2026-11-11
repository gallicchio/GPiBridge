# CLAUDE_PCB.md: how to design a board Jason will be proud of

Read this before starting or changing any PCB in this repository. It distils what went
right and wrong on six Claude-generated boards. Every rule here is something Jason had
to ask for, or a fault that a fab, a reviewer or a working board found.

| board | outcome | where the history is |
|---|---|---|
| **AI UNLEASHES CHAOS** (Lorenz attractor, `~/ai_unleashes_chaos`) | Built by JLCPCB; worked first time, including the RGB lamp and the sync input | its `CLAUDE_CODE_CHAT.md`, `docs/MANUFACTURING.md`, `docs/DESIGN_REVIEW.md` |
| **GPSDO-PYNQ-Z2** | Built by JLCPCB; brought up; rev B list from real measurements | `GPSDO-PYNQ-Z2/README.md` (rounds and prompts), `REVB_CHANGES.md`, `DESIGN_REVIEW_RESPONSE.md`, `HANDBOOK.md` |
| **Icepi Zero JLC rebuild** (`IcepiZeroADCDAC/jlcbuild`) | Built by JLCPCB after a wrong switch stopped the line | `IcepiZeroADCDAC/jlcbuild/README.md` |
| **ECP5-2ADC-2DAC** | Designed, five LLM reviews reconciled, not yet ordered | `ECP5-2ADC-2DAC/CLAUDE_CODE_CHAT.md`, `DESIGN_REVIEW_RESPONSE.md` |
| **IcepiZeroADCDAC** (maximal/minimal) | Abandoned: the BGA would not escape with an autorouter | `IcepiZeroADCDAC/README.md` |
| **GPiBridge** and **GPiBridge Lite** (USB-C to GPIB; designed here, then moved to its own public repository, github.com/gallicchio/GPiBridge, cloned beside this one at `../other/GPiBridge`) | Both ordered from JLCPCB on 2026-10-06, 2 assembled of each; not yet received | its `CLAUDE_CODE_CHAT.md`, `PLAN.md`, `DESIGN_NOTES.md`; its `CLAUDE_PCB.md` is a public snapshot of this file |
| **Halloween board** (`~/mudd/pcbs/halloween1`: a cute, physics-y board for Jason's six-year-old, the first with real power: 12 V, amperes into PCB coils) | In design from 2026-10-07 | its `CLAUDE_CODE_CHAT.md`, `PLAN.md` |
| **GPS GH adapters** (`~/mudd/pcbs/gps-gh-adapters`: JST-GH GPS port adapters, Holybro 10-pin to Cube 8-pin and an any-to-any debugging hub; public, github.com/gallicchio/gps-gh-adapters) | Designed 2026-10-08/09, rev A, not yet ordered | its `CLAUDE_CODE_CHAT.md`, `research/PINOUT_EVIDENCE.md` |
| **LAoE Discrete Op-Amp** (`~/mudd/pcbs/op-amp-pcb`: the Lab 5L op-amp of *Learning the Art of Electronics* from the book's six SOT-23 2N3904/2N3906 on a 100 x 100 mm board whose silkscreen is the schematic, for a first electronics lab; public, github.com/gallicchio/op-amp-pcb) | Designed 2026-10-24, rev A; design review round 1 (author, Gemini 4 Argon, Kimi K3) closed and applied 2026-10-27 (`design_reviews/`); the 741-style current limit replaced by one 330 ohm resistor inside the loop 2026-10-28; pre-order checks of 2026-10-29 (JLCPCB's drawings overlaid by the upload CPL, pin names, pages fitted, one rail missing simulated) passed, ready to order | its `CLAUDE_CODE_CHAT.md`, `docs/DESIGN_NOTES.md`, `docs/HANDBOOK.md` |
| **LAoE PID Motor Control Loop** (`~/mudd/pcbs/motor-pid`: Lab 10L of *Learning the Art of Electronics*, a motorized fader held to a target by P, D and I on a 170 x 120 mm board whose silkscreen is the schematic; seven LM321 singles, a D2PAK push-pull on 2 oz copper, a PTC fuse ahead of DRIVE; public, github.com/gallicchio/motor-pid) | Designed 2026-10-24/27, rev A, design review round 1 closed (three reviews applied); pre-order checks from the newer lessons 2026-10-29 (section 28), BOARD_DATE 2026-10-29, being ordered | its `CLAUDE_CODE_CHAT.md`, `docs/DESIGN_NOTES.md`, `docs/HANDBOOK.md` |

Citations like "(Lorenz P3)" or "(GPSDO r29)" point at the prompt (P) or round (r) that
taught the lesson. "(Rosenberg)" is Hans Rosenberg's *Electronic Product Development
Checklist*, version 5 (2025), folded in on 2026-10-07 wherever this file did not already
say the same thing. The PDF is copyrighted; it lives only in `halloween1/references/`,
which git ignores.

Sections 12-16 are different from the rest: general practice for the fast digital, RF
and high-power boards to come, written down before a board of Jason's needed it (Jason,
2026-10-07: "be sure to incorporate tips for those fancier boards"). They cite their
sources instead of a board. When a board teaches one of them the hard way, move the
lesson up beside the others and cite the board.

---

## 1. How Jason works with you

- **Log everything.** Each prompt goes verbatim, with minor typos fixed, into the
  project's `CLAUDE_CODE_CHAT.md`, followed by your response. Head each response with the
  real time range of the work. Put decision tables **in the response**, not only in a
  README. Responses show the renders as they were then, so the next prompt makes sense;
  include images only when they changed (Lorenz P7, P8).
  - The log lives in the board's own directory (`OpticsPCBs/<board>/CLAUDE_CODE_CHAT.md`),
    never at the repository's top level. A conversation belongs to its board, not to
    OpticsPCBs as a whole. CostasLink's first response was written to the top level and
    had to be moved into the board's log (Jason, 2026-10-10: "They are specific to the
    project or the board, not OpticsPCBs as a whole").
- **Questions.** Ask in the chat and in a temporary `QUESTIONS.md`; he answers in
  `ANSWERS.md`. Both are gitignored. Check them when you can (ECP5 P1).
- **"Go all night".** Keep going, log progress in the chat as you go, and write findings
  down before a session or the power could die (GPSDO r28). Do not stop to ask what you
  can decide; record the decision and why.
- **Be opinionated.** Recommend, with the trade-off stated; do not survey options you
  will not pursue (GPSDO P14).
- **Self-critical review.** End with the most likely causes of a dead-on-arrival board
  and what mitigates each (Lorenz P3: "If I got these back and told you they didn't
  work, what would be the most likely cause?").
- **Think five steps ahead** (Rosenberg). Before drawing each block, ask:
  1. What could go wrong, and what on the board would rescue it? A DNP footprint for
     the alternative part, a 0 Ω choice, a pi network, a spare pin brought to a pad.
     Prototype the subcircuit you are least sure of, in simulation or on the bench.
  2. Can it be assembled (by JLCPCB, with no hand work), and serviced?
  3. Will it last? Heat, ageing, and voltage, current and power at the worst case.
  4. Can one part do two jobs? "The best part is no part."
  5. Is there a simpler way?
  6. Can the number of unique parts drop, especially resistor and capacitor values?
     Fewer BOM lines mean fewer Extended fees, fewer feeders and fewer chances to fit
     "10" where "10k" was meant.
- **Rev A until ordered.** It stays "rev A" until Jason pays a fab. Then:
  - lock it: a git tag, a `<board>-revA.zip` of the project and `mfg/release/`, and
    SHA-256 sums;
  - start `REVB_CHANGES.md`, applied all at once (Lorenz P2, GPSDO P37, P42).
- **Outside reviews.** When the board is ready, write a brief for other LLMs and keep
  everything about the reviews under one `design_reviews/` directory at the project's
  root (op-amp board, 2026-10-24, Jason: "make a new directory called design_reviews
  ... They should make a new directory within this design_reviews directory that
  includes the date and their name. They should write a report in their own directory
  and only ever modify files within their own directory, since many agents will be
  doing the review at the same time. If they need to copy or clone any part of this
  project, they should do it in their own directory"). The op-amp board's
  `design_reviews/DESIGN_REVIEW_PROMPT.md` is the template:
  - `design_reviews/DESIGN_REVIEW_PROMPT.md` is the brief; `design_reviews/README.md`
    explains the layout and indexes the rounds and their verdicts;
  - each reviewer works in `design_reviews/<YYYY-MM-DD>_<Model-Version>/` (letters,
    digits, dots, hyphens and underscores; `2026-10-24_Claude-Fable-5.1`), writes
    `REPORT.md` there, and copies the project into its `project/` subdirectory to build
    or change anything (an `rsync` recipe in the brief, excluding `.git`, `build/`, the
    datasheets and `design_reviews/` itself); the project's `.gitignore` has
    `/design_reviews/*/project/` so the copies are never committed, and everything else
    a reviewer leaves is kept;
  - the brief says in bold, first, that only files count (below), lists what the build
    rewrites so "do not run the build in place" is concrete, states the claim to break
    with the board's own numbers, numbers the things to attack with the file to read for
    each, restates this file's rules as checks (the reviewers cannot read it), gives a
    tools table with what each command writes, lists what is already known or decided,
    and prescribes the report's sections (verdict; findings table first, then each in
    full with severity, place, evidence, fix, confidence; the brief's questions answered
    by number; what was checked and found right; what could not be checked; publishing
    concerns; patches);
  - the author's own review goes in the same place under its own model's name, written
    before reading anyone else's (below);
  - the date orders the rounds: a second round is a later date, not a "2" suffix. (The
    boards before the op-amp used `design_review_<Name>/` directories at the root and
    `design_review_<Name>2/` for the second round; leave those as they are.)
  Then reconcile the reviews by evidence (datasheet numbers), not by majority (ECP5
  P15-P17).
  - **What the op-amp's own round-1 review found** (2026-10-24, the author reviewing
    first, in `design_reviews/2026-10-24_Claude-Fable-5.1/REPORT.md`), each now a check:
    - **Derive what each switch position does on its own from the netlist.** A 2-pole
      DIP wired as a chain (pole 1 in series with the 1 k, pole 2 across the 1 k) made
      "2 alone" an open circuit while the board, the sheet and the handbook all called it
      "the bare 100 pF"; the checker's "pole 2 shorts R14" was true and useless. Write
      the switch table (each pole alone, both, neither) from the netlist, and assert
      each row.
    - **Mark ON on the silkscreen** at the side the footprint says, and make the
      preview check "the part's own ON marking is on the side of the silk ON". "On is
      toward the number" cannot be checked in a preview and was not true as drawn.
    - **A teaching board's bench-supply current limit is part of the design.** Compute
      what a scope's ground clip on every probe loop does (here 0.55 to 0.68 W into an
      0805 when Q2 C or Q3 E is grounded) and what a shorted output does; print the
      limit on the board and make it the handbook's rule, not a bring-up step.
    - **Rate the part JLCPCB stocks, not the famous maker's.** The C20526 "MMBT3904" is
      200 mW and 625 K/W where onsemi's is 350 mW and 357 K/W; "a short to a rail is
      survived" was written against the wrong datasheet.
    - **Do not change the project while a round runs.** The reviewers hold copies of a
      stated commit; the author's own fixes go into a tested patch in the author's
      review directory and are applied when the round is reconciled.
  - **What the outside reviewers then found on the op-amp** (2026-10-27, Gemini 4 Argon
    and Kimi K3), each now a check:
    - **A margin taken at 0 V in a class-B stage proves nothing about the load.** The
      author's "100 pF of coax raises the margin to 90 degrees" was measured with the
      push-pull in its dead band; a few volts off zero the follower oscillated at
      13 MHz.  Simulate capacitive loads in transient with the output well away from
      zero, and isolate the jacks with a resistor *after* the feedback tap (emitter
      sense resistors are inside the loop and isolate nothing).
    - **Size the resistors a misplaced scope clip loads, not just the supply limit.**
      A clip on Q3 E drew 45 mA, under the 50 mA limit, and put 0.65 W in an 0805.
      Compute every loop to ground at the real current and give each resistor a
      package that survives it (here a 1 W 2512 and a 1206).
    - **Read the side view for a terminal block's wire face.** "3.60" in the front view
      was the pin length; the pins sit 4.0 mm from the back.  EasyEDA draws the wire
      openings; fit them, not just the pin row, and set the CPL so they face the edge.
    - **A lookup on the first designator of a row is a bug.** PLACEMENT_CHECKS matched
      only "Q1" of "Q1, Q3, ..." and gave whole groups the wrong line or none.
    - **Model the rail diodes and bypass in the simulation** and take the rail voltage
      from it; a hard-coded 14.6 V beside ideal 15 V rails broke the handbook's KVL.
    - **Count pads, not pad numbers.** Four BNC posts numbered "2" collapsed to one in a
      dict keyed by number: 9 joints a board went missing from the cost.
    - **Reviewers misname themselves.** Kimi K3 signed its review "Claude"; ask the
      user which model ran before trusting a directory's name.
    - **Protection is a part count against the board's message.** On a board whose
      point is "op-amps are just transistors", a 741-style limiter (two transistors,
      two sense resistors, two diodes) made a third of the transistors not the
      op-amp.  One resistor inside the loop (330 ohm from the push-pull to OUT, the
      feedback taken after it) did the same job: a short draws 46 mA, the SOT-23s
      stay at 127 mW of 200, and it also isolates a cable.  Sweep the value for the
      smallest one with margin (270 ohm left 84 % of the rating at 25 C), keep no
      probe loop on the node it protects, and prefer the protection the student
      reads as one part.
  - **A second round before ordering** (ECP5 P31, 2026-10-07): after the fixes, a
    second brief (`DESIGN_REVIEW_PROMPT_2.md` beside the first, in the op-amp layout,
    the reviewers in new dated directories), so the
    rounds sit side by side. The brief says what changed since the first round, states
    the board's numbers and the claim "nothing blocks the order" for them to break,
    lists every tool with the command that runs it and where it writes, and restates
    this file's rules as checks: reviewers who have only the git branch cannot read an
    uncommitted `CLAUDE_PCB.md`, and the lessons added since the first round are the
    new questions. Reviewers copy anything they want to change into a temporary place;
    the author's own KiCad may have the project open, so nothing in the tree is touched.
  - **Review the design yourself first, before reading theirs** (OWL round 1,
    2026-10-09). With the four reports unread, the author's own pass found the one
    fault none of them had whole: a driver standing on its sense shunt, so its supply
    minus the shunt's drop sat under its UVLO in the worst corner (Kimi had the UVLO
    "minor", without the shunt). Then read them in full and weigh each finding by its
    evidence; the ranking that came out (Kimi: ran everything, found three real bugs,
    wrote no report; Gemini: broad, patched, two findings wrong and severities
    inflated; Grok: best judgment, saw the magnet cap nobody else saw; GPT: thin) says
    a review's worth is in what it ran and re-derived, not in its length or its verdict.
  - **Rebuild after folding reviews in, and expect three passes.** Every change the
    reviews earned went through the generators and the whole build: the first board
    pass showed a capacitor moved beside a sensor had overlapped two coil courtyards and
    blocked the shared fault line's one pass, and an ESD diode placed 0.2 mm inside an
    antenna's keep-out could not be reached; the second showed the fault line still in
    pieces (the new nets shifted the routing order: the shared lines now go first); the
    third was clean. A fix that is not rebuilt is a hypothesis.
  - **Only what is written down counts** (ECP5 P32, 2026-10-07: Grok's round-2 review was lost because it answered in
    its chat window and Jason closed the windows). Put it at the top of every review brief, in bold, before the ground
    rules: "Nothing you say in the chat will be read or kept. Your review exists only if it is a file in your
    directory." Make it equally plain that creating that directory and writing into it is **required**, not a change to
    the project: "do not modify the project" must never read as "do not write anything". Give the exact path of the
    report file, and ask the reviewer to write its verdict and findings table into it first, then fill it in.
  - **Before a round, fix what the lessons file already asks for.** Jason (ECP5 P31):
    "If you think those things should be fixed before others do a design review, fix
    them now." A reviewer's time on a known gap is wasted; the ECP5's fiducials, layer
    markers, order-number marker and the bench input's fuse went in as build 31 the hour
    before the brief.
- **Git.** In OpticsPCBs, the branch is shared with other agents and projects. Do not
  commit or push unless Jason asks, and never commit another project's files. In a
  project's own repository, where Jason says it is the agent's alone, **commit as you
  go** (Halloween board, 2026-10-07: "Commit as you go. You are the only one on this
  repo, so use git").
- **Minimise what Jason must do beyond uploading the JLCPCB order,** even at some extra
  cost (Halloween board, 2026-10-07). Every extra step lowers the odds that a deadline
  project is finished, most of all steps that depend on each other: printing, ordering,
  gluing magnets.
  - Prefer what JLCPCB makes and fits: PCB parts instead of printed ones, connectors
    instead of wiring, break-away tabs instead of separate orders, SMT standoffs
    instead of stick-on feet.
  - What remains goes on one list, and one print plate with no supports.
  - Count the steps in the plan, and say which depend on which.
- **Open source by default, permissive** (GPS adapters P2, 2026-10-08: "This is going to be
  an open source project with permissive license"). A new repository gets `LICENSE`
  (CERN-OHL-P-2.0 for the hardware, MIT for the scripts, the third-party notes) and
  `LICENSE-HARDWARE.txt` in its first commit, as GPiBridge has; the schematic's title
  block and the board's back say which.
- **Every request is a lesson.** When Jason asks for something on one board it goes into
  this file at once, as a rule with its reason, so he never asks for it again on the
  next board (ECP5 P26: "Put this requirement and lessons on how to do it in
  CLAUDE_PCB.md. Do that for all such requests and lessons").

## 2. Build system and sources of truth

- **One command makes everything:** schematic, PCB, checks, manufacturing files,
  renders, documents and cost estimate. `--clean` removes exactly what it generates, so
  it is obvious what lives in git (Lorenz P1, P2).
- **Reproducible from a fresh clone** on another machine (Lorenz P2, P7):
  - Vendor every symbol, footprint and 3D model the board uses into the project's own
    library. A fresh KiCad AppImage has an empty `~/.local/share/kicad/10.0/symbols`.
  - Relative paths only (Icepi P15): the next rule.
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
  - Audit on 2026-10-06: about 100 committed files in the older projects broke it.
    - Library tables and 3D model paths into `/home/annika`, `/Users/Xande` and
      `/Users/cathe`: SyzygyRadioDrivers, PMOD_direct_to_SMA, VerifierPCB, Photodiode
      amplifiers, STM32. Those boards open without their libraries and models anywhere
      else.
    - Netlists with an absolute `(source …)`: ECP5, GPSDO, IcepiZeroADCDAC,
      SyzygyRadioDrivers' review, and the old Windows ones (`C:\Users\cathe\…`).
    - Icepi's inherited plot directory, `/home/cyao/…`.
    - Scripts reading data or scratch files from outside the repository:
      SyzygyRadioDrivers' `SMABridgeTestAnalysis/`.
    - About 30 scripts name tools under `~`, many with no environment override
      (ECP5's `gen/gen.py`, `gen/kisch.py`, `tools/kisym.py`; GPSDO's `gen/kigen.py`).
    - The root `.gitconfig`'s diff driver in `/home/annika/.venv`.
    - Caches committed by mistake: `fp-info-cache`, `temp-freerouting.dsn`, STM32Cube's
      `.mxproject`.
- **One source of truth per fact**, and everything else derived from it:
  - pin assignments drive the schematic, the firmware constraints and the pinout
    document (Icepi P7, GPSDO P29);
  - part numbers live in one parts table;
  - the revision and date live in one place, and the silkscreen reads them;
  - placement drives the silkscreen labels that belong to parts (GPSDO r29: hand-placed
    "H"/"T" markers drifted away from their heaters).
- **One place for every parameter and every computed passive** (Jason, 2026-10-12: "Is
  the source of truth for the schematic, PCB, and simulations duplicated or all in one place
  (one place for each parameter or passive value)? If that source of truth is changed, does
  everything downstream get updated and remade? If there are hard coded things that cannot be
  traced to a single initial source of truth (often in markdown documentation), check that
  they are at least up to date."). Ask it of every board before an order, and do what follows.
  - **A value the arithmetic chooses is written once**, in the design script (CostasLink's
    `sim/budget.py`). The schematic generator gets it through a lookup to the parts table's
    nearest stocked value, which asserts the match (`gen/levels.py`: `res_key`, `cap_key`,
    `VAL`). Every note that quotes it is formatted from the same results. A passive may be
    typed into a generator only when nothing else uses its value: a decoupling capacitor, a
    pull-up. A resistor that also enters a latency sum or a trim's reach is a parameter.
  - **Run-time code gets the board's numbers from a generated module** (CostasLink's
    `gateware/board_constants.py`, written by the build from the budget). The driver and the
    register scripts import it, because they travel to the target without `build/`. A test
    fails when the module differs from the build. A constant copied by hand into a driver
    goes stale silently. The driver's `A_REG_V` had been the 10 m case's level, not the
    regulated one: 0.1 dB.
  - **Changing the source remakes everything downstream in one command**: the netlist, the
    board, the gateware includes, every analysis and its plots, the block diagrams. Any study
    a document quotes is a build step. A study left out of the build breaks unnoticed:
    CostasLink's `sim/wifi_channels.py` had crashed since its last edit. Only the network
    steps (release, cost) stay manual, and the build says so.
  - **Hand-written documents are checked, not trusted.** Every number a document quotes from
    the build has a claim in a docs step (`tools/doc_check.py`): a pattern, the files, the
    value it must read now. A claim that no longer matches anywhere fails too, so rewording a
    sentence cannot drop its check silently. Chat logs, review rounds and changelog rows are
    history and are not checked. Mark a past number as past in the text ("build 17 had …").
  - **Evaluate the design as fitted, not as computed.** Run the design arithmetic again with the
    stocked values the schematic draws, in the same script, and assert the result.
    - CostasLink's Costas loop was designed for 3000 Hz, ζ 0.707; the fitted 10 k makes it
      2916 Hz, ζ 0.687.
    - The budget had printed an "E24" 9.1 k that the board never had.
    - Its block diagram quoted the computed values, with a 2 % overshoot. A phase step's real
      overshoot with the PI's zero is 21 %.
  - **Then grep for the old number.** "If I change this, what still says the old value?" Two
    auditors (subagents, one per document group) checked every number in CostasLink's documents
    against the JSON (Prompt 30). The audit found:
    - 23 computed or shared passive values typed into five sheet generators. They were
      consistent, but nothing tied them to the budget.
    - A sheet note giving the log amp's input noise as 0.8 mV. That is the demodulator's input
      noise; the right figure is 2.3 mV, 9 dB more.
    - The driver's hand copies of the gains, levels and noise bandwidths. Its bring-up check also
      left out the I2C part added two prompts before.
    - The latency and its halves quoted in nine places as they were before build 18's 33 Ω made
      them 23.5 ns (8.5 + 15.0).
    - The supply current, in five documents, a revision behind. The budget also counted six
      comparators where the board has eight.
    - About 80 more stale figures in the plan: the noise floors, the isolation table, the ranges
      and the header pins.
    - Figures that no script computes at all, such as section 19's passive knobs. A figure no
      script produces is a figure nobody can update: write the script.
- **Generated documents.** From the source of truth, generate:
  - the pinout (ASCII art), a bring-up handbook and the end-user guide (GPSDO P29);
  - PDFs and PNGs of every sheet, layer plots cropped to the board outline (Lorenz P2),
    and 3D renders from several sides.
- **Look at the output.** Export the schematic to PDF/PNG, render the board, and look,
  as Jason will. Most of his corrections were visible in one glance at a render.
  - **To look at one corner as the fab prints it**, use
    `GPSDO-PYNQ-Z2/pcb/silk_region.sh BOARD X0 Y0 W H out.png`.
  - It plots F.SilkS, F.Mask and Edge.Cuts one at a time
    (`kicad-cli pcb export svg --mode-single --page-size-mode 0`). It crops
    each by rewriting the SVG's `viewBox` in board millimetres, recolours it
    and stacks the three.
  - One plot of all the top layers buries the silkscreen under copper fill
    and Fab text (GPSDO r45).
- **Every page fits what is on it: sized to it, centred, filling it** (Jason, 2026-10-29: "The
  board in ./mfg/release/CostasLink-PYNQ-Z2_assembly_top.pdf should take up the entire page (with
  a reasonable margin). Right now, if I were to print it, I couldn't read it. In general, the
  schematics, PCBs, and PDFs should be sized and centered properly. I've seen many examples of
  things hanging off of the page or the page being far too big for the thing on it.").
  - Schematic sheets, board plots, assembly drawings, block diagrams, renders and figures. The
    drawing spans the paper less a margin of about half an inch (12.7 mm, past any printer's
    unprintable edge), in whichever orientation suits its shape, with its centre at the page's.
    Nothing hangs off an edge; nothing sits in a corner of a page several times its size.
  - **The exporters do not do this.** kicad-cli plots a board 1:1 where it lies on its sheet. The
    CostasLink assembly drawing put the 120 x 100 mm board in the top-left corner of an A4 page,
    using 41 % of its width. Its `--scale 0` (autoscale) stayed on A4, at 77 % of the height and
    66 % of the width, 10 pt off centre (KiCad 10.0.7).
  - **Fit it after export:** CostasLink's `tools/fit_pdf.py fit IN OUT --caption "... scale
    {scale}:1"`.
    - It measures each page's drawn box with Ghostscript's bbox device, scales it onto Letter and
      centres it, all in vectors.
    - It prints the scale in the bottom margin, because a fitted drawing is no longer 1:1.
    - `make_release.py` runs it on both assembly drawings and refuses one that fails `check`.
  - **Plot drawings meant for paper in black** (`--black-and-white`). KiCad's pale yellow
    F.Silkscreen and pink B.Silkscreen hardly show on a printed page.
  - **A schematic's sheet size is chosen for its content.** The content fills the frame the
    same way the frame fills the page; a block that overflows gets a bigger sheet, or goes on
    a sheet of its own.
  - **Check it in code and by eye.** `fit_pdf.py check` prints each page's fill and its
    offset from centre. It cannot see a drawing clipped at the edge, or a circuit lost in one
    corner of a frame that fills the page. Render each page with `pdftoppm` and look at it whole.
  - **A board that hangs off its sheet at 1:1 must be plotted at another scale first** (the
    op-amp, 2026-10-29).  Its board sits at the sheet's origin, so at scale 1 its left jacks
    were off the A4 page, where the bbox device cannot see them.  At any scale but 1 kicad-cli
    centres the board (measured: `--scale 1.5` put the outline 150.1 mm wide, 1 pt off
    centre), so plot at 1.5 and fit from there; the op-amp's copy of `fit_pdf.py` takes
    `--from-scale 1.5`, so the caption's scale is against the board, not the plot.
  - **Make the fitted PDF the same every build:** Ghostscript's pdfwrite writes a date, a
    document ID and an XMP packet; `-dOmitInfoDate -dOmitID -dOmitXMP` drop them (gs 10.06),
    and two rebuilds then match byte for byte.
  - **Check that no text crosses the frame.**  The op-amp's title block (110 mm) holds about
    60 characters of title and 79 of each line under it; a 113-character company line and a
    98-character comment ran off the A2 page, and the schematic's overlap check, which reads
    the generator's boxes, passed them.  `pdftotext -bbox-layout` gives every printed line's
    box: fail any outside the frame, the frame's own ruler (one or two characters) excepted
    (op-amp `scripts/check_outputs.py`, `check_prints`).
- **Datasheets** go in `datasheets/`, gitignored for copyright. Fetch all of them: every
  IC, connector and mechanical part. Read pinouts from the datasheet's **pin figure**,
  not only its table.
  - **Analog Devices PDFs download directly** (Jason, 2026-10-08):
    `https://www.analog.com/media/en/technical-documentation/data-sheets/<name>.pdf`
    with plain `wget` (ECP5 `tools/adi_datasheet.py ad9238`). The product pages that link
    to them return 403 to scripts. The name is the datasheet's, not always the part's: the
    AD9767 is in `ad9763_9765_9767.pdf` and `ad9767.pdf` is a 404. Case does not matter.
    LCSC's copies come through JLCPCB's file endpoint (`tools/jlc_datasheet.py <code>`).
  - **When you have to ask Jason for a datasheet, ask for the link** he would click, not
    just the file: the link shows the vendor's URL pattern, so next time you can fetch that
    vendor's PDFs yourself.
- **Pad checks.** Check pad positions against KiCad's own pcbnew
  (`check_pads_kicad.py`), because rotation conventions have bitten every board.
- **A second board from the same pipeline** (GPiBridge Lite, 2026-10-06): one
  environment variable selects it, and one module holds every path that differs
  (project, checks, release folder, image names), so the two never overwrite each other.
  Refactor the shared code into functions first, and after each step check that the
  first board's schematic and board files come out **byte for byte** the same: with
  deterministic builds that is a free regression test, and it caught a refactor that
  had silently run a whole drawing section five times.
- **Bound every scripted edit of a hand-written document by the thing it replaces.** A
  table copied from a generated file ends at its last row, not at the next `##` heading.
  Keep a scratch copy of the document before the edit and diff after it. CostasLink's
  PLAN.md lost 70 lines of prose after a refreshed table (Response 10). The project had
  never been committed, and the text came back only from the session transcript.
- **Board IDs.** To tell variants apart in one firmware image, look first for a
  resistor that both boards already have in the same place, and fit it with a different
  value or to the other rail (GPiBridge's DC pull-up, 10 k up, became the Lite's 1 k
  down). The spare pin first chosen for a strap turned out to be walled in by
  decoupling copper.

- **Number the probe points by name, never by the order they were drawn** (op-amp board, 2026-10-24).
  A `testpoint()` helper that hands out TP1, TP2, ... as it is called renumbers every later loop when
  one is inserted earlier on the sheet, and the board generator, whose wires name "TP6", then
  connects six loops to the wrong nets and shorts half the board. Keep one `TP_NUMBER = {"IN-": 1,
  "IN+": 2, ...}` table and have the helper refuse a name it does not know.
- **A document-claims check must collapse whitespace before matching** (op-amp board,
  `scripts/gen_docs.py`). Prose wraps at 80 columns, so a regex written for "open-loop gain of about
  139" never matches "open-loop gain of\nabout 139" and reports every claim stale. Normalise the file
  with `re.sub(r"\s+", " ", text)` first; write the patterns against the normalised text.
- **The build re-reads every LCSC code against JLCPCB's own description** (op-amp board,
  `check_outputs.check_codes`): MPN prefix, value ("1kΩ", "100pF") and package ("0805", "SOT-23") must all
  appear in the API's description, from the gitignored cache; offline, it notes the date the codes were
  last checked rather than failing.

## 3. Parts and sourcing (JLCPCB)

- **One-step order.**
  - Every machine-placed part must be in JLCPCB's stock, deep enough to survive a week,
    and active at Digi-Key and Mouser too (GPSDO P2).
  - Consign only when Jason agrees and it saves real cost or complexity.
  - **Count a consignment's whole cost, spares included, before choosing it over JLCPCB's shelf**
    (CostasLink, Prompt 31, 2026-10-14).  Jason: "factor in the spare 'attrition on consigned parts',
    which I will probably not use. If I order more than 2 prototype boards, I'd be more willing to
    consign than just for the initial 2 quick prototypes."  A consigned line costs the pieces for the
    boards PLUS two spares a line (JLCPCB's attrition and one for the bench) that are never used, tax,
    the distributor's shipping, the parcel to Shenzhen ($35-60) and a week; for a two-board order a
    shelf part up to about $100 dearer than the distributor's price is still the cheaper buy
    (`mfg/cost_estimate.py consignment_cost`), and the number shrinks as the board count grows.
    - So: JLCPCB's shelf first when it covers the order; keep the distributor numbers as a
      **fallback** the release applies only when the live stock is short on the day
      (`gen/parts.py` `consign=` on a part that also has an LCSC code; `mfg/make_release.py`
      parts_report).
    - **A single part that forces a consignment is worth replacing** even by a slightly dearer or
      slightly different part on the shelf, when the datasheets say it is the same thing.  The
      ADL5380's sheet uses a Johanson 5400 balun (0 at JLCPCB); the TDK HHM1907B1 (7,884) is the same
      ratio and band with better numbers, and swapping it took the only consigned line off the order.
      Search JLCPCB's library by category ("balun", then every maker's prefix), not only by the
      datasheet's part number: the earlier searches had tried three numbers and missed it.
  - **A consigned part's distributor number and price come from the distributor's own page,
    read on the day the release is written** (CostasLink, Prompt 30). Keep them once, with the
    date, in the parts table, and let the estimate and the release read them there.
    - The balun's Digi-Key number had been copied from an old listing and was no Digi-Key
      part.
    - Digi-Key had renumbered ADI's parts with a `505-` prefix.
    - The ADL5375 was $17.26, not the $14.12 an aggregator had shown.
  - **Read the datasheet of the number you buy, not of its legacy number.** Johanson's
    5400BL15B0050001E is rated 4900-5875 MHz; the legacy 5400BL15B050E's sheet said 5900.
    The board's band changed with it.
  - Prefer Basic parts: each distinct Extended part costs a setup fee (about $3).
- **Query stock and price** through JLCPCB's parts API (`jlc_api.py`, which caches each
  answer with its timestamp). Never trust memory: "in stock" is a statement about a
  moment, and their search web page does not render for an agent (GPSDO r40).
- **Every code is checked against its description.** Eight ECP5 codes typed from memory
  named the wrong part: a 2.2 pF capacitor was a 180 kΩ 1206 resistor, a 24.9 Ω load
  470 kΩ. Every check that existed passed (ECP5 4c). The release must fail if:
  - any LCSC code's JLCPCB description lacks the schematic's value and package;
  - any SMD part has no code. Eleven codeless parts silently became "hand-solder" on
    ECP5.
- **The part must fit the copper.** Compare every ordered code's EasyEDA land pattern
  with the board (`footprint_check.py`: HOLE, PADS, LAND, datum). A substituted switch
  with two locating posts and no holes stopped JLCPCB's line (Icepi P38).
  - An MPN search can return a zero-stock code first; read the stock column.
  - Family variants differ mechanically.
- **Connectors JLCPCB stocks only in part** (GPS adapters, 2026-10-08). The genuine JST GH
  side-entry headers: 10-pin plenty (C2683602), 8-pin none (C265111), 6-pin 118. JUSHUO's
  GH-compatible GH125-SxxDCA-00 had all three. Its signal pads match KiCad's JST land
  pattern exactly, but its mounting pads sit 0.30 mm further toward the mating face, so the
  footprint's pads were stretched to take either part. Beware "1.25 mm" headers that are
  Molex PicoBlade (MX 1.25) clones, not GH: the description says which.
- **A vendor's interface table can be wrong; its schematic and the firmware decide.**
  CubePilot's own GPS1 table says the safety button is "shorted to GND on press". Their
  Cube Orange schematic has a 1.5 k pull-down on SAFETY, and ArduPilot's IOMCU hwdef says
  `PB5 SAFETY_INPUT INPUT PULLDOWN`: the button pulls up to 3.3 V. Two CubePilot pages also
  swap GPS1's TX and RX against their own carrier schematic.
- **Ratings.** Read voltage, current and power off the code's own description:
  - a 50 mA chip inductor was drawn where a 600 mA power inductor was required (ECP5 4b);
  - check resistor power at the worst-case input (ECP5 R2).
- **The part is its attributes, not its value field** (GPSDO, 2026-10-10). Rev A and
  rev B carried F2002 as "1.1A PPTC", and its code C70076 is the nSMD050-24V: 0.5 A
  hold, 1 A trip, under the 643 mA heater it fuses. Read every protection and power
  part's ratings (hold and trip current, voltage, power) off the code's own attributes
  (`jlc_api.by_code(code)` in GPSDO's `mfg/`) and compare them with the value printed
  on the sheet.
- **Re-query stock on the day of the order** (`build_release.py N --refresh`): a cache
  from yesterday is not "in stock".
- **BOM.** One line per LCSC code. "51R1%" and "51R" mapped to one part produced
  JLCPCB's "multiple lines matched to the same part" (GPSDO P32).
- **Packages.** 0805 or 0603 for hand rework and probing, unless the datasheet or the
  density says otherwise (GPSDO P6, Icepi P16). Prefer solderable packages that are
  common everywhere.
- **A fetched footprint can carry the board edge.** An edge-mount jack's EasyEDA
  footprint (easyeda2kicad) draws Edge.Cuts lines, and KiCad cuts the board along them.
  Read a fetched footprint's layers before vendoring it. Choose vertical or edge-mount
  on purpose. CostasLink's first MMCX candidate, BWMMCX-KEF (C5250057), was edge-mount;
  the taps wanted the vertical BWMMCX-KE (C5137198).
- **Annotated BOM.** Price per item and for N boards, stock with the time of the query,
  Basic/Extended/consigned, and a note for anything to look at (GPSDO P23).
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

* **JLCPCB's engineers ask about polarity before production.**  CostasLink rev A (2026-10-18, the day
  after the order): "we are not so sure about the polarities of the T101, L102 components", with a
  placement snapshot attached (their red mark is their model's pin 1).  The parts were the four-terminal
  balun and an 0402 chip inductor whose library entry is flagged polarised.  Answer from the board file,
  not from how the picture looks: compute where pad 1 lands from the footprint's rotation, name the net
  on it and the neighbour it runs to, check the datasheet's marking end, and say which end of the part
  their mark should be on.  Keep their picture in the board's mfg/jlcpcb_order/ and record the answer
  where the rotation is recorded, so the next order knows the question was asked and settled.

- **Parts to know for a teaching board** (op-amp board, 2026-10-24):
  - **RH-5019 SMT test loop, C5199800** ($0.10, 101 k in stock): one 4.0 x 2.2 mm pad, a 3.8 mm wire loop a
    scope hook or mini-grabber takes. The right "test point" when students will clip on; a 2.54 mm pin
    is through-hole and flops over with the hook. JLCPCB rotation 0 (predicted; the loop lies along x).
  - **KingTek DSIC02LSGET 2-way DIP, C54949** (SMD, 2.54 mm, raised sliders): one per selectable variant,
    so nothing ships loose. Same family as the Lorenz 6-way, whose +270 was read; the 2-way is +270
    predicted. Pins 1-4 are position 1, 2-3 position 2; "ON" is toward +x in the footprint frame.
  - **MMBT3906 has no Basic-library code**: C53444 (onsemi), C2143 and C727128 are all Extended. The
    MMBT3904 C20526 is Basic. One Extended fee is the price of a real PNP.
  - **Bourns 3362P-1-xxx, C52754333 (50 Ω)**: three holes in a triangle, so it fits one way; 520 in stock, with
    the 100 Ω C52754331 as the drop-in alternate.  Its body is not centred on the pins: pins 1 and 3 sit
    3.53 mm from the body's edge and pin 2 2.54 mm further in, so the body's centre is on the line of pins
    1 and 3 (Bourns' 3362P drawing; EasyEDA's agrees).

## 4. Schematics: the Art of Electronics standard

Jason worked with Paul Horowitz. The bar is a schematic drawn so that every question a
reader would ask is answered at the place they would ask it (GPSDO P7, ECP5 P1).

- **Flow.**
  - Signals go left to right and power comes from the top.
  - Series parts are horizontal on the signal line; shunts are vertical, hanging off
    the node.
  - Draw it as the circuit is understood, not as the netlist happens to connect.
- **No disappearing labels.** A label that vanishes and reappears elsewhere is allowed
  only for power and ground. Wire it if you can (Icepi P27: "connect it with a wire
  rather than a label").
- **Sheets.** Jason almost never prints: a big sheet that keeps a long signal path and
  its parallel copies together beats several small ones, and a net label that goes off
  to some other page ("possibly more than one -- who can tell?") is what he dislikes
  most (ECP5 P26). Keep every drawing inside the page's border and out of the title
  block's corner; the generator's margin check fails on either.
- **Notes at the node.**
  - Put voltage ranges, frequencies, rise times and impedances **right at the node**
    they describe, in small boxes with small arrows to the probe point (GPSDO P6, P7).
  - Notes are short columns broken at logical places (after a sentence, before a
    formula), 50-70 characters wide like a newspaper column, never one long line across
    the top of a sheet that needs zooming and dragging to read (GPSDO P7, P8, ECP5 P26).
    Size the box to the text: a box narrower than its longest line re-wraps the line
    ends and strands a word ("to") on a line of its own.
  - Prefer "just in time" notes beside the block they describe over one essay at the
    top: the gain and noise list under the pair of amplifiers it describes, "THS4521
    fully-differential driver at gain 1" right above its block, block titles centred
    on their block (ECP5 P26).
  - A comment that says which of two chips a series resistor belongs beside goes next
    to the resistor, sideways if need be: "I can read small amounts of sideways text".
- **Why boxes.** Explain why a part was chosen ("74LVC1GU04: U = unbuffered; LVC =
  5.5 V tolerant at 3.3 V"), and when to fit each jumper ("50 Ω: fit for all but the
  ZED-F9T").
- **Limits at every connector:** maximum DC, Vpp before clipping, Vpp before damage,
  and output ranges (Icepi P15, GPSDO P21).
- **Labels in a row stand alike** (CostasLink Response 15; Jason, of the board's SMAs:
  "their labels should all be in the same relative orientation: for example, all above and
  closest to the thing they refer to or all Southwest and closest to the thing they label.
  This consistency requirement needs to be enforced"). It holds on the sheet as on the board.
  - Parts drawn in a row or a column (jacks, taps, test pads, jumpers, the four copies of a
    channel) carry their names, limits and notes in one relation to each part: the same
    side, the same offset, nearest their own part, never between two of them.
  - Draw every copy with one function, so the relation is the same by construction, and
    have the overlap check report a label nearer another member of the row than its own.
- **Nothing overlaps anything.** No text, reference or value overlaps a symbol, wire,
  box or other text, and everything stays inside the page border.
  - Check it in code and by looking at the exported PDF (Lorenz P1, GPSDO P5, P6).
  - The usual offenders: references on vertical R/C, GND flags on decoupling caps,
    notes next to GND symbols.
  - A text's real extent is not its anchor. KiCad snaps a field's anchor to the 1.27 mm
    grid and draws a reference's glyphs from 0.76 x size before the anchor to 0.23 x
    size after it, a value's from 0.38 x size after the anchor to 1.37 x size after,
    whatever the symbol's rotation (measured on a calibration sheet, ECP5 P26). Model
    that in the generator's overlap check, and test wires against text boxes and text
    against symbol bodies, not only text against text.
  - Then check the exported PDF itself: `pdftotext -bbox` gives every word's box; two
    words whose boxes overlap, or one past the page's frame, fail the build
    (`gen/check_sch_text.py`). The PDF is what Jason reads.
  - **A checker that passes is only as good as its model of KiCad** (GPSDO, 2026-10-10).
    GPSDO's check had passed for weeks with four faults: every text anchored on its
    baseline (KiCad centres one unless told top or bottom); power symbols skipped as
    bodies; a label's direction read from its angle while kigen writes left-pointing
    labels as angle 0 with `justify right`; and one width, 0.82 × height per character,
    when capitals and digits run 0.87-0.99. Fixed, it found fourteen kinds of real
    overlap, among them a pull-up resistor drawn across another pin's wire. Calibrate the
    model against a render whenever the eye sees what the check does not. In the PDF
    scan, a word box includes the font's whole ascent and descent: demand overlap of
    half a line before calling two lines of a note overlapping.
  - Hide every field but reference and value: a footprint suffix ("K1A2") printed in the
    middle of a BAV99 is a question Jason will ask (ECP5 P26).
- **Symbols the right way up.** No upside-down GND flags or `+3V3` arrows pointing down
  with upside-down text. No PWR_FLAG left floating in a corner (GPSDO P8, Icepi P15,
  P29).
- **Hierarchical and global arrows** are justified so they do not overlap boxes. They
  point the way the signal goes (bidirectional only when it is), and their names say
  where they go ("…_FPGA") (Icepi P14, P15, GPSDO P10).
- **A sheet pin's name reads inside its sheet box**, as KiCad draws its own (a left pin's
  text runs right).  kisch had them outside, so a net label on the wire beside the pin
  printed the name twice ("double labels", CostasLink Prompt 35).
- **A coaxial jack's pin faces the line.**  Conn_Coaxial has its pin on the left and its
  shield below: an input drawn at rot 0 puts its body under the first series part ("C101
  right on top of the SMA connector"), an output at rot 180 puts the ground on top.  Draw
  an input mirrored (pin on the right, the jack first on the line), an output at rot 0, a
  monitor jack upright with the ground below (CostasLink Prompt 35).
- **Every IC's box opens with what the part is**: "PE43711, RF digital step attenuator: 0
  to -31.75 dB in 0.25 dB steps", "THS4541, fully differential amplifier", "MAX2871, PLL
  frequency synthesizer (23.5 MHz to 6.0 GHz)", then the detail of its use.  A student
  reads the function before the part number (Jason, CostasLink Prompt 35).  And a sheet
  carries no record of the designer's mistakes ("the OPA2187 first drawn here needed
  4.5 V..."): that is the chat log's job.
- **Do not split ICs into many sub-symbols.**
  - The power pins stay on the IC; never a separate rectangle that looks like another
    chip (Icepi P15, P16).
  - Big multi-function parts are the exception. The ADC/DAC is drawn as one trapezoid
    per channel plus a common box, with a dashed box around all of them, and so are
    multi-unit symbols such as the PHY and the FTDI (ECP5 P2).
  - When a chip is split (dual op amps), its units get a dashed box, and the power unit
    sits under the gap between the two amplifier units with room round it: nothing
    else inside the box, no wire through it (ECP5 P26: a tap's ground sat on an
    OPA1612's power unit, a wire ran through another).
  - A converter is drawn like a MUX: the long side of the trapezoid is the digital
    bus, the short side the analog signal, and the clock comes in from below and turns
    up into the bottom edge like a flip-flop's clock. Control lines (WRT, CLK) come
    from the left, lower than the trapezoid, and turn up into it (ECP5 P26).
  - Each amplifier keeps its "entourage of passives" (feedback, gain, compensation)
    drawn around it, and placed around it on the board.
- **Decoupling.** One capacitor per supply pin, drawn **at that pin**, never bunched off
  to the side. The PCB then places each one at its pin (Icepi P28, P29).
- **Repeated blocks** are identical pages or identical tiles, differing only in names, so
  paging through the PDF shows the pattern. A missing 13th copy leaves a blank in the
  same place (GPSDO P4).
- **Net names.** Sensible, especially on long runs and anything leaving a page. Avoid
  names that read like other buses (`FPGA_SCLK_OUT` looked like I²C's SCL, Icepi P16).
- **Comments must not go stale.** A note that names "U112", or a part that is no longer
  there, is a bug. Say "the LM27761 here", and regenerate notes from data (Icepi P27,
  GPSDO r28 #9).
- **No four-way junctions.** Fix the ERC warnings that matter, refresh cached symbols,
  and save in KiCad 10's own format (`kicad-cli sch upgrade`) so opening the file asks
  nothing (Icepi P16).
- **Pins.** Check every pin of every generated symbol against the datasheet's pin
  **figure**. ECP5 found, all with checks passing:
  - an FDA's output pair swapped, making positive feedback;
  - a mini-HDMI with type-A numbering;
  - a SOT-23-6 EEPROM numbered like a SOIC;
  - a bit-reversed DAC port;
  - a TCXO's ground drawn as an enable;
  - a photodiode whose LCSC footprint has pad 1 = anode where KiCad's symbol has pin 1 =
    cathode;
  - three header pin-name lists printed in reverse;
  - a three-die LED (HL-AF-5060S22OC) whose generated symbol called pins 4-6 the anodes:
    the datasheet's circuit and JLCPCB's drawing ("+" at pins 1-3) both say 1-3, and the
    pumpkins would never have lit (OWLternating Current). Check every diode's anode
    against the datasheet **and** JLCPCB's drawing of the LCSC part.
- **Trace every path** with a netlist walk (`trace_paths.py`): signal paths end to end,
  power from the input to every pin, every configuration and strap pin, every clock.
- **The checks every schematic gets** (Rosenberg). Run them from the netlist in the build
  (§10, gates 13-14), and read their lists:
  - **One-pin nets** fail, except a deliberate test pad: a label typed once is an
    unconnected pin.
  - **One name per rail.** "VCC" on one sheet and "+5V" on another, or "GND", "DGND" and
    "AGND", are three nets that look like one. Print every power net with its pin count
    and the sheets it appears on.
  - **One ground net, poured as one plane,** even when a datasheet draws AGND and DGND
    apart: a split makes return currents detour round it. The exception is real
    galvanic isolation (the Lorenz board's isolated DC/DC).
  - **Copied blocks** bring their net names with them; a repeated name silently merges
    two nets.
  - **Inductive loads** (relays, solenoids, motors, PCB coils, electromagnets) each have
    a path for their current when the switch opens: a freewheel diode, a bridge's body
    diodes, or a clamp rated for the peak current (§15).
  - **A fuse** (or PTC, or eFuse) on every input that can deliver more current than the
    board's copper and connectors survive. **Rate everything in series with it for the
    fuse's hold current, not the board's draw:** ECP5 build 31 put a 1 A / 0.5 W Schottky
    ahead of a 2 A-hold PTC, so a 1-2 A fault would have cooked the diode without
    tripping the fuse (both round-2 reviews). A 3 A SS34 in SMA replaced it.
  - **Two supplies, two blocking elements.** A Schottky on the bench input keeps USB off
    the bench header; it does not keep the bench supply off USB's VBUS, which then
    back-feeds the laptop (ECP5 build 31; CopilotSDK round 2). Block each path: a P-FET
    on the USB path with its body diode pointing VBUS -> rail, gate pulled to ground
    (on) and lifted by the other supply's presence (off), as the Raspberry Pi Pico and
    Arduino do. It costs no drop on the main path; a second Schottky costs 0.35 V.
  - **Straps against an FPGA that is still configuring.** A PHY or other chip that
    leaves reset while the FPGA configures samples its straps then, and the FPGA's
    configuration pull-downs (every unconfigured ECP5 user I/O, up to 150 µA) beat a
    chip's internal pull-up. Every strap that must read 1 gets an external resistor
    (4.7 k), and so does every strap the vendor says needs one (Realtek §7.8). ECP5 build
    31 had RXDLY and PHYAD0 on internal pull-ups only.
  - **A control whose idle must be safe rests where an absent host leaves it** (CostasLink,
    2026-10-10, Response 15). An unpowered host clamps its pins near 0.6 V through their ESD
    diodes; a configuring one may pull them up (the Zynq's configuration pull-ups, 10 k at the
    strongest) or down (the ECP5's). A pull-up cannot hold a line high against the first, so
    the safe state must be LOW: make the line active-high (TX_EN, not TX_DIS), give it a
    pull-down that beats the configuration pull-ups (1 k: 0.35 V against a 74LVC's 0.8 V),
    and invert on the board when the chip's pin is active-low. CostasLink's TX_DIS sat on a
    100 k pull-down into the ADL5375's DSOP, which transmits "when grounded or floating", and
    the board has its own USB-C supply: the modulator ran, the synthesizers still programmed,
    whenever the PYNQ was off, booting its base overlay or loading another one. Ask of every
    line the host drives: what does it do with the host off, configuring, and running somebody
    else's overlay? Latch enables want a pull-down too, so a floating LE cannot load a word.
  - **Every op amp's supply range and input common-mode range against the rail it is on**
    (CostasLink, 2026-10-09, Response 9's self-review).  The Costas loop's PI filter and VC stage
    were an OPA2187 on 3.3 V with both inputs at 1.65 V: the part's recommended supply starts at
    4.5 V and its inputs stop 2 V below the rail.  Every number of the loop had been computed and
    asserted; the op amp's own operating conditions had not been read.  The schematic generator
    must assert, for each op amp, rail >= minimum supply and every input's quiescent voltage inside
    the common-mode range, from numbers typed from the datasheet beside the part.
  - **Trace a two-supply ORing in BOTH directions, with each FET's gate written out.**  A P-FET
    ideal diode with its gate grounded conducts both ways once the output rail is up: powered from
    the second input, it fed the rail back onto the first input's connector, which lifted the
    second FET's gate and turned it off, leaving the board on a body diode at 4.1 V.  The fix is
    one small N-FET (the first input's presence pulls the first FET's gate down; otherwise the
    second rail holds it up).  "Neither feeds the other" is a claim to derive, not to write.
  - **A comparator or logic input on a connector** gets a series resistor sized to the
    input clamp's current limit at the worst signal a student can plug in (TLV3501:
    10 mA; 1 kΩ for a 10 V generator). An AC-coupling capacitor is a short at the
    signal's frequency, not a limiter (ECP5 CLK IN, build 31).
  - **Polarized parts** the right way round, and every capacitor rated above the
    worst-case voltage across it, with margin.
  - **Coupled windings:** transformer and coupled-inductor dots, and common-mode chokes
    wired common-mode.
  - **No floating inputs:** unused logic inputs, op-amp sections (wired as grounded
    followers) and ADC channels go to a defined level.
  - **Values.** "10" typed for "10k" is a classic. Assert each design equation against
    the values the netlist really carries (gain, cut-off, divider ratio, LED current,
    time constant), as the Lorenz board's 147 assertions re-derive its equations.
  - **Each equation's inputs: the guaranteed figure, at the operating point, through what
    the next stage really sees** (CostasLink's design review, Prompt 18; four reviewers found
    one each):
    - the datasheet row for the operating frequency (the ADL5611's 6 GHz P1dB, 16.0 dBm, sat
      in a 5.8 GHz budget whose row says 12.8);
    - the minimum or maximum, not the typical (the THS4541's input range is VS+ − 1.3 V
      guaranteed, VS+ − 1.2 V typical; the HMC536's isolation and P0.1dB were printed on the
      silkscreen at their typicals);
    - a supply's drop at every series part's maximum resistance from the lowest supply the
      board is promised (a PTC's R1max, a FET's RDS(on) max, the bead), and a pin's bias
      current through the divider that biases it (the ADL5375's 2 × 41 µA lifted a 0.5 V
      divider to 0.61 V);
    - a detector's gain as its load sees it: a switch that passes one leg of a pair against
      mid-supply passes half the differential swing (CostasLink's Kd was 2× too high, the loop
      ran at 2.05 kHz and ζ 0.48).
  - **Ratings:** every part within its voltage, current and power at the worst-case
    input and temperature (§12).
  - **Options where unsure:** an empty footprint for the alternative, and a configuration that
    software can set rather than a jumper (§9, "Remote first"; §1, "Think five steps ahead").
  - **The drawing:** few wire crossings, sheets in order from input to output, and a
    block diagram first when there are many sheets. Rosenberg allows labels for buses
    and MCU I/O; Jason's rule above (wires, not labels) stands.

- **Draw a part added late at the END of its sheet** (CostasLink, Prompt 31).  The generators number
  references in drawing order, and the board's hand anchors are by reference: a DNP pull-up drawn beside
  the TCXO renumbered R220-R227 and the anchors then placed the wrong parts (a 49.9 ohm into a jack's
  leg, a DRC fault).  The balun's DC blocks and the TCXO's pull-up are drawn last, after the sheet's
  other parts, and the build's netlist is diffed against the last commit's for the sheet's references.
- **A filter drawn by hand is checked by its nets, not its picture** (CostasLink, Prompt 31).  Both
  ADS1115 "10 k / 100 nF" input filters had the capacitor hanging from the SOURCE end of the line, so
  100 nF sat on the fast arms' outputs; the blue box said 160 Hz and five reviewers read the box.  For
  every RC at a chip's pin, assert in the netlist that the capacitor is on the pin's net and the
  resistor between the pin and the source (`tools/net_check.py` can walk it); a fresh-eyes review with
  the netlist as ground truth found it in an hour.

## 5. Placement and routing

- **Floorplan first.**
  - Decide where the connectors and blocks go.
  - Run each signal path through its chips in the order the schematic draws it.
  - Then hang each chip's passives directly off its pins.
  - Leave room for labels from the start: spread out rather than bunch into a corner
    (Lorenz P3, ECP5 P11).
- **Orientation.** Placement follows the schematic: a horizontal series resistor is
  horizontal on the board, along the trace; a vertical shunt is vertical (Lorenz P4: "I
  even specifically asked that the 100R resistors be horizontal").
- **Rotation.** Verify what 0/90/180/270 actually do to each footprint's pads before
  relying on them. "0 = horizontal" was wrong more than once (ECP5 P2, P9).
- **Decoupling** at the pins: straight to a ground via, on the back if that is closer
  (ECP5 P9, Icepi P28).
- **Blocks.** Each functional block sits in a silkscreen box. Everything that belongs to
  it, part and label, lies inside its box; nothing else does.
  - Check it in code (`check_silk_boxes.py`). Rev A of GPSDO printed 71 designators in
    the wrong box (GPSDO P41, ECP5 P14).
  - Identical channels are laid out identically (ECP5 P11).
  - And in the order their names suggest: ADC A above ADC B **and** DAC 1 above DAC 2,
    even when the chip's pins come out the other way round; swap the strips, not the
    names (ECP5 P26: "no end of student confusion").
- **Power.** Distribute it in pours or wide traces. GPSDO's +3V3_A lost 109 mV in 1.4 m
  of 0.5 mm track because the "plane" was never poured (GPSDO REVB #5, ECP5 P2).
  - Check the regulator's dropout from the **worst** input. A USB port can give 4.75 V,
    less a fuse and a diode.
  - Measure the drop, not the width: a script that walks each rail's copper as a
    resistance network from its source to every supply pin (ECP5 `tools/power_path.py`)
    answers "is enough power getting there?" with millivolts, and finds the 0.127 mm
    feed nobody remembered (ECP5 P28: 102 mΩ to VCCAUX, 4 mV, fine).
  - The analog rails get planes, not traces: an LDO 16 mm from its converter on 0.4 mm
    track is 45 mΩ, op amps fed 60 mm from one bead share 0.2 Ω, and the fix is a
    patch on the power layer from the regulator to the chip, a via per pin (ECP5 P30:
    45 → 5 mΩ, 206 → 5 mΩ, and the router finished in half the time).
    Such a model must join copper by overlap, as KiCad's connectivity does: a via on
    a track's interior, a track ending inside a through-hole pad on the back layer.
    An endpoint model reports opens that are not there; find the construct, do not
    explain the report away (ECP5 P29).
  - Measure every rail's width in the shipped file, by net, and compare it with the
    rule. ECP5's router narrowed a whole net to the narrowest pad it touched: one
    0.25 mm LQFP pin laid 200 mm of +3V3_ADC at 0.23 mm, and +5V and +3V3 the same,
    through 27 builds that all said "0.4 mm rails" (ECP5 P26). Do not fix it in the
    router: every rule that routed the rails wide and narrowed them near the fine pads
    took the room the converters' own signals needed (three build-28 runs each lost two
    to five nets). Route at the pad's width as before, then widen each track toward
    its class width wherever the copper round it leaves clearance (`pcb/fatten.py`): no
    route moves, DRC sees the same board or more room, and the long runs come out wide.
- **Ground.** Keep an unbroken ground reference under every fast signal. A layer change
  gets a ground via within about 1.5 mm. Keep analog and digital apart physically, and
  keep switch nodes small (ECP5 P2).
- **Stack-up and layer assignment** (Rosenberg). Choose the stack-up before routing, from
  the fab's own table, because impedances and via inductances follow from its
  thicknesses (JLCPCB's JLC04161H-7628: 0.21 mm from L1 to L2; inner copper 0.5 oz
  unless 1 oz or 2 oz is ordered).
  - **2 layers:** top = parts, signals and supplies; bottom = ground plane, with as few
    traces as possible, each short.
  - **4 layers, parts on top:** L1 parts and signals; **L2 solid ground with nothing but
    via holes in it: no traces**; L3 supplies and leftover routing, the rest filled with
    ground stitched to L2; L4 the same as L3.
  - **4 layers, parts on both sides:** L1 and L4 parts, signals and supplies; L2 ground;
    L3 supplies.
  - **Why the ground goes on L2:** a via's inductance grows faster than its length.
    Rosenberg's curve: about 45 pH for the 0.38 mm from L1 to L2 of a typical 4-layer
    board, about 500 pH through 1.6 mm, eleven times as much. On 2 layers there is no
    choice, which is the main reason 4 layers ground better.
- **Layout order** (Rosenberg):
  1. pour the ground plane (and any power plane);
  2. the critical lines: high-dynamic-range analog inputs, RF, crystals, reset, short and
     with ground on both sides;
  3. the high-current supply paths, wide and short;
  4. each block's own routing;
  5. the connections between blocks;
  6. whatever is left.
- **Each ground pad gets its own via,** at the pad (Rosenberg: "I cannot stress enough how
  important this is"), and each power-plane connection likewise, beside its decoupling
  capacitor. A shared via is shared inductance, which couples the parts that share it.
  On 2 layers, make that via the pad's only path to ground: a second path through
  top-layer copper closes a loop that picks up and couples.
- **Unshielded inductors** couple when they lie in line along their axes: space them or
  turn one 90° (Rosenberg).
- **Aggressors and victims** (Rosenberg). Switching converters, motor and coil drivers
  and fast logic are aggressors; receivers, ADCs, sensors and high-gain analog are
  victims. Distance first, then a shield can. When schematic order and distance
  conflict, weigh both.
- **No floating copper** (Rosenberg): an island connected to nothing is a resonator at
  RF and an antenna everywhere. Remove it or stitch it to ground.
- **Copper balance** (Rosenberg): about the same copper on every layer, over the whole
  board. A region bare on every layer laminates badly and warps the board. Fill unused
  area with ground on every layer and stitch the layers together; it also spreads heat.
- **Vias as large as the room allows:** small drills are less reliable and more
  inductive. Keep the smallest for fine-pitch fan-out (Rosenberg).
- **Room to assemble:** parts packed tighter than the assembler's spacing rules cannot
  be placed, inspected or reworked (JLCPCB publishes its own).
- **Paste:** check the paste layer. Every pad that needs solder has an opening; test
  pads, fiducials and edge contacts usually do not; a large exposed pad gets a
  window-pane pattern (about 50-70 % coverage) so the part does not float (Rosenberg).
- **Fiducials:** three on the board, at three corners and as far apart as possible, and
  three more at the corners of a box round each fine-pitch part (Rosenberg). JLCPCB adds
  its own on the rails of the panels it makes, but marks on the board itself are what
  align a fine-pitch part.
- **Layer markers:** each copper layer's number in copper on that layer, all at one spot,
  so the fab (and anyone holding the board against a light) can tell the layer order
  (Rosenberg).
  - **In a generated board, fiducials and layer markers are netless graphics, not
    footprints** (ECP5 build 31): a filled `gr_circle` on the copper layer and a larger one
    on the mask layer make a fiducial, a `gr_text` on each copper layer a marker. No
    footprint means no symbol, no parity warning, no BOM or CPL row. They must be known
    to everything that places or routes: the placer's keep-out list, the router's
    obstacle grid (the fine-grid rebuild included) and the silkscreen's occupancy map,
    or a track or a label lands on them. Pick the spots by scanning the previous build
    for discs free of copper, silkscreen and courtyards on both sides; the slot band
    that the enclosure hides is a good home for the layer numbers (and for JLCPCB's
    order number), not for fiducials, which the assembler's camera must see.
- **Check footprints at 1:1:** print the placed board at 1:1 (measure the outline with a
  ruler) and lay the real parts on it: the idiot-proof check for anything Jason buys in
  hand, especially connectors and mechanical parts. Ribbon cables mirror (Rosenberg).
- **DC resistance of high-current paths:** count the squares and compute the drop,
  return path included (Rosenberg; §15). GPSDO's +3V3_A below is the example.
- **Plan the copper.** On GPiBridge the maze router was left only the ground vias:
  every other connection, down to each decoupling capacitor's 1 mm stub, is written as
  coordinates computed from the pads. The router's versions wandered (VBUS through
  three layers, a UART line along the board edge); the planned ones look like a person
  drew them and are no more work to write than the fixes they replaced.
- **Three hundred passives are placed by rule, not by hand, and the rules are the schematic's own**
  (CostasLink, 2026-10-09, gen/placement.py): a shunt stands perpendicular at the pin it serves, outside
  the chip's courtyard, its signal pad nearest the chip; a series part lies on the line between the two
  pads it joins; a part whose far end's net has nothing placed yet hangs off its known end and becomes
  the next part's anchor; a capacitor between a rail and ground belongs to the chip the SCHEMATIC drew
  it beside (the netlist cannot say: read the sheets' symbol positions and take the nearest chip on that
  rail on the same sheet); a part hangs off a chip pin, then a placed passive, then a jumper, and off a
  40-pin connector last.  Then push apart until no courtyards overlap (outward first, then sideways,
  then a spiral), report what stayed overlapping, and draw the plan (courtyards, pads, designators) to
  look at BEFORE KiCad: the picture found the socket mirrored and the USB-C turned into the board,
  which the overlap count could not.
- **pcbnew's Flip() onto the back mirrors y, whatever its enum says** (CostasLink, 2026-10-09: measured
  with FLIP_DIRECTION_LEFT_RIGHT in KiCad 10.0.6, the socket's even row went from +2.54 to -2.54 and
  its odd row stayed).  Never model a flip; put the HOST's measured connector pins into the generator
  (the PYNQ-Z2's header, from GPSDO-PYNQ-Z2/pcb/geom.py) and have the board generator read pcbnew's
  own pad positions back and refuse to lay copper until pins 1, 2, 3, 39 and 40 sit on them.  The same
  check holds the RF pads on their chain lines, which is how each chip's rotation was settled.
- **A connector's pad row faces the way its rotation says, not the way its name suggests**: the HRO
  USB-C at rot 270 faces -x (GPiBridge's left edge); on a right edge it is rot 90.  Turned the wrong way
  its pads lie past the board edge, outside the routing grid, and the ground fan-out divides by zero.
- **A pour's membership test must use its outline, not its bounding box** (CostasLink, 2026-10-09,
  Response 9).  The router joined a supply via to its In2 pour when the via lay inside the pour's
  bounding box; an L-shaped pour (the +3V3_ANA pour wrapped round the PLL's) has a notch inside that
  box, two vias landed in the notch, the router called them joined, and DRC called them dangling.
  Test the polygon, with a margin from its edges (`routing.inside_margin`), and the two vias went away.
- **A series part placed at the midpoint of a long line strands it under whatever is there**
  (CostasLink, 2026-10-09).  The rule "a series part lies on the line between the two pads it joins"
  put the slow Q stage's 1 k resistors in the middle of a 32 mm run, under the RX synthesizer, and the
  resolver could not push them out of its fan band.  When a two-terminal part's two ends are far apart
  the placement is wrong, not the part: move the destination (the slow comparators went under their
  stage, 5 mm away) and the rule works again.  Print the span of every rule-placed series part and
  look at the long ones.
- **Place an amplifier's feedback, gain and shunt resistors at its pins, by hand, and check the
  pair order first.** A rule placer treats a feedback resistor as a series part between two pins
  of one chip and can put it anywhere along a detour. CostasLink's I-arm THS4541 got its 4.02 k
  feedback resistors 10 and 13 mm from its pins: a long summing node on an 850 MHz-GBW amplifier,
  which invites peaking. Its Q arm's input lines crossed beside the chip, because the + input's
  network sat to the left and the − input's above. For a differential pair, make the source's pin
  order match the amplifier's. Where it cannot, swap the pair at the input (it inverts the
  signal; say so in the schematic) rather than cross beside the chip.
- **Check that a pair's pins face each other before laying it** (CostasLink build 17,
  KimiK3's review).  The MAX2871's RFOUTA_P faced the ADL5380's LOIN, so the drawn
  P-to-LOIP pair had to cross on one layer, and the router took one leg 44 mm round the chip
  (60° of skew at 5.8 GHz).  Swap the pair at one end (inverting an LO into a mixer costs a
  Costas loop nothing: sign(I)·Q is even in it), stand its series parts as mirror images,
  and gate the legs' lengths summed through their series parts: KiCad's skew constraint
  compares single nets, and each leg here is three.
- **A generated board's router is chaotic: build placement variants in parallel.**  One moved
  part reroutes the whole board, and a net that routed before can end up walled in somewhere
  else (CostasLink build 18: moving one tap resistor walled in DAC 2's pins; anchoring it beside
  its jack walled in a comparator's input instead).  The build is deterministic, so copy the
  project to three or four scratch directories, change one anchor in each, run them at once
  (32 cores; about 25 minutes for four), and keep the one that routes completely, instead of
  one guess per 11-minute build.
- **Reserve every labelled connector's name-and-limit strip in the placer, not only the edge
  rows.**  CostasLink's REF OUT jack (J108) was in no label row, so nothing kept its strip clear;
  when build 18's reshuffle moved a tap resistor under its name, the silkscreen found no place for
  "25 MHz, 1.6 Vpp/50R" and the release's label gate failed.
- **A hand anchor keyed by reference follows the number, not the part.** References are handed out
  in drawing order, so adding one part to a schematic helper renumbers every part drawn after it
  on that sheet. CostasLink's Q arm gained a trim resistor in Response 14, and its two anchored
  feedback resistors slid to R117 and R118. The anchor for "R116" then placed the new trim where a
  feedback resistor belonged, and the routing failed there. After any schematic change, check each
  anchored passive's value and nets against what its anchor's comment says it is. Better, give the
  parts you anchor explicit references in the generator.
- **Keep a band round every fine-pitch chip free of parts, in the placement, before any fan-out is
  planned** (CostasLink, 2026-10-09).  OWLternating Current's fan reported the pins it could not
  serve and the parts were moved by hand; with 25 chips that is a day.  Give the placer the rule:
  a chip of 16 pads or more owns a band (1.8 mm beyond its courtyard) that no part may stand in; its
  own shunts are placed just outside the band, and the resolver pushes everything else out.  The fan's
  vias then always have the room they need, and the fan's "why" list shrinks to the parts placed
  before the rule existed.
- **Check that every shunt's signal pad is the one nearer its chip, in code, after placing**
  (CostasLink, 2026-10-09, Response 9).  The rule that turns a two-terminal part to stand at a pin
  had its sense inverted for parts above or below a chip (KiCad's rot 90 puts local -x at +y, i.e.
  below), so every rail capacitor and every shunt on a chip's top or bottom row faced the pin with
  its GROUND pad, and the fan-out planner then reported "C126.2 GND" in front of pin after pin.
  The picture of the plan could not show it (a 0402 looks the same either way round); a six-line
  check that measures both pads' distances to the pin found 65 of 65 wrong, and 0 after the fix.
  Any rule that orients a part by a case split needs a measurement after it, not a reading of it.
- **A radius-0 cell query on a line laid at pad coordinates finds no cell at all** (CostasLink,
  2026-10-09).  The track-widening pass asked the grid for the cells under a track's centre line
  with reach 0; a fan-out stub drawn from a pad centre like x = 26.79 lies between the 0.1 mm grid
  nodes, so the query returned nothing, nothing blocked it, and the stub at a 0.5 mm-pitch QFN pin
  was widened to 0.8 mm into its neighbours (14 shorts).  Sample with half a pitch of reach; and
  never widen a planned line or anything within a millimetre of a fine-pitch pin.
- **Every chip's fan-out before any chip's local nets, and a planned line runs straight out of a
  fine pin for the fan band's depth before it turns** (CostasLink, 2026-10-09, Response 9).
  OWLternating Current routed each chip's short local nets before its own fan-out, so the fan's
  vias would not wall them; with twenty-five chips, a local net of one chip (a feedback resistor
  9 mm away) ran along the NEXT chip's pin row before that chip had its fan, and sealed two pins
  (the stamp of the router's grid showed the pad enclosed on an otherwise empty board).  Fan every
  chip first; from its via a local net has every layer and goes round.  Likewise a planned line
  that leaves a 0.5 mm-pitch pin and turns at the pad's tip passes the neighbouring pin at exactly
  the clearance: DRC-legal, and nothing can ever leave that neighbour.  Run straight for 1.4 mm.
- **Let the board choose the swappable pins: river routing with late assignment.**
  Agents (and people) fix a chip's interchangeable pins in a table before anything is
  placed: GPIO 0 drives coil 1, LED channel 0 lights star 0. The table's order then
  fights the board's, the router has to cross lines that never needed to cross, and the
  failures look like congestion. Before routing, list every set of interchangeable pins
  (an MCU's GPIOs, an LED driver's channels, a mux's inputs, the sections of a dual
  op-amp or a gate package, the contacts of a connector you define), and leave them
  unbound until the rivers meet:
  1. Route each destination's line back toward the chip, without choosing a pin, until
     it reaches a ring round the chip. A coarse multi-source search outward from the
     ring, with only the big obstacles in it, does this for every destination at once.
  2. Read off the order in which the lines arrive on the ring.
  3. Bind the pins in that cyclic order. A minimum-cost matching on distance along the
     ring is non-crossing. Keep within each pin's real constraints:
     - an LED driver's channels are all alike (keep a feature's LEDs in one brightness
       bank only if the firmware needs it);
     - an MCU's GPIOs move within their function classes: ADC pins, a bridge's two PWM
       inputs on one slice, I2C and UART on the pins their instance allows, consecutive
       pins where the firmware does one masked write.
  4. Route each bundle in that order as a river, outermost line first.
  5. Generate the schematic and the firmware's pin and channel headers from the
     result, so nothing downstream is edited by hand.

  OWLternating Current's first routing pass, with a table written before placement, left
  59 nets unjoined. Most were LED-driver channels and GPIO lines.

  A signal's destination is the chip pin it reaches, not every pad on its net. Follow it
  through series parts (a two-pad R, C or L whose far side is not a rail) and drop
  shunts. CostasLink's first header swap averaged the positions of its 1 k series
  resistors, which the placer puts wherever the header pin pulls them: the assignment
  chased itself (14 moves, then 4 more) until the destinations were the comparators.
  Re-run the swap after the rebuild; it is right when it proposes nothing.
- **Plan every fine-pitch chip's fan-out; never leave it to the router.** A maze router
  routing net by net walls a QFN's later pins in: the first lines hug the chip, and its
  vias at the pin's tip (0.45 mm vias, 0.4 mm pitch) shut the neighbours. A fan-out
  band (no vias near the pins) or stubs straight out at the pins' pitch do not help: a
  0.4 mm comb leaves no room for a via between its teeth or for a tip to turn. Before
  routing anything long, give each signal pin a stub (to 0.25 mm past the pad), then a
  straight line to a via of its own:
  1. per side, go from the middle pin outward, each via outward of the one before, so
     the lines spread like a fan and none crosses another or passes in front of a pin
     still to come;
  2. no line steeper than about 35 degrees from the pin's axis (at 0.4 mm pitch a
     steeper line passes closer than track plus clearance to the next pin's stub end);
     outer pins go deeper, not steeper;
  3. vias evenly spaced, in one row (0.62 mm apart for 0.45 mm vias) or two staggered
     rows (lines to the second pass between the first's vias), with a straight run out
     of the pins first where capacitors stand in front; search the spacing, depth,
     sideways shift and run for the cheapest pattern that serves every pin;
  4. check planned lines with exact geometry (segment to segment, pad, via, zone), not
     the router's grid: a grid judges a line at any angle only to within its pitch
     (0.07 mm on a 0.1 mm grid), and one that answers "radius 0" queries only at nodes
     it lands on exactly hardly checks diagonal lines at all (OWLternating Current's
     first fan-out overlapped; 53 shorts in DRC);
  5. route the chip's short local nets first (USB, flash, a current-setting resistor),
     and plan lines that leave from the middle of a side (a crystal's XIN and XOUT): a
     routed one cuts diagonally in front of the pins beside it and closes them in.
  A pin a fan cannot serve is walled in by its neighbours' lines, whatever comes after
  (keeping its line's place, an escape to the nearest via spot, routing it first: all
  tried, all walled it or its neighbours in). The cure is placement: a decoupling
  capacitor straight in front of a signal pin blocks it and both neighbours, so put it
  midway between two signal pins (an 0402 standing across fits between pins 1.2 mm
  apart) or at the end of the row in front of ground pins that go inward to the
  exposed pad. Have the fan print what blocks each pin it cannot serve.
  The router then starts each net from its via with every layer to choose from.
  OWLternating Current's RP2354A (QFN-60, 33 signals) and LP5036s: 37 nets unjoined
  with the router escaping on its own; with planned fan-outs, the placement moves the
  fan's report asked for, and rip-up and reroute, 1.
- **Router.**
  - The Java autorouter (Freerouting) made things worse.
  - A simple maze router plus hand-planned routes worked (GPSDO). River-routing buses
    first worked (ECP5 P5).
  - When routing fails, look at postage stamps of the router's own obstacle grid around
    one failed connection. Three looks found what a day of blind rebuilds did not (ECP5
    P3; memory). Take them the moment the net fails: by the end of the run later nets
    have covered over what walled it in.
  - Rip-up and reroute is a short function and worth it: keep the cells a walled-in
    search explored, take out the router-laid copper of the nets that bound them, route
    the walled-in net first and then those, and keep the result only if fewer nets end
    in pieces (else put the old copper back exactly). On OWLternating Current it
    finished 4 to 6 nets per run that ordering alone could not. Tag what the router laid
    (planned copper is never ripped), and make vias removable (count each drill's
    keep-out instead of setting a flag).
  - Put every signal on the FPGA face that looks at its chip when the plan is first
    made, spare balls permitting. A slow control line on the far face is the board's
    longest route and the first to fail when anything tightens (ECP5's AD9238 DCS and
    PDWN_A: 60 mm detours from bank 8 that only the fine grid finds). Moving them late
    is not free: the pin swap that follows a plan change reshuffles other balls and a
    board routed at the margin loses other nets (build 28 tried and reverted). A long
    slow line the router finds only by luck is laid by hand on the route it once found,
    before routing: the router cannot lose what it never has to find.
  - A routing report's first-pass failure list is not the result; the retry and fine
    passes fix most of it. Judge by DRC's unconnected count.
  - **A net router must not stop at the first piece it cannot join.** OWLternating
    Current's first runs joined each net's pieces smallest first and returned on the
    first failure: one walled-in pad left +3V3 in 35 pieces. Set the failed piece aside
    (others may still reach it) and go on; report why each failure failed (walled in, or
    out of search budget), because the cures differ.
- **Clean traces.** No zig-zags, loops or detours around a part's own pins. If a resistor
  is in the way of its own trace, rotate the resistor (ECP5 P11).
- **Order reversals need a layer change.** When a chip's pins leave it in the reverse
  of a connector's contact order (GPiBridge Lite: the RP2354A against the GPIB plug),
  no single-layer routing exists, however the lines bend. Find the one place where the
  lines run in the connector's order and change layer there, once per line: on the
  Lite, where the ribbon rises into a row of series resistors, a via above each takes
  it to the bottom layer and straight down to its contact.
- **Two side-entry headers on one side of a board always meet in reverse pin order**
  (GPS adapters, 2026-10-08). Turn them how you like: ribbons leaving two connectors on the
  same face keep the same handedness, so head-on they reverse, and every shared net crosses
  every other. With SMD headers, a net needs two vias. The plan that drew both adapters:
  - each net leaves its pin on the top layer to a via in its own column, runs down or up
    the bottom layer to the row of its pin on the other header, and comes back up;
  - put the second header's rows half a pitch (0.625 mm for GH) off the first's. Then a
    track along any row clears every other row's vias by 0.625 - 0.1 - 0.3 = 0.225 mm.
    Assert it in the generator;
  - the net that is the middle pin of both headers (SDA there) can cross on the top layer
    with a jog and no via;
  - two vias of one net closer than about 1 mm break hole-to-hole (0.5 mm). Join the
    second track to the first via instead of drilling again;
  - any column order works; choose it for where the other parts need their taps.
  A third header in the same bus (the any-to-any hub) is the same thing with one column per
  signal for all of them.
- **Look at a gate package's pinout against the routing before choosing it.** The
  74LVC2G14's VCC pin sits between its two outputs, so on a 2-layer board whose bottom was
  all bus columns its supply had no way out. Two R + LED lamps from 3.3 V into the lines
  (lit while low, about 1 mA, only then) did the job with no IC (GPS hub).
- **No vias in holes.** Keep vias out of through-hole drills, including the routing
  net's own. GPSDO shipped a via drilled inside a header pin (GPSDO r28 #2).
- **Fill zones in the file you ship.** GPSDO's committed board had **no pours**: zones
  were filled into a copy for DRC, and the original went to the gerbers (GPSDO r29 #18).
  Count `filled_polygon` in the shipped `.kicad_pcb` and fail on zero.
- **Pin-header footprints anchor on pin 1**, not on their centre: a lying 1x2 reaches
  6.1 mm past its anchor, a 1x3 8.6 mm. Compute the courtyard from the footprint before
  moving one, or a westward nudge lands on the neighbour (ECP5 P26).
- **The page.** The board sits in the middle of its page with a margin (25 mm) and the
  title block clear below it; a board at the page's 0,0 overlaps the border and the
  title block (ECP5 P26). Keep the design's own frame (origin at the board's corner)
  for every computation and shift only the written file, so gerbers, drill and CPL
  come out in one frame.

- **Never fence a block on both routing layers** (GPSDO rev B, 2026-10-09). The helper
  block's right edge carried the +3V3_D spine on F.Cu and an I2C pair on In2 for its
  whole length, so nothing could leave that side. The six clock branches to the
  right-hand column went round the block: 171-319 mm and 6-14 vias each, against rev
  A's 39-115 mm and 2, and one did not route at all. The detours then stranded three
  other nets. Run a long run on the layer that leaves the other free where the branches
  cross, and draw the crossing by hand.
- **After every routed build, list each clock net's length and vias against the last
  revision.** DRC passes a 300 mm clock; the comparison does not.
- **And every RF net's length against the shortest path through its pads** (CostasLink rev A
  bring-up, 2026-10-29).
  - What happened: LO TX MON's tap, C231 to the U.FL J204, 12.3 mm apart, was routed 115.6 mm round
    the north half of the board.
  - DRC, the net check and the design reviews passed it: they ask whether a net is connected, not
    how far it goes. The bench found it: the monitor read 25.7 dB low at 5.8 GHz, and its loss grew
    from 2 dB at 3 GHz with ripple, a long mismatched line.
  - The check: each net's track length over its pads' minimum spanning tree, printed for every net
    over 2x; an RF net (touching a U.FL, SMA or MMCX, or named RF or LO) fails at 1.5x and 10 mm
    extra (CostasLink `tools/detour_check.py`).  A monitor tap is as much an RF line as the path it
    taps: route it by hand, short, as the 50 ohm line it is.
  - **Put it in the RF net class.** Neither CostasLink LO MON tap, nor the synthesizer outputs that
    feed them, was in any class list. They went in at the Default 0.15 mm and 0.2 mm (about 60-75 ohm
    against the 0.29 mm CPWG's 50), through 2-4 vias each, with their 27 nH pull-ups at the ends of
    2.5-17 mm branches instead of at the pins. LO RX MON's 9.5 mm tap still read 8 dB low at 5.8 GHz
    and 17-22 dB low at 3.0-3.4 GHz. The same chips' other outputs, in the LO class, were laid right:
    the pull-up 1.0 mm from the pin.
- **A board at the router's limit fails one net at a time, and a different one each run**
  (GPSDO rev B, 2026-10-10, after 26 parts were added). More attempts (16, 32) and a
  wider board did nothing. What did:
  - **Terminal protection**: while a net routes, block the free cells round every other
    pending net's terminal, and give exactly those back before its own copper goes in.
    Otherwise an early net runs half a millimetre past a later net's hand-over point and
    seals it in.
  - **Exempt the nets that route first** and must stay short (the helper clocks): under
    protection they detoured round every pending terminal, 149 mm instead of 98.
  - **A keep-away for asynchronous aggressors**: clocks 1.2 mm from I2C. A router with
    one clearance put a 55 mm clock beside SCL.
  - **Late hand routes**: copper drawn by hand only if the net is still split after
    routing, and only where the real geometry is clear (several candidate paths, vias
    checked). Laid early, any hand copper in the congested band moves the outcome.
- **Never route ground, or a rail with a plane or pour, "whole" as a net** (CostasLink,
  2026-10-10, Response 15). It cost 875 mm of top-layer copper nobody needed.
  - What happened: the planned-copper stage gave a fan-out line to every pin of a
    chip, the ground pin of a chip without a paddle included. A pin the fan-out could
    not serve was then routed "whole, while the board round it is still empty". For a
    ground pin, the whole net was GND.
  - It ran before the stage that drops a via beside each ground pad. Every bare ground
    pad on the board was still a piece of its own, and the router joined them all to
    each other with tracks on the top layer: 875 mm in 580 segments. They ran between
    U112's two pin rows and along pin rows.
  - The via stage then found every ground pad already joined and placed no vias. Its
    log said "0 ground vias" in every build of Response 14, and nobody read it.
  - The top layer round the loop block was fenced before the first signal was routed.
    VC's 2 mm hop from U112 pin 7 to its capacitor was walled into 48 cells. Four nets
    failed in every variant tried (eight router orders, a wider rip-up, smaller pours)
    until the planned copper was looked at.
  - The rule: a plane net's pads each get their own short stub and via ("Each ground
    pad gets its own via", above). Any helper that routes the rest of a net skips GND
    and the rails that have a pour.
  - The check, every build: print each plane net's track length per layer after the
    planned stage, and the vias the via stage placed. GND on a signal layer is a few
    hundred stubs of half a millimetre (CostasLink after the fix: 288 mm in 550, and
    173 ground vias). A long run, or zero vias, means something else joined the pads
    first.
- **Join a net's short connections before routing any net whole** (CostasLink Response
  15). A router that takes nets in order of span routes a board-wide net's 2 mm hop late:
  VC's U112 pin 7 to its capacitor, the PI node's two resistors. By then the long nets
  have fenced the pad in. Before the long routing, join every pair of a signal net's
  pieces whose pads lie within 5 mm, shortest pair first. Search only round the pair:
  the top layer without a via first, then any layer. CostasLink joined 72 of 95 that way.
  With the GND fix, nets in pieces after the repair went from 3 to 2, and from 3 to 1
  together with the next item. GPSDO rev B's terminal protection is the other cure for
  the same disease.
- **Count what an inner layer's supply pours leave for the signals.** A pour drawn as a
  routing obstacle closes its layer to every other net. CostasLink's In2 pours covered
  73% of In2; with In1 solid ground, most of the board had two signal layers, one of
  them under the parts. Draw a pour only where its rail's pins need it. The +3V3_DIG
  pour served three slow chips across the whole loop block; shrunk to the comparator
  strip that needs it, and with In2 priced at 3 instead of 6 for signals, the last two
  nets routed. The trials, run side by side on copies of the project: 2 nets in pieces
  with short connections first alone, 1 (only GND, which the fills join) with both.
- **Join a track that ends inside its own via, off the via's centre, to the centre**
  (CostasLink Response 15). Planned fan-out vias sit at exact, off-grid places; a grid
  router ends its tracks on its grid inside them, up to 0.2 mm off. KiCad does not count
  such an end on an inner layer as connected. The cleanup pass then saw a dangling via,
  removed it and cut ERR in two. Add a segment no wider than 0.15 mm from the end to the
  centre: it lies inside the via's pad. Moving the end instead dragged 346 tracks at an
  angle into their neighbours (18 clearance errors, 7 crossings) and collapsed short
  tracks to nothing. A 0.5 mm rail-width segment stood out of the via's pad: 2 more.
- **Ask KiCad which pads nothing reaches, and join them** (CostasLink Response 15). A grid router
  can count a line that runs past a pad as joined to it; KiCad wants the copper on the pad.
  TX_EN's line passed R227's pad 0.05 mm clear of its rounded corner, both of the line's ends
  were anchored elsewhere, so the dangling-end pass never saw it, and DRC said "unconnected".
  After the fill: for every SMD pad whose `GetConnectivity().GetConnectedItems(pad)` holds
  nothing but pads, add a segment from its centre to the nearest same-net track on its layer
  within reach. Decide by KiCad's connectivity, not by geometry of your own: a test of track
  ends inside the pad flagged eight pads that a track crossing them already joined.
- **When the same nets fail whatever the router does, the wall was laid before the
  router ran** (CostasLink Response 15). Build the planned stage alone and look at it
  as the router receives it. A cleanup pass that removes dangling copper must not run
  on that view: every fan-out via dangles before routing, and the tidied view showed
  nothing round the chip that was walled in.

- **A shunt-at-pin rule on an ADC's inputs walls its neighbours** (CostasLink, Prompt 31).  Four 100 nF
  placed hard against the ADS1115's pins boxed the series resistors' far pads and the slow ADC's SCL pin:
  the same two nets failed in six route seeds.  A 160 Hz filter does not care where its parts sit: anchor
  them a few millimetres out, with the I2C side clear, before trying seeds.  Seeds are for luck; a net
  that fails in every seed is a placement fault.
- **A new footprint changes the router's luck** (CostasLink, Prompt 31).  Swapping a 6-pad balun for a
  4-pad one left 3 nets in pieces where the last build had 1.  Try seeds side by side in rsync'd copies
  (`COSTASLINK_ROUTE_SEED=n python3 gen/board.py`, 9 min each, six at once on 32 cores) and keep the
  seed that finishes in `gen/routes.py`.

- **A rail routed wider than its fan-out stub leaves a sliver the tidy re-makes** (CostasLink Prompt 35: rails
  routed at 0.3 mm into 0.15 mm stubs; a 0.2 mm overhang at the DSA's VDD pin was called dangling by the DRC,
  removed by the refill, and laid again by the next tidy, in every pass of six builds).  Route a rail at the
  stub's width and let the widening pass (which keeps narrow near fine pins) do the rest, or end the stub where
  the wide track starts.  And measure the result by net: the widening finds room on a third of the length.
- **A connector's courtyard is what the placer says, not the body** (U.FL 4.35 x 5.0 mm, MMCX 4.9 square,
  SOT-23-5 4.1 x 3.4, a 1x2 header 3.5 x 6.1 with its origin on pin 1): print `load_footprints()[name]["court"]`
  before laying a row of jacks, and keep GAP (0.5 mm) between courtyards.  Seven U.FL at 5.5 mm pitch need 38 mm.

- **SOT-23 geometry decides the transistor's rotation** (op-amp board, 2026-10-24). KiCad's SOT-23
  pads are 1.475 x 0.6 mm with a 0.4 mm gap between the rows, so nothing routes under the body between
  them, but the lone pad (3, collector) faces a 1.3 mm gap between the two same-side pads (1 base,
  2 emitter). To draw a transistor the way the schematic does, place it at rotation 90 (collector up,
  base lower-left, emitter lower-right) and run the collector wire straight up between nothing; mirror
  to rotation 270 when the base arrives from the right (the + input's Q2, the sink's Q6 with its
  divider on the right). Every wire then leaves a pad in the symbol's own direction and the silkscreen
  emitter arrow can be derived from the real emitter wire.
- **Copper follows the drawn wire.** On a board whose silkscreen is the schematic, the generator takes
  one list of wires (net, points, width) and draws each both as F.Cu track and as F.SilkS line, so the
  picture *is* the netlist. Crossings are "hops": the crossing track dives to B.Cu between two vias and
  the silkscreen draws a half-circle arc over the other wire, as a textbook draws a jump. No front pour:
  fill would bury the drawing, and a 2-layer board with a solid back ground plane needs none. Three hops
  on a 100 x 100 mm six-transistor board; plan the floorplan (inputs left, output right, rails top and
  bottom as lines) to keep it there.

## 6. Silkscreen: the board explains itself

The board should be usable without the schematic. It must be obvious how *not* to make a
mistake with an input level or a plug direction (GPSDO P7).

- **Identity:** the board name; "by Jason Gallicchio and Claude"; the URL; the date; and
  "rev A", the least prominent of these (Lorenz P1, P5, GPSDO P10). Add a QR code with
  its URL printed under it when there is a web page (Lorenz P2, P4).
  - The date is the day the file was built, written by the build, never typed in.
- **Connectors.**
  - Names are **big**, right next to the connector they name, never between two
    connectors (ECP5 P2, memory).
  - Every connector that leaves the board is labelled with what it is for and its
    limits: "±1 V MAX", "15 V DC, 1 A MIN" (ECP5 P2, GPSDO P13).
  - The label sits by **that** connector, not the neighbour's (GPSDO P17).
  - A U.FL tap's name stands beside the tap and its designator is not printed: "J107"
    reads as a jumper, and nobody finds the jumper (ECP5 P26).
  - A connector that is one of a pair says which way it goes ("TRIG A" with "OUT" on a
    small line over its level; "ANT" with "TX+RX" under it).  A limit may hold a newline:
    KiCad prints it on two lines, the placer reserves the longest line wide and both tall
    (CostasLink Prompt 35: "TRIG OUT A" did not fit before the next chip).
  - **The user's instructions go on the back** where the back is bare: how to cable the
    alternatives (one antenna or two), which 5 V source is which, the jumpers' defaults
    (CostasLink Prompt 35).  Silk over tented vias and tracks is fine; never over pads.
  - **One relation per row, enforced** (CostasLink Response 15). Jason: "There should be
    a big-font silk screen right next to the connector, so it's obvious what it's for. For
    example, "TRIG A" seems fine, but "TRIG B" is between two SMAs and off to the side ...
    If there are SMAs in a row, their labels should all be in the same relative
    orientation ... This consistency requirement needs to be enforced."
    - A row: connectors of one footprint in a line. The SMAs along one edge are one row
      however far apart; taps and test pads a few millimetres apart are one.
    - Every name in a row stands on the same side of its own connector, at the same gap,
      centred on its signal pin the same way, at the same angle and size. Its limit
      follows the name the same way, or is printed once for the row when all share it.
    - Rev A's first try put "TRIG B" above its jack, between two jacks, while "TRIG A"
      sat right of its own. Its test pads' rails alternated above and below. Its window
      monitors had three names above and one below. All three fail the rule.
    - Big: 1.5 mm for an SMA, 1.0-1.2 mm for a tap or a pad. Long names on a tight pitch
      (rails on 4 mm pads, four U.FL at 5.5 mm) stand turned, one column per connector.
    - Decide each row's side in the placement plan and reserve its strips **before** the
      small parts are placed (CostasLink `gen/placement.py` `LABEL_ROWS`, `HEADER_LABELS`).
      A label laid after placement finds the room already taken, and rev A's first build
      dropped five SMA names silently. A name with no room means moving a part. Never
      move the one label off the row's relation.
    - A reserved strip moves the small parts placed by rule, and the move cascades. One
      strip over a selector's middle pin pushed one capacitor and reshuffled seven of the
      TX synthesizer's parts. The synthesizer's rail then failed to route. Measure every
      moved part against the pin it serves. Pinning a moved part back changes the placer's
      order and shuffles its neighbours instead, so move the strip that caused it. A
      selector's function name can go below the jumper as well as above.
    - The labeller takes the planned side at a smaller size before any other side at a
      bigger one. J502's name at 1.2 mm on an unplanned side took the room planned for
      JP101's labels. Labels placed later (part names, designators) keep 0.8 mm from a
      connector's name, and 2 mm along its line: "VCXO" beside "REF OUT" read as one name.
    - Check it on the written board, independently of the placer, and fail the release on
      it (CostasLink `tools/label_check.py`, run by `make_release.py`). Every name must be
      present, at least 1.0 mm tall (SMA) or 0.9 mm (tap, pad), and its own. Judge
      ownership from the name's near end, where a reader ties it to a part, with no
      other body nearly as near. Each row must hold one relation. A limit left off is a
      named exemption with its reason, printed on every run.
- **Header pins.** Every pin is labelled next to itself: the top row's labels above it,
  the bottom row's below. Never all on one side, which makes people probe the wrong pin
  (GPSDO P29, Icepi P30).
  - Rotate the labels with the header (GPSDO P17).
  - Name the colours and signals of screw-terminal wires at the screw (GPSDO P13).
    - Centre each label under its pin, in the strip just outside the
      terminal's outline.
    - Reserve that strip before placing the terminal's own resistors, and keep
      the designator out of it.
    - A placer that slides a label sideways to clear a part makes it read as
      the neighbouring pin's. Rev A's `red` sat nearer GND than VCC
      (GPSDO r45).
- **Jumpers.** Say what each does, **right beside it**, on every copy: a legend's "1-2 =
  50R" asks the reader to find pin 1, which a fitted shunt hides, and a column of tiles
  turned 180° puts the same choice at the other end (GPSDO rev B: `50R` and `PARK` beside
  each header's own pins, a tick at the common one). A 2-pin jumper's "50Ω IN /
  hiZ OUT" or "x1 IN / x10 OUT" next to its pins, a 3-pin selector's two choices beside
  its two outer pins with a tick through the centre pin between them. Two selectors
  stacked with "PD" and "NOISE" between them label neither (ECP5 P11, P26). Fail the
  build when a jumper's label lands more than a few millimetres from it. A jumper that
  cannot select what its label says is a bug Jason will find.
  - Take each choice's text from the net on that pin, never from the drawing's left and
    right. CostasLink's two sign jumpers printed "Q-" at pin 1, and the netlist puts Q_P
    there (found in Response 15). Two selectors with the same choices also need
    different names ("SIGN B1", "SIGN B2"), or the board cannot say which is which.
- **Test points.** Labelled at the pad with the rail or the expected reading ("3V3",
  "In 10 MHz 0.7-8 Vpp"). If a legend is used, it must be legible and aligned, and the
  letters unambiguous (an "I" read as a "1": GPSDO P29, P13).
- **ICs.** Name them by function and part number ("MPY634 multiplier", "op-amp
  LF412"), along with the component values (Lorenz P1, P3).
- **Region labels** sit **inside** the box, under its top edge, never in the line: a
  name cut into a line that two boxes share reads as either box's, and "ADC B IN" ended
  up halfway between ADC A and ADC B (ECP5 P14, P26). A label for a box must not look
  like a label for one part inside it.
- **Overlap.** Nothing overlaps anything: silk on silk, silk on pads, silk over the
  edge. A label that will not fit goes to F.Fab, not on top of something.
  - The checks must cover labels as well as components (ECP5 P14).
  - Report both lists every build: labels outside their part's box, and parts outside
    their box. A part on one side of the line with its label on the other is "never
    good" (ECP5 P26); grow the box or move the part.
  - Leave out "MountingHole" and its reference (Lorenz P2).
- **Printable sizes.** At least 0.8 mm text height and 0.15 mm line width at JLCPCB.
  KiCad checks text height but **not the width of graphic lines**: stock footprints draw
  0.12 mm (GPSDO r29 #23).
- **Never drop a library's silkscreen by a crude test.** ECP5's writer dropped every footprint
  silk line that came within a square the size of a pad's longer side, which removed nearly
  all outlines and the SOD-123's cathode line (0.2 mm from its pad), so JLCPCB's viewer and
  anyone holding the board had no cathode end to check D501 by (2026-10-08). Clip against
  the pad's real outline plus the fab's silk-to-pad clearance, and count each footprint's
  silk lines in and out of the writer.
- **Pin-1 marks.** Add one only where the pad pattern is symmetric under a half turn
  **and** the library prints nothing. A second dot next to the library's triangle is one
  more dot to confuse with JLCPCB's purple one (Lorenz P5, Icepi jlcbuild). Oscillators
  and crystals with only an "L" for a cue need a big dot (GPSDO P35).
- **Prose on the silkscreen.** Left-justified, broken at sentence boundaries, and
  checked for grammar (Lorenz P3, P4).
- **A legend paragraph sits beside what it explains**, wrapped to the room there: the
  headers' paragraph above the box the headers live in, the USB paragraph under the
  FTDI. "The largest free area" put them in the middle of the board (ECP5 P28).
- **Look at the real thing.** Judge silkscreen from KiCad's own rendering
  (`kicad-cli pcb export svg`, rasterised), not from a quick matplotlib plot that draws
  text at a third of its size: the plot said "fine" where the print overlapped (ECP5
  P26).
- **Card slots.** A microSD on the back, inboard, says which way the contacts face
  ("contacts toward the board") and where the card goes in ("card slides in here")
  (ECP5 P26).
- **Ports named for the student.** "USB USER", not "USB FPGA": a name that says whose
  port it is keeps the one cable out of the wrong jack (ECP5 P26).
- **Every pin of every connector, even at 1.25 mm pitch** (GPS adapters P2: "It would be
  nice if all pins of each connector could be labeled, again even if the labels are small";
  "the github page ... even if it's very small"):
  - 0.9 mm text in a column beside the pads, one label per pin, centred on its row;
  - the back of the board repeats them with the pin numbers and longer names. It is free
    room when every part is on top: "2 TX: FC TO GPS";
  - the URL goes on the front even at 0.8 mm, and on the back with the QR code.
- **Name UART lines by whose they are.** Pixhawk, CubePilot and ArduPilot label a GPS port
  from the flight controller's side (pin 2 TX); Holybro's GPS tables label the same wires
  from the GPS's side (pin 2 "RX (in)"). Print "FC TX" and "FC RX", say so on the board,
  and map connectors by pin number, never by the words.

- **No label in another unit's box, checked on the written board** (GPSDO rev B,
  2026-10-10; Jason: "one of the most confusing things from last time was when labels for
  one unit showed up in another unit's box").
  - A placer check that only covers parts with a home box misses parts that live in a
    tile but belong to another sheet. Rev B's in-tile heaters had no home, and eight of
    their designators sat in the NEXT unit's box.
  - Give such a part its tile as home, and keep a homeless label out of every unit box.
  - Then read every F.SilkS text off the written board with KiCad's own text boxes and
    find each one's owner: a designator's footprint, a free text by the placer's record
    of who placed it. GPSDO's `pcb/check_unit_labels.py` does this in every build; with
    `--stamps DIR` it draws one picture per unit, labels coloured by owner, for the
    look by eye.
- **A designator prints only where its own part is the nearest one**, or it goes to
  F.Fab. A last-resort search for "any clear spot inside the box" had walked 236 of
  GPSDO rev B's names up to 9 mm, beside other parts (R251's name under the heater R2002,
  so the heater read as R251). A name by the wrong part is worse than none, inside a unit
  as much as across units.
- **A tap's name says what it carries, and sits tight against the jack** (GPSDO rev B:
  `IN` and `SQ` on each channel), on the side away from any jumper. A first try that
  let the name range 8 mm put it on a 3-pin header's edge, where it read as one of the
  jumper's settings.

- **For people who have never seen the material, every label is a word** (Jason, op-amp board,
  2026-10-24: "'tail' should indicate that the transistor is there to make a constant current source.
  Other labels like 'comp' should be full words, even if they need to be rotated. This is for people who
  have never seen this material."). No "COMP.", no "1 cap / 2 no 1k": "COMPENSATION", "1: 100pF + 1k",
  "2: no 1k", "CURRENT SOURCE" standing up the side of the TAIL box when it has no room across. Rotate
  a title rather than abbreviate it.
- **Never name a node after a part that exists** (op-amp board). The diff pair's output was labelled
  "C2" on the sheet and on its probe loop, while the board also has a 10 µF bypass called C2. Name nodes
  by part and pin, "Q2 C", "Q3 E", "Q1 B", on the schematic labels, the loop values and the handbook
  alike, and keep the one spelling everywhere, because the netlist names are what the board's wire table
  and the circuit checker match on.
- **KiCad's stroke font is about as wide as it is tall**: measured with `PCB_TEXT.GetBoundingBox()`
  on the op-amp board at 0.15 mm stroke, capitals advance 0.95-1.05 x the size per character
  ("PUSH-PULL" at 0.8 mm = 7.45 mm, "OUTPUT CURRENT" = 10.8 mm, "FOLLOWER x1" = 8.4 mm), lowercase and
  digits 0.8-0.9 x ("1: X to IN- (x11)" at 0.8 mm = 11.3 mm), and a lone letter 1.2 x. The earlier
  "0.76 x size" in this file was a lowercase average and put four titles through box edges. Measure a
  string before giving it a slot: load the board in pcbnew and ask for the bounding box. The board's
  DRC rules (silk text 0.8 mm minimum, silk-to-silk clearance 0.15 mm, warnings counted) then catch
  every overlap, so design to them rather than to the eye: lines of lowercase text 0.8 mm high need a
  pitch of 1.3-1.5 mm (descenders and commas), capitals 1.2 mm. A dashed stage box's title must
  dodge the wires that enter the box from above: a vertical feed to a transistor's collector cuts the
  title strip in two, and a transistor's symbol circle (r 4 mm) blocks the rows beside it.
- **A wire crossing a box's title band gets a jog, not the title an abbreviation** (op-amp board):
  Q4's collector could not run straight up to +15 V without splitting "PUSH-PULL FOLLOWER", so it
  steps 4 mm sideways just above the circle, rises along the box's edge and hops under the bus. The
  jog is a cost in schematic fidelity paid once; an abbreviated or missing stage name is paid by every
  student.
- **Nothing sits on a box edge.** The box generator clips its dashes round every courtyard, so a
  part whose courtyard straddles an edge erases a whole run of it: the op-amp board's FEEDBACK
  switch sat 0.2 mm below the limiter box and the bottom of one box and the top of the next both
  vanished (Jason: "There is a component right on the border ... that prevents the bottom of the
  'OUTPUT CURRENT LIMIT' box and the top of the 'FEEDBACK' box from being drawn"). Leave a clear band
  of 1 mm or more between boxes, and run any bus that joins two boxes along that band (the limiter's
  two diode returns go round the outside of the push-pull box, above and below), never through a
  third box.
- **Dashed boxes around the stages, named as the book names them** (Jason, op-amp board: "draw boxes
  with labels around things like 'difference amplifier' and 'push pull emitter follower' or however the
  book explains it"), with the stage's gain in the title ("x11", "x30", "x1"). The box generator clips
  its dashes around pads, courtyards and the wires that cross its edges.
- **A loop that sits on a labelled rail needs no label of its own**; "+15V" printed beside a loop on the
  line already marked "+15 V" is one more thing to dodge in the band above the rail.

- **Label a thing where it is, never somewhere else by its designator** (Jason, op-amp board,
  2026-10-24, to go in this file in as many words: "if you can label something where it is relevant,
  it's *much* easier for humans to read than labeling it somewhere else with its reference
  designator. I don't want to have to read something on the top and say to myself, 'Okay, now
  which switch is SW3?', nor do I want to see a switch (or group of switches) and say to myself,
  'Okay, now where is the function of this described?'"). A switch's function goes in a box
  round the switch; a connector's limits beside the connector; a stage's name in the stage's
  box. A legend band that says "SW3: ..." is a failure of layout, not a solution to it. Plan the
  room for the words when the part is placed, as for connector names.
- **A transistor symbol a novice can read** (op-amp board, after Jason, twice: "the arrows on your
  transistor symbols aren't that great. They need to be inside of the circles. It should be very
  obvious ... whether it's NPN or PNP, and which pin is the emitter, base, and collector"; then "The
  vertical line where the base comes in, the emitter arrow, and the collector's line should all be
  more well within the circle. Maybe the circle just needs to be bigger. The 'E', 'B', and 'C' labels
  can be inside of the circle. The 3 SMT pads themselves also awkwardly connect to the symbol lines
  ... make them much thinner than the lines for the symbol itself"). What works, round a SOT-23
  (`gen_pcb.q_geometry` on the op-amp board): a circle of r 4.0 mm (0.25 mm line) centred on the
  package; the base bar 2.2 mm from the centre on the side the base wire arrives from, 2.8 mm long,
  0.55 mm wide; the base lead from the circle to the bar; the collector and emitter legs (0.45 mm)
  leaving the bar's two ends at 45 degrees, turning vertical at 3.6 mm and leaving the circle at the
  top and bottom directly above and below the package, so the wires outside are straight; a filled
  arrowhead on the emitter leg, at its outer end pointing out for an NPN, against the bar pointing
  in for a PNP; B, C and E in 0.8 mm letters inside the circle, in the three empty corners; and a
  0.16 mm hairline from each pad to its lead, square on to the leg, with the copper under the
  hairline and under the lead out to the circle, so the wire, the symbol and the pad are one
  conductor. Everything in a frame with the bar on the left and the collector up, mirrored per part
  (base side, NPN/PNP), with the wires ending where the leads leave the circle (resolve a transistor
  pad in a wire to that point, not to the pad). The symbol replaces the footprint's own outline
  (drop its F.SilkS items; set `lib_footprint_mismatch` to ignore) and the wire clipper treats the
  circle as a keep-out so the wire stops at the ring. Turn the package so the base pad is on the
  bar's side, always: rotation 90 (lone pad up) for an NPN with the base from the left, 270 for one
  with the base from the right, and 90 for a PNP, whose lone collector pad then sits under the
  emitter leg and gets a hairline running down between the other two pads. The other arrangements
  put a pad where its copper cannot reach without crossing another lead (the 0.4 mm gap between the
  lone pad and the pair is impassable; the 1.3 mm gap between the pair is not). A wire must reach
  the circle square on, along the lead's line: a riser that touches the ring tangentially looks
  wrong, so a base that comes from below turns horizontal 1.4 mm before the ring. One type legend
  ("Q1 Q2 Q4 Q6 Q7 = 2N3904 NPN") in the title band beats eight captions fighting for room.
- **Grounds point down, except where ground really is above** (Jason, op-amp board: "Move things
  around so that the ground symbols always point down. The exception ... might be for the decoupling
  capacitors for the -15V, where ground really is above -15V"). A part that returns to ground hangs
  down from its rail: the divider under the output line, the +15 V lamp down from the top rail, the
  -15 V lamp up from the bottom rail with its symbol pointing up. A ground stub may be a path (pad,
  corner, via) so the symbol can hang down beside a connector body instead of pointing sideways
  out of it.
- **The schematic's own characters**: KiCad's stroke font has ± (U+00B1); write "±13 V", not "+/-13 V",
  on the board and on the sheet.


### Lessons from the PID motor board (Lab 10L, 2026-10-24/26)

- **An op-amp in SOT-23-5 is drawn + on top.**  Pin 1 (+IN) is the upper-left pad, pin 3
  (−IN) the lower-left, so a triangle round the package has + above − whatever the book
  does; feed the − network from below and put the feedback row under the triangle.
- **V− of a SOT-23-5 is trapped.**  Pin 2 sits between the two inputs; no front copper can
  leave the triangle from it.  Take it to the back through a via *inside* the triangle,
  surface it just under the triangle's bottom edge as a "−15 V" flag with the bypass
  capacitor hanging from it, and join the flags with a back trunk.  The sheet draws a power
  symbol at each op-amp; the board can too.  Draw the hairline from pad 2 to the via dashed.
- **A signal that must cross every stage goes on the back as a dashed line** (POSITION
  from the plant terminal back to the LOOP switch): a net label with a route.  Everything
  else stays a drawn front wire.
- **Back runs box the ground plane.**  Two −15 V branches plus a +15 V spine plus their
  taps made a closed rectangle on the back with a bypass via inside it; the fill removed
  the island and DRC said "unconnected".  After the fill, test every ground via against the
  plane polygon (`ZONE.HitTestFilledArea`) and fail the build if one is outside; route the
  taps to one side so no loop closes.
- **A three-pin slide switch with the pins on one edge (MSK12C02) traps its common pin.**
  Pin 2 sits between 1 and 3 on the same edge: with the body horizontal (rot 0/180) the two
  outer wires go up and turn away left and right and the common goes straight up between
  them; with the body vertical the outer wires must leave up and down.  So choose the
  schematic's pole assignment for the board: pole 3 (the upper pin at rot 90) = "into the
  sum", pole 1 (lower) = "off"; and put the D-capacitor selector *before* its two capacitors
  so its common faces the ERROR column.  The datasheet draws pin 2 common and nothing about
  which travel closes which pole: unverified, on the DOA list.
- **KiCad symbol coordinates have y up.**  The SW_SPDT's pin 1 at (5.08, 2.54) is the
  *upper* right pin on the sheet; `mirror x` puts pole 3 on top.  Check a pin's sheet
  position before deciding which pole is "upper".
- **A DPAK symbol.**  KiCad's TO-252-2 has the base and emitter pads 2 mm below the tab, in
  line; a 45-degree emitter leg from a bar beside the tab cannot pass between the tab and
  the base pad with silkscreen clearance.  What fits: the circle r 8.2 centred 1.5 mm
  toward the tab, the bar 4.5 mm out, legs at 33 degrees (BH 3.25, bend 6.17), the base
  hairline running horizontally from the pad to the bar's line and the bar extended down to
  it, the emitter hairline just below its pad across to the leg's vertical, the E letter
  between the tab and the emitter pad, the collector lead 2 mm wide into a pour that stops
  outside the circle.  Two DPAKs in a push-pull with 2512 sense resistors between them need
  the circles 32 mm apart centre to centre.
- **A 'silk clipped by solder mask' warning names the nearest pad, not the cause.**  It
  pointed at the tab while the leg's corner touched it 1.6 mm away from the bar it seemed to
  blame.  Delete the symbol's pieces one at a time in a scratch build until the warning
  moves: five minutes, where reasoning about the geometry took an hour.
- **Grounds pointing up are allowed when the geometry forces it:** the difference
  amplifier's 100k from the + input to ground has no room below the + row (the − row is 6
  mm under it), so it stands above with its symbol up, like the −15 V decoupling exception.
- **Dashed back-run silk is silk**: it collides with text, footprint outlines and pads like
  any line.  Route it under part bodies only where their silk is clear (between the
  terminals' pins and the parts above them), and keep probe loops off it.
- **Keep the fab's silk minimum in mind from the first text**: this board's rules say 0.8
  mm; thirty labels written at 0.75 all came back as `text_height` errors.
- **Clockwise is more resistance; say what that does.**  Jason (2026-10-25): "I generally do
  want clockwise 'screwing in' to increase the resistance.  Sometimes that corresponds to
  decreasing the relevant gain, which might be counter-intuitive."  Bourns' 3362 data sheet
  marks terminal 3 CW (the wiper reaches it turning clockwise); wire every trimmer as a
  rheostat between 1 and 2 with 3 tied to the wiper, and put a short arc over the top of
  each knob and trimmer ending in an arrowhead at 12 o'clock with the effect beside it
  ("↑R ↑P", "↑R ↓I", "↑TARGET").  Newstroke has ↑ ↓ → ↻ ↷ (not ⟳), so the arrows are
  plain silk text.  `check_circuit` asserts the 1-2 wiring; `gen_pcb` refuses an arc that
  comes within 0.5 mm of a drawn wire, since DRC does not mind ink over ink.
- **The arc needs 5 mm of clear board above the part.**  A 3362P's wiper is on top, so
  its tie to terminal 3 wanted to leave upward through the arc; run it under the body
  instead (pin 2 across to pin 3's column and down: the one wire the part hides), feed the
  ends from the sides, and give the stage the height (the D stage's feedback row went up
  1 mm and its return row down 0.5 mm).  Radius 5 from 238 degrees: a 10 o'clock start
  lands on the wire that feeds terminal 1, and anything lower than 4.1 mm above the centre
  overlaps the trimmer's own silk box (DRC silk clearance 0.15 mm).
- **Probe-ability beats the PCB price on a low-volume board.**  Jason, on 170 x 120 mm
  against the 100 x 100 discount: "I'd rather keep the ability to probe than save a few
  dollars.  Not every student needs one of these boards, whereas every student needs an
  op-amp board."  Shrink a board every student gets; let a lab-station board be big.
- **The back silkscreen is the students' manual.**  Jason (2026-10-25): "Students will *not* read
  the documentation in the README.md, but they might read this silkscreen."  Use the back's
  room: one item per line (each switch position its own line, a second column for the
  options), inputs, outputs, trimmer directions, a start sequence, warnings; a wide column is
  fine if it buys one idea per line.  URLs with https://.  Name class-foreign words in class
  terms ("fader (motorized potentiometer)").  Skip what the front shows.
- **A probe loop on every op-amp output**, and on the push-pull's bases, so the crossover
  jump (about 1.2 V as the output crosses zero) can be seen.  Where a loop's name has no room
  beside it, print it rotated 90 degrees between the parallel wires.
- **A slide switch's travel can be read from the data sheet's section.**  The MSK12C02
  drawing shows the handle carrying the moving contact onto the terminal on its own side,
  with the common in the middle: the slider toward pin 1 closes pin 1.  Still an ohmmeter
  check on the first board.
- **Decode the off-board part's order code before trusting "a 10k linear track".**  The lab's
  fader turned out to be a Bourns PSM01-082A-103B2, not the SparkFun part the design assumed:
  its "B2" taper is linear only from 10 % to 90 % of the travel (flat 10 mm at each end), and
  the linear one is the second, "servo" track.  The same data sheet gave the motor polarity
  (A positive moves the lever toward terminal 1), so the handbook can say "1, 2, 3 to POT 1,
  2, 3" instead of "swap the wires if it runs away".  Ask for the exact part number of
  anything the board plugs into.
- **Read a chart's curves from the PDF's vector paths**, not by eye: `pdftocairo -svg -f N -l N`
  and parse the `<path d=...>` points with their `transform`; the grid lines give the axes.
  Eyeballing a rendered chart put the same curve's ends 5 % apart on two tries.
- **A motor's ohmmeter reading is high.**  18 Ω on a meter, 14 Ω from the stall current at
  5 V: the brushes' film at a few mA.  Use the stall current at a few volts for R.
- **A D2PAK is too big to draw round.**  Its tab (10.8 x 9.4 mm) fills any circle that
  holds it.  Draw the transistor's circle round the two leads and let the tab cap it (the
  arc stops at the tab's silk clearance); run the base lead straight through the base pad
  into a bar between the leads; end the collector leg at the tab.  The pour round the tab,
  on the collector's net, then reads as the collector.
- **An NPN/PNP push-pull in one unmirrorable package needs one crossing.**  Turning the PNP
  180° keeps its B, C, E in the same cyclic order as the NPN's, while the schematic's PNP is
  mirrored, so the wire from BASES to the PNP's base must cross the PNP's emitter wire or go
  round its collector pour.  With big pours, plan one hop under the emitter wire beside the
  emitter resistor and leave room for its two vias.
- **Put the fuse ahead of everything a student can reach.**  A PTC in the motor lead left
  the DRIVE probe loop, the driver's feedback and DRIVE OUT ahead of it, so a scope's ground
  clip on the DRIVE loop was a short that only the transistors limited (2.3 A, 28 W in one).
  Put it straight after the output stage's emitter resistors and take the feedback from
  behind it: the loop then corrects the PTC's 0.2-1.7 Ω, the motor gets exactly what the
  loop asks for, and the only unfused copper is the short run from the emitter resistors to
  the fuse, with no loop and no name.  The clamps and the snubber can stay at the
  transistors, ahead of it.  Ask of every probe loop: what does a ground clip here do?
  (Review round 1; Jason: "move the fuse".)  `check_circuit` asserts the set of parts ahead
  of the fuse, and that none is a TP or a connector.
- **An integrator's capacitor is a filter part: film or C0G, never X5R.**  A 10 µF X5R
  loses much of its value at the few volts the integrator holds, so I's time constant moves
  with its own output (section 12).  Polypropylene at 10 µF is a brick (27.5 mm leads), so
  go to 1 µF and let the 1 M trimmer carry RC to 1 s; that also spreads the useful I range
  over the whole turn instead of its first tenth.  The price is a bipolar op-amp's bias
  current through the bigger resistance (LM321: 45 nA x 1 MΩ = 45 mV of residual), which a
  behavioural op-amp model does not show: put it in a check.  Panasonic's ECW-F (450 V,
  "active filter circuit" in its own data sheet) is stocked at JLCPCB (C242107, 18.1 x 9.3 mm,
  leads on 15 mm); JLCPCB's land pattern (`easyeda.py`) confirmed the footprint's origin.
- **Check a CPL rotation by overlaying their drawing on your pads, posts included.**
  Transform every pad of JLCPCB's land pattern (`easyeda.py <code>`) by the upload CPL's
  (x, y, rotation, counter-clockwise) and measure each against the board's pads.  A pin row
  alone is symmetric under 180 degrees: one reviewer "confirmed" the RK09K knob's rotation
  from its pin row while the posts and the body sat on the wrong side, 6-8 mm off; the
  overlay showed it at once.  Calibrate the overlay on parts whose rotation a real preview
  showed, and expect pad numbering to differ for LEDs and connectors.
  - The op-amp's `scripts/check_overlay.py` (2026-10-29) does it from the upload files
    themselves (Mid X, Mid Y, Rotation, the BOM's codes), in the build: each of their pads
    within 0.25 mm of one of ours, pad for pad by number where both sides number alike,
    and for a connector whose pins are symmetric (BNC, screw terminals) the face a cable
    enters, turned by the CPL, against the nearest board edge's outward normal.  A terminal
    block turned for its wire openings puts their pin 1 in our hole 2: say so, it is right.
- **A pad fit cannot see the body: draw a through-hole part's body from the maker's
  drawing, and compare the centre of JLCPCB's whole drawing with your courtyard's**
  (the op-amp, rev A preview, 2026-10-29).  Every pad check passed RV1, a Bourns 3362P, at
  0.04 mm, but its footprint centred the body, silk box, courtyard and 3D model on the
  triangle of pins, where Bourns puts the body's centre on the line of pins 1 and 3,
  1.3 mm away.  The preview drew JLCPCB's body poking out of the printed box and Jason
  nudged it to the box, which moves the pins off the holes; harmless for legs that only
  fit their holes, wrong for anything placed by machine.  The centre of EasyEDA's drawing
  is in the `docType 4` entry's `bbox` (canvas units of 10 mil, from the land pattern's
  `c_origin`); turned and placed by the upload CPL it lands within 0.11 mm of the
  courtyard's centre for every other part on that board (0.4 mm for a KF301's side tab),
  so 0.5 mm is the line (op-amp `scripts/check_overlay.py`, `BODY_TOL`).
- **A PTC opens only above its trip current, and its own resistance is in the circuit.**
  Between hold and trip the data sheet promises nothing; the PID board's full-drive stall
  (0.61 A) sits between the 0.35 A part's 0.35 and 0.70 A, so "it opens a stall in seconds"
  was false (minutes, or never), and a smaller part does not cure it: the 0.30 A part's
  own 3 ohm pulls the stall current back below its 0.60 A trip.  Simulate the fault with
  the fuse's resistance range in the deck, read the typical time-current curve, and if a
  short can put a rail across the open fuse, take the higher voltage grade.
- **Split rails with series reverse-supply diodes want a clamp from each rail to ground.**
  With one rail connected and the other open, the loads drag the open rail past ground and
  reverse-bias its electrolytic; a Schottky from each rail to ground, reverse-biased in use,
  holds it within 0.4 V.  The same part as the series diodes costs no order code.
  - **Simulate the missing rail before adding them.**  The op-amp board (ceramic bypass only)
    with one rail open, a follower, IN+ over +/-12 V: the open rail floated from -1.7 to
    +8.7 V (or -12.7 to 0), each rail LED saw at most 5.2 V reversed through its 10 k, the
    other supply gave at most 14 mA.  With nothing polarised there was nothing for a clamp to
    save.  The one stress was an input driven far below a missing -15 V: 6.9 V of B-E reverse
    bias on the input pair, past the 2N3904's 6 V, which a rail clamp does not prevent (the
    input is outside the rail, not the rail outside ground).  The fix there is a line in the
    handbook: turn both rails on together.
- **A series diode's resistance at a few milliamps couples load current into anything
  referenced to that rail.**  On the PID board the motor's current through the -15 V
  diode (several ohms at 4 mA) moves the fader track's midpoint, which asks for more drive:
  with TARGET from a ground-referenced jack the loop rests at a volt of DRIVE, stuck in the
  friction.  A source referenced to the same rails (the knob) cancels it exactly.
- **Model an LM358-class output 2 V from each rail.**  TI: V+ - 2 V typical, V+ - 3 V
  guaranteed, and it sinks milliamps only about 2 V above V-; a model clamped at V+ - 1.5
  and V- + 0.1 overstated the drive by more than a volt.
- **A reviewer can misname itself.**  Kimi K3, run through the Copilot SDK, called itself
  "Claude (Fable 5)" and named its folder so (motor-pid round 1; Jason confirmed the model
  the next day).  Name review folders by what was run, not by what the report says, and
  before committing a review folder move out any datasheet text or page crops it gathered
  and shorten absolute paths in its logs.

## 7. Mechanical: connectors, cables, enclosure

- **Connectors point out.** Check the **3D render**, not the footprint's rotation (ECP5
  P2: an RJ45 faced into the board; Icepi P16: SMAs sideways).
- **Flush at the edge, or a little past it.**
  - USB-C must sit where its drawing says, so a fat moulded plug can seat.
  - For the **HRO TYPE-C-31-M-12 (C165948)** the board edge is 5.79 mm past the upper
    shell tab, with the mating face 0.99 mm past the laminate. Do not let a
    silkscreen-to-edge DRC rule move a connector; trim the silkscreen instead (Lorenz
    R10).
  - Behind an end plate, faces must stand past the board edge by the plate's thickness
    (ECP5 R9).
- **Cables.** Leave room for fat plugs beside each other: USB next to HDMI next to RJ45
  (ECP5 P14). Space SMAs for fingers and wrenches, and spread them evenly along one edge
  (ECP5 P2, GPSDO P2).
- **Holes.** M3 mounting holes in the corners, clear of headers (GPSDO P4: a hole through
  the 2x20 header). Leave a keep-out where cards and plugs slide in, checked in code
  (ECP5 P14, microSD).
- **Enclosures.**
  - Design for a real one and check it against its **drawing**. ECP5 was 8 mm short of
    its Hammond extrusion, so the SMAs would not have reached the end plate (ECP5 #2).
  - Check part heights against the floor and slot positions (ECP5 #4).
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
- **3D models.** Every part has one; missing ones were noticed every time (Lorenz P2,
  ECP5 P2, Icepi P39).
- **Gender and orientation** of anything that plugs in. Label header pins 1, 2, 39, 40
  as the mating module prints them, so a module that flips upside down goes in right
  (Icepi P30, P34, P35).

## 8. Manufacturing package (JLCPCB)

- **The order form, spelled out in the form's own order** (Jason, 2026-10-09: "To minimize
  error when I upload (over and over as we make changes)"). `FABRICATION_NOTES.txt` opens
  with JLCPCB's order form as a list, field by field in the order the web form shows them,
  each with the value to pick and, where it is not the default, why. Values that come from
  the board are computed (dimensions, layers, the smallest via's option, the sides that
  carry parts, the assembled quantity), never typed. JLCPCB's form as of 2026-10-09 (ECP5
  `mfg/make_fab.JLC_PCB_FORM`, `JLC_PCBA_FORM`):
  - **PCB:** Base Material, Layers (High Precision PCB 6, 8...), Dimensions, PCB Qty,
    Product Type (Industrial/Consumer electronics, Aerospace, Medical).
  - **PCB Specifications:** Different Design, Delivery Format, PCB Thickness, PCB Color,
    Silkscreen, Material Type (FR4 TG135 default, TG155 and others), Surface Finish (OSP
    new and default, ENIG; ENIG adds Gold Thickness 1 U" / 2 U").
  - **High-spec Options:** Outer Copper Weight, Inner Copper Weight, Specify Layer Sequence,
    Specify Stackup, Impedance Control (shown once a stack-up is chosen: No requirement /
    +-10%), Via Covering (Tented, which the form may upgrade to Via Plugged for free: say
    "Tented or Plugged" in the order notes when either is fine, as it is unless a via must
    stay open; CostasLink rev A, 2026-10-17), Min via hole size/diameter (0.3/(0.4/0.45) default down to
    0.1/(0.2/0.25)), Board Outline Tolerance, Confirm Production file, Mark on PCB (Remove
    Mark / 2D barcode), Electrical Test, Gold Fingers, Castellated Holes, Press-Fit Hole, Edge
    Plating, Blind Slots, UL Marking, Backdrill, Humidity Indicator Card.
  - **PCB Assembly:** PCBA Type (Economic / Standard), Assembly Side, PCBA Qty, Edge
    Rails/Fiducials (Added by JLCPCB: two 5 mm rails, 158 x 119 becomes 158 x 129),
    Confirm Parts Placement, Stencil Storage, Fixture Storage, Parts Selection; Advanced
    Options in rows: Bake Components, Photo Confirmation, Board Cleaning, Conformal Coating,
    Special stencil, Packaging, Depanel boards & edge rail before delivery, Solder Paste,
    Flying Probe Test, Nitrogen reflow soldering, Function test, Assembly remark. Then Stencil.
  - **Every dialog the form raises gets its own line in the table**, with the answer and why
    (Jason, 2026-10-09). JLC06161H-7628 raises a Reminder: "The actual thickness of this
    stackup is 1.5544mm (tolerance +-10%), not 1.6mm ... Do you still want to select this
    stackup?" The answer on ECP5 is Yes: no connector clamps the board edge, the
    extrusion's slots take it, and the impedances depend on the outer prepregs only. A board
    with an edge-clamp connector (an edge-launch SMA that straddles the board, a card-edge
    finger) must check that connector's thickness range before answering.
  - **Impedance Control is its own field** (2026-10-09), separate from Specify Stackup.
    +-10% binds JLCPCB to the impedance and obliges an impedance table or diagram in the zip
    (which net, layer, width, target); without the table the order waits on an engineering
    question. "No requirement" still holds width and spacing to +-20%, and a specified
    stack-up fixes the dielectric. Choose +-10% only for a line long against its edges, and
    then generate the table from the router's widths. ECP5: No requirement (SMA feeds 8 mm,
    MDI 20 mm; the 70 mm HDMI pairs are 0.1-0.127 mm, not drawn to an impedance).
  - **A 0.15 mm via hole costs about $56 on 5 boards of 158 x 119 mm** (2026-10-09): the
    0.15mm/(0.25/0.3mm) option $38.14, plus the 4-Wire Kelvin Test ($17.89) and FR4 TG155
    ($3.81) that JLCPCB then selects by itself. Use it only where the BGA's fan-out needs it.
    The rest of that PCB page: engineering $33, board $13.20, ENIG 1 U" $19.00, stack-up
    JLC06161H-7628 $33.08, confirm production file $1.05: $159.17 for 5.
  - **JLC06161H-7628 as JLCPCB's Layer Stackup dialog lists it** (2026-10-09): 1 oz outer,
    0.5 oz inner; 0.035 / 7628 0.2104 / 0.0152 / core 0.4 / 0.0152 / 7628 0.2028 / 0.0152 /
    core 0.4 / 0.0152 / 7628 0.2104 / 0.035 = 1.5544 mm. It is a "special stackup" that
    Economic PCBA does not support. The other 6-layer 1.6 mm choices: -3313, -7628D, -1080,
    -2116A, -1080A, -3313C, -1080B, -3313E, -1080C, -2116B, -2116, -7628B, -3313D, -2116C,
    -7628A, or No requirement. Copy the dialog's layers into the board's stack-up
    (ECP5 `pcb/board.py` had the middle prepreg 0.0076 mm thick until build 35).
  - **Mark every value that differs from JLCPCB's default** (Jason, 2026-10-09: "so that I
    don't accidentally pick up on the Default setting in a late-night or
    office-hours-is-about-to-start rush"). In the notes (plain text) such a line starts with
    `>>` and names the default to avoid; in any Markdown table that shows a default beside
    the value to set, the value to set is **bold** and the default plain. Keep the value
    exactly as the form spells it.
  - The defaults are not the board's: OSP finish and a 0.3 mm minimum via on ECP5, whose
    vias are 0.3 mm across with 0.15 mm drills, would both have been wrong. The form changes;
    when Jason sends a screenshot, update the lists and the date.
- **Surface finish: ENIG, 1 U" gold**, for any board with a BGA or fine-pitch parts, parts on
  both sides or through-hole parts: OSP is flat too, but each reflow and the wave or hand
  soldering consume it, it keeps months rather than years, and test pads under it do not
  probe well. 2 U" gold is for gold fingers and other wearing contacts.
- **Upload files:** gerbers zip, BOM (one line per LCSC code), CPL (KiCad native), CPL
  JLC-corrected, assembly notes to paste, and a cost estimate. Write `release/` so that
  Jason uploads exactly that folder.
  - **CPL file names** (Jason, 2026-10-08): `<board>_cpl_jlcpcb_upload.csv` is the one he
    uploads, with JLCPCB's rotations and positions; `<board>_cpl_kicad_native.csv` is
    KiCad's own numbers, for reference. The names say which file goes to JLCPCB, which
    `_cpl.csv` beside `_cpl_jlc_corrected.csv` (GPSDO, Icepi) or `_cpl_native.csv` (ECP5)
    did not. Every board in OpticsPCBs was renamed to it; a plugin's `CPL-<board>.csv`
    (SyzygyRadioDrivers) is renamed after each run.
- **Nothing hand-soldered, except a host socket that costs more than a few dollars to
  have fitted.** Every part is assembled by JLCPCB, through-hole included (SMAs, RJ45, DIP
  switch, 2.54 mm headers at their own lengths, Pmod sockets) (ECP5 P26: "I don't want to
  hand solder anything"). The exception (GPSDO rev B's J4001; CostasLink Prompt 15, Jason:
  "if it costs more than a few dollars to have JLCPCB solder the raspberry pi connectors,
  I'll do that myself. I'd like them to do SMAs and small-pin headers"): a 2x20 socket on
  the BACK, alone there, makes the order two-sided (a second setup, a second stencil, its
  feeder: about $38 before duty, $51 with it), so it goes in `hand_solder_bom.csv` with its
  LCSC code to order loose, and the order is one-sided. Price it every time; when nothing
  else is on the back and the saving is more than a few dollars, Jason solders it. The
  same list carries what ships loose (jumper shunts, with each jumper's position).
- **DRC.**
  - At least as strict as JLCPCB's rules for the chosen stackup, at every severity, 0
    errors, with schematic parity.
  - Fill the zones and save them first.
  - Count unconnected items yourself: GPSDO printed a false "UNROUTED" caption while
    DRC said 0.
- **CPL rotations.** KiCad's zero and JLCPCB's zero differ by a property of **their**
  drawing of each LCSC part. Apply two things, in this order:
  1. **Bottom-side mirror:** `rot -> 180 - rot` (fixed points 90 and 270; confirmed on 10
     placements, Icepi jlcbuild).
  2. **Per-footprint correction**, taken only from a real "Confirm parts placement"
     preview. Absent from the table means nobody has looked; zero means somebody looked.
     A prediction from the drawings is a placeholder, not a reading: CostasLink's SMAs
     were predicted +90 from a wrong reading of the footprint's barrel direction and every
     one needed turning in the preview.  When a part is predicted, read the footprint's
     own body outline (F.Fab) for its direction at 0, not a description of it.  The
     predictions by pin number (`footprint_check.py`'s fit of JLCPCB's drawing on ours)
     were right 32 for 32 on CostasLink rev A; the one from a description was the wrong one.
     Known so far:

| footprint / part | correction | evidence |
|---|---|---|
| `SOT-23-5` | +180 | GPSDO, 59 placements |
| `VSSOP-8_2.3x2mm_P0.5mm` | +180 | Icepi jlcbuild |
| `Texas_DRT-3` | +270 | Icepi jlcbuild (top side) |
| `TSOP-II-54_22.2x10.16mm_P0.8mm` | +270 | Icepi jlcbuild |
| `SOIC-8_5.3x5.3mm_P1.27mm` | +270 | Icepi jlcbuild, read twice |
| `QFN-20-1EP_4x4mm_P0.5mm` | +270 | Icepi jlcbuild, read twice |
| `Oscillator_SMD_SiT_PQFN-4Pin_2.5x2.0mm` | 0 | Icepi jlcbuild, read twice |
| `D_SOD-523` | 0 | Icepi jlcbuild |
| LF412 SOIC-8 (C15322), MPY634 SOIC-16W (C1523457) | +270 | Lorenz P8 |
| 6-way DIP switch C54952 | +270 | Lorenz P8 |
| 78L12 / 79L12 SOT-89 (C8615, C8626) | +180 | Lorenz P8 |
| BNC C41416668 | +90 | Lorenz P8 |
| Edge SMA BWSMA-KWE-Z001 C496551 | **0** | READ in JLCPCB's viewer (CostasLink rev A, 2026-10-17): at +90 all nine SMAs needed a quarter turn clockwise.  The footprint says the same: its body runs along +x at 0, as JLCPCB's drawing does.  The +90 had been predicted from a misreading of the footprint (barrel along -y), and the ECP5 build 33 note that '+0 lay along the edge' is contradicted by this reading: ECP5 re-reads its SMAs in its own preview before ordering |
| 2.54 mm headers PZ254V-11-02P C492401, -03P C2937625, -06P C492405, PZ254V-12-18P C492426 | +270 | JLCPCB draws them lying along x, KiCad standing along y (ECP5 build 34; the 1x3, 1x6 and 2x9 by pin number, the 1x2 from the drawing). READ for the 1x2 and 1x3, with their 1.27 / 2.54 mm datum moves, in CostasLink rev A's preview (2026-10-17) |
| 2835 red LED XL-2835SURC-05 C2843878 | +180, and the CPL point 2 x 0.30 mm along its axis | READ in JLCPCB's viewer (ECP5 build 34, 2026-10-08): our footprint is JLCPCB's own drawing, yet +0 showed the cathode on the anode's side |
| 2x6 right-angle Pmod socket C22373932 | +270 | ECP5 build 33 preview showed +0 wrong (a quarter turn round); +270 from the drawings' body directions. Confirm in the next preview |
| USB-C HRO TYPE-C-31-M-12 C165948 | 0 | Lorenz (built), GPiBridge preview. Its *position* needs moving 1.572 mm: see "Part positions" below |
| GPiBridge's eleven: RP2354A 0, SN75160B +270, SN75161B 0, AO3401A, 2N7002, XC6206 +180, BM03B +180, AOTA inductor +180, KT-0805Y/G and NCD0805R1 LEDs 0 | as predicted | GPiBridge rev A preview, 2026-10-06: "all of the rotations were correct" |
| CostasLink rev A's 32, on KiCad's own footprints: QFN-24-1EP (ADL5380, ADL5375, PE43711), VQFN-16 (THS4541), MSOP-8/-10 (HMC536, AD8310, MCP4728), VSSOP-8 (OPA2187), TSSOP-10/-16 (ADS1115, AD5696R) all +270; SC-70-5/-6 (74LVC1G04/1G17/2G34/1G3157, TLV3601/3603) +180 and the TS5A3159's SC-70-6 +270, by pin number; SOT-89 ADL5611 C208262 +180 with a 0.7 mm datum move; U.FL C88374 on `U.FL_Hirose_U.FL-R-SMT-1_Vertical` +270 with a 0.763 mm datum move; MMCX BWMMCX-KE C5137198 0; QFN-32 MAX2871, QFN-6 SKY65404, the 3225 TCXO/VCXO, the HHM1907B1 balun, the SMAJ5.0A, the 1N4148W, the 0603 LEDs and the 5x5.9 polymer 0 | as predicted | CostasLink rev A preview, 2026-10-17: "Everything look correct except the SMAs" (the SMAs' row above); each by LCSC code in CostasLink's `mfg/jlc_rotation.py` |
| AMOD-and-RFMOD's SOT-23 family on KiCad's `SOT-23` / `SOT-23-5` / `SOT-23-6` where JLCPCB's package name ends "-BR" (pin 1 bottom-right): AO3401A C15127 (every powered tile's switch FET), 2N7002 C20917, MMBT3904 C20526, TMP235 C2868809, LM2664 C108573, TLV3501 C193413, TPS22917 C2681320, TPS7A2033 C2862740, SN74LVC1G17 C7836, LMH6629 C2059678, SMS7630 C6489012 | **+180** | Fit by pin number (AMOD-and-RFMOD `scripts/check_rotations.py`, 2026-10-28), agreeing with the GPSDO's SOT-23-5 and GPiBridge's AO3401A / 2N7002 readings above.  Rev A's table had them all at 0 as "the standard drawing", a prediction from a description: every powered tile's P-FET would have gone on backwards.  Not yet read on these boards; **read** for MMBT3904 C20526 and MMBT3906 C53444 on the op-amp's rev A preview (2026-10-29) |
| SOT-23-6 drawn in rows, "-BL" (pin 1 bottom-left): OPA847 C160422, LT6230 C580235, MT3608 C84817 | +270 | the same fit |
| SOT-23-5 drawn "-TL" (KiCad's own): OPA810 C2833513 | 0 | the same fit: the suffix, not the package, decides |
| `SOIC-8_3.9x4.9mm` PAM8302A C113367, `SOIC-14_3.9x8.7mm` MC1496 C7295, `TSSOP-16_4.4x5mm` 74HC4046 C546981 | +270 | the same fit, as the SOIC and TSSOP readings above |
| 1x3 header C2937625, 1x5 / 1x2 sockets C2894928 / C2894925 | +270, the datum at the middle pin (2.54 / 5.08 / 1.27 mm) | the same fit, as the header rows above |
| `Crystal_SMD_3225-4Pin` (TC32H4 TCXO C5119013, TXC 7U crystal C2889142) | 0 | the same fit, and CostasLink's 3225 reading; AMOD-and-RFMOD's table had said +180 from reading JLCPCB's drawing with y upward (easyeda's SVG y runs down) |
| GALI-84+ C3193261 on KiCad's `SOT-89-3` | +180, datum 0.593 mm | the same fit, on pins 1 and 3 only (pad 2 is the tab in their drawing, the lead in KiCad's) |
| MSK12C02 slide switch C431540 | 0, datum 0.251 mm | the same fit |
| The op-amp's rev A preview (2026-10-29), all **read**: DSIC02LSGET C54949 on its own 2-way footprint; KF301-5.0-2P / 3P C474881 / C474882 with the wire openings to the edge; B5819W C8598 and 1N4148W C81598 on KiCad's `D_SOD-123`; RH-5019 loop C5199800; R2512 C2934068 | +270; +180; 0; 0; 0 | Jason: "Everything else looked fine" |
| Bourns 3362P C52754333 on a footprint with pins 1/3 at y +1.27 and 2 at -1.27 | 0, read, **but its body is not centred on its pins** | pads fit within 0.04 mm, yet the preview showed JLCPCB's body 1.3 mm off the op-amp's printed box and Jason nudged it: see "A pad fit cannot see the body", below |

  Third-party rotation tables disagree with each other: GPSDO took one and got two wrong,
  one of them on 59 placements. List every unverified footprint in a
  `PLACEMENT_CHECKS.txt` for the day of ordering.
- **Predict the corrections from JLCPCB's own drawings** (GPiBridge, 2026-10-06).
  - **A part that numbers its pins unlike KiCad gets no prediction, and it must not ship at
    KiCad's angle** (ECP5 build 33's preview: every edge SMA lay along the board edge and
    both Pmod sockets stood a quarter turn round). Pads that fit by position only -- a
    square of five SMA holes, a 2x6 grid -- say nothing about which way the body faces.
    Read the body's direction off JLCPCB's land drawing (the EasyEDA record's `png`: the
    silkscreen outline shows where the barrel or the socket goes) against KiCad's
    courtyard, put the correction in the per-part table, and make the release fail on any
    part of three or more pads that has neither a prediction nor a table entry (ECP5
    `mfg/make_fab.py` does since build 34).
  - **Every correction lives in the file, made by the script, from a source of truth** (Jason,
    2026-10-08): never nudge or turn a part in JLCPCB's viewer. "I don't want to do that every
    time I upload the BOM and CPL", and every hand fix is lost on the next upload. A preview
    reading goes into the rotation or position table, with the screenshot's evidence, and the
    release recomputes the CPL from it.
  - **Their viewer can turn a part about its body, not its origin** (ECP5 D201, the 2835 LED):
    +180 put the cathode right, and the part then sat 0.56 mm short -- twice the 0.30 mm
    from the drawing's origin (the pads' midpoint) to the body outline's centre. Move the CPL
    point by twice that, turned with the part (`jlc_rotation.VIEWER_HALF_TURN`,
    `footprint_check.body_centre`), and draw it the same way in the computed preview.
  - **Reading the viewer:** the purple dot is JLCPCB's pin 1 of each part, and a neighbour's
    dot can sit beside a small part (U502's beside Y501). A four-pad crystal is right when the
    dot is on a pad wired to the oscillator, pin 1 or 3 of the diagonal pair; an oscillator or
    any other part, when it is on pin 1. Compute it: their pad 1 at the CPL's position and angle
    must land on our pad 1 (ECP5 `preview_check.py`, 42 parts).
  - **A footprint copied from JLCPCB's drawing is not a reading of their viewer.** ECP5's 2835
    LED used JLCPCB's own land pattern, so +0 was taken as "derived" and right; their viewer
    drew the part a half turn from that drawing and showed the cathode where our anode is
    (Jason's screenshot, 2026-10-08). Only a preview reading settles a polarized part; until
    then list it, however its footprint was made.
  - **Polarity from JLCPCB's own pin names.** Their symbol for each diode or LED names its
    pins (K, A, COM+), and their land pattern numbers its pads to match; put their
    cathode pad where the CPL puts the part, and it must land on our cathode. A pad number
    proves nothing: their 0603 LEDs call the cathode 2 (ECP5 `mfg/preview_check.py`, which
    found a 180-turned copy of D501, D309 and D602 REVERSED and the real CPL right).
  - **Jason: check the BACK in JLCPCB's preview too** (2026-10-08: "I almost forgot to check
    the back parts"). The preview opens on the top side, and the back is easy to skip. The
    back is also where the rotation rules are least proven (the bottom mirror, a board that
    stores its back pads the other way round), and the computed preview below covers only
    the top. Every `PLACEMENT_CHECKS.txt` and every response that hands Jason an upload ends
    by naming the back-side parts to look at.
  - **Compute the preview before Jason sees it** (ECP5 `mfg/preview_check.py`, build 34): put
    JLCPCB's own land drawing of every part where the upload CPL says, turned as it says,
    and compare it with the board -- each of their pads must land on one of ours, and their
    silkscreen outline (the body) must lie on the same side of the part as our courtyard.
    Pad fits alone cannot see a half turn of a symmetric pattern; the outline can. Run it
    on a release known to be wrong first, to see it fail (build 33's CPL: it flags the six
    SMAs and both Pmod sockets the preview showed). Make the build stop on it. Footprint
    checks compare footprints; only this compares placements.
  - The EasyEDA land pattern of each LCSC part (`footprint_check.py` fetches it), turned
    until its pads lie on ours *by pin number*, predicts the correction: minus that
    turn. It reproduces every top-side correction in the table above (7 footprints),
    for all 14 part numbers that use them on the Icepi, GPSDO and ECP5 boards.
  - It must be **per part, not per footprint**: JLCPCB draws the SN75160B lying down and
    the SN75161B upright, on the same SOIC-20W.
  - For two-pad polarized parts, use the **polarity mark** in their drawing, not the pad
    numbers. JLCPCB's KT-0805 LEDs call the cathode pad 2, and their AOTA inductor has
    its dot at pad 2 where Raspberry Pi's has it at pad 1.
  - On the bottom side it was untested until ECP5 build 34 (below). ECP5-2ADC-2DAC stores
    its bottom SOT-23-5s mirrored left-right, while the Icepi parts behind `BOTTOM_FLIP`
    are mirrored top-bottom. Look hardest at those in the preview.
  - **A generated board may store its bottom side the other way round** (ECP5,
    2026-10-06). KiCad's own flip mirrors a footprint's pads top-to-bottom; ECP5's writer
    mirrors them left-to-right, which is a top-bottom mirror turned half way round, so the
    same physical placement carries a stored angle 180 from KiCad's, and `BOTTOM_FLIP` must
    see angle + 180 first (`jlc_rotation.BOTTOM_STORED_X_MIRRORED`, with
    `verify_bottom_convention` reading the file so the flag cannot go stale). Every bottom
    rotation in ECP5's earlier CPLs was 180 out. Two checks agree with the fix: a part placed
    on both sides (the BAV99) predicts the same correction from its bottom-side fit (turn +
    180) as from its top-side fit, and EasyEDA-sourced footprints on the bottom (the magnetics,
    the microSD) predict 0, as they must. **Confirmed in a preview:** Jason checked the back
    of ECP5 build 34 in JLCPCB's viewer on 2026-10-08 and every part was right (the three
    SOT-23-5 regulators, the two BAV99s, the magnetics, the microSD and the 0402/0603
    passives under the BGA).
  - ECP5's `make_fab.py` does the prediction in the build: `FOOTPRINT_CHECK.txt`'s fit becomes
    the CPL's rotation where nobody has read the part, `PLACEMENT_CHECKS.txt` lists every
    predicted part, and a cross-check prints the prediction beside each correction somebody has
    read (7 of 7 agree on ECP5: SOT-23-5, TSOP-II-54, SOIC-8 5.3 mm, VSSOP-8).
  - **Polarity marks without rasterising:** the EasyEDA API's footprint record carries a `png`
    URL (`image.easyeda.com/component_pngs/...`, protocol-relative) of the drawing with its
    +/− marks; fetch it and look. ECP5's five KiCad-library LED and SOD-123 codes all draw
    the cathode on the left at 0, where KiCad's pad 1 is: correction 0 by mark, listed as
    predicted.
  - Put predictions in the CPL, marked "predicted", and still list them in
    `PLACEMENT_CHECKS.txt`.
  - **Confirmed:** all eleven of GPiBridge's predictions (12 placements, including the
    SN75160B's 270 beside the SN75161B's 0 on one footprint, and the LEDs and inductor
    read by polarity mark) were right in its preview (2026-10-06).
- **Order number.** (Superseded: since May 2026 JLCPCB prints none by default and asks
  for no `JLCJLCJLCJLC`; choose "Remove Mark", see the JLCPCB rules below.) Before then,
  JLCPCB printed its order number on the silkscreen wherever it liked
  unless the board carried the text `JLCJLCJLCJLC` and the order form said "Remove order
  number: Specify a location"; then it landed there. Put the marker on the back, in a
  band the enclosure hides (ECP5 build 31: the top slot band on B.SilkS). Say so in the
  fabrication notes Jason pastes.
- **Preview checkerboards.** JLCPCB's preview shows an "unknown part" checkerboard where
  their library has no drawing, so those rotations cannot be read there. The Lorenz RGB
  LED went in right from the plain CPL; say so in the notes (Lorenz P8, P9, MANUFACTURING).
- **Part positions: JLCPCB places THEIR origin.** The CPL's Mid X/Y is where JLCPCB
  puts the origin of *their* library drawing of the part. Where that is not KiCad's
  origin, the part lands off its pads by the difference, whatever the rotation.
  - Every USB-C so far has done it. JLCPCB's drawing of the HRO TYPE-C-31-M-12
    (C165948) has its origin 1.572 mm from KiCad's, towards the pad row. So the preview
    showed it hanging off the board edge with its pads beside ours, and Jason moved it
    by hand on every board (Lorenz P9-P10; GPiBridge, 2026-10-06).
  - The Lorenz board's answer, that nothing in a CPL can address their model's origin,
    was wrong. The JLCPCB CPL is read by JLCPCB alone (the native CPL stays as KiCad
    wrote it), so put each part where their origin goes.
  - `footprint_check.py` fits their land pattern onto ours and reports where their
    origin sits in our footprint (its "datum"); GPiBridge's `make_release.py` adds it,
    turned with the part, to the JLCPCB CPL, and `PLACEMENT_CHECKS.txt` lists what
    moved. Check in the preview that each moved part sits on its pads.
  - AMOD-and-RFMOD's `scripts/check_rotations.py` (2026-10-28) does the same fit over every
    code on every board, turn and datum together, against `parts.JLC_ROTATION` and
    `parts.JLC_DATUM`; `gen_outputs.py` applies both and `check_outputs.py` accepts exactly
    those moves.  Run it whenever a part is added: it found the SOT-23 family above wrong
    on all five boards of a design that had passed every other check.
  - Through-hole parts with keyed hole patterns go in one way only; note them (Lorenz
    MANUFACTURING).
- **Through-hole parts: have JLCPCB fit them** (Jason, 2026-10-06, ECP5: "even if it costs
  extra"). JLCPCB's THT labour is a per-order fee (about $3.58, Icepi jlcbuild J1) plus a
  per-joint rate, and every USB-C's soldered shell legs already put the per-order fee on the
  order, so after that each through-hole part costs only its joints and its code. The SMAs, the
  RJ45, the DIP switch, the 2.54 mm headers and the Pmod sockets go in the BOM and CPL like
  everything else, and the cost estimate counts their joints (ECP5 `mfg/make_fab.py`).
  - **Order each header at its own length, not as a strip to snap** (Jason, 2026-10-08, ECP5
    build 33's preview). A 1x40 / 2x40 strip (C2337, C29952) is what JLCPCB stocks and draws,
    so the preview showed every jumper as a 100 mm bar centred on its pin 1, running across
    the board and off its edges, and nobody can check a placement in that. GPSDO was built
    from strips, but the exact parts are stocked, cheaper per header (about $0.02 against
    $0.13), and fit the footprint by pin number like any other part: XFCN PZ254V-11-02P
    C492401, -03P C2937625, -04P C2691448, -06P C492405 (one row), PZ254V-12-16P C492425,
    -18P C492426 (two rows). Their drawings' origin is the middle of the pins, so the
    release's datum shift moves the CPL point there from KiCad's pin 1.
  - A header's "value" is the jumper's name (TERM, RAILS): check its code for the pitch, not
    the name.
  - Say which through-hole parts are keyed (SMA, RJ45, DIP) and which the preview must show
    pointing the right way (SMA barrels off the edge, Pmod openings off the edge).
- **JLCPCB options that constrain a design** (read on their capability and help pages,
  2026-10-07, for the Halloween board; re-check, they change):
  - **Colour decides the assembly service.** Economic PCBA does 4-layer boards in green
    only; purple, black or any other colour on 4 layers means Standard PCBA, whose
    smallest single board is 70 × 70 mm. Smaller boards go on a panel, or ride as
    break-away tabs on a bigger one.
  - **An assembled panel stays inside 250 × 250 mm.** JLCPCB accepts bigger "at the
    customer's risk": it warps through two reflows, and an engineering question follows.
    Plan a multi-design panel inside it from the start; turn a tall board 90° if that
    is what fits (OWLternating Current: 323.6 × 154.2 mm became 245.2 × 223.2 mm).
  - **Standard PCBA loads a feeder for every distinct part** ($1.53, Basic or Extended
    alike; the Extended-only fee is Economic PCBA's). Every BOM line merged saves it.
  - **No order number.** Since May 2026 JLCPCB adds none by default and asks that
    "JLCJLCJLCJLC" not be put on the silkscreen: choose "Remove Mark".
  - **Locating posts.** JLCPCB's own drawing of a part can put its posts somewhere other
    than the maker's land pattern does (the MSK12C02 slide switch: 0.30 mm further from
    the pins). Make each hole take both, and check every NPTH post against their drawing.
  - **2 oz outer copper** on multilayer boards: the solder-mask dam needs 0.20 mm
    between pads (0.10 mm at 1 oz), and the minimum track and gap is 0.15-0.16 mm (design
    to 0.2 mm). Inner copper is 0.5 oz unless ordered; 2 oz inner has been tied to the
    JLC3313 stack-up, which changes every impedance.
  - **Lead time:** a 4-layer board takes 2-5 days, Standard PCBA at least 4 more, and
    parts not in stock 9-15 days of global sourcing. To the US, DHL and FedEx Express
    are for corporate accounts; individuals get UPS Express Saver (DDP, 4-5 business
    days). Plan on about two weeks from order to door.
  - **Duty:** DDP pre-collects a flat 35 % on PCBs and assembly, 40 % on 3D prints.
    JLCPCB's own table (news page, March 2026; tariff FAQ updated September 2026): PCB 35 %,
    SMT 35 %, a stencil ordered on its own 90 %, CNC and sheet metal 40-90 % by material.
    They set the rate "based on the product type and material", not on the usage Jason
    picks at checkout, and "reserve the right to replace the HS code to match the actual
    product". The field is the form's **Product Type**: Industrial/Consumer electronics,
    Aerospace or Medical; every board of Jason's so far is Industrial/Consumer electronics.
    So the usage choice is a truthful description for the declaration, and
    no truthful choice is cheaper than another: pick the board's real primary use (Jason's
    boards are all research, teaching or hobby; the Halloween board is a child's
    decoration), never a category picked for an exemption (ECP5 P38, 2026-10-08).
  - **JLC3DP** prints SLA, MJF, SLS and FDM (8001 resin is clear or translucent) but
    nothing glow-in-the-dark; JLCCNC mills acrylic (polished edges on request) but
    nobody in the group laser-cuts it.
- **Fab review.** JLCPCB may return a "gerbers_Y11" set to confirm. Compare it with what
  was sent: hole counts, NPTH, outline (Lorenz P11).
- **Cost estimate:** board, parts, setup, stencil, Extended fees, SMT and THT joints,
  shipping and duty, for 1, 2, 5 and 20 boards. Note the quantity break where
  panelising pays (Icepi P31).
  - **Itemise it as JLCPCB's cart does, and calibrate every line on a real order** (ECP5,
    2026-10-08: 5 PCBs, 2 assembled, $616.06 in the cart; 2026-10-09 with every option set:
    $727.90, PCB $159.17, PCBA $566.41, depanel $2.32; the model gives $615.97 and $727.89).
    JLCPCB's components line runs 0.66 % above the API's price breaks for the same
    quantities, on both carts; no per-line rule explains it (attrition stacked on the
    feeder minimum overshoots, rounding each line to the cent recovers a fifth), so it is a
    calibrated markup (`PARTS_MARKUP`) until JLCPCB's per-line BOM page shows the cause. Fixed per
    order: 6-layer engineering $33, confirm production file $1.05, Standard PCBA setup $51.50
    and stencil $16.54 (both sides), hand-soldering labour $3.61, PCB assembly fixture
    $16.54, packaging $0.51, special components $0.12, depanel $2.32. Scaled: the 158 x 119
    6-layer ENIG board $2.64 a PCB; feeder loading $2.70 per Extended code (49: $132.33);
    SMT $0.0017 per pad plus $1.50 a board; through-hole $0.0157 per joint; X-ray $1.65 a
    board. Components: JLCPCB buys the parts needed plus each line's attrition (the API's
    `lossNumber`, 10 extra 0402s) and at least a feeder's minimum (`leastPatchNumber`), at
    that quantity's price break. Ask Jason how many will be assembled: he orders 5 PCBs and
    assembles 2.
  - Calibrate against JLCPCB's cart. GPiBridge (5 boards, 2 assembled, 4 layers, ENIG,
    60 x 25.5 mm): $24.80 PCBs + $60.56 assembly; GPiBridge Lite $25.85 + $40.18
    (2026-10-06). The estimate was about $5 low on each: it left out the through-hole
    labour that the USB-C's soldered shell legs bring. ENIG is most of the PCB price at
    this size.
  - **Three buckets, from the generator** (CostasLink, 2026-10-09, `mfg/cost_estimate.py`): JLCPCB (the
    boards, the assembly fees as the ECP5 cart calibrated them, their parts with attrition, 35 % duty,
    shipping), Digi-Key (the consigned lines plus tax, shipping and the shipment on to Shenzhen) and
    "other" (the bench and the field: attenuators, pigtails, antennas, power banks).  Say which lines
    are the cart's, which the API's and which a model with a range, and where the money could move
    (an Extended code merged, a consignment avoided) before Jason asks.

- **Reading JLCPCB's "Confirm Production file" zip** (CostasLink, 2026-10-17, the full
  worked case in `CostasLink-PYNQ-Z2/mfg/PRODUCTION_FILE_CHECK.md`).  The zip
  (`<name>_Y21.zip`, about 17 MB) holds `ok/`: their CAM layers named `tl bl l2 l3`
  (copper), `ts bs` (mask), `to bo` (silk), `drl`, `ko` (outline with rails), `vcut`, `sk`
  (the tented vias), `qrt qrb` (QR places), all RS-274X in inches 2.6; `YG/`: the upload
  echoed back (check it is byte-identical to the release zip); and `YG/4te.json`, the order
  record in GBK (`iconv -f GBK`: layers, thickness, copper, finish 沉金 = ENIG, 过孔塞油 =
  tented vias, 不加客编 = no order number, the rails remark).  Check it by rendering, not by
  reading: `pip install --target <scratch> gerbonara`, `GerberFile.open(...).to_svg(force_bounds=
  panel frame)` for theirs and ours (ours offset so the outline sits at the panel's board
  position), inkscape to PNG at 20 px/mm, threshold, numpy diff, erode 2 px to drop the
  polygon-conversion slivers, label what survives and match it to pads with pcbnew.  Expect
  exactly: non-functional pad removal on the inner layers (through-hole pins with no
  connection on that layer lose the annulus; connected ones keep it), the rails with their
  V-cuts, tooling holes, fiducials and QR places outside the outline, plated drills 0.13-0.15
  mm over finished size, vias unchanged.  Anything else on the board itself is a question for
  them before confirming.  The record carries no stack-up field; that is read off the order
  page.  Do not commit the zip (`*_gerbers_Y*.zip` is ignored); commit the check.

## 9. Bring-up and debuggability

- **Remote first: anything a jumper, a DNP option or a re-cabling would set, set it from software instead** (Jason,
  2026-10-29: "I spend more time away from the bench than at it, and having remote control of these things is generally
  better than requiring me to come in").  CostasLink rev A's loop sign needed two jumpers moved by hand, and every test of
  its night needed a cable moved (its REVB "Quality of life" rows are the worked list).
  - **Pins are not the obstacle.** Static settings go on an I2C GPIO expander (8 outputs for under $1, no host pins) on a
    bus the board already has. Fast signals stay on the host's pins.
  - **Defaults:** an expander's outputs come up as inputs, so pull resistors give the safe or usual setting at power-up.
    The board then works with no firmware, as with a jumper.
  - **Read it back:** read the state back (the expander's input register) and log it with every measurement.
  - **Use the right switch for each kind of signal:**
    - a logic choice (a sign, a source select): a logic gate (XOR, 2:1 mux), with no resistance question at all;
    - DC and up to some 100 MHz (terminations, gain and bias resistors, a reference clock): an analog switch (1-5 ohm,
      a few pF);
    - RF (loopbacks, terminations, monitor routing): an RF switch, at 0.5-1 dB and 30-50 dB of isolation.
  - **Where a switch is a bad idea:** a jumper stays where a switch would cost what matters. For example: ahead of an LNA,
    where its loss is noise figure; in a precision reference; in a power path or a safety choice. Write the reason beside
    it.
  - **DC levels too: a monitor mux to a DVM jack** (Jason, 2026-10-29: "if it's a few dollars to analog MUX every interesting
    signal down to a few connectors for DVMs, if we don't need to monitor things simultaneously, that would have made finding
    the high resistance path into the USB plug much faster").  CostasLink rev A's 5 V input path lost 192 mohm from VBUS to
    +5V_RF (its REVB row 2), and finding which part took it meant probing by hand.
    - **What to route:** every interesting DC node.
      - each rail at its source and at its far load;
      - both sides of each part in a high-current path (fuse, FET, ferrite, connector), as Kelvin taps;
      - each bias and reference (V_MID, the DACs' outputs, the FDAs' Vocm, the comparators' thresholds);
      - each regulator's input and output.
    - **The mux:** a dual 16:1 analog mux, ideally one on I2C. For example the MAX14661 takes +-5.5 V signals on a single
      supply; check its stock at design time. A dual mux puts any two of the 16 nodes across the meter, so a drop is read
      differentially, with no ground error.
    - **Where it goes:** to a two-terminal DVM jack (banana or a 2-pin header), and to a spare channel of the board's own ADC
      for unattended logging.
    - **Why the mux's resistance doesn't matter:** a 10 Mohm meter makes its 10-100 ohm irrelevant. Its nA of leakage is also
      nothing on a low-impedance node.
    - **Nodes over the mux's range:** a precision divider ahead.
    - **Never mux a node whose leakage or capacitance matters:** a high-impedance node, a loop filter, a fast or RF node.
      Buffer it first, or leave it out.
  - **Currents too:** a current monitor on each rail that feeds a separate section, on I2C (INA226 class, a few mohm shunt). The
    bench supply's one number cannot say which section draws what, or which part is hot.
  - **For RF boards, give the board ways to test itself without hands:**
    - an internal loopback through a fixed pad, with a 50 ohm load on each port, so calibration and leak tests run any
      time;
    - each amplifier's enable on a control line;
    - a selector that routes the monitor taps to one analyzer jack and one or two scope jacks.

- **Before calling a dip the chain's response, check that it follows a knob in the path** (CostasLink rev A, 2026-10-29).
  - **What happened:** a 10 MHz-step map showed a "notch" at 5.89 GHz with a "recovery" above it. It was the chain cancelling against a transmitter leak that bypassed the step attenuator. Above 5.86 GHz, RX MON and the demodulator's I/Q did not move between 0 and 31.75 dB of attenuation, and the null moved with the setting.
  - **The rule:** sweep every frequency at several settings of an attenuator, a switch or an enable that sits in the path. Believe only the part that follows it.
  - **Measure the leak floor first:** transmitter on, the receiver's input terminated, no cable between them.
  - **Then trace the rest:** model the input network as laid out (§14) before suspecting the chips.
- **Plug in; don't solder or hold.** Jason does not want to solder wires or hold probes
  to debug. Provide labelled test points with ground clips nearby, U.FL monitor taps for
  signals worth scoping, and headers that take standard probes (ECP5 R17, GPSDO P2).
  He has many USB scopes, and wants to plug one in and walk away. So: **lots** of taps,
  on every analog node worth a look (GPSDO r45, REVB #19). And since 2026-11-07, every
  test point is a jack (next bullet but one).
- **A monitor tap's series resistor is its divider and its load** (GPSDO r45).
  - 450 Ω is a 10× probe into a 50 Ω scope, and loads the node with 500 Ω.
  - 1 kΩ is ÷21, and loads it with 1 kΩ.
  - A series capacitor keeps a biased node's DC (and keeps a 50 Ω scope from
    pulling current out of a rail).
  - **Never tap a node whose amplitude sets a timing**, such as a comparator's or
    squarer's input behind a series resistor. Plugging the scope in would move the
    thing measured. Tap the low-impedance side.
  - **Follow a tap's DC path into the scope.** A 50 Ω input, and the ADALM2000's 1 MΩ,
    are DC-coupled. GPSDO rev B first tapped each channel on the GATE side of its 10 nF
    coupling cap, where the only DC is a 1 MΩ replica bias: plugged in, the scope pulled
    the gate's bias from 1.5 V to 2 mV (50 Ω) or 0.75 V (1 MΩ) and the channel stopped
    squaring. Found while writing the bring-up on order day; moved to the SOURCE side of
    the cap, where at 10 MHz the waveform is the same and the DC lands on the 51 Ω and
    2.2 kΩ. A tap on any node whose DC is set through a high resistance needs the
    coupling cap between it and the node, or a series cap of its own.
  - U.FL is rated for 30 matings, MMCX for about 500.
- **A picture beside every place a bring-up step names** (Jason, 2026-10-10: "include a
  thumbnail around the 3D render so that I can easily find the reference on a crowded
  board, which sits on a crowded desk. Double check that the reference is actually next
  to the component or probe point you want me to probe.") Cut each from the board's own
  3D render (`kicad-cli pcb render --side top --quality high`; the opaque area, alpha
  over 128, is exactly the board, so board mm map straight to pixels): a small whole
  board with a red box, the zoom beside it, the part or pin circled and the words the
  board prints for it boxed, drawn the way the board sits on the bench. Generate them in
  the build from a list of (designator, pad, printed words), and fail the build unless
  each spot's words are beside it AND nearer it, from the words' centre, than any other
  part of its kind (another test point, U.FL, jack, pin of the same header). GPSDO's
  `gen/handbook_figs.py`: the first run found a test point whose letter had silently
  stopped printing when its net was renamed.
- **Every test point is an MMCX jack; U.FL only where there really is no room for
  MMCX** (Jason, 2026-11-07, after the OWLternating Current rev A bench: "I hate
  soldering little wires and clipping a ground clip to one little wire and a probe clip
  to the other little wires. This is annoying, time consuming, and they keep falling
  off when unattended."). Rev A had six rail test points as pads; one had a wire soldered
  on, the hooks slid off twice, one landed on the wrong pad, and two ramps aborted on
  readings that were the hook, not the rail (`bringup/REVB.md` 1.1 there). A jack carries
  its own ground, so a probe adapter or a coax to the scope plugs in and stays. Label
  each with the net name in silk. **In the production run leave the jacks unpopulated**;
  the bare footprint is then an ordinary test pad. This supersedes the 2026-10-10 rule
  ("If they are there for brief, one off probing, they can stay as pads. If I would have
  to hold something for more than a few seconds, make them U.FL."): the hold-time test
  now only decides MMCX against U.FL where space is tight, never jack against pad.
  - And anything a computer-controlled instrument will log is a jack even when a meter
    would do (CostasLink Prompt 35: the lock detects, the switch control, the log amp and
    the seven rails went from pads to U.FL / MMCX, the rails' pads kept "at least in
    addition").  A jack drawn late on its sheet gets explicit references, so no hand
    anchor moves.
- **Tap the node nothing else reaches.** GPSDO rev B's first tap per channel was on the
  input, which a tee at the channel's own SMA already shows for as long as you like. The
  edge the sampler actually takes, the squarer's output, had no access at all; the
  handbook said "The squared signal has no test point". Rev B taps it: 1 kΩ with its pad
  on the track, the U.FL 2.5 mm from the helper clock and 6 mm from the squarer's input.

- **Read the DNP flag before saying what is fitted.**
  - A part drawn on the schematic is not a part on the board.
  - GPSDO's pps jacks draw a 51 Ω terminator, marked DNP. Round 44 called the
    inputs terminated and dropped a test that works.
  - `excluded_from_assembly.csv` answers the question in one grep (GPSDO r45).
- **Try a new bench source as an aggressor before trusting it as a channel.** A
  USB-powered CircuitGear's DDS 10 MHz on one GPSDO input made every other channel's
  beat chatter (common mode: the pair differences stayed clean). It brings its ground
  and its spurs with it (GPSDO r45).
- **Rails at a glance.** An LED per rail, and an "in range" indication where it matters
  (GPSDO P40, REVB #6). Drive the LEDs so that they do not load a quiet rail.
- **Bring-up order** in a `HANDBOOK.md`: current-limited bench supply first, then each
  rail, then the programmer, then the first firmware, then the interfaces (ECP5 §4, GPSDO
  P39).
- **Bench instruments are scriptable.** `lab-instrument-control` (Siglent scopes and
  generators, an HP 33120A over GPIB, an ADALM2000) lets the agent take its own
  measurements once a board is cabled. Design tests that use them.
- **Firmware is part of the design.** A board with an MCU or FPGA needs its first
  firmware written and building before the board is ordered. That shakes out pin and
  clock choices: the GPSDO's I²C driver could not *read* until bring-up (GPSDO r30
  #28).
- **Write the experiment's gateware before ordering too, and read its reset state against the
  board** (CostasLink Response 15). Writing the safe state (`safe()`: TX muted, loop held,
  receive) is what found that the board's own idle was not safe (section 4, "rests where an
  absent host leaves it"). Keep a REVA_CHANGES list while writing it, each entry found / what /
  change / state.
- **FPGA tool facts that cost hours** (CostasLink Response 15):
  - A Vivado block design's module reference needs a Verilog top, not SystemVerilog.
  - Never edit the sources while Vivado builds: the module reference's out-of-context run goes
    stale and the core comes out a black box, with no error.
  - Vivado 2024.1 segfaults (exit 139) in synthesis on a function called with a variable part-select
    of a parameter (`morse(CALLSIGN[8*ci +: 8])`): build the table in a generate loop with constant
    indices.
  - Yosys merges identical flip-flops even when marked `keep`; a copy of a register per block (a
    register bus near each block, a reset tree) survives only as its own `keep_hierarchy` module.
    Vivado honours either.
  - nextpnr's Fmax moves 10 % from seed to seed on a full ECP5: once the paths are pipelined, let the
    Makefile try seeds until one meets the clock rather than chase the last nanosecond.
  - Every constant compare (`x > 1`, `x <= 1`) may become a carry chain in Yosys; write it as a
    reduction (`|x[31:1]`). A block RAM's output on the ECP5 is 5.6 ns clock-to-out: register it.
- **Run the host's driver against the RTL** (CostasLink `gateware/driver/test_sim.py`). Icarus
  reads commands from one named pipe and answers on another (`$fscanf`, `$fwrite`, `$fflush`),
  so the Python that will run the experiments drives the simulated core with a loopback model.
  End every command on a falling edge: a model knob changed between commands otherwise races the
  model's own rising-edge process, and a flipped bit or a trigger lands a clock off.
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
- **A bring-up plan is a table from the dead-on-arrival list to the stage that retires each risk**
  (CostasLink `BRINGUP.md`, 2026-10-09): stages in order, each with its connections, measurement,
  pass condition and what to do if it fails, and a last table that says which stage answers which DOA
  item and what the fallback is.  An accessory from AliExpress has a spec table on its page or none
  at all (the 5.8 GHz "SAW + LNA" module had none): write the assumed numbers into the budget as
  assumptions, and make measuring them a step of the plan.  An external PA with 40 dB of gain wants a
  pad on its input: the board's +10 dBm would drive it 17 dB into compression.
  - **And measure them on a VNA before the board arrives, if one is within reach** (CostasLink Prompt 42,
    2026-10-24, the boards in transit): the "SAW + LNA" module assumed at 15 dB measured 29, the "40 dB" PA 46,
    the 10 m cables 10 dB each at 5.8 GHz where the budget had 5 dB of LMR-200, and two of four grid antennas had
    their feeds turned against their bars.  Each changed a step of the plan (the PA's pad, the frequency plan,
    where the amplifiers sit).  Two antennas measured as a pair give the board a link whose loss and delay are
    known to a dB and 0.1 ns before it is powered: calibrate the receiver's level scale against that, not a
    generator.  Measure the fixture (the pad chain with no device) before every de-embedded campaign, check a
    recalled calibration on a thru after a power cycle (S21 against S12), and let the plan quote the `.s2p`
    files by name: the pads' values are files too.
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

- **A book circuit as a lab instrument: say what it is good for, circuit by circuit** (op-amp board,
  2026-10-24). Jason: "I want to show students that opamps aren't magic (just made of transistors) ...
  Could this be used for the first few circuits in lab 6 and 7 and maybe even 8?" Read the actual lab
  circuits out of the book's PDF (`pdftotext -layout`, then the section headings) and judge each one
  against the amplifier's real numbers: a 0.7 mA BJT pair has ~2 µA of input bias current, so the
  photodiode converter's 10 MΩ and the integrator's 10 MΩ leak are out, the 100 kΩ phototransistor
  version and a 1 µF integrator are in, and the output has no current limit where the LF411 has 25 mA.
  Jason, on being told: "Being a 'bad' integrator isn't the end of the world ... As long as it doesn't
  run away in a tiny fraction of a second (and can't be fixed with a bigger capacitor), I'm perfectly
  happy with a 'not very good op-amp' that is made of real discrete transistors that the students can
  see and poke at." Non-idealities are the lesson; a dead output transistor is not. Put the verdicts in
  the handbook and the bias current and the missing current limit on the back of the board.

- **A class-B output stage needs diodes in its current limiter** (op-amp board, found in
  simulation before the board was drawn). The 741's limiter (a sense resistor in each emitter and a
  transistor across it that steals the drive) assumes a class-AB stage whose two bases sit a volt
  apart. With the book's bare class-B pair the bases are tied, so while one half conducts the idle
  sense transistor's base sits a Vbe above its collector: the junction conducts, dumps current into
  the drive node that the 12 k pull-down cannot sink, and the negative swing collapsed from -14 V to
  -9 V. A 1N4148 in series with each sense transistor's collector (anode toward the drive node)
  blocks it and costs nothing at the limit, which sits 1.25 V away from OUT. Simulate the limiter
  shorted and swinging, not just at rest; and when a protection circuit is added to a textbook
  circuit, give it its own box on the board and say in it that it is a safety feature.
- **A lesson about budgets**: adding six parts to a finished 100 x 100 mm layout cost a whole
  re-plan of the right-hand third (feed, return, switch, divider, loops) and raised the hop count
  from three to nine. Decide the protection before the floorplan.

## 10. Verification gates (run them every build)

Before calling a schematic, PCB or release done:

1. ERC clean (the warnings understood), with the netlist exported.
2. Every symbol pin checked against the datasheet figure.
3. A path trace of every signal, power rail, clock and strap.
4. No overlaps on schematic sheets, checked in code, by `pdftotext -bbox` on the
   exported PDF, and by eye on the PDF.
5. DRC at least as strict as the fab's: 0 errors and 0 unconnected, on the shipped file,
   with its zones filled.
6. Pads where KiCad puts them; connectors pointing out in the 3D render; every part with
   a 3D model.
7. Silkscreen:
   - no overlaps;
   - every label inside its box;
   - text at least 0.8 mm high and lines at least 0.15 mm wide;
   - nothing printed off the board;
   - every jumper's label beside it, every part and its label in the same box.
8. Parts:
   - every SMD part with an LCSC code;
   - every code's description matching its value and package;
   - every ordered land pattern fitting the board (no HOLE);
   - stock and price fetched with a timestamp.
9. CPL native plus JLC-corrected, with `PLACEMENT_CHECKS.txt`.
10. The revision and date on the silkscreen match the source of truth. A release is
    stamped DRAFT until the date is a real date.
11. Every rail's width measured by net from the shipped file against the rule.
12. `hand_solder_bom.csv` empty.
13. From the netlist (Rosenberg, §4): no one-pin nets but test pads; the list of power
    nets read for aliases; every inductive load with its freewheel path; every
    high-current input fused; every polarized part's orientation listed for the
    preview.
14. The design equations asserted against the netlist's values (§4, "Values").
15. Fiducials and layer markers present; paste openings on exactly the pads that need
    them (Rosenberg, §5).
16. Copper balance (each layer's copper fraction, by quadrant) and current capacity:
    each high-current net's narrowest track against its current (IPC-2221, §15) and
    its drop at full current, ground return included.
17. **The upload-readiness pass** (ECP5 P31: "is there anything that might block a
    successful run if I uploaded the board now?"), read from the release, not from
    memory: DRC and ERC counts with every warning named and placed (a zone's
    `connection_width` warning reports the zone's anchor, not the neck: shrink each
    filled polygon until it splits to find it); BOM lines against CPL rows (no
    designator in one and not the other, no duplicate code); stock against the need
    for the order with the fetch time; the hand-solder list empty; the gerber job's
    stack-up and the drill header; `git grep` for absolute paths; every capacitor's
    dielectric read off its part number (C0G where it sets a frequency or sits in the
    signal path); the dissipation of every regulator at the worst load (the ECP5's
    ADC LDO: 1.7 V x 0.2 A in a SOT-23-5 at 187 °C/W is +64 °C); a fuse on every input;
    fiducials, layer markers and the order-number marker present.
18. **Every silkscreen text against the unit and region boxes**, from the written board
    with KiCad's own text boxes, and every designator nearer its own part than any other
    (§6; GPSDO `pcb/check_unit_labels.py`).
19. **Every clock net's routed length and via count against the previous revision** (§5).
20. **Every net class binds the nets it was written for**, counted from the netlist (KiCad
    writes each net's class into it).  CostasLink's `/^RF_/` and `/^LO_/` matched none of
    `Net-(U101-RF_IN)` or `/Receiver and Costas loop/LO_RX_P`, and its CPWG gap fell to the
    pour's 0.2 mm without a warning.  Bind generated designs' classes by exact name from the
    generator's own list of the nets.
21. **Every exposed pad's and tab's via count against its datasheet's land pattern**, the
    small ones too (CostasLink build 17: 2 × 2 where the ADL5380 draws 3 × 3, none in the
    LNA's paddle or the SOT-89 tabs).
22. **Every RF launch measured in the plotted gerbers** (§14, "The stock SMA footprint"): at
    each through-hole RF pin, no pad flash on the inner layers, the planes the solved antipad
    off the barrel on every inner and back layer, the top pour the solved clearance off the
    pad, no track of another net inside the connector's legs on any layer, and the distances
    printed by name in the release log (CostasLink `tools/launch_check.py`).  Not the board's
    settings, not DRC: the copper.
23. **Every PDF and image fills its page** (§2, "Every page fits what is on it"). Check
    schematic sheets, assembly drawings and plots: the drawing is centred, about half an inch
    from the paper's tighter edges, and nothing is off the page. Use `fit_pdf.py check` and a
    render of every page.
24. **Every RF net's routed length against the shortest tree through its pads** (§5, "And every
    RF net's length"): no RF net, monitor taps included, over 1.5x its tree and 10 mm extra.
    CostasLink `tools/detour_check.py`; rev A's LO TX MON tap was 9.4x, 25.7 dB low on the bench.
25. **Every RF path simulated as laid out** (§14, "Simulate the circuit the copper makes").
    - **Which paths:** jack to pin, pin to pin and pin to jack, extracted from the written board. Each is compared with the vendor's circuit placed at the pins.
    - **Pass:** within 1 dB of it across the band ±20 %, and no 3 dB dip or peak that it lacks. Print the range over the parasitics' sweep.
    - **The power side in the same run:**
      - each RF supply pin's impedance against the reference circuit's;
      - each choke's cold end;
      - each bead-capacitor resonance and its damping;
      - each plane island's modes in the band;
      - the coupling between chains through the rails, in dB.
    - **Rev A:** none of this was done, and its receive chain lost 30 dB at 5.8 GHz (REVB 8, 10).
26. **Every RF matching, shunt, bypass and bias part's track to the pad it serves**, measured on the written board.
    - **Limits:** matching parts under λ/50 at the top frequency (0.5 mm at 5.8 GHz); bypass and bias parts under 1 mm.
    - **No RF part on a branch of the line.**
    - **Print every T-junction on every RF net,** with its branch length and what hangs on it. Rev A's 0.5 pF match was 4.0 mm away, on a 1.8 mm branch.
27. **Every RF shunt part's and RF bypass capacitor's ground:** a via in, or touching, its ground pad (centre within 0.3 mm of the pad's edge), to the plane directly under it.
    - **Every RF IC's ground pins** joined solidly to its exposed pad and the pour.
    - **The exposed pad's vias:** at least the count gate 21 asks for.
28. **Every bias choke and every ferrite into an RF rail:**
    - an RF bypass on its cold pad, within 1 mm, via in pad;
    - no plane via ahead of that capacitor;
    - its SRF against the band, written in the design notes.

    Rev A: all three ADL5611 chokes went to a plane via with no capacitor within 5.4-13.6 mm (`bringup/layout/layout_survey.py`).
29. **Every supply plane island: which RF chains it serves.**
    - **Fail:** two chains on one island, or a transmitter's output stage and a receiver's input, without a filter between them.
    - **Under every relief window:** ground.
    - **Its cavity modes in the band:** listed.
30. **Stitching measured on the filled pours.**
    - **Within 10 mm of any RF net:** no pour point more than λ/20 from a ground via (1.25 mm at 5.8 GHz in FR4).
    - **Elsewhere:** no point more than λ/6 (4 mm).
    - Rev A: 8.6 mm near the receive chain, 20.7 mm elsewhere.
31. **The isolation budget:** each transmitter-to-receiver path estimated in dB, written beside the receiver's dynamic range and its attenuator's range, and measured at bring-up (§9).
32. **Every RF line segment measured on the filled board**, segment by segment:
    - its width against the class's;
    - its gap to the pour against the CPWG's, within 0.02 mm;
    - ground on the next layer under at least 95 % of it, outside the designed voids;
    - fence vias at least 1.5 per mm on any run over 2 mm;
    - which plane lies under the voids.

    Rev A (`bringup/layout/layout_survey.py`):
    - **Width, gap and ground:** right everywhere (0.29 mm, the gap 0.25 mm, ground under 100 %).
    - **Fence:** short. 0.9-1.0 vias per mm on its longer runs, where the generator skipped spots, and none within 1.6 mm along RX MON's 5.8 mm tap.
    - **What cost the dB:** gates 25-31.

## 11. KiCad 10 and tooling quirks

- **`~/OpticsPCBs` is a symlink** (to `mudd/OpticsPCBs`), and `find` does not follow a
  symlink given as its starting point: `find ~/OpticsPCBs -name fit_pdf.py` found nothing
  and the op-amp board nearly got a second, divergent fitter.  Search with `find -L` or a
  trailing slash (`find ~/OpticsPCBs/ ...`), and grep the tools a lesson names before
  writing one.

- **Running KiCad.** The AppImage is `~/.local/bin/kicad-10.0.6-x86_64.AppImage`
  (`kicad-cli` is a subcommand). An extracted copy is at `~/.local/kicad10/AppDir`. Run
  its Python as `AppDir/AppRun python3.11 script.py`: calling `usr/bin/python3.11`
  directly with `LD_LIBRARY_PATH` set segfaults on `import pcbnew` (10.0.6).
- **pcbnew from a script** (GPiBridge, 2026-10-06):
  - `board.Save()` also rewrites the `.kicad_pro` with default net classes and rules.
    Write the project file again after saving.
  - A `LoadBoard()` in a process that has already saved a board built in memory reuses
    KiCad's in-memory default project: its zone fill ignores the project's net classes and
    custom rules, and its save writes the defaults over the `.kicad_pro` (CostasLink build
    18: Default clearance 0.2 mm, 479 DRC errors).  Fill by the project's rules in a fresh
    process (`AppRun python3.11 board.py --refill`), then write the project file again.
  - `pcbnew.WriteDRCReport()` segfaults in a bare Python (it needs KiCad's program object).
    Run `kicad-cli pcb drc` on the saved file instead.
  - **KiCad's DRC and its connectivity API disagree about a track end that lands on the
    middle of another track of its net:** `TestTrackEndpointDangling()` calls it joined, and
    the DRC calls it `track_dangling` (CostasLink build 18: a fan-out stub whose via never
    fit, ending on the router's own line).  After the last fill, take the DRC's list from
    kicad-cli and remove each such track whose removal leaves the unconnected count where it
    was (`gen/board.drop_dangling_by_drc`).  One such pass a process: after a zone fill,
    KiCad's SWIG hands back `GetConnectivity()` as a bare object without its methods.
  - **A clean-up pass that adds copper must be idempotent.**  CostasLink's `snap_to_vias`
    added its joining segment again every time the tidy ran: build 17 carried 90 duplicate
    segments, and a second tidy after the refill made 786.  Key what a pass adds by (net,
    layer, both ends) and skip what is there; drop exact duplicates at the end
    (`gen/tidy.dedupe`).  Count the tracks before and after a pass: a count that doubles is
    the symptom.
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
- **A zone fill's narrow necks.** KiCad's `connection_width` warning on a zone names the
  zone and its anchor, nothing else. Find the neck by reading the zone's
  `filled_polygon`s and shrinking each (shapely `buffer(-w/2)`) until one splits: the
  piece that splits is the crumb, and its bounding box says where (ECP5 build 30: two
  ground vias 0.7 mm apart in the gap between two In4 planes, their annuli joined by
  0.03 and 0.06 mm webs of fill -- harmless, but it took a script to say so). The fill's
  own `min_thickness` does not remove such webs: the deflate-inflate pass re-merges two
  lobes whose cores were separate.
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
  the native Wayland canvas, not the file. Open boards with a `kicad-gui.sh` that sets
  `GDK_BACKEND=x11`.
- **Schematic quirks:**
  - A field's justification is mirrored when the symbol's rotation plus the field's
    angle is 180.
  - A footprint field's angle is **absolute**.
  - Pins that touch a wire's interior do not connect.
  - Text bounding boxes are about 2.0x the text size high, not 1.6x.
  - A field's glyphs sit in a measured band about the anchor (reference: -0.76 to
    +0.23 x size; value: +0.38 to +1.37 x size), and the anchor snaps to 1.27 mm.
  - Power symbols need numbers: seventy all referenced "#PWR" make `kicad-cli sch
    export netlist` warn "schematic has annotation errors". Number them `#PWR0001`...
    across the sheets of one run.
  - **Bus aliases live in the project file.** KiCad 10 keeps them in `.kicad_pro` as
    `schematic.bus_aliases: {"NAME": ["A[12..0]", "B", ...]}` (an object of member
    lists; a `{"members": [...]}` shape is ignored), and `kicad-cli sch upgrade` drops
    any `(bus_alias ...)` from a sheet wherever it is placed. A generator that writes
    the alias only into the sheet passes ERC until the first upgrade, then every wire
    into the `{NAME}` bus is "not a member" (ECP5 build 28: 26 warnings, found by the
    build, not by the manual ERC that ran before the upgrade). Write aliases into the
    project file; the inline form `{A[12..0] B C}` needs no alias but is 90 mm of text.
- **easyeda2kicad footprints** are in the old format (run `kicad-cli fp upgrade`), and
  their courtyards exclude the pads.
- **DRC rule trap.** A custom `silk_clearance` rule on text makes KiCad 10 report every
  designator against Fab text and courtyards as `silk_overlap`.
- **Layer names in pcbnew.** KiCad 10's `board.GetLayerID()` knows only the long names
  (`F.Silkscreen`); `"F.SilkS"` gives an undefined layer, the item is saved there, and
  `kicad-cli` then refuses to load the board ("items on undefined layers"). Map layer
  names to the `pcbnew.F_SilkS` constants yourself.
- **`BOX2I.Merge()` returns a non-owning view of the box it was called on.**  `bb = bb.Merge(b) or bb`
  keeps the view and drops the owner, the box is freed under it, and KiCad aborts later with
  "malloc(): unaligned tcache chunk detected", sometimes (CostasLink, 2026-10-09: two 25-minute
  builds lost at their last stage).  Merge in place and keep the owner: `bb.Merge(b)` on its own line.
- **`SHAPE_POLY_SET.Outline(i)` is a view into the set.** On a temporary
  (`make_set(...).Outline(0)`) it reads freed memory: Edge.Cuts segments to -1000 mm.
  Keep the set in a name while its outline is read.
- **PCB coils as net-tie footprints** (the footprint's own copper is the spiral, joining
  pad 1 to pad 2; OWLternating Current's `gen/coils.py`):
  - the footprint's copper may overlap its own pads without a DRC error, but pads with
    no net (the layer-change vias) are still held to hole clearance against it;
  - DRC never checks a net tie's copper against its own pads, so the generator must
    check that geometry itself;
  - DRC does not compare copper of no net in one footprint with copper of no net in
    another, so the courtyard must enclose all of a coil's copper: it is the only check
    that keeps two spirals apart.
- **Inkscape 1.x** hangs with `DISPLAY`/`WAYLAND_DISPLAY` and a session bus. Run it with
  those unset and `DBUS_SESSION_BUS_ADDRESS=/dev/null`.
- **Scratch space.** An agent's scratchpad directory can vanish between sessions. Keep
  build scratch inside the project's gitignored `build/`.
- **Text strokes are clamped to a quarter of the character width.** 0.58 mm wide letters
  came out with 0.145 mm strokes and failed DRC's 0.15 mm `text_thickness`. Keep letters at
  least 0.6 mm wide for 0.15 mm strokes, and assert it where texts are made (GPS adapters).
- **0.8 mm text is up to 1.1 mm tall** once it has parentheses, commas or descenders.
  Lines of notes need a pitch of about 1.36 mm, or leave the parentheses out.
- **QR codes are a board item in KiCad 10** (`pcbnew.PCB_BARCODE`, `BARCODE_T_QR_CODE`).
  - Make it a knockout (`SetIsKnockout(True)`): a white square with the modules left
    dark. Silkscreen modules on a dark mask read inverted, which many phone cameras will
    not decode.
  - KiCad pads the knockout by at least a tenth of the code's size (9 mm -> 10.8 mm), and
    DRC wants 1 mm of "barcode visual separation" from the board edge and from vias.
  - Make it on the front and `Flip()` it to the back, so it reads right from the back.
  - Measure its extent with `GetBoundingBox()`, not from the size you asked for.
- **Pin names with spaces come out with underscores** in KiCad 10's symbols: "FC TX ->
  GPS RX" printed "FC_TX_->_GPS_RX". Use hyphens.
- **Local labels name a net with the sheet's path** ("/TX_FC_TO_GPS"); power symbols do
  not. A local label and a power symbol of the same name join under the power symbol's
  name. A board generator that looks nets up by name must try both.
- **Gerber and drill files carry the time they were plotted**, so a rebuild never gives the
  same zip. Stamp the design date over `TF.CreationDate`, the job file's `CreationDate` and
  the header comments, and give the zip entries a fixed date (GPS adapters'
  `mfg/make_release.py`); then an unchanged board makes the same bytes.
- **A stock 3D model's axes are the stock footprint's.**  A footprint drawn in another frame
  (CostasLink's underside socket: rows along -x, the even row at -y) shows KiCad's socket
  model turned 90 degrees.  Give the model a `rotate` in the footprint (gen/footprints.MODEL_ROT)
  and LOOK at `kicad-cli pcb render --side bottom`: Jason saw it in the 3D view (Prompt 35).
- **kisch mirrored the field justification both ways for a mirrored symbol**, so a
  connector mirrored to face right had its value drawn inside its own box. A mirror about the
  vertical axis swaps left and right only (fixed in the GPS adapters' copy of `kisch.py`).
- **A 0.25 mm occupancy grid cannot judge a 0.15 mm line.** Two boxes that only touch
  round onto the same cell; test thin silk lines against the exact boxes of the texts
  already placed (ECP5 P26: no centre-pin ticks were drawn at all, and the plot could
  not show it).

- **Generated symbols: every pin on the 1.27 mm grid** (CostasLink, 2026-10-09). KiCad connects
  wires and pins only where they coincide on the 50-mil grid. A box symbol that centres an even
  number of 3.81 mm-pitch pins puts them at odd multiples of 1.905 mm; the generator's grid-snapped
  wires then miss them by 0.6 mm, and ERC reports 35 "unconnected wire endpoint" stubs of 0.03 mm
  and every ground pin "not connected". Round each pin's position to a multiple of 1.27 when the
  symbol is drawn (the pitch stays; the row shifts by 0.635).
- **A box symbol's rows are not centred on its anchor.** Place a chip by the pin that must sit on a
  line (`part_at_pin(key, ref, pin, x, y)`: compute the pin's offset from the symbol and place the
  anchor accordingly), or every RF line into it bends by a row.
- **Make the schematic checker say which line drew the wire.** Record `file:line` of the caller for
  every wire segment (`inspect.stack()`), and print it beside each touch/overlap message; with a
  `sch_where.py SHEET X Y` that lists the parts and wires near a point, a collision takes one look
  instead of a page of arithmetic (CostasLink: 108 problems to 0 in an hour).
- **Vertical chokes on adjacent output pins need 15 mm of row pitch**: an RF chip's differential
  outputs at 2.54 mm pitch cannot each carry an inductor standing up to a rail flag (the second
  pin's choke and flag text land on the first pin's line, whatever the lines' detours). Give the
  symbol empty rows instead.
- **`extends` chains.** A KiCad 10 stock symbol may extend a parent that extends another
  (`OPA2189xDGK` → `OPA2196xDGK` → …); flattening one level yields a symbol with no pins. Resolve
  the chain recursively, and rename every `NAME_u_s` sub-symbol whatever its prefix.
- **ERC's JSON positions are in 100 mm units** (`"x": 2.9972` is 299.72 mm).
- **Datasheet fetching** (2026-10-09): ADI's direct PDF links want a browser `User-Agent` (a bare
  `curl` times out); Skyworks' `/-/media/` links need the exact revision in the file name (the
  product page returns HTML for a guessed name); JLCPCB's file endpoint (`tools/jlc_datasheet.py
  <code>`) serves the LCSC copy of oscillator and connector sheets. Digi-Key returns 403 to
  scripts and the aggregators (findchips, octopart) omit it or 403 too: ask Jason to read
  Digi-Key/Mouser stock in a browser; quote the aggregator snapshot as such.
- **A PCB coupler or other copper-only element is a net-tie part**, not a label: a symbol with the
  line's two pins and the coupled line's two, a footprint whose own copper joins each pair
  (`net_tie_pad_groups`), `in_bom` off. Then ERC, the netlist walk and the board all know it.

- **Block diagrams are generated, annotated and pedagogical** (CostasLink, 2026-10-09, Jason's request).
  Once the design is settled, draw it as block diagrams whose block titles read at a glance and whose
  EVERY arrow carries a box with the signal's level (dBm and mV), centre frequency, bandwidth and DC
  offset, plus a thumbnail of the signal in time or frequency, and a "how to read this" paragraph for
  the students.  Make them from the budget's JSON (docs/blockdiagram.py -> docs/images/block_*.svg, text
  kept as text so it zooms) so the numbers cannot drift from the design; a PNG for the README.  A
  stray `%` in a formatted matplotlib string is the usual crash.
- **Absolute paths in every shell command** (CostasLink, 2026-10-09).  The tool shell's working
  directory can be reset between commands; one batch wrote four datasheet PDFs at the repository root.
  Use absolute paths, and check `git status` at the repository root before calling a response done.
- **Every wire states what is on it** (CostasLink, 2026-10-09, Jason's Prompt 3: "looking at the schematic,
  one can instantly see what the levels, DC offset, frequency, and bandwidth are at every wire or pair of
  wires").  A distinct colour of note (blue, sch_util.sig) beside every signal wire: frequency | level in
  dBm and mV | bandwidth | DC offset or common mode, for the stated operating point (the bench link); the
  strings come from one module (gen/levels.py) fed by the budget's JSON, which the block diagrams also read,
  so sheets, diagrams and plan never disagree.  Yellow stays for explanation.  Place the boxes last and run
  the overlap checker filtered to them: a box across a supply cap's ground or a monitor jack is the usual
  miss.  A crash in the schematic generator must exit with a code the build does not accept as "overlaps".
- **A comparator has a floor; put it in the budget** (CostasLink, 2026-10-09, Response 6).  A fast
  comparator decides nothing below about twice its offset plus hysteresis (20 mV for a TLV3601).  Refer
  that to the antenna through the chain's gain and compare it with the noise-limited threshold: the
  CostasLink receiver as first drawn was deaf 17 dB above its noise.  Balance the two with RF gain (a
  second gain block is 0.3 ns) and give a sensitive path its own baseband gain; then every range table
  takes the shorter of the noise limit and the floor.
- **A root sheet's wiring columns must stay clear of the sheet boxes, and the sheets' pin rows must not
  share a y with another sheet's pin rows that the same wires cross** (CostasLink, 2026-10-09).  Adding
  five signals pushed the pwr-to-sheet columns past a sheet's left edge and put two pwr rows on the
  transmitter's rows: three silent shorts that only the net walk and ERC caught.  Compute the columns'
  extent and the row coincidences in the generator and assert them; route the far sheet through a
  corridor below the others.
- **Place, then check, then look** (CostasLink, 2026-10-09, Jason: "The text boxes in your schematics are
  overlapping with each other and with components in many cases... Look visually if nothing else").  A
  checker that reports overlaps is half the job; the generator must also PLACE: notes are deferred until
  the sheet is drawn, then each is put at the nearest clear spot against the checker's own geometry
  (texts, symbol bodies incl. their fields, wires, the page) within a small radius of where it was asked
  for (sch_util.flush_notes), and the report names what could not be cleared.  Part labels have fixed
  offsets, so their collisions are geometry: capacitor rows need 10.16 mm, not 7.62; two parts on one
  node line need their texts on opposite sides; a pull-up next to a supply bar's flag is a resistor up to
  the bar, not a second flag; KiCad's diode symbols lie down (rotate them up, cathode where the rail is).
  Then render every sheet and zoomed crops of each flagged spot and look, because the numbers miss a
  label 0.4 mm into a ground symbol and a switch drawn with its signal through its own body.
- **A shunt hanging down from the upper of two stacked rows runs through the lower row** (CostasLink,
  2026-10-09, Response 8: a 300 dpi crop showed the IN- line through the body of the IN+ summing node's
  shunt resistor; the touch checker tests pins, not bodies, and the earlier look at the sheet was too
  coarse to see it).  Stand such a part on a loop ABOVE its row (up 5.08, the resistor lying along the
  top, its ground hanging from the far end), and crop the PDF at 300 dpi round every two-row block
  before calling a sheet clean: a 4000-pixel render of an A2 sheet is 7 pixels per millimetre.
- **Adding the pins a symbol lacked must not widen it**: a box symbol widened to take nine ground pins
  on its bottom row moved every block drawn to its right by 25 mm and a monitor jack off the page.  Put
  extra ground pins down a side and join them with one bar to one ground (sch_blocks.side_gnd).
- **A generated symbol can be incomplete, and every existing check passes** (CostasLink, 2026-10-09,
  Response 8: the pin audit found nine of the PE43711's grounds, the HMC536's paddle and the SMA's
  centre pin without a net; ERC, the netlist walk and the sign-off renders all said fine).  The gate
  that catches it: for every component, every pad of its library footprint must carry a net or a
  no-connect flag (tools/net_check.py).  A vendored connector footprint numbered unlike its symbol
  (JLCPCB's SMA: legs 1-4, centre 5; KiCad's Conn_Coaxial: 1 centre, 2 shield) is the same fault:
  renumber the footprint's pads to the symbol's pins in the generator.

- **Footprint items keep the library's uuids in every copy** (GPSDO rev B, 2026-10-09).
  A generator that copies a `.kicad_mod`'s text into the board gives every instance's
  pads, graphics and keep-outs the same uuids: 97 of them on 1491 items. KiCad 10's
  solder-mask check keys apertures by uuid, and it reported a U.FL's mask rectangle as
  bridging a track of another U.FL's net 125 mm away, in one build and not the next.
  Give each instance's items their own uuid, derived from the reference and the library
  uuid so rebuilds stay identical (GPSDO `pcb/build_pcb.py`, `footprint()`).
- **KiCad's text bounding box includes the font cell**, about 0.3-0.4 mm above the
  capitals. A containment check on KiCad's boxes needs that much tolerance, or a heading
  standing on its own box's edge reads as "in" the box.

- **pcbnew hands back a fresh Python wrapper on every call, so `is` never matches.** `t is item`
  over `board.GetTracks()` is always false; compare `item.m_Uuid.AsString()`. CostasLink's first
  cleanup pass found every track touching itself and fixed nothing until it compared IDs.
- **Finish every routed board with KiCad's own connectivity, not the router's grid.** A grid router
  calls two pieces joined when their cells meet, but their copper can stop 0.05-0.2 mm apart, or a
  stub can end just outside a pad's corner: DRC then reports dangling tracks and unconnected items
  the router never saw. After the zones are filled, ask `GetConnectivity().TestTrackEndpointDangling`
  for each track. Join each dangling end to same-net copper within 0.45 mm with a short segment;
  remove what is left if it is a short dead stub, and remove dangling vias. Refill the zones.
  Join before removing anything, and recompute after every round that joined: removing a dangling
  via first stranded the tracks that nearly reached it, and later rounds removed those too, which
  broke two nets in CostasLink's first run. `gen/tidy.py` is the pass.

- **KiCad 10's SWIG loses VECTOR2I after a Remove/Add and a connectivity rebuild** (CostasLink,
  Prompt 31): `track.GetStart()` comes back as an opaque SwigPyObject with no `.x` on the next item.
  One removal a process, then a fresh process (gen/board.py `drop_dangling_by_drc`), as the fills
  already do.  And the library's sexp round trip keeps one of two identical pad keys: to change a
  vendored pad's `remove_unused_layers`, replace its line, do not add one.

- **pcbnew 10.0.7 from Python** (op-amp board, 2026-10-24):
  - `pcbnew.STROKE_PARAMS` is not exposed to SWIG, so a dashed line cannot be set by stroke style: draw
    the dashes as individual segments (and clip each around pads and wire crossings yourself).
  - A fiducial without a footprint (so schematic parity stays clean) is a filled `PCB_SHAPE` circle on
    F.Cu (r 0.5) plus a filled circle on F.Mask (r 1.0); DRC accepts the unconnected copper graphic.
  - `kicad-cli pcb drc --severity-all` lists warnings in the same `[rule]:` form as errors; a build that
    counts lines starting with "[" stops on `silk_over_copper` warnings too, which is the right call on a
    board whose silkscreen is the point.
  - `kicad-cli pcb export pdf --mode-single` of F.Cu + F.SilkS + Edge.Cuts, rasterised with `pdftoppm`
    and cropped to the outline's ink, is the quickest "look at the board" image; crop regions of it by
    board millimetres (px = (mm + pad) x dpi / 25.4) when chasing one label.

- **A drawn symbol replaces the footprint's own outline** (op-amp board, 2026-10-24). KiCad's SOT-23
  prints a rectangle round the package; inside a hand-drawn transistor symbol it reads as a fourth
  lead. Remove the footprint's F.SilkS graphics in pcbnew (`fp.GraphicalItems()`, `fp.Remove`) when the
  symbol is drawn, and set `lib_footprint_mismatch` to ignore in the project's rule severities with the
  reason in a comment, because DRC otherwise reports every edited footprint as differing from its
  library copy. Jason's reaction to the first version, with the outline and shallow leads: "Those
  transistor symbols are still really confusing. They don't look like the transistor symbols in the Art
  of Electronics. Isn't the arrow always the emitter?" The arrow is always the emitter; the legs leave
  the bar near its ends at about 30 degrees, and the package sits between them.


### ngspice through the netlist (PID motor board)

- **Simulate the exported netlist, not a hand-typed deck.**  `sim/pid_sim.py` parses
  `out/<stem>.net`, emits an R/C/D/Q/X line per component with behavioural models, adds the
  plant, and sweeps the switches and trimmers by name; a wiring mistake on the sheet then
  shows up as a wrong step response rather than staying hidden in a deck that says what was
  meant.
- **Take a transistor's dissipation from its own pins.**  The stall sweep computed Q1's
  power as I x (V(+15 V) - V(DRIVE)) with DRIVE at the emitter resistors' junction, which
  quietly counted the 1 Ω resistor's I²R as transistor heat (3.7 W, of which 0.25 W was the
  resistor); when the fuse moved, DRIVE became a node past the PTC too.  Use V(collector) -
  V(emitter) from the netlist's own pins (`Deck.pin("Q1", 2)`), and say what a rounded-up
  figure covers when a check keeps it.
- **Report a step's peak, its swing back and where it comes to rest separately.**  With
  sticking friction a step can stop past the target without ever overshooting; one
  "overshoot" number (peak past target) called the dead band an overshoot and "settles in
  1500 ms" meant "never enters the band round the target".
- **Hash every UUID the generator writes.**  The schematic's rectangles wrote their key
  ("box/fuse") as the UUID; `kicad-cli sch upgrade` replaced the invalid strings with random
  ones, so the sheet changed on every build.  `uid(key)` (uuid5) everywhere.
- **Let an explicit tool path win, and check the version of one found on PATH.**  Two
  reviewers' machines had KiCad 9's `kicad-cli` in /usr/bin; it beat KICAD_APPIMAGE and
  /usr/share/kicad's KiCad 9 libraries beat the AppImage's.
- **A stage that reads another stage's output must make it if it is missing**: the sim ran
  before the schematic and read `out/*.net`, which is not committed, so a fresh clone fell
  back to the committed results with a misleading message.
- **Make the netlist-to-SPICE step refuse a value it has no model for.**  The sim stage ran
  before the schematic stage on the previous netlist; after the transistors were renamed,
  the old value fell through to the SOT-23 branch and every result was garbage with no
  error.  An unknown value stops the build with "rebuild the schematic first".
- **`limit(x, lo, hi)` in ngspice is a random (Monte-Carlo) function**, not a clamp: an
  op-amp model written with it returned zero.  Use `min(max(x, lo), hi)`.
- **"+15V" and "-15V" sanitise to the same node name** unless the sign is spelled ("P15V",
  "M15V"); the op point failed silently until it was.
- **An integrator starts railed** unless the deck says `.ic V(<its output>)=0`; the
  scenario that switches I in needs it.
- **Friction that lets the slider creep is wrong.**  Coulomb friction as `F tanh(v / v0)`
  with v0 a fair fraction of the working speed lets anything below break-loose creep, and
  a P-only loop then walks its residual away.  Make v0 tiny (10 µm/s) and add a Stribeck
  rise, `(Fc + (Fs - Fc) exp(-(v / vs)^2)) tanh(v / v0)`: the deck then sticks, slips and
  hunts on a slow triangle as the bench fader does, and ngspice (gear, 20-50 µs steps)
  still runs it.  `vs` is a fit to what the bench shows, so say so.
- **Measure the natural frequency from the ringing, not from all the crossings.**  With
  friction, a step at high gain rings a few cycles (31 Hz) and then hunts slowly (5 Hz); the
  mean of every zero crossing in the first second gave 5 Hz and a D rule off the end of the
  trimmer.  Count crossings in the first 150 ms after the first half-cycle.  Settle to 5 %,
  not 2 %: sticking friction leaves a few per cent of dead band.
- **Parts rotations and datums need the same table**: JLCPCB's origin for a DPAK is 1.9 mm
  toward the tab from KiCad's, the RK09K's is the body centre, and their D2PAK is drawn
  turned 180° from KiCad's TO-263-2 (pins at +x) with its leads 2.45 mm further out.  `JLC_ROTATION` entries are
  `(deg, (dx, dy), how, note)`; the upload CPL moves each part by its shift rotated into
  board coordinates, and `check_outputs.py` proves the two CPLs differ by exactly the table.
- **The AppImage does not ship every 3D model its footprints name** (MSK12C02, RK09K, the
  1812 fuse).  Generate a stand-in body and let `gen_pcb.py` swap it in when the named file
  is not on disk, or the model check fails and the render shows bare pads.
- **Vivado drops the tristates inside an IP Integrator module reference** (CostasLink rev A,
  2026-10-29).
  - **What happened:** the block design's cells were synthesized out of context, and every
    PYNQ build said "[Synth 8-5799] Converted tricell instance to logic" for the I2C SCL and
    SDA pins. That is a critical warning, and nobody read the log.
  - **The result:** the FPGA drove the open-drain lines instead of releasing them. I2C never
    worked on the board, and the build still reported success.
  - **The fix:** `set_property synth_checkpoint_mode None` on the `.bd` (global synthesis),
    or real IOBUF instances.
  - **Check it in the build:** fail the build unless each tristate port's leaf cells are an
    IOBUF or OBUFT (`get_pins -leaf` of the port's net; the plain net only reaches the
    hierarchical cell). Read every critical warning of every build, not only the timing.
  - **Give every bus master a timeout**, and a register showing its raw pin levels. A master
    that waits forever on SCL turns a wiring fault into a hang. With the levels readable, the
    fault took minutes to place.

## 12. Choosing real components (Rosenberg)

A schematic assumes ideal parts, and every real part does the circuit some damage.
Choose the part that does the least, at a sensible price.

- **Class 1 ceramics (C0G/NP0):** low loss, stable with voltage and temperature, 5 % (1 %
  for more money), up to about 220 nF/25 V in 1210. Use them for filters, RF matching,
  oscillators and crystal loads, PLL loop filters, timing, and low-distortion coupling.
- **Class 2/3 ceramics (X7R, X5R, Y5V...)** are cheap and large, but their value moves:
  - **with DC bias:** an X5R can lose about 84 % of its capacitance at its rated voltage.
    Read the maker's bias curve for the actual part (Murata SimSurfing, TDK, Samsung)
    and design with the capacitance at the working voltage. Use a larger value or a
    higher rating: Rosenberg uses 100 nF/100 V X7R up to 35 V. The same value in a
    smaller case loses more.
  - **with temperature:** −70 % from 25 to 75 °C in the worst part Rosenberg has seen.
  - So **never in an RC timer, a filter that sets a frequency, or an audio coupling
    capacitor**: the time constant comes out short and the signal distorted.
  - **They are piezoelectric.** They pick up vibration beside a sensitive sensor, and a
    current at audio frequency makes them sing: LED PWM, coil drives and burst-mode
    regulators between 1 and 20 kHz make MLCCs audible. Use C0G or film there, or
    switch above 20 kHz.
- **Self-resonance:** every capacitor is a series RLC and an inductor above its
  self-resonant frequency. Pick values and packages whose SRF lies above the band they
  serve. Mounted, the pads and vias usually add more inductance than the part (§13).
- **Aluminium electrolytics:** the most capacitance per dollar; polarized (reversed, they
  vent "dirty brown muck and smoke"); leaky; ±20 %; and they wear out. Life is rated in
  hours at 105 °C at rated ripple current, and roughly doubles for every 10 °C cooler.
  Check the ripple current at the frequency it flows at.
- **Polymer** (aluminium or tantalum polymer): "dry" electrolytics with low ESR, little
  loss of value under bias, and long life (check the datasheet). An economical
  replacement for a bank of large MLCCs.
- **Tantalum (MnO2)** is mostly replaced by polymer. If one is used, derate its voltage
  by half: they fail short, and can burn.
- **Film:** stable, accurate, low loss, high voltage; polypropylene has the lowest loss.
  Mostly through-hole; SMD parts are PPS. **Silver mica** is the best and dearest, for
  crazy specifications only.
- **Resistors:** check dissipation at the worst case and the voltage rating (typically
  50-75 V for 0603, 150 V for 0805). Thick film is fine for most things; use thin or
  metal film for low 1/f excess noise and low distortion in precision analog, with a low
  tempco and power to spare where self-heating would distort. Pulse-rated (anti-surge)
  parts take inrush and surges. A hot resistor needs copper to spread its heat, and big
  copper adds capacitance.
- **Inductors:** for a DC-DC converter, the type its datasheet asks for, with a
  saturation current above the peak current (not the average), shielded where
  neighbours are sensitive. For RF matching and filters, simulate with the maker's model
  including Q, and keep the SRF well above the frequency of use, or the inductor is a
  capacitor.
- **Linear regulators:** dissipation is (Vin max - Vout) x I max, at the highest ambient
  inside the enclosure. ECP5's ADC LDO was 0.36-0.45 W in a SOT-23-5 (187 °C/W): 110-129 °C
  in a 45 °C box. A resistor ahead of it shares the drop and filters the input (2.2 Ω
  1206: 0.1 W), as long as the headroom at the lowest input stays above the dropout.
- **Semiconductors:** compute dissipation and junction temperature at the highest
  ambient. A MOSFET's R_DS(on) at 100 °C is about 1.5 times its 25 °C value; add
  switching loss. θJA comes from the copper the part sits on, not from the datasheet's
  test board.

## 13. Fast digital

For the fast boards to come; nothing here has been tested on one of Jason's boards yet.
Sources: Howard Johnson, *High-Speed Digital Design*; Eric Bogatin, *Signal and Power
Integrity — Simplified*; Henry Ott, *Electromagnetic Compatibility Engineering*; the FPGA
vendors' PCB guides (AMD/Xilinx UG583, Lattice's ECP5 notes).

- **Before choosing a faster host, add up every term of the latency chain for each host, the FPGA's
  sampling included** (CostasLink, Prompt 20, `sim/hosts.py`).  The Icepi Zero's missing 200 Ω
  header resistors save 2 ns over the PYNQ-Z2 only if its inputs sample at 656 Ms/s (GDDRX2); at the
  200 Ms/s its first gateware used, the 5 ns grid gave all of it back and tripled the jitter.  A
  carry-chain TDC (CARRY4, CCU2) beats any sampling grid, on any host, without new hardware.  And
  where a threshold is set by the noise (CFAR), widening the detection filter speeds the rise but
  moves the threshold out: the two nearly cancel, so check before widening.
- **Edges, not clocks, set the bandwidth:** BW ≈ 0.35 / t_rise. A 10 MHz clock with 1 ns
  edges has content past 350 MHz. **Give every FPGA and MCU output the slowest slew rate
  and lowest drive strength that meet timing.**
- **A trace is a transmission line** once its one-way delay exceeds about a sixth of the
  rise time. FR4 delays are about 6 ps/mm for outer-layer microstrip and 7 ps/mm for
  stripline, so with 1 ns edges anything over about 25 mm is a line. A line gets a
  defined impedance and a termination: a series resistor at a point-to-point source
  (22-33 Ω, so that it plus the driver's own impedance equals Z0), parallel or Thevenin
  at the end of a multidrop bus, or on-die termination where the chip has it.
- **Impedance comes from the fab, not from a formula.** Use the stack-up's thicknesses
  and Dk and the fab's own calculator (JLCPCB's), and order impedance control. Targets:
  50 Ω single-ended; differential 90 Ω for USB, 100 Ω for Ethernet, LVDS, HDMI, MIPI and
  SATA, 85 Ω for PCIe (100 Ω tolerated).
- **The return current runs in the plane directly under the trace.** So:
  - never route a fast line across a split, slot or void in its reference plane, and keep
    it a few widths in from the plane's edge;
  - every layer change of a fast signal gets a ground via within about 1 mm (two for a
    differential pair, one each side);
  - where the reference changes between a ground and a power plane, put a stitching
    capacitor beside the via.
- **Differential pairs:** routed together at constant spacing, on one layer where
  possible. Match the two lines within a few picoseconds (about 0.1-0.15 mm) at multi-
  Gb/s, compensating near where the mismatch arises (at the bend), not at the far end.
  Serpentine gaps at least 3-4 trace widths, so the meander does not couple to itself.
- **Groups:** match delays (per layer, not just lengths) to the interface's timing
  budget: DDR data and mask to their strobe within the byte lane, address and command
  to the clock, a parallel ADC bus to its clock.
- **DDR3/DDR4:** fly-by topology for address, command, control and clock, with VTT
  termination at the far end; data point to point; byte lanes over a solid reference.
  Swap bits within a lane, and lanes within the bus, only where the controller allows
  it. The controller's guide is the rulebook.
- **Crosstalk:** long parallel runs at least 3 widths apart, centre to centre; keep
  aggressor-victim parallel lengths short; stripline for long buses (its far-end
  crosstalk is nearly zero).
- **Vias at multi-Gb/s:** an unused via stub is a quarter-wave resonator at
  c / (4·L·√εr): about 26 GHz for a 1.4 mm stub in FR4, harmless below 10 Gb/s on a
  1.6 mm board, harmful on thick ones (12 GHz for 3 mm). Use layer pairs that use the
  whole barrel, back-drill, or use blind vias. Size anti-pads for impedance and remove
  unused inner pads.
- **Wide pads** (AC-coupling capacitors, connector pads) drop the impedance: void the
  reference plane under them.
- **Fibre weave:** at 5-10 Gb/s and up, one line of a pair over glass and the other
  over resin skews the pair. Route at about 10° to the weave, or ask for spread glass
  (1067/1078/2116 rather than 7628 or 106).
- **Power integrity:** keep the supply's impedance below Z_target = ΔV allowed / ΔI step
  from DC up to the edge rate: the regulator at low frequency, bulk and MLCCs in the
  middle, the capacitance of an adjacent power/ground plane pair (thin dielectric) and
  the package above that. An MLCC is limited by its mounted inductance: vias at the pad
  ends or in the pad, short and wide, two per end for large parts, the smallest packages
  nearest the pins. Mixed values anti-resonate; check the combined impedance (the FPGA
  vendor's PDN tool) rather than adding values by habit.
- **Clocks:** inner layers between planes, away from board edges and connectors,
  series-terminated at the source, one load per output (or a fan-out buffer), nothing
  routed under a crystal or oscillator, a ground guard round the crystal. Clock jitter
  caps an ADC's SNR at −20·log10(2π·f_in·t_jitter).
- **Simultaneous switching:** spread a wide bus over banks with enough ground pins, and
  terminate it.
- **EMC:** every cable is an antenna.
  - Keep fast lines away from connectors and board edges, and filter whatever leaves the
    board at its connector.
  - Stitch the edges of ground pours with vias at λ/20 of the highest frequency of
    concern (in FR4, about 3 mm at 2.4 GHz).
  - Plane-pair cavities resonate from c / (2·√εr·length) up: about 720 MHz on a 100 mm
    board. Stitching and decoupling along the edges damp them.
  - The "20H rule" (pulling a power plane back from the edge) shows little measured
    benefit on ordinary stack-ups; do not count on it.
- **Simulate the risky nets:** IBIS models of the drivers, a 2D solver for the
  cross-section, and openEMS (installed: `~/.local/bin/em-env`) for vias, launches and
  transitions, as in SyzygyRadioDrivers' `SMABridgeTestAnalysis/FIELD_SOLVER.md`.

## 14. RF

Also for boards to come, from the vendors' reference designs, Rosenberg, and the
SyzygyRadioDrivers field-solver study.

- **Copy the radio vendor's reference layout exactly**, as GPiBridge copied the RP2350's
  regulator: the same kind of stack-up, the same 50 Ω line, the matching network beside
  the chip, the ground vias under and round it.
- **Lines:** grounded coplanar waveguide (CPWG) on L1 over a solid L2, a fence of ground
  vias on both sides at no more than λ/10 in the dielectric (1-1.5 mm in practice below
  6 GHz), the gap constant, no right-angle corners at multi-GHz (mitre or curve them).
  Match pad widths to the line, or void the plane under wide pads (U.FL, SMA, 0603). At
  one SMA launch, SyzygyRadioDrivers measured 70 % of the power reflected and got back
  to 20 % with four changes that cost nothing to fabricate.
- **Always leave a tuning network and a test port:** a pi (shunt-series-shunt) footprint
  set between radio and antenna, fitted 0 Ω and DNP at first, and a U.FL or a switch
  connector (Murata MM8030) to measure S11 and conducted power. Tune it on the bench with
  a NanoVNA.
- **Parts:** C0G capacitors, high-Q wire-wound or thin-film inductors (Murata LQW/LQP),
  self-resonances well above the band, and the makers' S-parameter models in the
  simulation (Rosenberg).
- **Antennas:**
  - A chip or PCB antenna sits at a board edge or corner, with every layer cleared to
    the vendor's keep-out, and the ground plane size the vendor assumed: the ground is
    half the antenna.
  - No metal near it: batteries, screws, shields, cables.
  - A plastic case or a hand pulls the resonance down a few percent (εr 2-3). Design a
    little high and tune down.
  - A custom antenna is simulated with the real stack-up, the board's ground plane and
    the enclosure (openEMS; NEC2 for wire antennas), then measured. FR4's Dk (4.2-4.7)
    and loss tangent (about 0.02) vary from lot to lot.
- **Ground:** many vias in an RF chip's exposed pad and along every RF line; no floating
  copper (Rosenberg: islands resonate); no slots; shield-can footprints round RF
  sections where the budget allows (the assembler places a frame; the lid goes on
  later).
- **Isolation:** the PA away from the LNA and the crystal; RF supplies through LC or
  ferrite-plus-capacitor filters (read the bead's impedance at its DC current, and damp
  the bead-capacitor resonance); regulators with PSRR at the frequencies that matter.
- **Crystals:** the radio's ppm budget sets the crystal (Espressif asks for 40 MHz
  ±10 ppm). Load capacitors from C_L = C1·C2/(C1+C2) + C_stray, with 2-5 pF of stray.
  Close to the chip, guarded, nothing routed under it.
- **Harmonics:** keep the vendor's low-pass at the PA output, and look at the harmonics
  with a spectrum analyser.
- **The decision SNR of a zero-IF arm is P / (kTF B), B its baseband noise bandwidth.**
  The I noise is the RF noise of both sidebands, 2B wide, so a sign comparator errs with
  probability Q(√snr), not the textbook Q(√(2 Eb/N0)) with Eb/N0 = snr. CostasLink's
  rates script used the textbook form, and every coherent range was 3 dB optimistic. An
  RF-level simulation (carrier, white noise, ideal mixer, brick-wall B) settles it in ten
  lines.
- **A link that idles counts false events per hour, not errors per decision.** Noise
  carries the idle point over a threshold u σ away at Rice's rate, ν0·exp(−u²/2), with
  ν0 ≈ the filter's corner. For one false event an hour at 100 MHz, u = 7.3. A wrong
  message needs only about 3.7 σ, for 1e-4 of the messages sent. Set the idle-side
  threshold from the idle, 7.3 σ out, not halfway to the message. The FPGA finds that
  place by counting each comparator's false events (CFAR, as radar does).
- **For latency, a decision boundary should pass through the idle point, not the
  origin.** The filtered signal moves from the idle point to the message in a straight
  line. A boundary through the idle point, or a threshold set from it, is crossed at a
  fraction of the rise that falls as the SNR rises. A line through the origin (sign(I),
  a phase comparator) is crossed at a fixed fraction whatever the SNR: half the rise for
  a 180° flip. CostasLink's search is `sim/constellations.py`.
- **No receiver decides sooner than t ≥ z²·N0 / P**: the received energy must clear the false-alarm
  threshold z ≈ 7.5 σ (a sequential test at best).  CostasLink's board alone gives 85 ps at the
  bench but 3.1 ns at 3 km; a +20 dB PA makes that 31 ps.  At range, transmitter power is a
  latency knob before bandwidth, and widening the bandwidth speeds a noise-set threshold crossing
  only as 1/√B.  And before buying speed in the radio, find where the time goes: in a responder the
  clocked FPGA path dominates (rev A's decoder ~59 of ~71 ns), and a CML path outside the FPGA is the
  big step (PLAN.md section 19, `sim/latency_roadmap.py`).
- **In a latency link, selectivity costs delay at both ends: about order/(2π·f_c) each.**  To
  slot CostasLink into a WiFi channel, a 4th-order filter at both ends adds ~17 ns for 80 MHz and
  ~33 ns for 40 MHz.  That turns a 2.4 ns path into 20-36 ns.  A one-pole "channel" is cheap but
  rejects the neighbour by only ~7.5 dB.  Get interference immunity from what costs no time:
  directional antennas, the channel choice, gating the receiver to when an event can come, and a
  decoder that wants a settled vector.  Put the idle carrier on the interferer's spectral nulls
  rather than narrowing (PLAN.md section 19, `sim/wifi_channels.py`).
- **Budget the whole chain before buying radio nanoseconds.**
  - In CostasLink's QPV prover, the Pockels driver and cell (25-55 ns) and the photon detector
    (10-60 ns) dwarf a well-made radio path (~25 ns).  The responder's antenna cables count (3.9 ns/m
    each way; 10 m is 78 ns).
  - So the radio should be robust (decide on the first edge, veto with a slower, more sensitive path,
    answer "invalid"), not heroic.
  - Links between trusted nodes need precision, not latency.  A herald can wait in a fibre coil:
    1 km is 4.9 µs for ~0.2 dB.
  - (docs/SYSTEM.md, `sim/system_budget.py`.)
- **An ESD / DC shunt on a microwave line must stay inductive across the band.**  Use a wirewound part
  whose self-resonance is above the band (CostasLink: LQW15AN6N8, 6.8 nH, ≥ 6.0 GHz, 400 Ω-1.5 kΩ across
  4.9-6 GHz, ~0.05 dB).  A multilayer 0402 of the same value (LQG15HS: 3.4-4.5 GHz) is capacitive there.
  - Put it on the jack's side of the DC block, so it drains the cable's static.
  - Anchor it by hand on the line.  A rule placer stood it 4 mm off, a stub that would detune the line
    once fitted.  Keep any stub under ~0.05 of a wavelength.
- **A late block can break the board somewhere else.**  Adding CostasLink's detectors moved the router's
  power tracks beside a regulator 60 mm away and cut its ground pin's pour off.  Re-run the whole DRC
  after any addition, and try a few route seeds side by side rather than nudging parts.
- **A coherent receiver's "RSSI" from an averaging ADC works only when locked.**  On a zero-IF arm,
  unlocked noise and interference average to zero, whatever their power.  If the receiver must ever
  measure the band it is not locked to (an interference survey, a channel choice), give it a detector
  (an RMS or log detector after the channel filter, not a broadband RF one at the input).  Or use what
  CostasLink rev A had to fall back on: window comparators with DAC thresholds and a counter.  Duty
  against threshold is the amplitude distribution, and its probit line gives σ (PLAN.md section 19,
  `survey()`).
- **A transceiver (SERDES) buys throughput and timing resolution, not latency.**  It works in
  words.  Even raw, with its buffers bypassed, a decision waits ~6-10 word clocks (≈ 15-25 ns at
  25 Gb/s, est).  Its CDR wants a running, balanced stream, and 100G Ethernet's RS-FEC adds hundreds
  of ns.  An RFSoC's converters are 90-117 ns from DAC to ADC (QICK).  The fast path is a
  combinational LVDS or CML path; the transceiver is the time-stamper and the verifier's waveform
  source.
- **In free-space optics, pointing is a latency knob, and the terminal's length is latency.**
  - Étendue fixes the detector: d = θ·D/NA.  A photodiode's bandwidth falls with its area, roughly
    10 GHz × (40 µm/d)^1.6.  A steadier beam (a fast steering mirror) permits a smaller, faster
    detector.
  - A refractor's 0.55 m from objective to focus is 1.8 ns each way, more than all the fast
    electronics.  Give the fast path short dedicated apertures.
  - A metre of fibre is 4.9 ns.
  - Never amplify after the modulation with an EDFA: its 5-30 m of doped fibre is 25-150 ns.
    Amplify the CW light before the modulator, or use an SOA.
  - A 1 mm plastic fibre at a 550 mm focus throws a 1.8 mrad beam, which closes only ~100 m
    (PLAN.md section 19, `sim/optics_roadmap.py`).
- **A link's rise time is the transmitter's and the receiver's together.**  CostasLink's
  94 MHz receiver arm rises in 3.9 ns, but the PYNQ's 200 Ω header resistors into about 10 pF
  add 4.4 ns at the transmitter's ladder: 6.6 ns end to end, as if the link were 53 MHz wide
  (`sim/trajectories.py`).  Budget the transmitting pins' RC with the arm, and simulate the jump
  from the idle with every pole in it before choosing thresholds and decision delays.
- **Read the gain block's P1dB at the operating frequency, for the largest constellation
  point.** The ADL5611's P1dB is 21 dBm at 900 MHz and 12.8 dBm at 5.8 GHz. That is
  where CostasLink's corner points land when the axis point is 9.8 dBm.
- **Regulatory (US):** a certified module keeps its FCC ID only with its own or its
  listed antennas. A bare-chip radio with a custom antenna is uncertified: FCC §15.23
  lets a hobbyist build up to five, not from a kit and not for sale, for personal use. A
  board that radiates says this in its README.

- **RF grounds join the pour solidly: no thermal reliefs on the top or the inner layers** (CostasLink,
  Prompt 32, from Annika's SyzygyRadioBoard checklist).  A relief's four 0.25 mm spokes are inductors at
  5.8 GHz; a balun's ground pad, an ESD shunt, a 49.9 ohm load or an SMA's leg through them is not grounded
  at RF.  Set the zone's pad connection to solid (gen/routing.zone connect="solid"); give the one
  hand-soldered part its own thermal setting on its pads (zone_connect 1) and leave the back fill thermal.
  Reflow does not need reliefs.
- **The stock SMA footprint is wrong for a launch above a GHz, and it has bitten twice**
  (SyzygyRadioDrivers' first test board: 70 % of the power reflected, found on the bench with a VNA;
  CostasLink build 36: 85 % in the gerbers, 8 dB at each of five jacks, found by a gerber parser one
  commit before an order of about $1,000 of boards).  What the vendor's and KiCad's default pad does:
  the through-hole pad carries its full ring on every layer (`remove_unused_layers no`), a 2 mm disc
  0.2 mm above the ground plane and a flange at every inner layer; the planes come up to the barrel at
  the zone's clearance (0.25-0.9 mm); the top pour hugs the pad at the line's CPWG gap; and DRC never
  says a word, because each of those is "correct".  Together they are 2 pF across a 50 Ω line at
  5.8 GHz.  **Standard practice for every through-hole RF launch, on every board from now on:**
  1. the signal pad on the end layers only (`remove_unused_layers yes` + `keep_end_layers yes`),
     confirmed in the plotted inner layers, not in the footprint file (KiCad 9 and 10 rewrite an
     explicit layer list);
  2. an antipad on every inner and back layer drawn as a rule area without copper fill, in the
     generator (CostasLink: radius 2.2 mm on a 1.6 mm 4-layer board; the study: 4.0-4.6 mm across on
     its 6-layer): never a DRC `hole_clearance` rule (a wrong property name in its condition matches
     nothing, silently) and never the pad's own clearance property (it binds every layer, every
     connector with that footprint and every track, and the generator's router does not know it);
  3. the top pour the solved distance off the pad (0.9 mm on both boards), as a rule area on the top
     layer too;
  4. a plain round pad of the vendor's diameter, symmetric under rotation: no taper (the study's
     "1.0 mm taper" was hidden inside its pad disc; CostasLink's real 1 mm taper from the pad's edge
     moved S11 by 0.03 dB) and no smaller pad for an annulus under 0.3 mm;
  5. nothing else inside the legs on any layer: a router keep-out over the connector's body (the
     LNA's supply track once circled J101's pin inside the legs to get across the line);
  6. the field solve re-run on the actual stack and connector with the study's model, anchor first,
     the result and the gerber distances written up (`docs/LAUNCH.md`);
  7. the gerber parser as a release gate (§10, item 22).
  The two notes below are the details of how this was learned.
- **Check the RF launches in the plotted gerbers, not in the board's settings** (CostasLink, Prompt 33).
  A DRC rule meant to hold the planes 1.35 mm off an SMA's pin never matched (a wrong property name),
  DRC said nothing, and the gerbers had a 1.8 mm antipad where the design said 4 mm; the top pad sat
  over the ground plane at 0.21 mm.  Draw the antipads and the ground relief under RF pads as rule
  areas in the generator (explicit copper, whatever the DRC engine thinks), and gate the release on a
  parser of the copper gerbers (`tools/launch_check.py`: no pad flash at the pin on the inner layers,
  the planes the designed radius off it, the plane under each relieved pad clear).  Jason, from the
  SyzygyRadioBoard study: the KiCad defaults for a connector's through-board transition are not right.
- **A new stack or a new connector means the launch study is run again, not copied** (CostasLink,
  Prompt 33).  The SyzygyRadioDrivers field solve (`SMABridgeTestAnalysis/fieldsolver/launch_model.py`,
  validated on the V1 and V3 test boards) is parametric; `CostasLink-PYNQ-Z2/sim/launch/launch_cl.py` is
  the same model with the 4-layer stack and the BWSMA-KWE-Z001 substituted.  Order of work: reproduce one
  of the study's cached points with its own code on the machine at hand (the anchor: S11 and IL to three
  figures), run the study's rasterised-metal check on every new geometry, then sweep the knobs that the
  study showed matter (inner antipad, pad diameter, taper, pad clearance to the top pour, B.Cu clearance)
  and read the optimum off the sweep.  Twelve to twenty solves of 1-2 M cells, six at a time, in one to two
  hours on 32 cores (`em-env`).  Jason: "I'd rather spend design time and simulation time here to get it
  right."
- **Trace every path by hand before an order** (CostasLink, Prompt 32; `docs/PATHS.md` is the pattern):
  hop by hop from each jack or pin through every series and shunt part to the next IC pin, with the DC on
  the node, the level, the coupling, and a second table of every port's impedance, operating range and
  absolute maximum against what the circuit presents.  A netlist walker (`tools/path_walk.py`) supplies
  the hops so nothing is from memory.  Walking the paths this way is what found the ADC filters drawn
  capacitor-first and the balun with no blocks (Prompt 31), which five reviewers reading the sheets had
  missed.

### Simulate the circuit the copper makes (a design step and a review step)

CostasLink rev A's receive chain had controlled-impedance lines everywhere:
- 0.29 mm CPWG;
- the 0.25 mm gap held along every millimetre;
- solid ground under all of it;
- a via fence.

It still lost about 30 dB at 5.8 GHz (bench, 2026-10-29). Two layout faults caused it:
- **the parts on the lines were not where the vendor's circuit puts them;**
- **the bias chokes fed a supply plane that both chains share.**

The checks the board passed could not see either fault, because none of them asks what circuit the copper makes:
- DRC and ERC;
- the net check and the detour check;
- the field-solved launches and the gerber parser;
- five design reviews.

A rough simulation of the as-laid circuit shows both faults in an afternoon. Jason: "Even if the simulation doesn't match exactly, it helps to know if it's going to roughly (and certainly qualitatively) work."

**Do it for every path that carries a frequency where a millimetre matters:** above about 500 MHz, or wherever λ/50 in the dielectric is under 2 mm. Do it before the order, then rerun it in the design review from the written board.

1. **Cut the paths at their ports.**
   - **What a port is:** every jack and every IC pin on the path.
   - **Representing an IC:** its vendor's S-parameters, or the datasheet's S11 and S22. For a part matched by external parts, use the admittance that the vendor's matching network assumes (CostasLink: Y = 1/50 − jωC_match).
   - **Scope:** the simulation does not need to go through the ICs, only between them: jack to pin, pin to pin, pin to jack.
2. **Extract from the written board, not the schematic.** Read the `.kicad_pcb` (CostasLink `bringup/layout/rfgeo.py`: tracks, arcs, vias, pads, zone fills).
   - **Each track segment of each RF net:** its width, length and layer.
   - **Each junction:** a branch is a stub. Record its length and what hangs on its end.
   - **Each pad:** a shunt capacitance to the plane under it, or the relief and what lies below that.
   - **Each via:** its inductance and the layers it spans. About 0.1 nH to a plane 0.2 mm down; about 1 nH through a 1.3 mm core.
   - **Each part:** between its own pads.
   - **Each part's ground return:** its pad, the track or pour to its via, and the via.
3. **Model every element.**
   - **Lines:** transmission lines, with Z0 and εeff from the stack's formula for each width and gap (`sim/rf_lines.py`).
   - **Parts:** the makers' Touchstone files where they exist (Murata, Coilcraft and the IC vendors publish them).
   - **Capacitors without a file:** C with its mounted ESL (0402: about 0.3 nH) and ESR.
   - **Inductors without a file:** L with its Q and its self-resonance, C_p = 1/((2π·f_SRF)²·L), taken from the datasheet's SRF. Above f_SRF the part is a capacitor.
   - **Ground returns:** series inductance. A 0.2 mm track over a 0.2 mm dielectric is about 0.3 nH/mm; a 0.4 mm track about 0.25 nH/mm.
4. **Simulate the reference beside it.** This is the vendor's circuit with the same parts placed at the pins: no lines and a via-in-pad ground. The difference between the two is what the layout costs.
   - **Anchor the model first where you can.** The vendor's evaluation circuit should give the datasheet's gain within a few dB, as the launch study anchors on its cached point.
5. **Sweep what is uncertain:**
   - ESL 0.2-0.5 nH;
   - each ground return ×0.5 to ×2;
   - εr 4.2-4.7.

   If the result flips inside that range (for example, a resonance wanders into the band), change the layout. Do not tune the model.
6. **Pass criteria,** across the band and 20 % either side:
   - the as-laid path within 1 dB of the reference;
   - no dip or peak of 3 dB that the reference does not have;
   - each IC port's return loss what the vendor assumed.

   Write a table and a plot per path into the design notes, so a reviewer can rerun them.
7. **Run the same simulation on the power and ground paths.**
   - **Supply pins:** each RF IC's supply pin, through its tracks, inductor and capacitors to their ground vias. Compare the impedance the pin sees across the band with the reference circuit's.
   - **Bias tees:** model each choke from its maker's file, and look at what sits on its cold end. Above its SRF the choke is a capacitor of a few hundred ohms, so RF reaches the cold end.
   - **Ferrite beads:** each bead at its DC current, with the capacitors after it. Find the bead-capacitor resonance and its damping.
   - **Plane islands:** treat each island as a cavity. List its modes, f_mn = c/(2√εr)·√((m/a)² + (n/b)²) from its size. List which chokes, relief windows and vias tap it.
   - **Coupling between chains:** from all of the above, the coupling from each transmitter or amplifier output to each receiver input through the rails, in dB. Compare it with what the receiver must reject.
8. **Tools.**
   - **The circuit:** plain ABCD cascades in numpy (`bringup/layout/lna_input_model.py`, 80 lines), or scikit-rf with the Touchstone files. Qucs-S, or ngspice's transmission-line elements, for an AC sweep.
   - **3D discontinuities only** (launches, wide pads, a via transition): openEMS. Its results go into the circuit as S-parameter blocks.
   - **The geometry:** `bringup/layout/layout_survey.py` reads the board file for everything gates 26-32 measure.

The faults this simulation, and the gates that measure their causes, should have caught on CostasLink rev A:

- **A part in a matching network sits on the pin's own pad, or on the line at the pin, never on a branch.**
  - **Phase length:** at 5.8 GHz on JLC04161H-7628, 1 mm of 50 Ω CPWG is 12°.
  - **What rev A did:** the LNA's 0.5 pF input shunt (Skyworks: "a shunt capacitor match at the RF input port") sat 4.0 mm of track from RF_IN, about 50°. It was at the end of a 1.8 mm branch of 0.2 mm track.
  - **Why it failed:** the branch's ~0.6 nH, the capacitor's 0.3 nH and its ground's ~0.5 nH series-resonate with 0.5 pF near 5.9 GHz. That is a short across the input.
  - **Result:** the model loses 25 dB at 5.8 GHz; the bench lost 20-30 (`CostasLink-PYNQ-Z2/bringup/REVB.md` row 8).
  - **The rule:** the track from the part to the pin under λ/50 at the top frequency (0.5 mm here), on no branch.
  - **Background:** this is "Copy the radio vendor's reference layout exactly", above, made measurable. Skyworks says of its LNAs that "the most sensitive regions are the input match and the RF decoupling regions", and adds multiple vias on its evaluation boards to cut their parasitic inductance (Microwave Journal, "Two-Stage Ultra Low Noise Amplifiers", SKY65048/49/66).
- **A shunt part's ground return is part of its value.**
  - **The rule:** every RF shunt part (match, ESD choke, load, bypass) gets a via in, or touching, its ground pad, to the plane right under it.
  - **Model it:** count the return's inductance in the simulation.
  - **Rev A:** its parts reached ground through the pour to vias 0.7-0.8 mm away. The LNA's exposed pad had one via.
- **An RF IC's supply pin sees an inductance the vendor chose.**
  - **The reference:** the SKY65404 has 0.6 nH from VCC to its 100 nF.
  - **Rev A:** 1.6 mm of 0.2 mm track before the inductor and 2.3 mm of 0.4 mm track after it, about 2 nH in all.
  - **The rule:** put the inductor on the pin and the capacitor on the inductor's far pad, with a via in its ground pad. Count the tracks' inductance.
- **A bias choke's cold end gets its RF bypass on its own pad, before any via to a plane.**
  - **The parts:** rev A's three ADL5611 chokes are LQW18AN43NG00D, self-resonant at 2.7 GHz or above (Murata). At 5.8 GHz each is a capacitor of about 340 Ω.
  - **What happened:** each went to a +5V_RF via 0.8 mm from its cold pad, with no capacitor within 5.4-13.6 mm. The 68 pF the schematic drew "beside" the receive chokes was placed 36 mm away.
  - **The risk:** RF on the plane can reach the other chain. On rev A it did not, measurably (the next bullet), but only because of the stack.
  - **The rule:** on the cold pad, via in pad, put a capacitor that is series-resonant near the band (a few pF in 0402) and a 68-100 pF. Then a ferrite or a resistor to the rail.
- **One supply island per RF chain, and ground under the RF lines.**
  - **Rev A's plane:** +5V_RF was one 86 x 44 mm island under both chains. Every choke and every relief window under an ADL5611 pad opened onto it.
  - **What the bench found:** a transmitter leak entering the receiver after its step attenuator, at -53 dBm at RX MON. It capped the attenuator's range at 23 dB and swamped the chain above 5.86 GHz (REVB row 10).
  - **Model the plane before blaming it.** The shared island was the first suspect, but the as-laid simulation cleared it.
    - **Why:** the island sits 0.21 mm over the bottom layer's ground pour. That thin cavity is a low-impedance plane pair, about 1 Ω between the chokes' vias.
    - **The numbers:** the choke-to-plane-to-choke path models 20-40 dB under the measured leak, with the wrong shape against frequency (`CostasLink-PYNQ-Z2/sim/aslaid/REPORT.md`).
    - **The lesson:** the cavity that matters is the one each island forms with its nearest ground, which may not be the plane named in the stack-up. Simulate it (§14 step 7) before calling it the path.
  - **The rule still stands:** separate islands for transmit and receive, each through its own ferrite and capacitors. A stack with the supply far from any ground would have made rev A's plane a real path. The layer under a relief window is ground, not a supply.
- **The as-laid simulation's own lessons** (CostasLink rev A, `sim/aslaid/REPORT.md`):
  - **Count the pads' capacitance on a thin dielectric.** An 0402 pad 0.21 mm over its plane is about 0.08 pF. Eight DC blocks, the shunts and the tees on rev A's receive chain cost about 2 dB at 5.8 GHz and 8 dB at 5.0, through gain blocks with a poor match. Void the plane under RF passives' pads, or use 0201 parts and fewer series parts.
  - **Take a CPWG's width from a field solver, not a closed form.** Rev A's lines are 53.7 Ω by a 2D finite-difference solve, where the closed form gave 49.8. Its couplers' quarter wave came out at 5.97 GHz, not 5.8, because the even and odd modes' εeff (3.20 / 2.73) were never computed.
  - **Find where a vendor's S-parameters are referenced.** A gain block's table is often measured at its evaluation board's SMAs, launches and lines included. It is not the pins.
  - **Fit at most one parameter, and say which.** Rev A's model matched the bench after one fit (C102's ground return, 0.14 nH extracted, 0.59 nH fitted). A model with several free parasitics fits anything and predicts nothing.
- **Stitch the pours.**
  - **Near RF:** every point within λ/20 of a ground via, which is a via grid at λ/10 (2.5 mm at 5.8 GHz in FR4).
  - **Everywhere else:** within λ/6, so that no via-free patch reaches the half wave that resonates.
  - **Rev A:** its fences ran along the lines only. 43 % of the top pour round the receive chain was more than 2.5 mm from a ground via, up to 8.6 mm. Elsewhere on the board it reached 20.7 mm.
- **The isolation budget is a design number.**
  - **Before the order:** estimate each path from a transmitter to a receiver: rails, plane cavities, layout coupling. Write the leak beside the weakest signal the receiver must resolve and beside its attenuator's range.
  - **On the bench:** measure it first (§9).
- **RF matching, decoupling and bias parts are anchored by hand to the pad they serve, and the build measures the distance.**
  - **What the rule placer does (§5):** it hangs a rail's capacitor on "the chip the schematic drew it beside", at the pin's fan band (3-8 mm). If the sheet's nearest chip on that rail is another one, the capacitor goes tens of mm away.
  - **Rev A:** its design reviews flagged this ("no decoupling within 2.5 mm of any RF chip's supply pin", REVA_CHANGES 35), and it was sent to the bench as "to confirm".
  - **The rule:** a review finding about where an RF part sits is a layout change before the order, not a bench item.
- **Leave rework room on rev A.**
  - **Why:** rev A's faults can be tested on the bench only because the parts are reachable: lift C102; bodge a capacitor onto a choke's cold pad.
  - **The rule:** give each RF IC pin a DNP 0402 shunt pad on its own pad, and each choke's cold end a capacitor pad. Then the bench can try what the simulation suggests.

## 15. Power, current and magnetics

The Halloween board (2026-10-07) is the first of Jason's boards with real power: a 12 V
brick and amperes into PCB coils. Until it has been built, these are rules from the
standards and app notes, with the arithmetic checked.

- **Width for current** (IPC-2221): I = k · ΔT^0.44 · A^0.725, with A in mil², ΔT in
  °C, k = 0.048 for outer layers and 0.024 for inner. For a 10 °C rise in 1 oz outer
  copper: 1 A needs 0.30 mm, 2 A 0.78 mm, 3 A 1.37 mm, 5 A 2.77 mm; 2 oz halves those.
  Inner layers need about 2.6 times the area (3 A in 1 oz inner: 3.6 mm), and JLCPCB's
  inner layers are 0.5 oz unless ordered thicker. IPC-2152, which replaced 2221's
  charts, allows more on boards with planes; 2221 is the safe side. Compute it per net
  in the build and fail on a narrower track (§10, gates 11 and 16).
- **A linear driver into a stalled motor dissipates most at half the rail, below any
  fuse.**  The pass transistor takes (Vcc − V)·V/R, at most Vcc²/4R at V = Vcc/2: 3.7 W
  from ±15 V into the PID board's 14 Ω motor, at 0.49 A, while the 0.35 A PTC sized for
  the full-drive stall (0.63 A) holds and 0.14 A at 2 V already makes 1.8 W.  A smaller
  fuse cannot help when the motor needs 0.15 A just to move.  Size the heatsink for
  Vcc²/4R (a DPAK on a small pour is ~70 °C/W: 2 W is too much), or give the transistor a
  real heatsink, before trusting a fuse.  Sweep the stall over DRIVE in the simulation.
- **Check the heatsink on the board as built, in the build.**  Export each pour as KiCad
  filled it and the ground plane's fill (with the cuts the back runs make), solve two copper
  sheets with FR4 between on a 0.5 mm grid, and fail above a junction limit (PID board:
  125 °C, leaving 25 °C under 150 for the model's error).  Calibrate the model on one data
  sheet figure (TI: DDPAK on 1 in² of 1 oz, 26 °C/W).  The as-built pours came out a few
  degrees worse than the rectangle the comparison assumed.  Keep back runs out from under
  a heat-spreading pour: the plane there is half the heatsink; send supplies up the edge.
- **2 oz copper changes the rules.**  JLCPCB's 2 oz track and gap minimum is 8 mil, so the
  board's 0.2 mm rules go to 0.21; the order form's "Outer Copper Weight" must say 2 oz
  (generated, with the reason); and KiCad's Python cannot set the stackup
  (`GetStackupDescriptor()` is a bare SwigPyObject), so write the `(stackup ...)` block into
  the saved file, or the gerber job file says 0.035 mm.
- **Drop and heat:** a square of copper is 0.98 mΩ at 0.5 oz, 0.49 mΩ at 1 oz and
  0.25 mΩ at 2 oz, rising 0.39 % per °C. 100 mm of 2 mm track in 1 oz is 50 squares,
  25 mΩ: 75 mV and 0.23 W at 3 A. Count the squares of every high-current path, its
  ground return included (Rosenberg).
- **Vias carry about 1 A each** (0.3 mm drill, for a 10 °C rise): use an array at every
  power layer change (at least four for 3 A), and thermal vias under hot parts.
- **Connectors:** check the rating of the exact part. Barrel jacks run from 1 A to 5 A
  and more; 2.54 mm headers about 3 A a pin; screw terminals by their datasheet.
- **Hot-plugging a supply on a cable rings.** The cable's inductance and an all-ceramic
  input make an LC that rings to about twice the supply at contact (Linear Technology
  AN88): 12 V becomes 24 V or more. Damp it with a bulk electrolytic or polymer capacitor
  (its ESR is the damping), and clamp with a TVS above the working voltage.
- **Protect the input:**
  - reverse polarity: a P-MOSFET with its gate pulled to ground through a resistor and
    clamped by a zener, or an ideal-diode controller (a series Schottky wastes
    0.4 V × I);
  - overcurrent: a fuse or PTC that opens below what the copper and the connector
    survive, or an eFuse, which also limits inrush;
  - a TVS. A 12 V, 5 A brick can make a dropped paper clip across two pads hot enough
    to burn a finger.
- **Inductive loads** (coils, motors, solenoids, relays) keep their current when
  switched off. Give each a freewheel path (an H-bridge's body diodes, or a diode across
  a low-side-switched coil). Expect regeneration: a decelerating motor or a collapsing
  coil returns energy through the bridge into the supply, and if the bulk capacitance
  (with a TVS or clamp) cannot absorb it, the rail rises and kills what hangs on it
  ("supply pumping").
- **Switching converters:** the datasheet's layout is the layout. Keep the hot loop
  (input capacitor, high-side and low-side switches) as small as possible, the switch
  node small (§5), the feedback trace away from the inductor and the switch node, and
  the controller's ground at a quiet point of the plane. Exposed pads get via arrays to
  the inner planes.
- **Current sensing:** a Kelvin (four-terminal) connection to the shunt, the two sense
  lines routed as a pair, an RC filter at the amplifier or ADC. A low-side shunt lifts
  the load's ground; a high-side one needs an amplifier with the common-mode range.
- **Gate drive:** a small gate loop (driver, gate, source, back), a gate resistor to set
  the edge and damp ringing, the bootstrap capacitor at the driver, dead time between
  the two switches of a half bridge.
- **PCB coils:**
  - Inductance of a planar spiral, from the current-sheet formula of Mohan et al. (IEEE
    JSSC, 1999): L = μ0·n²·d_avg·(c1/2)·(ln(c2/ρ) + c3·ρ + c4·ρ²), with d_avg =
    (d_out + d_in)/2 and ρ = (d_out − d_in)/(d_out + d_in); c = (1.00, 2.46, 0, 0.20)
    for a circle, (1.27, 2.07, 0.18, 0.13) for a square. Identical layers in series on a
    thin dielectric couple almost completely: four give nearly 16 times one layer's L.
    Check anything that matters with a field solver.
  - Resistance: count squares. The skin depth in copper is 66 µm / √(f in MHz): 210 µm
    at 100 kHz (35 µm copper is all used), 25 µm at 6.78 MHz (it is not), and the
    proximity effect between neighbouring turns adds more.
  - Q = ωL/R sets a resonant link's efficiency: at best
    η = k²Q1Q2 / (1 + √(1 + k²Q1Q2))², with k the coupling.
  - A coil is a heater: compute its temperature at its current, and limit duty in
    firmware.
  - Turn-to-turn and layer-to-layer capacitance set the self-resonance; stay well
    below it.
  - A coil is also a sensor: a magnet moving over it induces a voltage (Faraday). Size
    it before relying on it. By reciprocity the EMF is the coil's force per amp times
    the speed: about 3 mV for a 48-turn PCB coil under a pendulum bat (Halloween
    board), where a classic kicker's 1500-turn coil gives volts. A Hall sensor is
    usually the better position sensor; the back-EMF is a bonus.
  - **Void every plane under a coil, on every layer, with a margin.** A plane is a
    shorted turn: it cancels the coil's AC field (no wireless power through it),
    lowers the inductance, and brakes a magnet moving over it with eddy currents.
  - **A PCB coil's L/R is microseconds** (31.5 µH and 3.35 Ω is 9.4 µs on the
    Halloween board). Driven by an H-bridge at tens of kHz, its current follows the PWM
    square wave: amperes of ripple, and the heat that goes with it. Switch at hundreds
    of kHz, use 3-level PWM (ripple vanishes near zero mean current), or add series
    inductance.
- **Simulate a feedback loop with its sensor's noise and quantisation before trusting
  its gains.** The Halloween board's levitation loop held the bat at the first tuning,
  but with 0.6 A rms of chatter (1.4 W) from Hall-sensor noise through the derivative
  term. Averaging the ADC and a lower bandwidth took it to 20 mA rms (1 mW) with the
  same catch range (`halloween1/sim/physics/levitation_loop.py`).
- **Copper weight:** order 2 oz outer copper when a coil or power path needs the
  conductance. It costs extra and raises the fab's minimum track and gap for the whole
  board. Say so on the order, and in the release notes Jason pastes.
- **Mains stays off the board:** a certified (UL/ETL-listed) external adapter. A board
  that touches mains needs the creepage and clearance of a safety standard (IEC
  62368-1), which no board here has had.

- **Budget a rail in the board's worst state, not its working one** (GPSDO rev B,
  2026-10-10). A self-biased unbuffered LVC gate draws about 10-15 mA at its threshold
  (rev A measured 180 mA from 14 of them), not the 3 mA the sheet had assumed. Rev B
  biases a replica gate on every channel all the time. With nothing driven and nothing
  parked, all 26 gates sit at threshold: 290-420 mA on a 300 mA LDO. Put the measured
  number on the sheet, the instruction in the bring-up steps, and keep the input fuse
  sized for its fault job, not the current.
  - **Check which state the instruction actually produces.** The first version said "fit
    every shunt (50R or PARK) before the first power-up". A 50 Ω termination shunt does
    not quiet an AC-coupled, self-biased gate: with its source off, the gate still sits
    at threshold. Only PARK does. Writing the bring-up step by step, with the expected
    reading at each, is what caught it (2026-10-10, order day): "0.25-0.35 A with every
    channel parked" cannot be written for a board with eleven 50R shunts and no sources.

## 16. Boards for children

The Halloween board is for a six-year-old (2026-10-07).

- **Magnets:** two swallowed neodymium magnets can pinch through the intestine. The US
  toy rules (ASTM F963, through 16 CFR 1250; 16 CFR 1262 for other magnet products)
  target magnets that fit the small-parts cylinder (31.7 mm) and have a flux index of
  50 kG²·mm² or more, which is every useful NdFeB magnet (even a 2 × 1 mm N52 disc
  scores about 81). Encapsulate each one completely in a part too big for the cylinder:
  print it in (pause the print and drop it in) rather than glue it into a pocket. For
  ages 3-8 the part must keep it after soaking, drops, 4 in·lbf of torque, a 15 lbf
  pull and a 30 lbf squeeze (F963's use-and-abuse tests).
- **Small parts:** nothing that fits the small-parts cylinder may come loose. That
  includes the printed piece that holds a magnet: a snap-on cap of 25 × 13 × 6 mm with
  0.8 mm hooks is a small part with a hazardous magnet in it (OWL, Grok's review,
  2026-10-09); glue it to the board it sits on, or make it too big for the cylinder.
- **Bare metal a child is told to touch** (a theremin's gold antenna) is an ESD path
  straight into whatever gate it reaches: an ESD diode at the pad (a sub-picofarad one,
  so a capacitive sensor hardly notices) and a series resistor to the gate (OWL,
  2026-10-09). A hardware ceiling on the speaker (the amplifier's gain) keeps a toy
  under 85 dB whatever the firmware does; snapped mouse-bite edges get sanded before the
  board is handed over.
- **Violet and UV LEDs** (420 nm and below) are a blue-light hazard. Keep their radiant
  power low, diffuse them, point them away from eyes, prefer 400-410 nm to 365-395 nm,
  and read the datasheet's IEC 62471 risk group (the cheap ones give none). 395 nm
  looks dim, so the blink reflex does not protect; and 62471 rates exposure at 200 mm,
  where a child's eye at 2 cm gets about a hundred times more.
- **Heat:** anything a hand can reach stays below about 45 °C, coils and regulators
  included. Where the hardware could exceed it, a temperature sensor and the firmware
  enforce it.
- **Edges and finish:** rounded corners and no sharp tabs; a lead-free finish (ENIG or
  lead-free HASL) on a board that will be handled.
- **Power:** a certified wall adapter at a safe extra-low voltage (12 V), a fuse on the
  board, and nothing exposed where a dropped hairpin could short the supply.

## 17. Lessons from AMOD-P and AMOD-A (2026-10-25)

Tile boards: a 100 x 100 mm grid of 20 mm cells, every cell a circuit between two SMA jacks, the
silkscreen the schematic.  What the two boards taught, each a fault found by DRC or by the eye:

- **A pad table keyed by pad number loses pads.** A vertical SMA jack's four legs are all pad "2";
  a USB-C's four shell pads are all "SH".  Keyed by (ref, number) they collapse to one, and a router
  or a silk clipper that reads that table puts vias and silk on the three it cannot see.  Keep
  every pad in a list for obstacles and the (ref, number) map only for wire ends.
- **Get the geometry from KiCad, not from memory.** Dump every footprint's courtyard and pad
  bounding boxes with pcbnew (`FootprintLoad`, `GetCourtyard`, `GetBoundingBox`) before placing by
  hand; the SOT-23-5 pin-one triangle pokes 0.09 mm past its courtyard, the SOIC pads are 0.6 wide
  at 1.27 mm so nothing passes between them, the 0402 is the only passive whose body fits a 1.27 mm
  pin pitch.  Every hand placement that was budgeted against those numbers passed DRC first time;
  every one from recalled numbers did not.
- **The 20 mm cell has a budget, and a switch and a FET take a third of it.** A powered tile with a
  slide switch (MSK12C02, 9 x 4.5 mm courtyard) along its left edge and a SOT-23 FET at its foot
  leaves 14 x 9 mm under the jacks for the circuit: one SOT-23-5 op amp and six passives, or one
  SOIC-16 and six 0402s.  Anything bigger (a DIP switch beside a SOIC, a second op amp, a loop with
  a label) goes, and the plan must say so before the layout starts.
- **One hand-laid geometry per circuit kind, reused with an offset.** The non-inverting op-amp
  stage was laid once (`opa_tile`) and used by five tiles; a double tile uses it with x + 21.5.
  The hours go into the first instance; the rest are free and DRC-clean.
- **A SOIC across a cell: the pin rows face the jacks and the board's edge, the gap between the
  rows is the only corridor (3 mm: three 0.35 mm wires), and the ends of the rows are the only
  pins that can leave sideways.** Pins between other pins leave only outward.  NC pins are
  passages for a wire of the node next to them (declare them passive in the symbol so ERC
  agrees; the datasheet must say "no internal connection").
- **The silk needs 0.15 mm from everything, and a tile's frame line is 0.6 mm wide.** Right-justify
  names at the frame's inner edge minus 0.25; keep 0.5 mm above and 0.7 mm below an 0.8 mm text
  line; a tented via under a label is fine, an exposed pad is not.
- **Rails as pours on an inner layer, one polygon per rail.** Two zones of one net that overlap
  fail `zones_intersect`; two that only touch do not connect once each is inset by its minimum
  width.  Draw the rail as one polygon.  A strip of pour narrower than two via clearances is cut
  by the first via of another net that crosses it (the -5 V strip under the Pmod plug was): keep
  rail strips 1.5 mm wide and vias of other nets out of them.
- **A via with copper on one layer only is "dangling".** A back wire that T-joins another back
  wire must not end in a via; make it one polyline, or let it end on a pad.
- **"Pmod pin k is pad 2k-1" is true of KiCad's numbering only.**  KiCad's horizontal 2 x 6 header and socket put pad 1
  on the row FAR from the body; JLCPCB's drawings of the same parts (PZ254R-12-12P C492434, HC-PM254 C22373932) put pad 1
  at the other end of the row NEAR the body, so their pad p is KiCad's pad 13 - p.  AMOD-A and RF-MOD were laid with the
  KiCad rule on the JLCPCB footprint: every plug pin k met the host's pin 13 - k, IO lines on the host's ground and 3.3 V.
  Caught before the order by mating the two footprints on paper; fixed by moving the plug two columns and renaming the
  nets, and a fab check (`check_pmod`) now maps every plug pad to its standard pin.  For any keyed two-row connector,
  derive the pin from the pad's POSITION relative to the body, never from its number, and check both mating halves.
- **A 2 x 6 Pmod plug's lower row is reachable only through the upper row's 0.74 mm gaps**
  (0.2 mm tracks with 0.27 mm to spare) or along the bottom edge (two tracks fit between the pads
  and the 0.3 mm edge clearance).  Feed the upper row from the back, straight down; feed the lower
  row from the front.  Feeds come from one side, each above the feed of the pad to its right, so
  none cross.  A via that an F.Cu feed passes needs 0.625 mm from the feed's centre line.
- **Keep a corridor for the board's long lines before the tiles are laid.** The Pmod lines down
  the back of two tiles needed a 2.5 mm strip clear of sockets and jacks; it moved twice because
  the tiles had not reserved it.  Reserve it in the plan, in board coordinates, and tell every
  tile.
- **The generic schematic block** (a label on every pin, parts in rows) wants: adjacent same-net
  pins joined under one label, the passive rows spaced by the longest net name, the rows started
  under the tallest chip symbol, the notes shrunk when the drawing needs the room.  Its layout
  check (text boxes against each other) catches all of this before KiCad does.
- **KiCad's share ships no STEP file for some library footprints** (the WSON-8 DSG0008A, the HRO
  USB-C, the 1812 fuse).  The release check that every model resolves is right to fail; point
  those footprints at a stand-in body of the same name in the project's own 3dshapes.
- **JLCPCB's 0402 basics** (10 k C25744, 1 k C11702, 470 C25117, 1.5 k C25867, 100 n C1525,
  1 n C1523) and the 0603 10 ohm (C22859) and 1 uF (C15849) are the values that let a SOIC's
  pins have their resistors at the pin pitch; 51 ohm (C25125) and 3.9 k (C51721) are extended.

## 18. Lessons from RF-MOD and the Icepi Pmod adapter (2026-10-25)

- **A tile's RF rules belong in the generator, not in each tile.**  A wire of one width (0.29 mm on JLC04161H-7628)
  is a 50 ohm CPWG line: the generator gives it an "RF" net class (0.25 mm clearance), pours L1 ground round it at
  0.25 mm, fences it with ground vias (0.845 mm off its centre, every 1.0 mm, wherever a via fits clear of pads,
  tracks and other vias), and voids L2-L4 within 2.2 mm of every RF jack's centre pin (rule areas with fills
  forbidden).  The tile only says `t.rf(net, pts)`.
- **Two-port jacks in a checkerboard** (IN top-left, OUT bottom-right) keep a 20 mm grid's closest pair at 14.85 mm
  (one cell's diagonal; 15.2 across a gutter) instead of 10.5.  Decide it before the first tile: changing it later
  re-lays every tile (section 19).
- **A synthesizer loop filter for two bands at once:** the VCO's range is fixed (3-6 GHz on the MAX2871) and the
  output divider sits outside the loop, so each band sees the loop through Kvco / N at the VCO.  Search the stocked
  values with the open-loop model over the Kvco spread and every N in use, and keep the phase unwrapped (a margin of
  350 degrees is a wrapping bug, not a stable loop).
- **A 0.5 mm pitch QFN on a 0.2 mm board:** give the chip's own nets a fine net class (0.127 / 0.15 mm, 0.45 / 0.25
  vias; JLCPCB's four-layer floor is lower) and lower the board's floor to match; the rest of the board keeps 0.2.
  Fan the pins out at 45 degrees to 0402s on a 1.2 mm pitch, ground pins straight into the paddle, the paddle's
  vias first.
- **A stand-in VRML body is drawn in mm and VRML's unit is 2.54 mm:** substitute it with a scale of 1/2.54.  And
  copy a SWIG vector's numbers before the list that owns it goes away: `m.m_Scale` kept as a proxy wrote a scale of
  1486236861 into the board file.
- **A board that grows past its host is fine** when the host's holes stay put: the Icepi adapter grew 15 mm past the
  Icepi Zero's end for a right-angle Pmod socket, with the module above ending short of it.
- **Inner-layer lines between through-hole pads need no vias**: on a four-layer interposer whose outer layers are
  full, eight lines ran on In2 from header pin to socket pin, 0.2 mm wide through the 0.84 mm half-pitch gaps.  Lay
  them so the leftmost line turns lowest and the highest lane descends rightmost: no crossings, by construction.

## 19. Lessons from moving AMOD-P's and AMOD-A's jacks into the checkerboard (2026-10-25)

Twenty finished tiles were re-laid because their jacks stood 10.5 mm apart in rows; afterwards every pair on all
three boards was 14.85 mm or more.  What it taught:

- **The checkerboard leaves each cell two quarters, not a half.**  With jacks at the top-left and bottom-right
  (6.5 mm bodies, 7.1 mm courtyards) the circuit gets the top-right quarter (about 10.8 mm square) and the
  bottom-left one, which a powered tile's switch and FET mostly fill.  The signal runs on the anti-diagonal.  Plan
  every tile's parts against those two squares before choosing packages.
- **Choose the small package first, and look for it under every name.**  A SOIC-16 (10.5 mm courtyard) and a SOIC-8
  op amp did not fit beside both jacks; the TSSOP-16 and the SOT-23-6 did.  TI's TSSOP 4046 had 21 in stock, but
  Nexperia's automotive grade (74HC4046APW-Q100J) had 234: search the "-Q100" and other vendors' parts before giving
  up on a package.  Read the small package's pinout from the datasheet; the SOT-23-6 OPA847 moves the pins.
- **A long part between diagonal jacks stands at 45 degrees.**  An HC-49S crystal (11 mm courtyard) fits on the
  diagonal with the jacks 0.5 mm further out; a ceramic resonator likewise.  JLCPCB places any angle; say so in the
  assembler's notes so nobody "corrects" it.
- **Moving a jack moves what was behind it.**  The back's QR code, the board's long back wires (the Pmod lines), the
  gutter labels of the tiles above and below, and a neighbour's ground symbol all met the moved jacks.  Each was
  caught by a check (the QR-over-hole check, DRC's silk rules), so run the full build after every tile, not at the
  end.
- **Render one tile at a time while laying it out.**  `kicad-cli pcb export svg` of F.Cu, F.Silkscreen and
  F.Courtyard, cropped to the cell with Inkscape's `--export-area`, shows a tile at 35 px/mm in seconds; most
  mistakes are visible before DRC runs.

## 20. Lessons from AMOD-2 and RF-MOD-2 (2026-10-25)

Two second-level boards, twenty-one tiles, laid tile by tile in one session and taken to ERC 0, DRC 0 and every fab
check.  What they taught:

- **Never replace a string you have not proved non-empty.**  A scripted edit computed `old` as a slice that came out
  empty, and `s.replace("", new)` inserted `new` between every character of a 50 kB board module.  It was recovered
  by striding the corrupt text (`s[L::L+1]` with `L = len(new)`), but every scripted edit now asserts `old` is non-empty
  and occurs exactly once, and a scratchpad copy is taken before each one.
- **A tile's local net names share a namespace with its helpers'.**  The power header names its FET's gate `G`; a
  laser driver's own gate net, also `G`, merged with it.  The merge is legal, so ERC and the netlist check were silent;
  DRC found it only as one unconnected pad.  Give FET nodes distinctive names (`GQ`, `SQ`), and grep a helper's nets
  before reusing a short name.
- **Plan each tile's crossings before its coordinates.**  Write the nets that must meet (the tank node, the switch, the
  buffer input), find the planar order, then pick each part's rotation so its pins face where their nets arrive.  A
  SOT-23-5 op amp at rot 270 has +IN, V- and OUT along the top and -IN and V+ along the bottom; rot 0 puts OUT, V- and
  +IN down the left.  Most of the night's rework came from choosing a rotation first and discovering the crossing in DRC.
- **Hop a low-impedance or slow net, never a high-impedance node.**  An op amp's output, a DC bias, a 5 V feed and a
  Pmod line may run on the back between two vias; a resonator's node or a summing junction may not.  An output may
  travel the length of the tile to its jack; put the buffer by the node it reads.
- **Every back-layer polyline end is a via.**  A branch that ends on the middle of another back trace drops a via
  there, often under a front-side part.  Draw a branch as one polyline from via to via (overlapping a same-net segment
  is fine), never ending in mid-trace.
- **A board's fixed furniture must yield to its parts.**  The fiducials were hard-coded; one landed on a screw
  terminal in the corner margin.  `FIDUCIALS` (and `FEET`) are now per board; check them against every margin part,
  and keep a stick-on foot's 8 mm circle off any through-hole joint.
- **Weak capacitive ports beat buffers in a crowded tile.**  Two coupled LC tanks read through 2.2 pF into the host's
  50 ohm inputs (about -43 dB at 10 MHz) need no op amp, no bias and no power, and load the tanks less than a buffer's
  input would: the cavity's coupling antennas, on a board.
- **A DIP switch is for milliamps.**  Its contacts are rated tens of milliamps: switch a reference resistor or a
  coupling capacitor, never a current shunt.  Laid out at rot 90 its two rows become two columns: one side for the
  common node, the other for the switched parts.
- **A dual op amp in SOIC-8 rarely fits a cell's quarter; two SOT-23-5 singles usually do.**  The dual's eight pins on
  two sides force its four signal nets to cross; two singles can each face their own jack.
- **A single-cell tile's schematic block is small.**  A part-heavy tile (a 16-pin bridge driver, a buffer, two diodes,
  two terminals) left no room for four lines of notes; the overlap check failed until the notes were one line.  Put
  the long explanation in the docstring and the handbook.
- **Read the jack legs' real pad radius before threading a trace between them.**  The SMA legs are 1.1 mm in radius,
  more than the drawing suggests; a 0.35 mm line 1.2 mm from a leg's centre shorts to it.
- **Thin stock the user has accepted is a per-part exception, not a loosened rule.**  `stock_exception` on the part
  records who accepted it and when; the fab check prints it beside the stock instead of failing.

## 21. Lessons from relabelling the AMOD and RF-MOD silkscreens (2026-10-28)

Jason read the five boards' renders and could not tell what most tiles did or which jack was which.  What fixed it:

- **A label in the gutter between two boxes belongs to neither.**  The jack names sat centred in the 1.5 mm gutter
  above or below each jack, so "OUT A  REF IN  IF" under one tile read as that tile's when two of the three belonged
  to the tile below.  Put a jack's name ON its own tile's frame line, beside the jack, and break the frame round it
  (a legend in a fieldset): a name inside a frame's line reads as that frame's, and the neighbour's frame across the
  gutter stays unbroken.  Any tile text that sits on the frame breaks it the same way.  Clear the jack's legs: their
  pads reach 3.64 mm from its centre, so the name's box stops 0.22 mm short of that.
- **Say what a tile is in words, not by its chip.**  "QPL9547", "GALI-84+", "AD8318" mean nothing to a reader without
  the datasheet; "LNA QPL9547", "GAIN", "POWER METER" do.  The top frame line, right of the top-left jack's name, is the
  one strip every tile has free: put a short title there, slid left from the right end until it clears pads, bodies,
  drawn wires and the neighbours' names (0.8 mm along, 0.5 mm across the gutter).  Put the ranges and levels (RF
  0.4-2.5 GHz, LO 0 to +6 dBm, IF DC-200 MHz) inside the tile where they fit.
- **Place free text by search, not by coordinates.**  A raster of each tile at 0.1 mm (bytearray rows; `find(1, i0,
  i1)` tests a box in C) marked with every pad, courtyard, footprint silk item, drawn wire (with its half-width) and
  placed text, plus 0.22 mm; KiCad's own box for each text (`PCB_TEXT.GetBoundingBox()`); candidates sorted by
  distance from where the tile asks.  A block that does not fit drops its last lines with a warning, so the build
  says what the silk lost.  Tented vias are not obstacles.  KiCad's DRC (`silk_overlap`, `silk_over_copper`) is the
  check.  Of 56 tiles, about 15 had no room for their ranges; their titles and jack names fit.
- **Never print a document's section numbers on copper.**  The tiles carried the tutorial sections they serve
  ("4.06 5.02"); the tutorial is renumbered as it grows and the board cannot be.  Name pages by title in the
  handbook, nothing on the board.
- **Give each tile its own picture in its handbook entry.**  Render the board's top at about 25 px/mm, find the board
  in the image by its solder-mask green (columns and rows where G > R + 12 and G < 110), and crop each tile's frame
  with 0.9 mm round it.  A table with the picture in the first column and the description beside it means the reader
  never scrolls back to the board.  Save as JPEG: a render compresses badly as PNG.
- **Generate the README's tables and the handbooks from one source.**  A per-tile record (what it does, the chip and
  its maker's page, specs, limits, experiments, how to cable it, what to buy) feeds both, so they cannot disagree.
- **The pcb stage reads the tiles' JSON written by the sch stage.**  An edit to a board module followed by `--stage
  pcb` alone silently builds the old silk: run `--stage sch --stage pcb`.
- **Never `source` a Python file in bash.**  Its first line, `import atexit, glob, os`, runs ImageMagick's `import`,
  which waits for a mouse click to grab the screen: the shell hangs until it is killed.

## 22. Lessons from Jason's answers on the AMOD and RF-MOD tiles (2026-10-28)

- **A jack's name says whose port it is.**  "AUDIO IN" beside "MIC OUT" left Jason asking "whose in?"; "SPEAKER IN"
  names the thing the signal goes to.  On a tile with two channels, name each jack by its channel's device or function,
  never by a generic signal ("AUDIO", "SIGNAL", "RF" alone when the tile has two RF ports).
- **Before spending cells on a splitter, look for the output the chip already has.**  Two RF-MOD tiles were resistive
  splitters (two cells each, 6 dB lost) while each MAX2871's complementary output, RFOUTA-, sat terminated in 51 ohm.
  Brought to its own jack it is a second LO at full power, 180 degrees from the first.  A part the student can buy as a
  cable accessory (Jason: "I have passive splitters") does not earn board area.
- **A hand-soldered part must fit before it is offered.**  Jason allowed a hand-soldered AM tuning capacitor; a
  polyvaricon with its dial is about 20 mm square, a whole cell beside a jack.  The answer was a 2-way screw terminal
  beside the coil's, in parallel with the switched capacitors, for an external capacitor with a big knob.
- **A 50 ohm line may leave its tile, but its ground must go with it.**  R10's second output runs 1.25 mm below the
  tile, in the margin, because the slide switch fills the tile's bottom edge.  Outside the tile's top pour it was a
  microstrip (about 58 ohm on JLC04161H-7628); a tongue of pour that follows it (`Tile.pour_below`) makes it coplanar
  again.  Keep it 1.25 mm below the frame: KiCad's box for 0.9 mm text is 1.68 mm tall, and the jack's name sits there.
- **Narrow a fine-pitch RF part's pads rather than the RF class.**  JLCPCB's land pattern for the 1608 coupler leaves
  0.2 mm between 0.35 mm pads, under the RF class's 0.25 mm.  The part's terminals are 0.25 wide; 0.29 mm pads clear
  the class and still cover them.  Say so in the footprint's description and the DOA list.
- **Draw what is inside a module.**  A diode-ring mixer in a ceramic case is a white box; its two baluns and ring of
  four diodes drawn beside it on the silk (`Tile.draw_line`, `draw_arc`) are the lesson.  Check the drawing's topology
  on a high-resolution render: the ring runs A to C to B to D, the LO across one opposite pair, the RF across the other.
- **Two single-direction couplers back to back make a dual directional coupler.**  Each is used in the direction its
  datasheet specifies ("bi-directional: no"), its isolated port in 51 ohm: FWD from the first, REFL from the second.
- **Search JLCPCB by category before giving up on a part family.**  Part numbers found Mini-Circuits mixers with 2-15
  in stock; the category "RF Mixers" found the ADEX-10L+ with 861.

## 23. Lessons from AMOD-P2, PhMOD and the placement audit (2026-10-28)

- **Fit JLCPCB's drawing to every footprint before trusting a rotation table.**  The AMOD boards' table set every
  SOT-23 at 0 ("the standard drawing").  JLCPCB's SOT-23 drawings are KiCad's turned 180 ("-BR" in the package name: pin
  1 bottom-right), its row-style SOT-23-6s KiCad's turned +90 ("-BL"), and one SOT-23-5 is KiCad's own ("-TL"): every
  powered tile's P-FET would have gone on backwards.  "Standard" is a prediction from a description, the kind section
  8's rotation table warns about.  AMOD-and-RFMOD's `scripts/check_rotations.py` fits JLCPCB's land pattern onto the board's
  footprint by pad number at each quarter turn, and also reports the datum: it found the USB-C's 1.572 mm and the
  ADL5611's 0.7 mm that earlier previews had shown and that had been moved by hand.
- **Fit a datum on single pads, and drop a pad that is drawn differently.**  A SOT-89's pad 2 is the lead in KiCad's
  footprint and the tab in JLCPCB's drawing; a fit over every pad put the origin 1.5 mm off.  Fit on the pad numbers that
  are single on both sides and drop any whose residual exceeds 0.5 mm.
- **A passive board can take a little power from the Pmod.**  A step attenuator (150 uA) and an oscillator (2 mA) run on
  the host's 3.3 V through the board's own plug, with no USB tile (Jason: "If something can run on 3.3V, it could still
  be plugged into the PMOD port").  Pour the 3.3 V on an inner layer and give it a PWR_FLAG in the schematic: no
  regulator pin drives it.
- **Calibration standards on a board: the SHORT gets no launch void.**  A launch void (no top pour within 1.9 mm of the
  pin) leaves a pin on the ground net connected to nothing; the short wants the pour all round it.  The OPEN keeps its
  void.  The LOAD can sit at the end of a few millimetres of 50 ohm line, outside the jack's courtyard: a matched line
  is still a match.
- **An open-ended line is not a dangling track.**  Draw a stub as copper graphics on its net (KiCad joins them to the
  line they start on), or DRC calls its open end dangling.
- **A floating jack needs its legs on their own net and a void on every layer.**  A 1:1 transformer's OUT whose shell
  is the secondary: the four legs on their own net joined by a U of track, no plane within 5.6 mm, the schematic
  labelling the shield instead of grounding it.
- **A part 4.4 x 5.4 mm cannot sit on the diagonal between a cell's two jacks.**  The checkerboard leaves the top-right
  and bottom-left quarters free; anything wider than about 3.5 mm goes in one of them.
- **A change of case changes the silk's clearances.**  Two 0.8 mm lines 1.3 mm apart cleared each other in capitals and
  collided once "Clipper" and "pass" had descenders.  Allow 1.5 mm between line centres in mixed case.  About ten
  characters of 0.9 mm text fit a one-cell tile's top frame beside its jack: name tiles to fit (Attenuator, Balun, Preamp).
- **Give a new board a new name.**  AMOD-2 became PhMOD; the new passive board took AMOD-P2, not the freed AMOD-2,
  because the commits, the tutorial and the chat log mean the physics board by the old name.

## 24. Lessons from the back panels of the AMOD and RF-MOD boards (2026-10-28)

- **The back of a board of building blocks is its manual.**  Jason (AMOD-and-RFMOD Prompt 18): "When someone is
  screwing things into the board, it's far easier to read the silkscreen in front of them than it is to look up stuff on
  github and try to make sure they are looking at the correct list for the correct board."  Under each tile, on the
  back: its number and title, then its input limit, its load, its supply and switch, and the one thing that breaks it;
  where there is room, a small plot of the response to expect.  Keep the panel's lines in the board's source (a dict per
  board) so the handbook and the silk cannot disagree about which tile they describe.
- **The warnings that prevent damage go on the front as well.**  The back is read while cabling, but the front is what
  faces you when the board is on the bench.  "PULSES ONLY", an LNA's input limit and "start at mV" for a laser driver
  went onto the front, an LNA's noise figure making room.
- **Mirrored text: let KiCad measure it.**  `SetMirrored(True)` on B.SilkS; a left-justified mirrored text extends to the
  left of its anchor on the board, so it reads left-aligned from the back.  Take each line's box from a `PCB_TEXT` with
  the same settings, not from a character count: 0.8 mm text runs 0.65 (lower case) to 0.79 (digits) mm a character.
  At 0.8 mm, lines 1.5 mm apart: 1.4 mm collided once a line had parentheses.
- **Budget a line's length by the free space, not by the tile.**  On a 20 mm cell with jacks at two opposite corners
  the free space is about 10 mm wide: 13 characters at 0.8 mm.  Longer lines forced a panel into scattered pieces or
  into no room at all; shortening them ("IN < -20 dBm", "+22 dBm BURNS") placed every panel.  A QR code and its caption
  take most of a cell's back: the panel there gets 7 mm.
- **Place a panel in reading order and prefer compact to clear.**  A greedy nearest-free-spot placement of a panel's
  parts put lines above their own title.  Place each part below the one before; try one block, then two, three, four
  parts; for each split try clear of tracks and vias, then of tracks only, then over them.  A block over a tented track
  reads; a panel in four scattered pieces does not.
- **A plot on the back runs mirrored.**  Draw the x axis reversed in board coordinates so it reads left to right from the
  back; the y range in the line above the box ("0 to -60 dB"), the x ends below it, nothing inside but the curve; drop
  to a smaller size when the two x labels would meet.  Plot what the tile does: a clipper's OUT against IN, not its
  (flat) frequency response.
- **Run the stage that consumes your edit.**  The panels' text reached the board through the tiles' JSON, written by the
  schematic stage; rebuilding only the board stage drew the old text, and a debugging round went to a placement bug that
  was not there.
- **A step attenuator can have switches and SPI at once.**  The PE43711's direct parallel mode (P/S low, LE high) is
  pSemi's "ideal for manual control": an 8-way DIP (way 1 drives P/S for SPI, ways 2-8 the bits), 100 k pull-downs on
  every bit and P/S, LE pulled up by 100 k so a floating FPGA pin leaves the switches in charge.  In serial mode the
  parallel pins must be low (every bit off).  The chip still needs its 3.3 V: switches do not make an active switch
  array passive.

## 25. Lessons from renaming the AMOD and RF-MOD boards' tiles (2026-10-28)

- **Give a family of boards one letter each, and name a tile by its letter and a number, in lower case.**  Jason
  (AMOD-and-RFMOD Prompt 19): "If we can have a nice, well justified single-letter designator for each board, it would make
  everything much more clear", and "D11, Q11, C11, etc look like a reference designators for diodes, transistors, and
  capacitors.  d11, q11, and c11 don't look like obvious electronics or PCB things."  The letter is the initial of what
  the board is about; board names keep their capitals, ports are capitals, titles mixed case.
- **A rename must never move a name onto something else.**  Keep every letter on its board and retire, never reuse, the
  names that go: then a reference missed in the update points at nothing instead of at the wrong tile.  Reassigning A
  from the active board to the passive one, or renumbering a board with gaps, would have turned every stale "A4" or "R5"
  into a silent error.  Avoid letters that already mean something on the boards (s11 is a reflection coefficient) and
  letters that read as digits (i, l, o).
- **Rename with a tokenizer, not a regular expression.**  The same two characters were tile names, USB-C pin names
  ("A4": "VBUS"), local net names ("N1", "P1"), a 4046's R1 and C1, a paper size (an A1 sheet), a PBM header ("P1\n")
  and the reel suffix of part numbers (ADL5350ACPZ-R7).  Change a whole-string token only where the code makes it a tile
  (the tile constructor's first argument, the silk number, the keys of the per-tile dicts), change prose by word with a
  list of protected phrases, then grep the diff for a changed token glued to a hyphen or a part number.  Net names built
  on the tile name ("/X3_V33") hide from a word-boundary search: search for the name followed by an underscore too.
- **A document can hold two numberings.**  The tutorial's appendix kept the plan's tile numbers beside the as-built
  ones; renaming the whole file would have pointed the plan's "Y9, an H-bridge" at the built board's noise source.
  Rename only the as-built sections and mark the plan's names as its own.
- **A letter with a descender changes the silk's clearances.**  Lower-case p and q hang 0.15 of the text size below the
  line and met the line under them on three tiles; DRC found each.

## 26. Lessons from AMOD-C, AMOD-M and AMOD-B (2026-10-28)

- **Place against courtyards before the first DRC.**  A part placed by its pads alone collides with a neighbour's
  courtyard, a jack's legs or a slot one DRC round at a time.  Print each footprint's pads and courtyard box (a small
  script over the `.kicad_mod`), place against those, and check the boxes in the generator before running KiCad.
- **Choose the Pmod pins so the lines nest; do not route around a fixed pin order.**  On a 2 x 6 plug the lower row's
  lines leave through the gaps between the upper row's pads.  For lanes that never cross, the order of the exits along
  the plug must be the order of the lanes in the gutter, and the lane that turns off first must be the outermost.  Two
  lines shared by two tiles (SCK and MISO for an IMU and an encoder) cannot both branch from one bundle in a gutter
  without a crossing: run all the lines into one tile and let the other tile's lines leave it as a bundle above them.
  Swapping two pins' assignments (AMOD-B's MISO and CS ENC) made the whole bundle planar.
- **A chip under a motor routes on the back between the slots.**  Four radial slots leave 45-degree corridors: a back
  line along x + y = c (or x - y = c) clears a slot's end only where c is far enough from the slot's centre line, so
  compute the band of allowed c and give each line its own.  The MT6701's pins went to fine vias under its body, its
  lines on those diagonals; the SOIC turned 180 so its SSI pins faced the tiles they serve.
- **Holes cut inner-layer pours.**  The +3.3 V strip on L3 ran under the gimbal; its side slots cut it, the middle piece
  (the encoder's supply via) became an island, and DRC reported it only as two missing connections on the front.  After
  placing any slot or cutout, check every via on an inner pour reaches the rest of it; bridge the pour round the holes.
- **A fine board's DRC still uses each net's class.**  A 0.4 mm pitch QFN's stubs pass at 0.2 mm wide only (the
  Default class's 0.2 mm clearance applies between nets of that class); an LGA's unconnected pins, 0.15 mm apart, are
  each a Default net.  Put a fine tile's nets in the Fine class, and its unconnected pins too with a netclass pattern
  (`unconnected-(U601-*`).
- **Pass every width.**  A ground stub that defaults to "the tile's first wire" took a 1 mm motor rail's width on two
  tiles and shorted the pads beside it.  A default borrowed from elsewhere is a bug waiting for the first wide wire.
- **A net that leaves its tile needs a board-wide name.**  "DO" inside one tile is that tile's local net; the same name
  in the tile that reads it is a different net, and ERC is happy with both.  Name cross-tile nets globally from the
  start (`/ENC_DO`).
- **Compare every symbol's pins with the distributor's drawing.**  AMOD-and-RFMOD's `scripts/check_pinouts.py` reads the
  pin names of each LCSC code from EasyEDA and sets them beside the schematic symbol's: on AMOD-C it found a dual
  transistor whose pins were another part's order and a SAW filter whose output was on a ground pad.  The rest of its
  differences are naming ("+" against IN+); read each against the maker's table and say so in the board's DOA list.
- **A push-pull output cannot share a bus.**  The MT6701's DO drives whether or not its chip is selected; a 74LVC1G125
  enabled by its chip select lets it share MISO with an IMU.  Read "high impedance when deselected" in the datasheet
  before sharing any SPI output.
- **A divider to the negative rail is a level shift.**  A current amplifier's output centred on 1.65 V reaches 0 V
  through R1 from the output and R2 to -5 V with R2 x 1.65 = R1 x 5 (3.3 k and 10 k): gain 0.75, a 2.5 k source, read at
  an ADC's or a scope's high impedance.  It fitted where a difference amplifier did not.
- **Leave the back's pour a way to a plug's ground pad.**  Lanes on three sides of a Pmod plug's ground pad left it one
  thermal spoke (DRC: starved thermal).  Keep the nearest lane 1 mm off the pad row so the pour passes between them; on
  the fine nets' 0.35 mm pitch the rest of the lanes still fit above.
- **Rename the file with its references.**  An appendix's text was changed to new board names and its images kept the
  old file names: three broken pictures, found a day later.  After any rename, loop over every referenced file and
  check it exists.
- **Write the final expression, not a placeholder.**  `X if False else Y` left in while iterating reads as logic and is
  dead code; write Y, or a TODO the build fails on.

## 27. Lessons from CostasLink rev A's receive chain on the bench (2026-10-29)

The rules these lessons produced are in §14 ("Simulate the circuit the copper makes"), gates 25-32 and §9. What follows is why
they are general, for any board where a millimetre is a phase.

- **Controlled impedance is necessary, not sufficient.**
  - **What it means:** a 50 Ω line delivers what its ends present to it.
  - **Rev A:** every line measured right in the board file, and the chain still lost 30 dB at 5.8 GHz. The circuit made of the parts, their branches and their grounds was wrong; the lines were not.
  - **The question to ask:** check "is the circuit the copper makes the circuit we meant?", not only "is the line 50 Ω?".
- **Every check rev A had asked whether things were connected and correctly sized; none asked what they did together.**
  - **What passed it:** DRC, ERC, the net and detour checks, the field-solved launches, the gerber parser and five reviews.
  - **The rule:** a check that simulates the circuit as laid out is the only one that sees a stub, a ground return or a shared rail.
- **At microwave frequencies, "next to the pin" is a distance with a phase.**
  - **The arithmetic:** at f, 1 mm is 360°·√εeff·f/c. That is 12° at 5.8 GHz on FR4 CPWG, and 2° at 1 GHz.
  - **The trap:** the vendor's schematic shows lumped values at the pins. Its layout puts them there, and its numbers are only true there.
  - **The rule:** write down how far each part is, in degrees.
- **A rough model early beats an exact one late.**
  - **Rev A's model:** 80 lines of ABCD matrices, with lossless lines and an idealised LNA.
  - **What it did:** gave the bench's trend and most of its size, and named the part to lift.
  - **How far to trust it:** the anchor (the vendor's circuit at the pins) and the parasitic sweep tell you.
  - **What it settles:** whether the design will work roughly, and certainly qualitatively, before money is spent.
- **Supply networks are RF circuits too.**
  - **Above a few hundred MHz:**
    - a choke is a capacitor above its SRF;
    - a capacitor is an inductor above its own;
    - a via through a core is a nanohenry;
    - a plane island is a resonant cavity.
  - **The rule:** simulate the bias and decoupling paths with the signal paths, and keep each chain's supply its own.
- **An automatic placer optimises what it is told.**
  - **Rev A:** "the capacitor beside the chip the schematic drew it beside" put the receive tees' 68 pF 36 mm from their chokes.
  - **The rule:** anchor every RF part to the pad it serves, by hand, and measure the distance in the build.
- **A review finding about an RF part's placement is a change, not a bench item.**
  - **Rev A:** reviewers flagged the decoupling distances before the order (REVA_CHANGES 35). They were carried as "to confirm", and the bench confirmed them.
- **Inverting one arm of a quadrature receiver is a mirror, not a rotation: re-derive every loop sign after it.**
  - **What happened:** CostasLink Response 10 swapped the I arm's inputs so its pair would route uncrossed. Its note said the Costas loop "locks 180 degrees round". That is true when the LO is inverted, which flips I and Q together.
  - **Why it was wrong:** with I alone inverted, sign(-I) x Q = -sign(I) x Q, so the loop's feedback sign flipped. The jumpers' default was never changed.
  - **How it showed:** a wrong sign in a loop with a sign() detector does not run away, as the bring-up text expected. It holds at the detector's jumps (+-90 degrees) with the comparator chattering, which looks like a lock.
  - **The rule:** write the loop's sign out end to end in the design notes. That means the demodulator's I/Q convention, each arm's polarity, the comparator's sense, the switch's select, every inverting stage and the oscillator's tuning slope.
  - **Check it on the bench before closing the loop:** with the loop held and the carrier on a known side of the LO, the arms' phase order (Q ahead of or behind I) gives the sign.
- **At bring-up, separate the paths before interpreting a shape.**
  - **Rev A:** a notch and a recovery were the chain cancelling against a leak.
  - **The rule:** a knob in the path (an attenuator, a switch) sorts them. Measure the leak floor with the ports terminated first.

## 28. Lessons from motor-pid rev A's pre-order checks (2026-10-29)

- **A fix found on one board goes to every board that copies the part, the same day.**
  - The op-amp's review round 1 (2026-10-27) found its KF301 footprint had read the "3.60" of the front view as a depth, and turned the CPL 180 so the wire openings face the edge.
  - motor-pid, generated from the same code, kept the misreading for two more days. All three of its terminal blocks would have been fitted with the openings facing into the board.
  - AMOD-and-RFMOD's KF301 still has it (body -4.0 / +3.6, table 0), and the op-amp's own 3D model kept the old depths.
  - The same happened to the first-designator lookup in PLACEMENT_CHECKS. motor-pid's copy dropped the lines for J3, J6 and D3/D4 and had none at all for D5/D6.
  - After a lesson names a part or a function, grep every board for it.
- **A pin-number fit cannot see which way a symmetric part faces.**
  - A screw terminal's pin row fits the same at 0 and 180; a BNC's four posts are numbered differently by JLCPCB.
  - Compare JLCPCB's outline (the box of their top silk) with our courtyard, each measured from the pads' centre, and fail when they lean opposite ways (motor-pid `scripts/check_rotations.py`, FACING).
- **Check the upload itself, not only the table.**
  - Lay JLCPCB's drawing where the upload CPL puts it: their origin at Mid X/Y, y up from the drill origin, turned by Rotation. Measure each of our pads from theirs.
  - This tests the generator's sign conventions along with the table. motor-pid's table stores the datum y-up (as `gen_outputs.py` applies it to the CPL), while a fit in the footprint's frame reports it y-down. A comparison without the conversion called two right entries wrong.
  - Report mechanical pads (tabs, shells, posts) apart from signal pads, each with the reason it differs. The D2PAK's tab is pad 2 in KiCad's footprint and 4 in JLCPCB's, 1.3 mm further out.
  - Paste-only apertures have no number: leave them out.
- **"Capacitor_SMD:" does not mean "not polarised."** A skip list by library skipped the CP_Elec electrolytics. Skip by footprint name (`C_`, `R_`), not by library.
- **Keep the polarised two-pin parts in the pin-name check.**
  - AMOD's `check_pinouts.py` skips Device:D, LED and C. On motor-pid the diodes, LEDs and electrolytics are exactly where a numbering difference hurts.
  - JLCPCB's KT-0805G numbers its anode 1, so a pin-number fit says +180; at 0, their cathode pad lies on ours, as GPiBridge's preview showed.
- **Read the maker's land pattern, not only JLCPCB's.**
  - MSK12C02: Shouhan's datasheet (page 1) puts the terminals 1.95 mm from the posts' line, as KiCad's footprint does; JLCPCB's drawing puts them at 2.25 mm.
  - Lay the part by its terminals and slot the posts (0.9 x 1.45 mm) to take either.
- **Ghostscript's PDFs differ every run** (a document ID, dates, an XMP packet). Pass `-dOmitID -dOmitInfoDate -dOmitXMP` (Ghostscript 9.55 and later), or `fit_pdf.py`'s output churns in git. motor-pid's copy of it does.

- **The preview's bodies, read back** (rev A's preview, 2026-10-29: Jason nudged RV2-RV4 and SW1-SW5).
  - The trimmers are the op-amp's "A pad fit cannot see the body": BOCHEN's 3362P also centres the body on the line of pins 1 and 3, 1.30 mm from the middle of its pins.
  - **An SMD part with locating posts is placed by its body.** JLCPCB's MSK12C02 drawing puts its terminals 0.3 mm further from the posts than Shouhan's land pattern. A datum fitted to the terminals (0.25 mm) left the body 0.3 mm short of the posts. Set the datum so their body's posts land on ours (0.55 mm). AMOD-and-RFMOD's table still has the 0.251.
  - **Draw the actuator where it is.** The MSK12C02's knob sticks out 1.45 mm sideways from the long edge opposite the terminals. motor-pid's footprint and model had it standing up, outside the courtyard.
  - motor-pid's `check_rotations.py` takes the body from the component record (`/api/products/<code>/components`, the 3D model's outline in an SVGNODE) and lays it on our courtyard. The record is cached and fetched slowly, because easyeda answers a burst of requests with 403s.

## 29. Lessons from the AMOD and RF-MOD boards' pre-order checks (2026-10-29)

Section 28's KF301 finding was fixed here the same day (CPL +180, body 3.7 / 4.0, a wire-face check in `check_outputs.py`).
What follows is what the nine boards' checks added.

- **"In stock" is not "free to order".**
  - JLCPCB's parts API returns `stockCount` and `canPresaleNumber`. The second is the stock less what other orders hold.
  - On the order day four codes read 644 to 51 401 in stock and were oversold, the free count negative: a 27 ohm and a
    6.8 k 0402, a 220 nF 0402, the OPA847IDBVR. Another went from 40 328 to 74 in four days.
  - The rule: check the free count, for the codes a board orders, on the day you pay. AMOD's stock gate now uses
    `min(stockCount, canPresaleNumber)` and ignores codes no BOM orders (a dropped tile's crystal had none free).
  - Swap for the same value and package; for an IC the same die on another reel (OPA847IDBVT for IDBVR).
  - **Then fit the swapped code's rotation afresh.** JLCPCB draws each code separately: the IDBVT's drawing is a quarter
    turn from the IDBVR's (+180 against +270). Copying the old code's entry would have put the op amp in a quarter
    turn out; `check_rotations.py` caught it on the rebuilt BOM.
- **A wire end dropped at a pad's edge is a via in the pad.**
  - The tile generator puts a via at every back-side wire end and every ground stub's point. Ten landed with their holes
    in or across SMD lead pads (an 0402, two SOIC-8 pins, four SOT-23 pins, two 0805 LEDs, an 0805 capacitor), and four
    more 0.02-0.03 mm inside a pad. DRC passes them: same net.
  - The vias are tented and JLCPCB's economic assembly does not fill them, so a hole in a pad's mask opening drinks its
    solder: a starved joint or a tombstone.
  - The gate: no hole's edge inside an SMD pad's copper, exposed pads and tabs aside (a pad of at least 2.5 times its
    footprint's median area; paste-only apertures, which have no number, skipped). AMOD `scripts/check_layout.py`.
    Print the holes within 0.05 mm (mask registration).
- **A termination is a load a signal generator can burn.**
  - A 49.9 ohm 0402 is rated 62.5 mW. A generator set to 10 V p-p into 50 ohm (20 V p-p open) puts 0.25 W in it.
  - A back-termination behind an OPA810 into a shorted jack takes I_sc^2 R, about 0.28 W.
  - The rule: rate every termination and back-termination at 0.2 W or more. That needs no layout change:
    Vishay's CRCW0402...HP is 200 mW in 0402, and Yageo's SR0603 is 250 mW in 0603.
  - This is the op-amp reviewers' "size the resistors a misplaced scope clip loads", applied to every jack.
- **An assembly drawing is plotted from Fab, silkscreen and outline, without the drawing sheet.**
  - `--include-border-title` puts the board 1:1 in the corner of an A4 frame. F.Cu plotted black buries the silk under the
    pours.
  - Plot F.Fab, F.Silkscreen and Edge.Cuts (B.Fab, B.Silkscreen mirrored), then fit to Letter with the scale in a caption
    (CostasLink's `fit_pdf.py`).
  - On a page with slack, put the caption half a margin under the drawing. At the paper's foot it widens the drawn box
    that `fit_pdf.py check` measures, and a centred drawing fails as off centre.
- **CostasLink's RF gates on boards of internally matched blocks** (RF-MOD, IQ-MOD; `gates.py` in the session's scratchpad).
  - The lines were exact: 0.29 mm, a 0.25 mm gap, ground under 100 % outside the jacks' designed launch voids.
  - No matching part sat on a branch. The RF chips are internally matched, so the only shunt parts on RF lines are bias
    chokes, 0.5-2 mm off the line: under 10 degrees at 2.4 GHz.
  - The stitching fell short of gates 30 and 32 at the 5.8 GHz stretch, though:
    - fences of 0.2-1.7 vias per mm;
    - the top pour 2.0 mm (median) and up to 9.8 mm from a ground via near the lines.
    That is fine at 2.4 GHz (lambda/20 is 3 mm), and short of the gates at 5.8 GHz.
  - Write each gate's result per band, not only at the board's top frequency.
  - The synthesizers' output-pin nets were in no class, as on CostasLink, but here they are 3 mm long.
- **When JLCPCB's symbol leaves a polarised part's pins unnamed, read its drawing's silkscreen.**
  - The 220 uF electrolytic (C2992606) and the SMBJ12A (C19077565) have blank pin names.
  - Their land patterns carry the answer: a "+" and the chamfered corners at pad 1; a cathode band on pad 1's side.
  - Both agree with KiCad's pad 1 at a turn of 0. The rotation check had skipped the electrolytic, because it skipped
    every footprint in Capacitor_SMD (section 28's point). It now skips by footprint name.
- **A wrong package with the right pin order passes a pin-number fit; JLCPCB's preview showed it** (Jason, 2026-10-29:
  "AMOD-A's U1201 seems to have the wrong package in the preview").
  - The PAM8302AASCR (C113367) is an MSOP-8, the only PAM8302 JLCPCB stocks. It sat on a SOIC-8 footprint; its leads
    fell half-way between our pads.
  - `check_rotations.py` had fitted it at +270 with 0.77 mm rms and printed "ok": it reports the residual and never fails
    on it.
  - The gate (AMOD `scripts/check_overlay.py`, in the build): lay JLCPCB's drawing where the table's turn and datum put it.
    Every one of their pads' centres must lie inside our pad of the same number, or inside one of ours for a part
    numbered differently. Read custom pads' primitives: a SOT-89's tab is a primitive of pad 2.
  - Prove it fails: turned a quarter off, two SOT-23s stood 2.0 and 2.25 mm outside.
  - Two-pad parts escape it, so compare each R, C, L, LED and diode footprint's size code (0402 ...) with JLCPCB's stated
    package. 310 lines here, all agreed.
  - Compare the package name too. The MPN said only PAM8302A; the code's package field said MSOP-8.
- **EasyEDA's `c_spicepin` is the SPICE order, not always the printed pin number.**
  - Pairing names by it made the PAM8302's pin 2 read IN- and its pin 8 NC.
  - The printed number is the pin group's numeric text; use that when the two differ.
- **JLCPCB's order page: "Specify Stackup: No" is the JLC04161H-7628 construction.**
  - The impedance page lists "No requirement" for 4-layer 1.6 mm as the same layers: 0.2104 mm of 7628 prepreg and a
    1.065 mm core.
  - So a board drawn for JLC04161H-7628 needs no choice there. Jason could not pick one on the RF-MOD quote.
  - Set "Min via hole size" to the board's smallest via (0.25 mm holes: 0.25mm/(0.35/0.4mm)).
  - "Via covering" now offers Plugged by default, and Tented is greyed out. Plugged suits a design drawn for tented vias.
- **The MSK12C02 datum depends on the footprint** (section 28's 0.55 mm is for round post holes at Shouhan's 1.95 mm).
  - AMOD's footprint slots the posts (0.9 x 1.45 mm) where JLCPCB's drawing puts them.
  - With the datum fitted to the terminals (0.251 mm), JLCPCB's posts land at the slots' centre, and Shouhan's position
    lies inside the slots too. Keep 0.251 there.
