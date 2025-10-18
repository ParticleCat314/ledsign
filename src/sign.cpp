#include <string>
#include <unistd.h>
#include <stdio.h>
#include "sign.h"
#include <stdint.h>
#include <vector>
#include <memory>
#include <filesystem>



TextObject::TextObject(const std::string &t, size_t xpos, size_t ypos, const Color &c)
    : text(t), x(xpos), y(ypos), color(c) {}

void TextObject::Render(Sign &sign) {
    sign.drawText(text, x, y, color);
}

TextScrollingObject::TextScrollingObject(const std::string &t, size_t xpos, size_t ypos, size_t spd, const Color &c)
    : text(t), x(xpos), y(ypos), speed(spd) {
    color = c;
    type = RenderableType::SCROLLING;
}


void TextScrollingObject::Render(Sign &sign) {

}




Sign::Sign() {}

Sign Sign::create() {
    return Sign();
}

int Sign::Initialize() {
    RGBMatrix::Options matrix_options;
    rgb_matrix::RuntimeOptions runtime_opt;

    // I shouldn't hardcode these but oh well
    // Magic numbers are fun!
    matrix_options.hardware_mapping = "adafruit-hat";  // or e.g. "adafruit-hat"
    matrix_options.rows = 16;
    matrix_options.cols = 32;
    matrix_options.chain_length = 4;
    matrix_options.parallel = 1;
    matrix_options.disable_hardware_pulsing = true;

    // Load fonts
    // We look for the font file in the current directory and load all .bdf files
    for (const auto &entry : std::filesystem::directory_iterator(".")) {
        if (entry.path().extension() == ".bdf") {
            std::string bdf_font_file = entry.path().string();
            this->fonts.push_back(bdf_font_file);
        }
    }

    if (fonts.empty()) {
        fprintf(stderr, "No .bdf font files found in the current directory.\n");
        return 1;
    }
    
    auto p = rgb_matrix::FindPixelMapper("U-mapper;Rotate:90;Rotate:90",4,1);

    this->canvas = RGBMatrix::CreateFromOptions(matrix_options, runtime_opt);
    this->canvas->ApplyPixelMapper(p);

    if (canvas == NULL) {
        printf("This shouldn't happen lol");
        return 1;
    }

    return 0;
}


void Sign::clear() {
    canvas->Clear();
}

void Sign::drawText(const std::string &text, size_t x, size_t y, const Color &color) {
    printf("Drawing text at (%zu, %zu): %s\n", x, y, text.c_str());
    // Dummy drawText implementation
}

void Sign::handleInterrupt(bool interrupt) {
    interrupt_received = interrupt;
}

void Sign::setBrightness(int brightness) {
    // Dummy implementation - in a real implementation this would set LED brightness
    printf("Setting brightness to: %d\n", brightness);
}

void Sign::swapBuffers() {

}

void Sign::render() {
    for (const auto &renderable : renderables) {
        renderable->Render(*this);
    }
}



