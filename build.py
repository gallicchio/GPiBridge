#!/usr/bin/env python3
"""Make everything: library, schematic, board, checks, release, housing,
firmware, renders.  Each step stops the build if its check fails.

Two boards come out: GPiBridge (with the IEEE-488 transceivers) and GPiBridge
Lite (without).  The library, the housing and the firmware are shared; the
schematic, board, release and docs steps run once for each board.

    python3 build.py              everything, both boards
    python3 build.py board        from one step on (library, schematic, board, release,
                                  enclosure, firmware, docs)
    python3 build.py --only board just that step
    python3 build.py --full ...   only GPiBridge's steps (--lite: only the Lite's)
    python3 build.py --clean      remove what the build makes and git does not keep

Needs KiCad 10 (tools/kienv.py finds it), Inkscape, FreeCAD 0.19+ (freecadcmd),
and for the firmware CMake and arm-none-eabi-gcc; the Pico SDK is fetched by
firmware/fetch_sdk.sh.  Everything it makes that a reviewer or a fab needs is
committed, so nothing has to be built to look at the design or to order it.
"""
import os, shutil, subprocess, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))


VARIANTS = ["full", "lite"]          # narrowed by --full / --lite


def run(*cmd, cwd=ROOT, variant=None):
    t = time.time()
    env = dict(os.environ)
    if variant:
        env["GPIBRIDGE_VARIANT"] = variant
    print("  $ %s%s" % ("GPIBRIDGE_VARIANT=%s " % variant if variant else "", " ".join(cmd)))
    r = subprocess.run(cmd, cwd=cwd, env=env)
    if r.returncode:
        sys.exit("FAILED (%d): %s" % (r.returncode, " ".join(cmd)))
    return time.time() - t


def py(script, *args, variant=None):
    return run(sys.executable, os.path.join(ROOT, script), *args, variant=variant)


def each(*scripts):
    """Run these scripts for each board, in turn."""
    def go():
        for v in VARIANTS:
            for sc in scripts:
                py(sc, variant=v)
    return go


STEPS = [
    ("library", lambda: py("gen/library.py")),
    ("schematic", lambda: (py("gen/firmware_pins.py"), py("tools/check_pins.py"),
                           each("gen/project.py", "gen/schematic.py", "tools/sch_check.py")())),
    ("board", each("gen/board.py", "tools/pcb_check.py", "tools/check_plug.py")),
    ("release", each("mfg/make_release.py")),
    ("enclosure", lambda: (py("enclosure/build.py"), each("enclosure/render.py")())),
    ("firmware", lambda: (run("sh", "fetch_sdk.sh", cwd=os.path.join(ROOT, "firmware")),
                          run("cmake", "-S", ".", "-B", "build", cwd=os.path.join(ROOT, "firmware")),
                          run("cmake", "--build", "build", "-j8", cwd=os.path.join(ROOT, "firmware")),
                          run("make", "-C", "test", cwd=os.path.join(ROOT, "firmware")))),
    ("docs", each("tools/make_docs.py")),
]

CLEAN = ["build", "firmware/build", "firmware/test/test_prologix", "firmware/test/test_wire", "firmware/test/out",
         "enclosure/out/params.json", "enclosure/out/gpibridge_board.step", "enclosure/out/gpibridgelite_board.step"]


def main(argv):
    global VARIANTS
    if "--full" in argv or "--lite" in argv:
        VARIANTS = [v for v in ("full", "lite") if "--" + v in argv]
    if "--clean" in argv:
        for p in CLEAN:
            p = os.path.join(ROOT, p)
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.remove(p)
        print("clean")
        return 0
    names = [n for n, _ in STEPS]
    only = "--only" in argv
    args = [a for a in argv if not a.startswith("--")]
    start = names.index(args[0]) if args else 0
    todo = STEPS[start:start + 1] if only else STEPS[start:]
    t0 = time.time()
    for name, fn in todo:
        print("== %s" % name)
        fn()
    print("built in %.0f s: %s" % (time.time() - t0, ", ".join(n for n, _ in todo)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
