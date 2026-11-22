// Single-title Mega System 1-C peripheral and input adapter.
#include "burnint.h"
#include "timer.h"
#pragma GCC visibility push(default)
#include "street64_board.h"
#pragma GCC visibility pop
#include <array>
#include <filesystem>
#include <fstream>
#include <unordered_map>
#include <vector>
#include <zlib.h>

extern BurnDriver BurnDrvStreet64;
static std::unordered_map<uint32_t, std::vector<unsigned char>> chips;
static bool active;

static INT32 load_chip(UINT8 *dst, INT32 *written, INT32 index) {
    BurnRomInfo rom{};
    if (BurnDrvStreet64.GetRomInfo(&rom, index)) return 1;
    auto chip = chips.find(rom.nCrc);
    if (chip == chips.end() || chip->second.size() != rom.nLen) {
        fprintf(stderr, "Missing chip %08x (index %d)\n", rom.nCrc, index);
        return 1;
    }
    memcpy(dst, chip->second.data(), rom.nLen);
    if (written) *written = rom.nLen;
    return 0;
}

static UINT32 xrgb(INT32 r, INT32 g, INT32 b, INT32) {
    return (r << 16) | (g << 8) | b;
}

int street64_init(const char *directory) {
    if (active || !directory) return -1;
    chips.clear();
    try {
        for (const auto &f : std::filesystem::directory_iterator(directory)) {
            if (!f.is_regular_file() || f.file_size() > 1024*1024 || !f.file_size()) continue;
            std::ifstream stream(f.path(), std::ios::binary);
            std::vector<unsigned char> bytes(f.file_size());
            if (!stream.read(reinterpret_cast<char *>(bytes.data()),bytes.size())) return -1;
            const auto crc = crc32(0, bytes.data(), bytes.size());
            chips.emplace(crc,std::move(bytes));
        }
    } catch (const std::exception &e) {
        fprintf(stderr, "Reading chip directory: %s\n", e.what());
        return -1;
    }
    BurnLibInit();
    nBurnDrvActive = 0;
    nBurnBpp = 4;
    nBurnPitch = STREET64_WIDTH * nBurnBpp;
    nBurnSoundRate = STREET64_AUDIO_RATE;
    // SystemInit sets nBurnSoundLen from the board refresh rate and the output rate.
    BurnHighCol = xrgb;
    BurnExtLoadRom = load_chip;
    BurnInitMemoryManager();
    BurnTimerPreInit();
    for (unsigned i = 0; i < 2; ++i) {
        BurnInputInfo input{};
        BurnDrvStreet64.GetInputInfo(&input,18+i);
        *input.pVal = i == 0 ? 0xff : 0xfd;
    }
    const auto result = BurnDrvStreet64.Init();
    chips.clear();
    if (result != 0) {
        BurnExitMemoryManager();
        BurnLibExit();
        return -1;
    }
    active = true;
    return 0;
}

double street64_fps() { return nBurnFPS / 100.0; }

int street64_frame(uint32_t *pixels, int16_t *audio, unsigned p1, unsigned p2) {
    if (!active || !pixels || !audio) return -1;
    const unsigned players[2] = {p1,p2};
    static const std::array<int,8> masks = {128,64,1,2,4,8,16,32};
    for (int p=0; p<2; ++p) for (int i=0; i<8; ++i) {
        BurnInputInfo input{};
        BurnDrvStreet64.GetInputInfo(&input, p*8+i);
        *input.pVal = (players[p] & masks[i]) != 0;
    }
    pBurnDraw = reinterpret_cast<UINT8 *>(pixels);
    pBurnSoundOut = audio;
    memset(audio,0,sizeof(*audio)*2*nBurnSoundLen);
    ++nCurrentFrame;
    return BurnDrvStreet64.Frame() == 0 ? nBurnSoundLen : -1;
}

void street64_shutdown() {
    if (!active) return;
    BurnDrvStreet64.Exit();
    BurnExitMemoryManager();
    BurnLibExit();
    active = false;
}

#include "../frontend/board_progress.inc"
