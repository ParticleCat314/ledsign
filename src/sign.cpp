#include <string>
#include <unistd.h>
#include <stdio.h>
#include "sign.h"
#include <stdint.h>
#include <vector>
#include <memory>
#include <filesystem>



std::vector<std::shared_ptr<Renderable>> parseSignConfig(const std::string &config) {
  // Very lazy, we simply split the string by semicolons and create static text objects
  // We also assume the input is well-formed and enclosed in quotes like:
  // "Hello World";10;20;(255,0,0);END;"Goodbye!";5;25;(0,255,0);END
  std::vector<std::shared_ptr<Renderable>> renderables;
  size_t pos = 0;

  while (pos < config.length()) {
      // Find the next semicolon
      size_t next_semicolon = config.find(';', pos);
      if (next_semicolon == std::string::npos) {
          break;
      }
      std::string text = config.substr(pos, next_semicolon - pos);
      pos = next_semicolon + 1;

      // Get x position
      next_semicolon = config.find(';', pos);
      size_t x = std::stoul(config.substr(pos, next_semicolon - pos));
      pos = next_semicolon + 1;

      // Get y position
      next_semicolon = config.find(';', pos);
      size_t y = std::stoul(config.substr(pos, next_semicolon - pos));
      pos = next_semicolon + 1;

      // Get color
      next_semicolon = config.find(';', pos);
      std::string color_str = config.substr(pos, next_semicolon - pos);
      pos = next_semicolon + 1;

      // Parse color
      int r, g, b;
      sscanf(color_str.c_str(), "(%d,%d,%d)", &r, &g, &b);

      // Skip "END"
      next_semicolon = config.find(';', pos);
      pos = next_semicolon + 1;

      renderables.push_back(std::make_shared<TextObject>(text, x, y, Color(r, g, b)));
  }
  return renderables;
}

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
    matrix_options.hardware_mapping = "adafruit-hat";
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

void Sign::setFont(const std::string &font_path) {
    this->font = rgb_matrix::Font();
    if (!this->font.LoadFont(font_path.c_str())) {
        fprintf(stderr, "Couldn't load font %s\n", font_path.c_str());
        return;
    }
}

void Sign::clear() {
    canvas->Clear();
}

void Sign::drawText(const std::string &text, size_t x, size_t y, const Color &color) {
  this->font = rgb_matrix::Font();
  // Load the first font because I'm lazy
  // TODO: Font map

  if (!this->font.LoadFont(this->fonts[0].c_str())) {
      fprintf(stderr, "Couldn't load font %s\n", this->fonts[0].c_str());
      return;
  }
  rgb_matrix::DrawText(canvas, this->font, x, y, rgb_matrix::Color(color.r, color.g, color.b), nullptr, text.c_str());
}

void Sign::handleInterrupt(bool interrupt) {
    interrupt_received = interrupt;
}

void Sign::setBrightness(int brightness) {
    // Dummy implementation - in a real implementation this would set LED brightness
    printf("Setting brightness to: %d\n", brightness);
}

void Sign::swapBuffers() {
    // Later
}

void Sign::render() {
    for (const auto &renderable : renderables) {
        renderable->Render(*this);
    }
}



