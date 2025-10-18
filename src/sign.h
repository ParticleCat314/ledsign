#pragma once
#include <string>
#include <unistd.h>
#include <stdio.h>
#include <vector>
#include <stdint.h>
#include <memory>
#include "graphics.h"
#include "led-matrix.h"

using namespace rgb_matrix;
struct Sign;


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
    size_t x;
    size_t y;
    size_t speed; // Speed of scrolling
    Color color = Color(255, 255, 255); // Default white color
    
    TextScrollingObject(
      const std::string &t,
      size_t xpos,
      size_t ypos,
      size_t spd,
      const Color &c = Color(255, 255, 255)
    );
    void Render(Sign &sign) override;
};


struct Sign {
    size_t width = 64;
    size_t height = 32;
    volatile bool interrupt_received = false;
    std::vector<std::shared_ptr<Renderable>> renderables;
    
    std::vector<std::string> fonts;

    RGBMatrix *canvas;
    

public:
    Sign();

    static Sign create();

    // Initialize the sign hardware. Must call before use.
    int Initialize();

    // Clear the sign display. i.e. set all pixels to "black".
    void clear();

    void drawText(const std::string &text, size_t x, size_t y, const Color &color);

    void setBrightness(int brightness);

    void handleInterrupt(bool interrupt);

    void swapBuffers();

    void render();
};


std::vector<std::shared_ptr<Renderable>> parseSignConfig(const std::string &config);
