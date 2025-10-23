#include "sign.h"
#include "pixel-mapper.h"
#include <sstream>
#include <cctype>

#define LEDROWS 16
#define LEDCOLS 32
#define LEDCHAIN 4
#define LEDPARALLEL 1
#define HARDWAREMAPPING "adafruit-hat"
#define DISABLEHARDWAREPULSING true

// Helper function to safely parse an unsigned integer without exceptions
static bool safeParseUInt(const std::string& str, size_t& result) {
    if (str.empty()) {
        return false;
    }
    
    // Check if all characters are digits
    for (char c : str) {
        if (!std::isdigit(c)) {
            return false;
        }
    }
    
    // Simple manual parsing to avoid std::stoul exceptions
    result = 0;
    for (char c : str) {
        size_t digit = c - '0';
        // Check for overflow before multiplying
        if (result > (SIZE_MAX - digit) / 10) {
            return false; // Would overflow
        }
        result = result * 10 + digit;
    }
    
    return true;
}

// Helper function to safely extract field between semicolons
static bool extractField(const std::string& config, size_t& pos, std::string& result) {
    if (pos >= config.length()) {
        return false;
    }
    
    size_t semicolon_pos = config.find(';', pos);
    if (semicolon_pos == std::string::npos) {
        return false;
    }
    
    // Ensure we don't have negative length (pos > semicolon_pos)
    if (semicolon_pos <= pos) {
        return false;
    }
    
    result = config.substr(pos, semicolon_pos - pos);
    pos = semicolon_pos + 1;
    return true;
}

// Helper function to validate END token
static bool validateEndToken(const std::string& config, size_t& pos) {
    if (pos + 3 > config.length()) {
        return false;
    }
    
    if (config.substr(pos, 3) != "END") {
        return false;
    }
    
    pos += 3;
    
    // Skip optional semicolon after END
    if (pos < config.length() && config[pos] == ';') {
        pos++;
    }
    
    return true;
}

std::vector<std::shared_ptr<Renderable>> parseSignConfig(const std::string &config) {
  // Parse configuration for mixed static and scrolling objects
  // Format: "TYPE;text;x;y;(r,g,b);[speed];END" where TYPE is STATIC or SCROLL
  // Examples:
  // "STATIC;Hello World;10;20;(255,0,0);END;SCROLL;Breaking News;15;(0,255,0);50;END"
  std::vector<std::shared_ptr<Renderable>> renderables;
  size_t pos = 0;

  while (pos < config.length()) {
      size_t start_pos = pos; // Safety check for infinite loops
      
      // Get object type
      std::string type;
      if (!extractField(config, pos, type)) {
          break; // End of config or malformed
      }

      // Get text
      std::string text;
      if (!extractField(config, pos, text)) {
          fprintf(stderr, "Invalid config format: missing text after type '%s'\n", type.c_str());
          return {};
      }

      if (type == "STATIC") {
          // Static text: x;y;(r,g,b);END
          
          // Get x position
          std::string x_str;
          if (!extractField(config, pos, x_str)) {
              fprintf(stderr, "Invalid static config: missing x position\n");
              return {};
          }
          size_t x;
          if (!safeParseUInt(x_str, x)) {
              fprintf(stderr, "Invalid x position: '%s' (must be a positive integer)\n", x_str.c_str());
              return {};
          }

          // Get y position
          std::string y_str;
          if (!extractField(config, pos, y_str)) {
              fprintf(stderr, "Invalid static config: missing y position\n");
              return {};
          }
          size_t y;
          if (!safeParseUInt(y_str, y)) {
              fprintf(stderr, "Invalid y position: '%s' (must be a positive integer)\n", y_str.c_str());
              return {};
          }

          // Get color
          std::string color_str;
          if (!extractField(config, pos, color_str)) {
              fprintf(stderr, "Invalid static config: missing color\n");
              return {};
          }

          // Parse color (r,g,b)
          int r, g, b;
          std::stringstream ss(color_str);
          char ignore;
          ss >> ignore >> r >> ignore >> g >> ignore >> b >> ignore;
          
          if (ss.fail() || r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255) {
              fprintf(stderr, "Invalid color format: '%s' (expected format: (r,g,b) with values 0-255)\n", color_str.c_str());
              return {};
          }

          // Validate END token
          if (!validateEndToken(config, pos)) {
              fprintf(stderr, "Invalid static config: missing or malformed END token\n");
              return {};
          }

          renderables.push_back(std::make_shared<TextObject>(text, x, y, Color(r, g, b)));

      } else if (type == "SCROLL") {
          // Scrolling text: y;(r,g,b);speed;END
          
          // Get y position
          std::string y_str;
          if (!extractField(config, pos, y_str)) {
              fprintf(stderr, "Invalid scroll config: missing y position\n");
              return {};
          }
          size_t y;
          if (!safeParseUInt(y_str, y)) {
              fprintf(stderr, "Invalid y position: '%s' (must be a positive integer)\n", y_str.c_str());
              return {};
          }

          // Get color
          std::string color_str;
          if (!extractField(config, pos, color_str)) {
              fprintf(stderr, "Invalid scroll config: missing color\n");
              return {};
          }

          // Parse color (r,g,b)
          int r, g, b;
          std::stringstream ss(color_str);
          char ignore;
          ss >> ignore >> r >> ignore >> g >> ignore >> b >> ignore;
          
          if (ss.fail() || r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255) {
              fprintf(stderr, "Invalid color format: '%s' (expected format: (r,g,b) with values 0-255)\n", color_str.c_str());
              return {};
          }

          // Get speed
          std::string speed_str;
          if (!extractField(config, pos, speed_str)) {
              fprintf(stderr, "Invalid scroll config: missing speed\n");
              return {};
          }
          size_t speed;
          if (!safeParseUInt(speed_str, speed)) {
              fprintf(stderr, "Invalid speed: '%s' (must be a positive integer)\n", speed_str.c_str());
              return {};
          }

          // Validate END token
          if (!validateEndToken(config, pos)) {
              fprintf(stderr, "Invalid scroll config: missing or malformed END token\n");
              return {};
          }

          renderables.push_back(std::make_shared<TextScrollingObject>(text, y, speed, Color(r, g, b)));

      } else {
          fprintf(stderr, "Unknown object type: '%s' (expected STATIC or SCROLL)\n", type.c_str());
          return {};
      }

      // Safety check: ensure position has advanced to prevent infinite loops
      if (pos <= start_pos) {
          fprintf(stderr, "Parser error: position did not advance (infinite loop detected)\n");
          return {};
      }
  }
  
  return renderables;
}

TextObject::TextObject(const std::string &t, size_t xpos, size_t ypos, const Color &c)
    : text(t), x(xpos), y(ypos), color(c) {}

void TextObject::Render(Sign &sign) {
    // Assume the font is already set in the sign
    sign.drawText(text, x, y, color, sign.current_font);
}

TextScrollingObject::TextScrollingObject(const std::string &t, size_t ypos, size_t spd, const Color &c)
    : text(t), y(ypos), speed(spd) {
    color = c;
    type = RenderableType::SCROLLING;
    current_x_offset = 64; // Start from right edge (assume 64px width for now)
}


void TextScrollingObject::Render(Sign &sign) {
    // Calculate time delta for smooth animation
    auto now = std::chrono::steady_clock::now();
    auto delta = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_update);
    last_update = now;
    
    // Update scroll position based on speed (pixels per second)
    float pixels_per_ms = static_cast<float>(speed) / 1000.0f;
    current_x_offset -= static_cast<int>(delta.count() * pixels_per_ms);
    
    // Calculate text width to know when to reset
    int text_width = 0;
    for (char c : text) {
        text_width += sign.current_font.CharacterWidth(c);
    }
    
    // Reset to right side when text has completely scrolled off left
    if (current_x_offset < -text_width) {
        current_x_offset = static_cast<int>(sign.width);
    }
    
    // Render the text at current position
    sign.drawText(text, current_x_offset, y, color, sign.current_font);
}


Sign::Sign() {}

Sign Sign::create() {
    return Sign();
}

int Sign::Initialize() {
    RGBMatrix::Options matrix_options;
    rgb_matrix::RuntimeOptions runtime_opt;

    matrix_options.hardware_mapping = HARDWAREMAPPING;
    matrix_options.rows = LEDROWS;
    matrix_options.cols = LEDCOLS;
    matrix_options.chain_length = LEDCHAIN;
    matrix_options.parallel = LEDPARALLEL;
    matrix_options.disable_hardware_pulsing = DISABLEHARDWAREPULSING;

    // Load fonts
    // We look for the font file in the current directory and load all .bdf files
    try {
        for (const auto &entry : std::filesystem::directory_iterator(".")) {
            if (entry.path().extension() == ".bdf") {
                std::string bdf_font_file = entry.path().string();
                this->fonts.push_back(bdf_font_file);
            }
        }
    } catch (const std::filesystem::filesystem_error& ex) {
        fprintf(stderr, "Failed to read directory for fonts: %s\n", ex.what());
        return 2;
    }

    if (fonts.empty()) {
        fprintf(stderr, "No .bdf font files found in the current directory.\n");
        return 3;
    }
    
    current_font = rgb_matrix::Font();
    if (!current_font.LoadFont(this->fonts[0].c_str())) {
        fprintf(stderr, "Failed to load default font: %s\n", this->fonts[0].c_str());
        return 4;
    }

    auto p = rgb_matrix::FindPixelMapper("U-mapper",4,1);
    auto p2 = rgb_matrix::FindPixelMapper("Rotate",4,1,"180");

    if (!p) {
        fprintf(stderr, "Failed to create pixel mapper\n");
        return 5;
    }

    this->canvas = RGBMatrix::CreateFromOptions(matrix_options, runtime_opt);
    if (!canvas) {
        fprintf(stderr, "Failed to create RGB matrix. Check hardware configuration and permissions.\n");
        return 6;
    }

    if (!this->canvas->ApplyPixelMapper(p)) {
        fprintf(stderr, "Failed to apply pixel mapper to canvas\n");
        delete canvas;
        canvas = nullptr;
        return 7;
    }
    if (!this->canvas->ApplyPixelMapper(p2)) {
        fprintf(stderr, "Failed to apply pixel mapper 2 to canvas\n");
        delete canvas;
        canvas = nullptr;
        return 7;
    }
    return 0;
}

void Sign::setFont(const std::string &font_path) {
    if (font_path.empty()) {
        fprintf(stderr, "Font path is empty.\n");
        return;
    }

    // Have we already loaded the font?
    auto it = font_cache.find(font_path);
    if (it != font_cache.end()) {
        this->current_font = it->second;
        return;
    }

    // Create temporary font for loading
    rgb_matrix::Font temp_font;
    if (!temp_font.LoadFont(font_path.c_str())) {
        fprintf(stderr, "Couldn't load font %s\n", font_path.c_str());
        return;
    }

    // Cache and set the loaded font
    font_cache[font_path] = temp_font;
    this->current_font = temp_font;
}

void Sign::clear() {
    if (!canvas) {
        fprintf(stderr, "Canvas not initialized - cannot clear\n");
        return;
    }
    canvas->Clear();
}

void Sign::drawText(const std::string &text, size_t x, size_t y, const Color &color, const rgb_matrix::Font &font) {
    if (!canvas) {
        fprintf(stderr, "Canvas not initialized - cannot draw text\n");
        return;
    }
    rgb_matrix::DrawText(canvas, font, x, y, rgb_matrix::Color(color.r, color.g, color.b), nullptr, text.c_str());
}

void Sign::handleInterrupt(bool interrupt) {
    interrupt_received = interrupt;
}

void Sign::setBrightness(int brightness) {
    if (!canvas) {
        fprintf(stderr, "Canvas not initialized - cannot set brightness\n");
        return;
    }
    if (brightness < 1 || brightness > 100) {
        fprintf(stderr, "Invalid brightness value: %d (expected 1-100)\n", brightness);
        return;
    }
    canvas->SetBrightness(brightness);
}

void Sign::render() {
    // If we have animated objects, start continuous rendering
    if (hasAnimatedObjects()) {
        // Continuous render loop for animations
        while (!interrupt_received) {
            renderFrame();
            usleep(16667); // ~60 FPS (16.67ms per frame)
        }
    } else {
        // Single render for static content
        renderFrame();
    }
}

void Sign::renderFrame() {
    // Clear the canvas
    clear();
    
    // Update timing
    auto now = std::chrono::steady_clock::now();
    last_render_time = now;
    
    // Render all objects
    for (const auto &renderable : renderables) {
        renderable->Render(*this);
    }
    
    // The RGB Matrix library handles double buffering automatically,
    // but we can add an explicit swap if needed in the future
}

bool Sign::hasAnimatedObjects() const {
    for (const auto &renderable : renderables) {
        if (renderable->type == RenderableType::SCROLLING || 
            renderable->type == RenderableType::ANIMATED) {
            return true;
        }
    }
    return false;
}

void Sign::render(const std::string &config) {
  this->renderables = parseSignConfig(config);
  this->render();
}
