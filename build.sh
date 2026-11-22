#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 path/to/64street.zip (or its outer arcade ZIP)" >&2
    exit 2
fi
rom="$(realpath -- "$1")"
project="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export STREET64_WORK="$(realpath -m -- "${STREET64_WORK:-$project/.work}")"
work="$STREET64_WORK"
[[ "$(uname -sm)" == "Linux x86_64" ]] || { echo "Requires Linux x86-64" >&2; exit 1; }
pkg-config --exists sdl2 zlib
mkdir -p "$work/build/generated" "$work/vendor" "$work/private"
python3 "$project/tools/prepare_chips.py" "$rom" "$work/private/chips" > "$work/private/chip-hashes.json"

vendor="$work/vendor/FBNeo"
revision=61cd3ede225ec44b84011f7679db68123d72725d
if [[ ! -e "$vendor" ]]; then
    git init -q "$vendor"
    git -C "$vendor" remote add origin https://github.com/finalburnneo/FBNeo.git
fi
if ! git -C "$vendor" rev-parse --verify HEAD >/dev/null 2>&1; then
    git -C "$vendor" fetch -q --depth=1 origin "$revision"
    git -C "$vendor" checkout -q --detach FETCH_HEAD
fi
if [[ "$(git -C "$vendor" rev-parse HEAD)" != "$revision" ]]; then
    echo "Build expects FBNeo at $revision in $vendor" >&2
    exit 1
fi

cpu="$vendor/src/cpu/m68k"
cc -O2 "$cpu/m68kmake.c" -o "$work/build/m68kmake"
"$work/build/m68kmake" "$work/build/generated" "$cpu/m68k_in.c"
python3 "$project/aot/generate.py" --fbneo "$vendor" --generated "$work/build/generated" \
    --rom "$work/private/chips" --out "$work/build/aot"
bash "$project/aot/build.sh"
python3 "$project/board/build.py" --aot-object "$work"/build/aot-obj/*.o
make -C "$project/frontend" BUILD="$work/build"

dist="$work/dist"
mkdir -p "$dist/assets" "$dist/licenses"
install -m 755 "$work/build/street64" "$work/build/libstreet64_board.so" "$project/frontend/jogar.sh" "$dist/"
install -m 644 "$work"/private/chips/* "$dist/assets/"
install -m 644 "$vendor/src/license.txt" "$dist/licenses/FBNeo.txt"
"$dist/street64" --assets "$dist/assets" --headless --frames 400
echo "Built your private copy: $dist/jogar.sh"
