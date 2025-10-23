#include "parsecommand.h"
#include "sign.h"
#include <cctype>
#include <sstream>

TextObject::TextObject(const std::string &t, size_t xpos, size_t ypos, const rgb_matrix::Color &c, const std::string &font)
    : text(t), x(xpos), y(ypos), color(c), font_name(font) {
    type = RenderableType::STATIC;
}

void TextObject::Render(Sign &sign) {
    // Get the font for this text object from the sign's font cache
    const rgb_matrix::Font* font = sign.getFont(font_name);
    if (!font) {
        font = &sign.current_font; // Fallback to current font
    }
    sign.drawText(text, x, y, color, *font);
}

TextScrollingObject::TextScrollingObject(const std::string &t, size_t ypos, size_t spd, const rgb_matrix::Color &c, const std::string &font)
    : text(t), y(ypos), speed(spd), color(c), font_name(font) {
    type = RenderableType::SCROLLING;
    current_x_offset = LedSignConstants::DEFAULT_DISPLAY_WIDTH; // Start from right edge
    last_update = std::chrono::steady_clock::now();
}

void TextScrollingObject::Render(Sign &sign) {
    // Get the font for this text object from the sign's font cache
    const rgb_matrix::Font* font = sign.getFont(font_name);
    if (!font) {
        font = &sign.current_font; // Fallback to current font
    }
    
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
        text_width += font->CharacterWidth(c);
    }
    
    // Reset to right side when text has completely scrolled off left
    if (current_x_offset < -text_width) {
        current_x_offset = static_cast<int>(sign.width);
    }
    
    // Render the text at current position
    sign.drawText(text, current_x_offset, y, color, *font);
}

// Helper function to safely parse an unsigned integer without exceptions
bool safeParseUInt(const std::string& str, size_t& result) {
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
bool extractField(const std::string& config, size_t& pos, std::string& result) {
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
bool validateEndToken(const std::string& config, size_t& pos) {
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
    // Format: "TYPE;text;x;y;(r,g,b);[font];[speed];END" where TYPE is STATIC or SCROLL
    // Examples:
    // "STATIC;Hello World;10;20;(255,0,0);7x13;END;SCROLL;Breaking News;15;(0,255,0);50;6x10;END"

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
            // Static text: x;y;(r,g,b);font;END
            
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

            // Get font (optional, defaults to 6x10)
            std::string font_name = "6x10"; // Default font
            std::string font_str;
            if (extractField(config, pos, font_str)) {
                if (!font_str.empty()) {
                    font_name = font_str;
                }
            } else {
                // If extractField failed, we might be at END token, rewind pos
                // Try to validate END token directly
                if (pos < config.length() && config.substr(pos, 3) == "END") {
                    // We're at END, font is optional so use default
                } else {
                    fprintf(stderr, "Invalid static config: missing or malformed font/END token\n");
                    return {};
                }
            }

            // Validate END token
            if (!validateEndToken(config, pos)) {
                fprintf(stderr, "Invalid static config: missing or malformed END token\n");
                return {};
            }

            renderables.push_back(std::make_shared<TextObject>(text, x, y, rgb_matrix::Color(r, g, b), font_name));

        } else if (type == "SCROLL") {
            // Scrolling text: y;(r,g,b);speed;font;END
            
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

            // Get font (optional, defaults to 6x10)
            std::string font_name = "6x10"; // Default font
            std::string font_str;
            if (extractField(config, pos, font_str)) {
                if (!font_str.empty()) {
                    font_name = font_str;
                }
            } else {
                // If extractField failed, we might be at END token, rewind pos
                // Try to validate END token directly
                if (pos < config.length() && config.substr(pos, 3) == "END") {
                    // We're at END, font is optional so use default
                } else {
                    fprintf(stderr, "Invalid scroll config: missing or malformed font/END token\n");
                    return {};
                }
            }

            // Validate END token
            if (!validateEndToken(config, pos)) {
                fprintf(stderr, "Invalid scroll config: missing or malformed END token\n");
                return {};
            }

            renderables.push_back(std::make_shared<TextScrollingObject>(text, y, speed, rgb_matrix::Color(r, g, b), font_name));

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