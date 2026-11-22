CXX ?= c++
BUILD ?= ../../build
SDL_CFLAGS := $(shell pkg-config --cflags sdl2)
SDL_LIBS := $(shell pkg-config --libs sdl2)
CXXFLAGS ?= -O2 -g

.PHONY: all
all: $(BUILD)/street64

$(BUILD)/frontend.o: main.cpp progress.hpp street64_board.h
	mkdir -p "$(BUILD)"
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++17 -Wall -Wextra -Wpedantic $(SDL_CFLAGS) -c main.cpp -o "$@"

$(BUILD)/street64: $(BUILD)/frontend.o $(BUILD)/libstreet64_board.so
	$(CXX) $(LDFLAGS) "$<" -L"$(BUILD)" -lstreet64_board $(SDL_LIBS) -Wl,-rpath,'$$ORIGIN' -o "$@"
