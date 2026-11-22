"""Translate the two 64th Street 68000 programs to position-independent x86-64.

For every even ROM PC emit a native entry containing its extension operands as an
immediate, followed by a direct branch to precompiled instruction semantics.
All decoding happens here. Computed guest jumps use PC-to-code arithmetic.
The generated files derive from the owner's ROM and stay private to their build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile
import zlib

CPU_ROMS = (
    ("main", 0xed6c6942, 0x0621ed1d, 0x80000),
    ("sound", 0x632be0c1, 0x13595d01, 0x20000),
)
SLOT_SIZE = 16
VENEER_SIZE = 8


def read_programs(path):
    required = {crc for _, even, odd, _ in CPU_ROMS for crc in (even, odd)}
    chips = {}
    if path.is_dir():
        for item in path.iterdir():
            if item.is_file() and item.stat().st_size in (0x10000, 0x40000):
                data = item.read_bytes()
                crc = zlib.crc32(data)
                if crc in required:
                    chips[crc] = data
    else:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.CRC in required:
                    chips[info.CRC] = archive.read(info)
    result = []
    for name, even_crc, odd_crc, size in CPU_ROMS:
        image = bytearray(size)
        for lane, crc in enumerate((even_crc, odd_crc)):
            if crc not in chips or len(chips[crc]) * 2 != size:
                raise ValueError(f"Missing or incorrect {name} ROM {crc:08x}")
            image[lane::2] = chips[crc]
        result.append(bytes(image))
    return result


def decode_table(source):
    bodies = dict(re.findall(r"^static void (m68k_op_\w+)\(void\)\n\{\n(.*?)^\}", source, re.M | re.S))
    table = [("m68k_op_illegal", 0)] * 65536
    rows = re.findall(r"\{(m68k_op_\w+)\s*,\s*(0x\w+),\s*(0x\w+),\s*\{\s*(\d+),", source)
    if len(rows) < 1000 or len(bodies) < 1000:
        raise ValueError("Could not identify Musashi semantics and decode masks")
    for name, mask, match, cycles in rows:
        mask, match = int(mask, 16), int(match, 16)
        free = 0xffff ^ mask
        bits = free
        while True:
            table[match | bits] = (name, int(cycles))
            if bits == 0:
                break
            bits = (bits - 1) & free
    return bodies, table


def write_sites(images, ops, out):
    # All entries and veneers share one ELF section. Their relative distances
    # are known here; only the final 5-byte veneer branches need relocations.
    veneers = {opcode: i for i, opcode in enumerate(ops)}
    offset = 0
    veneer_base = sum(len(b) // 2 for b in images) * SLOT_SIZE
    assembly = [".text", ".p2align 4"]
    for image, (name, _, _, _) in zip(images, CPU_ROMS):
        words = [w for (w,) in struct.iter_unpack(">H", image)]
        padded = words + [0] * 4
        native = bytearray(len(words) * SLOT_SIZE)
        for i, opcode in enumerate(words):
            at = i * SLOT_SIZE
            ext = sum(padded[i+1+k] << (16*k) for k in range(4))
            dest = veneer_base + veneers[opcode] * VENEER_SIZE
            displacement = dest - (offset + at + 15)
            # movabs $extension_words,%rdi ; jmp rel32 ; nop
            struct.pack_into("<2sQBiB", native, at, b"\x48\xbf", ext, 0xe9, displacement, 0x90)
        blob = out / f"sites_{name}.bin"
        blob.write_bytes(native)
        sym = "street_sites_" + name
        assembly += [f".globl {sym}", f".hidden {sym}", f"{sym}:", f'.incbin "{blob.resolve().as_posix()}"']
        offset += len(native)
    for opcode in ops:
        assembly += [".byte 0xe9", f".long street_op_{opcode:04x} - . - 4", ".byte 0x90,0x90,0x90"]
    assembly.append('.section .note.GNU-stack,"",@progbits')
    (out / "sites.S").write_text("\n".join(assembly) + "\n")


def generate_header(cpu, out):
    source = (cpu / "m68kcpu.h").read_text()
    begin = source.index("INLINE uint m68ki_read_imm_16(void)\n{")
    end = source.index("\n}", source.index("INLINE uint m68ki_read_imm_32(void)\n{", begin)) + 2
    literal_reads = """
static uint64_t street_literals;
INLINE uint m68ki_read_imm_16(void)
{
    /* Each native site carries all four possible 68000 extension words. */
    unsigned int shift = (REG_PC - REG_PPC - 2u) * 8u;
    if (shift >= 64u) abort();
    REG_PC += 2;
    return (uint)(street_literals >> shift) & 65535u;
}
INLINE uint m68ki_read_imm_32(void)
{
    uint hi = m68ki_read_imm_16();
    return (hi << 16) | m68ki_read_imm_16();
}
"""
    header = source[:begin] + "#ifdef STREET_COMPILED_KERNEL\n" + literal_reads + "\n#else\n" + source[begin:end] + "\n#endif\n" + source[end:]
    (out / "m68kcpu.h").write_text(header)


def generate_core(cpu, table, out):
    core = (cpu / "m68kcpu.c").read_text()
    marker = '#include "m68kfpu.c"'
    extra = """
#include <stdio.h>
#include <stdlib.h>
extern int nSekActive;
extern const unsigned char street_sites_main[], street_sites_sound[];
unsigned char m68ki_cycles[4][65536];
static const unsigned char street_cycles[65536] = {
#include "cycles.inc"
};
void m68ki_build_opcode_table(void)
{
    memcpy(m68ki_cycles[0], street_cycles, sizeof(street_cycles));
}
static void street_run_site(void)
{
    unsigned pc = REG_PC & 0xffffff;
    const unsigned char *base;
    if (nSekActive == 0 && pc < 0x80000 && !(pc & 1)) base = street_sites_main;
    else if (nSekActive == 1 && pc < 0x20000 && !(pc & 1)) base = street_sites_sound;
    else {
        fprintf(stderr,"64th Street: no compiled code for cpu %d PC %06x (previous PC %06x)\\n",nSekActive,pc,REG_PPC);
        abort();
    }
    ((void (*)(void))(base + ((size_t)pc << 3)))();
}
"""
    old = "REG_IR = m68ki_read_imm_16();\n\t\t\tm68ki_instruction_jump_table[REG_IR]();\n\t\t\tUSE_CYCLES(CYC_INSTRUCTION[REG_IR]);"
    if core.count(old) != 2:
        raise ValueError("Unexpected 68000 execute loop")
    core = core.replace(marker, marker + "\n" + extra).replace(old, "street_run_site();")
    (out / "m68kcpu.c").write_text(core)
    (out / "cycles.inc").write_text("\n".join(",".join(str(c) for _, c in table[i:i+64]) + "," for i in range(0,65536,64)))


def write_kernels(ops, bodies, table, out):
    preamble = """#include <stdint.h>
#include <stdlib.h>
#define STREET_COMPILED_KERNEL
#include "m68kcpu.h"
extern void m68040_fpu_op0(void);
extern void m68040_fpu_op1(void);
"""
    # Interleave instruction families so the workload is balanced across files.
    for batch in range(64):
        chunks = [preamble]
        for opcode in ops[batch::64]:
            name, cycles = table[opcode]
            body = bodies[name]
            # Convert handler returns into a transfer to its fixed timing epilogue.
            body = re.sub(r"\breturn\s*;", "goto complete;", body)
            chunks += [f"#undef REG_IR\n#define REG_IR 0x{opcode:04x}u",
                       f"void street_op_{opcode:04x}(uint64_t operands)\n{{",
                       "    street_literals = operands;",
                       f"    m68ki_cpu.ir = 0x{opcode:04x}u;",
                       "    REG_PC += 2;", "    {", body, "    }",
                       f"complete: USE_CYCLES({cycles});", "}", ""]
        (out / f"kernel_{batch:02}.c").write_text("\n".join(chunks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("fbneo","generated","rom","out"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    images = read_programs(args.rom)
    ops = sorted({w for image in images for w, in struct.iter_unpack(">H",image)})
    bodies, table = decode_table((args.generated / "m68kops.c").read_text())
    cpu = args.fbneo / "src/cpu/m68k"
    generate_header(cpu,args.out)
    generate_core(cpu,table,args.out)
    write_kernels(ops,bodies,table,args.out)
    write_sites(images,ops,args.out)
    stats = {"cpu_sites":[len(image)//2 for image in images],
             "reset_pc":[int.from_bytes(image[4:8],"big") for image in images],
             "decoded_operations":len(ops),"program_sha256":[hashlib.sha256(b).hexdigest() for b in images]}
    (args.out / "translation.json").write_text(json.dumps(stats,indent=2)+"\n")
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
