#pragma once

#include <chrono>
#include <memory>
#include <string>
#include <vector>
#include "led-matrix.h"

// Forward declaration
struct Sign;

enum class RenderableType {
    STATIC,
    SCROLLING,
    ANIMATED,
};

/**
 * Abstract base class for renderable objects on the sign.
 */
struct Renderable {
    RenderableType type;
public:
    Renderable() = default;
    virtual ~Renderable() = default;
    virtual void Render(Sign &sign) = 0;
};

/**
 * Static text object that renders at a fixed position.
 */
struct TextObject : public Renderable {
public:
    std::string text;
    size_t x;
    size_t y;
    rgb_matrix::Color color = rgb_matrix::Color(255, 255, 255); // Default white color

    TextObject(
        const std::string &t,
        size_t xpos,
        size_t ypos,
        const rgb_matrix::Color &c = rgb_matrix::Color(255, 255, 255)
    );

    void Render(Sign &sign) override;
};

/**
 * Scrolling text object that moves horizontally across the display.
 */
struct TextScrollingObject : public Renderable {
public:
    std::string text;
    size_t y;
    size_t speed; // Pixels per second
    rgb_matrix::Color color = rgb_matrix::Color(255, 255, 255); // Default white color
    
    // Animation state - not mutable anymore, will be handled properly
    int current_x_offset = 0;
    std::chrono::steady_clock::time_point last_update = std::chrono::steady_clock::now();
    
    TextScrollingObject(
        const std::string &t,
        size_t ypos,
        size_t spd,
        const rgb_matrix::Color &c = rgb_matrix::Color(255, 255, 255)
    );
    
    void Render(Sign &sign) override;
};

// Helper functions for parsing
bool safeParseUInt(const std::string& str, size_t& result);
bool extractField(const std::string& config, size_t& pos, std::string& result);
bool validateEndToken(const std::string& config, size_t& pos);

/**
 * Parse sign configuration string into renderable objects.
 * Format: "TYPE;text;x;y;(r,g,b);[speed];END" where TYPE is STATIC or SCROLL
 * Examples:
 * "STATIC;Hello World;10;20;(255,0,0);END;SCROLL;Breaking News;15;(0,255,0);50;END"
 */
std::vector<std::shared_ptr<Renderable>> parseSignConfig(const std::string &config);
