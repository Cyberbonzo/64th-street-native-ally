#ifndef STREET64_BOARD_H
#define STREET64_BOARD_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    STREET64_MARGIN = 43,
    STREET64_WIDTH = 256 + 2 * STREET64_MARGIN,
    STREET64_HEIGHT = 224,
    STREET64_AUDIO_RATE = 48000,
    STREET64_MAX_AUDIO_FRAMES = 2048
};

enum {
    STREET64_UP = 1, STREET64_DOWN = 2, STREET64_LEFT = 4, STREET64_RIGHT = 8,
    STREET64_ATTACK = 16, STREET64_JUMP = 32, STREET64_START = 64, STREET64_COIN = 128
};

/* The game-specific board consumes extracted, CRC-verified chips. */
int street64_init(const char *directory);
double street64_fps(void);
/* XRGB8888, top to bottom, and interleaved 48 kHz signed stereo.
 * Return stereo frame count, or a negative value on a board error. */
int street64_frame(uint32_t *pixels, int16_t *stereo, unsigned p1, unsigned p2);
void street64_shutdown(void);

/* Zero size indicates that this build has no verified save-state implementation.
 * Save and load return zero on success. A rejected load leaves the board intact. */
size_t street64_state_size(void);
int street64_save_state(void *out, size_t size);
int street64_load_state(const void *data, size_t size);

#ifdef __cplusplus
}
#endif
#endif
