#pragma once
#include <sys/stat.h>

namespace LedSignConstants {
    // LED Matrix Configuration
    constexpr int LED_ROWS = 16;
    constexpr int LED_COLS = 32;
    constexpr int LED_CHAIN = 4;
    constexpr int LED_PARALLEL = 1;
    constexpr const char* HARDWARE_MAPPING = "adafruit-hat";
    constexpr bool DISABLE_HARDWARE_PULSING = true;
    
    // Display Configuration
    constexpr size_t DEFAULT_DISPLAY_WIDTH = 64;
    constexpr size_t DEFAULT_DISPLAY_HEIGHT = 32;
    
    // Animation Configuration
    constexpr int TARGET_FPS = 60;
    constexpr int FRAME_DELAY_MICROSECONDS = 16667; // ~60 FPS (16.67ms per frame)
    
    // Brightness limits
    constexpr int MIN_BRIGHTNESS = 1;
    constexpr int MAX_BRIGHTNESS = 100;
    
    // Socket Configuration
    constexpr const char* SOCKET_PATH = "/tmp/ledsign.sock";
    constexpr int SOCKET_BACKLOG = 8;
    constexpr mode_t SOCKET_PERMISSIONS = 0700;
    constexpr size_t MAX_MESSAGE_SIZE = 64 * 1024; // 64KB sanity cap
}

/**
 * Error codes for Sign initialization and operations
 */
enum class SignError {
    SUCCESS = 0,
    GENERAL_ERROR = 1,
    FONT_DIRECTORY_ERROR = 2,
    NO_FONTS_FOUND = 3,
    FONT_LOAD_ERROR = 4,
    PIXEL_MAPPER_ERROR = 5,
    MATRIX_CREATION_ERROR = 6,
    PIXEL_MAPPER_APPLY_ERROR = 7
};