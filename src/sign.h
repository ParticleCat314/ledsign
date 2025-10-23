#pragma once

#include <atomic>
#include <chrono>
#include <filesystem>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "constants.h"
#include "graphics.h"
#include "led-matrix.h"
#include "parsecommand.h"

using namespace rgb_matrix;
struct Sign;

/**
 * LED Sign Display Controller
 * 
 * This class manages an RGB LED matrix display, providing functionality for:
 * - Rendering static and animated text
 * - Font management and caching
 * - Brightness control
 * - Animation timing and frame rendering
 */
struct Sign {
    size_t width = LedSignConstants::DEFAULT_DISPLAY_WIDTH;
    size_t height = LedSignConstants::DEFAULT_DISPLAY_HEIGHT;

    std::atomic<bool> interrupt_received = false;

    std::vector<std::shared_ptr<Renderable>> renderables;
    

    // Available fonts as file paths
    std::vector<std::string> fonts;

    // Font cache
    std::unordered_map<std::string, rgb_matrix::Font> font_cache;

    rgb_matrix::Font current_font;

    std::shared_ptr<RGBMatrix> canvas;
    
    // Animation timing
    std::chrono::steady_clock::time_point last_render_time = std::chrono::steady_clock::now();
    

public:
    /**
     * Constructor - creates an uninitialized Sign object.
     * Call Initialize() to set up the LED matrix hardware.
     */
    Sign();
    
    /**
     * Destructor - ensures proper cleanup of resources and stops any running animations.
     */
    ~Sign();

    /**
     * Initialize the LED matrix hardware and load fonts.
     * @return SignError::SUCCESS on success, or appropriate error code on failure
     */
    SignError Initialize();

    /**
     * Set the current font for text rendering.
     * @param font_path Path to a .bdf font file
     */
    void setFont(const std::string &font_path);

    /**
     * Clear the entire display.
     */
    void clear();

    /**
     * Draw text at the specified position with given color and font.
     * @param text Text string to render
     * @param x X coordinate (pixels from left)
     * @param y Y coordinate (pixels from top) 
     * @param color RGB color for the text
     * @param font Font to use for rendering
     */
    void drawText(const std::string &text, size_t x, size_t y, const rgb_matrix::Color &color, const rgb_matrix::Font &font) const;

    /**
     * Set display brightness.
     * @param brightness Brightness level (1-100)
     */
    void setBrightness(int brightness) const;

    /**
     * Signal interruption to stop animation loops.
     * @param interrupt true to interrupt, false to resume
     */
    void handleInterrupt(bool interrupt);

    /**
     * Start rendering all configured objects. Will run continuously if animated objects are present.
     */
    void render();
    
    /**
     * Render a single frame of all objects.
     */
    void renderFrame();
    
    /**
     * Check if any of the current renderables require animation.
     * @return true if continuous rendering is needed
     */
    bool hasAnimatedObjects() const;

    /**
     * Parse configuration string and render the specified objects.
     * @param config Configuration string defining objects to render
     */
    void render(const std::string &config);

};

