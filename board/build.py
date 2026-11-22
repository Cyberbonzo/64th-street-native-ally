#!/usr/bin/env python3
"""Build the single-title 64th Street board, using the pinned FBNeo device sources."""
import argparse
import concurrent.futures
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("STREET64_WORK", HERE.parent.parent)).resolve()
FB = ROOT / "vendor/FBNeo"
SRC = FB / "src"
BUILD = ROOT / "build"
GEN = BUILD / "generated"
OBJ = BUILD / "board-obj"
SOURCE_FILES = """
burn/burn.cpp burn/burn_memory.cpp burn/tiles_generic.cpp burn/tilemap_generic.cpp
burn/burn_bitmap.cpp burn/debug_track.cpp burn/burn_sound.cpp burn/burn_sound_c.cpp burn/load.cpp burn/timer.cpp
burn/snd/burn_ym2151.cpp burn/snd/ym2151.c burn/snd/msm6295.cpp
cpu/m68000_intf.cpp
""".split()

def update(path, data):
    if not path.exists() or path.read_text() != data:
        path.write_text(data)

def prepare():
    OBJ.mkdir(exist_ok=True, parents=True)
    GEN.mkdir(exist_ok=True, parents=True)
    update(GEN/"driverlist.h", """extern struct BurnDriver BurnDrvStreet64;
static struct BurnDriver *const pDriver[] = { &BurnDrvStreet64 };
static const struct {const char *game_name; char *sourcefile;} sourcefile_table[] = {
    {"64street", (char*)"d_megasys1.cpp"}, {"", (char*)""}};
""")
    code = (SRC/"burn/drv/pre90s/d_megasys1.cpp").read_text()
    # The selected PCB is known at translation time. Remove the unconnected
    # Z80 and Yamaha 2203 paths of other Mega System 1 revisions.
    for before, after in [
        ("static INT32 system_select = 0;", "static constexpr INT32 system_select = 0xC;"),
        ("system_select = nSystem;", "assert(nSystem == system_select);"),
        ("\n\tsystem_select = 0;", ""),
    ]:
        assert code.count(before) == 1, before
        code = code.replace(before, after)
    update(GEN/"street64_devices.cpp", code)

def compile_object(source):
    cpp = source.suffix == ".cpp"
    flags = [os.environ.get("CXX","g++") if cpp else os.environ.get("CC","gcc"),
             "-std=gnu++17" if cpp else "-std=gnu17", "-O2", "-fPIC",
             "-fvisibility=hidden", "-ffunction-sections", "-fdata-sections",
             "-fno-strict-aliasing", "-Wno-write-strings", "-Wno-narrowing",
             "-DLSB_FIRST", "-DEMU_M68K", "-DBUILD_HEADLESS",
             "-DBUILD_X64_EXE", "-DNO_VIZ", "-DHAVE_UNISTD_H"]
    includes = [SRC/"burn", SRC/"burn/devices", SRC/"burn/snd", SRC/"cpu", SRC/"cpu/m68k",
                SRC/"burner/headless", SRC/"burner", SRC/"intf", SRC/"burn/drv/pre90s", GEN,
                HERE.parent/"frontend"]
    out = OBJ / (source.name + ".o")
    # A fresh compile also picks up the generated CPU, frontend and board headers.
    subprocess.run(flags + [f"-I{x}" for x in includes] + ["-c",str(source),"-o",str(out)],check=True)
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects-only", action="store_true")
    parser.add_argument("--aot-object", nargs="+", type=Path)
    args = parser.parse_args()
    prepare()
    sources = [SRC / s for s in SOURCE_FILES] + [GEN/"street64_devices.cpp",HERE/"street64_board.cpp",HERE/"standalone.cpp"]
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        objects = list(pool.map(compile_object,sources))
    if args.objects_only:
        return
    if not args.aot_object:
        parser.error("provide compiled 64th Street AOT CPU objects via --aot-object")
    subprocess.run(["g++","-shared","-Wl,--gc-sections,-z,defs","-o",str(BUILD/"libstreet64_board.so"),
                    *map(str, objects + args.aot_object),"-lz","-lm","-pthread"],check=True)

if __name__ == "__main__":
    main()

