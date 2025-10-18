#pragma once
#include <string>
#include <unistd.h>
#include <stdio.h>
#include <vector>
#include <stdint.h>
#include <memory>


struct Color {
    uint8_t r, g, b;
    Color(uint8_t red, uint8_t green, uint8_t blue) : r(red), g(green), b(blue) {}
};
struct Sign;


struct Renderable {
public:
    Renderable() {}
    virtual ~Renderable() = default;
    virtual void render(Sign &sign) = 0;
};


struct TextObject : public Renderable {
public:
    std::string text;
    int x;
    int y;
    Color color = Color(255, 255, 255); // Default white color

    TextObject(const std::string &t, int xpos, int ypos, const Color &c = Color(255, 255, 255))
        : text(t), x(xpos), y(ypos), color(c) {}

    void render(Sign &sign) override;
};




struct Sign {
    int width = 64;
    int height = 32;
    volatile bool interrupt_received = false;
    std::vector<std::shared_ptr<Renderable>> renderables;


public:
    Sign() {}

    static Sign create();

    int Initialize();

    void clear();

    void drawText(const std::string &text, int x, int y, const Color &color);

    void scrollingText(const std::string &text, int speed);

    void setBrightness(int brightness);

    void handleInterrupt(bool interrupt) {
        interrupt_received = interrupt;
    }

    void swapBuffers();

    // Helper function to parse multiple renderables from a comma-separated list
    void parseRenderableList(const std::string &input) {
        std::vector<std::shared_ptr<Renderable>> result;

        if (input.empty()) {
            return;
        }

        size_t pos = 0;
        size_t start = 0;
        int braceCount = 0;

        // Parse comma-separated list of JSON-like objects
        for (size_t i = 0; i < input.length(); ++i) {
            if (input[i] == '{') {
                if (braceCount == 0) {
                    start = i;
                }
                braceCount++;
            } else if (input[i] == '}') {
                braceCount--;
                if (braceCount == 0) {
                    // Found complete object
                    std::string objectStr = input.substr(start, i - start + 1);
                    auto renderable = parseSingleRenderable(objectStr);
                    if (renderable) {
                        result.push_back(renderable);
                    }
                }
            }
        }

        renderables = result;
    }

    // Helper function to parse a single renderable object
    std::shared_ptr<Renderable> parseSingleRenderable(const std::string &objectStr) {
        if (objectStr.length() < 2 || objectStr[0] != '{' || objectStr.back() != '}') {
            return nullptr;
        }

        // Extract values from the object string
        std::string text;
        int x = 0, y = 0;
        uint8_t r = 255, g = 255, b = 255; // Default white

        // Parse text field
        size_t textPos = objectStr.find("text:");
        if (textPos != std::string::npos) {
            size_t quoteStart = objectStr.find('"', textPos);
            size_t quoteEnd = objectStr.find('"', quoteStart + 1);
            if (quoteStart != std::string::npos && quoteEnd != std::string::npos) {
                text = objectStr.substr(quoteStart + 1, quoteEnd - quoteStart - 1);
            }
        }

        // Parse x coordinate
        size_t xPos = objectStr.find("x:");
        if (xPos != std::string::npos) {
            size_t numStart = xPos + 2;
            size_t numEnd = objectStr.find_first_of(",}", numStart);
            if (numEnd != std::string::npos) {
                x = std::stoi(objectStr.substr(numStart, numEnd - numStart));
            }
        }

        // Parse y coordinate
        size_t yPos = objectStr.find("y:");
        if (yPos != std::string::npos) {
            size_t numStart = yPos + 2;
            size_t numEnd = objectStr.find_first_of(",}", numStart);
            if (numEnd != std::string::npos) {
                y = std::stoi(objectStr.substr(numStart, numEnd - numStart));
            }
        }

        // Parse r value
        size_t rPos = objectStr.find("r:");
        if (rPos != std::string::npos) {
            size_t numStart = rPos + 2;
            size_t numEnd = objectStr.find_first_of(",}", numStart);
            if (numEnd != std::string::npos) {
                r = static_cast<uint8_t>(std::stoi(objectStr.substr(numStart, numEnd - numStart)));
            }
        }

        // Parse g value
        size_t gPos = objectStr.find("g:");
        if (gPos != std::string::npos) {
            size_t numStart = gPos + 2;
            size_t numEnd = objectStr.find_first_of(",}", numStart);
            if (numEnd != std::string::npos) {
                g = static_cast<uint8_t>(std::stoi(objectStr.substr(numStart, numEnd - numStart)));
            }
        }

        // Parse b value
        size_t bPos = objectStr.find("b:");
        if (bPos != std::string::npos) {
            size_t numStart = bPos + 2;
            size_t numEnd = objectStr.find_first_of(",}", numStart);
            if (numEnd != std::string::npos) {
                b = static_cast<uint8_t>(std::stoi(objectStr.substr(numStart, numEnd - numStart)));
            }
        }

        // Create and return TextObject with parsed values
        if (!text.empty()) {
            Color color(r, g, b);
            return std::make_shared<TextObject>(text, x, y, color);
        }

        return nullptr;
    }

    void renderAll() {
        for (const auto &renderable : renderables) {
            renderable->render(*this);
        }
    }
};
