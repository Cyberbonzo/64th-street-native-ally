"""Extract the World arcade set from the user's ZIP; accept a ZIP wrapping 64street.zip."""
import argparse
import hashlib
import io
import json
import tempfile
from pathlib import Path
from zipfile import ZipFile

# Chip identity, independent of the label on a particular dump.
CHIPS = {
    "64th_01.rom": (524288, 0x06222F90), "64th_02.rom": (262144, 0x0621ED1D),
    "64th_03.rom": (262144, 0xED6C6942), "64th_04.rom": (524288, 0x98F83EF6),
    "64th_05.rom": (524288, 0xA89A7020), "64th_06.rom": (524288, 0x2BFCDC75),
    "64th_07.rom": (65536, 0x13595D01), "64th_08.rom": (65536, 0x632BE0C1),
    "64th_09.rom": (131072, 0xA4A97DB4), "64th_10.rom": (262144, 0xA3390561),
    "64th_11.rom": (131072, 0xB0B8A65C), "mo-91009.mcu": (16384, 0xC6F509AC),
    "pr91009.12": (512, 0xC69423D6),
}


def extract(archive, output):
    by_id = {(i.file_size, i.CRC): i for i in archive.infolist()}
    missing = [name for name, chip_id in CHIPS.items() if chip_id not in by_id]
    if missing:
        raise ValueError("Missing World set chips: " + ", ".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        stage = Path(scratch) / "chips"
        stage.mkdir()
        hashes = {}
        for name, chip_id in CHIPS.items():
            data = archive.read(by_id[chip_id])
            (stage / name).write_bytes(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        if output.exists():
            for name, digest in hashes.items():
                if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
                    raise ValueError(f"Existing file differs: {output / name}")
        else:
            stage.rename(output)
        return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with ZipFile(args.zip) as archive:
        nested = [i for i in archive.infolist() if Path(i.filename).name.lower() == "64street.zip"]
        if nested:
            if len(nested) != 1 or nested[0].file_size > 16 * 1024 * 1024:
                parser.error("Unexpected nested arcade archive")
            with ZipFile(io.BytesIO(archive.read(nested[0]))) as inner:
                result = extract(inner, args.output)
        else:
            result = extract(archive, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
