#pragma once

#include <memory>
#include <string>
#include <unistd.h>
#include <stdio.h>
#include <vector>
#include <stdint.h>
#include <memory>
#include <chrono>
#include <unordered_map>
#include <stdint.h>
#include <filesystem>
#include <sstream>


#include "graphics.h"
#include "led-matrix.h"


using namespace rgb_matrix;
struct Sign;

#include <atomic>


enum class RenderableType {
    STATIC,
    SCROLLING,
    ANIMATED,
};

/*
  Abstract base class for renderable objects on the sign.
*/
struct Renderable {
    RenderableType type;
public:
    Renderable() {}
    virtual ~Renderable() = default;
    virtual void Render(Sign &sign) = 0;
};


struct TextObject : public Renderable {
public:
    std::string text;
    size_t x;
    size_t y;
    Color color = Color(255, 255, 255); // Default white color

    TextObject(
      const std::string &t,
      size_t xpos,
      size_t ypos,
      const Color &c = Color(255, 255, 255)
    );

    void Render(Sign &sign) override;
};

struct TextScrollingObject : public Renderable {
public:
    std::string text;
    size_t y;
    size_t speed; // Pixels per second
    Color color = Color(255, 255, 255); // Default white color
    
    // Animation state
    mutable int current_x_offset = 0;
    mutable std::chrono::steady_clock::time_point last_update = std::chrono::steady_clock::now();
    
    TextScrollingObject(
      const std::string &t,
      size_t ypos,
      size_t spd,
      const Color &c = Color(255, 255, 255)
    );
    void Render(Sign &sign) override;
};

std::vector<std::shared_ptr<Renderable>> parseSignConfig(const std::string &config);

struct Sign {
    size_t width = 64;
    size_t height = 32;

    std::atomic<bool> interrupt_received = false;

    std::vector<std::shared_ptr<Renderable>> renderables;
    

    // Available fonts as file paths
    std::vector<std::string> fonts;

    // Font cache
    std::unordered_map<std::string, rgb_matrix::Font> font_cache;

    rgb_matrix::Font current_font;

    RGBMatrix *canvas;
    
    // Animation timing
    std::chrono::steady_clock::time_point last_render_time = std::chrono::steady_clock::now();
    

public:
    Sign();

    static Sign create();

    int Initialize();

    void setFont(const std::string &font_path);

    void clear();

    void drawText(const std::string &text, size_t x, size_t y, const Color &color, const rgb_matrix::Font &font);

    void setBrightness(int brightness);

    void handleInterrupt(bool interrupt);

    void render();
    
    void renderFrame();
    
    bool hasAnimatedObjects() const;

    void render(const std::string &config);

    ~Sign() {
        if (canvas) delete canvas;
    }

};

