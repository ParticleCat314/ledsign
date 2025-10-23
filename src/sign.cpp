#include "sign.h"
#include "constants.h"
#include "pixel-mapper.h"
#include <sstream>
#include <cctype>
#include <unistd.h>
#include <memory>
#include <filesystem>




Sign::Sign() {}

Sign::~Sign() {
    // Ensure interruption is set to stop any running render loops
    interrupt_received = true;
    
    // Clear the canvas if it exists
    if (canvas) {
        canvas->Clear();
    }
}

SignError Sign::Initialize() {
    RGBMatrix::Options matrix_options;
    rgb_matrix::RuntimeOptions runtime_opt;

    matrix_options.hardware_mapping = LedSignConstants::HARDWARE_MAPPING;
    matrix_options.rows = LedSignConstants::LED_ROWS;
    matrix_options.cols = LedSignConstants::LED_COLS;
    matrix_options.chain_length = LedSignConstants::LED_CHAIN;
    matrix_options.parallel = LedSignConstants::LED_PARALLEL;
    matrix_options.disable_hardware_pulsing = LedSignConstants::DISABLE_HARDWARE_PULSING;

    // Load all fonts into cache
    if (!loadAllFonts()) {
        fprintf(stderr, "Failed to load fonts\n");
        return SignError::FONT_LOAD_ERROR;
    }

    // Set default font
    const rgb_matrix::Font* default_font = getFont("6x10");
    if (default_font) {
        current_font = *default_font;
    } else {
        fprintf(stderr, "Default font 6x10 not found\n");
        return SignError::FONT_LOAD_ERROR;
    }

    auto p = rgb_matrix::FindPixelMapper("U-mapper",4,1);
    auto p2 = rgb_matrix::FindPixelMapper("Rotate",4,1,"180");

    if (!p) {
        fprintf(stderr, "Failed to create pixel mapper\n");
        return SignError::PIXEL_MAPPER_ERROR;
    }

    this->canvas = std::shared_ptr<RGBMatrix>(RGBMatrix::CreateFromOptions(matrix_options, runtime_opt));
  
    if (!canvas) {
        fprintf(stderr, "Failed to create RGB matrix. Check hardware configuration and permissions.\n");
        return SignError::MATRIX_CREATION_ERROR;
    }

    if (!this->canvas->ApplyPixelMapper(p)) {
        fprintf(stderr, "Failed to apply pixel mapper to canvas\n");
        return SignError::PIXEL_MAPPER_APPLY_ERROR;
    }
    if (!this->canvas->ApplyPixelMapper(p2)) {
        fprintf(stderr, "Failed to apply pixel mapper 2 to canvas\n");
        return SignError::PIXEL_MAPPER_APPLY_ERROR;
    }
    return SignError::SUCCESS;
}

void Sign::setFont(const std::string &font_path) {
    if (font_path.empty()) {
        fprintf(stderr, "Font path is empty.\n");
        return;
    }

    // Extract font name from path for cache lookup
    std::filesystem::path path(font_path);
    std::string font_name = path.stem().string();
    
    // Try to get from cache first
    const rgb_matrix::Font* cached_font = getFont(font_name);
    if (cached_font) {
        current_font = *cached_font;
        return;
    }

    // If not in cache, try to load it directly (fallback)
    rgb_matrix::Font temp_font;
    if (!temp_font.LoadFont(font_path.c_str())) {
        fprintf(stderr, "Couldn't load font %s\n", font_path.c_str());
        return;
    }

    // Cache the font and set as current
    auto font_ptr = std::make_unique<rgb_matrix::Font>();
    if (font_ptr->LoadFont(font_path.c_str())) {
        current_font = *font_ptr;
        font_cache[font_name] = std::move(font_ptr);
        fonts.push_back(font_path);
    }
}

void Sign::clear() {
    if (!canvas) {
        fprintf(stderr, "Canvas not initialized - cannot clear\n");
        return;
    }
    canvas->Clear();
}

void Sign::drawText(const std::string &text, size_t x, size_t y, const rgb_matrix::Color &color, const rgb_matrix::Font &font) const {
    if (!canvas) {
        fprintf(stderr, "Canvas not initialized - cannot draw text\n");
        return;
    }
    rgb_matrix::DrawText(canvas.get(), font, x, y, rgb_matrix::Color(color.r, color.g, color.b), nullptr, text.c_str());
}

void Sign::handleInterrupt(bool interrupt) {
    interrupt_received = interrupt;
}

void Sign::setBrightness(int brightness) const {
    if (!canvas) {
        fprintf(stderr, "Canvas not initialized - cannot set brightness\n");
        return;
    }
    if (brightness < LedSignConstants::MIN_BRIGHTNESS || brightness > LedSignConstants::MAX_BRIGHTNESS) {
        fprintf(stderr, "Invalid brightness value: %d (expected %d-%d)\n", 
                brightness, LedSignConstants::MIN_BRIGHTNESS, LedSignConstants::MAX_BRIGHTNESS);
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
            usleep(LedSignConstants::FRAME_DELAY_MICROSECONDS);
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

const rgb_matrix::Font* Sign::getFont(const std::string &font_name) const {
    auto it = font_cache.find(font_name);
    if (it != font_cache.end()) {
        return it->second.get();
    }
    return nullptr;
}

bool Sign::loadAllFonts() {
    const std::string font_dir = "./rpi-rgb-led-matrix/fonts/";
    
    // Clear existing cache
    font_cache.clear();
    fonts.clear();
    
    try {
        for (const auto &entry : std::filesystem::directory_iterator(font_dir)) {
            if (entry.path().extension() == ".bdf") {
                std::string font_path = entry.path().string();
                std::string font_name = entry.path().stem().string(); // filename without extension
                
                // Create a new font object
                auto font = std::make_unique<rgb_matrix::Font>();
                if (font->LoadFont(font_path.c_str())) {
                    font_cache[font_name] = std::move(font);
                    fonts.push_back(font_path);
                    printf("Loaded font: %s -> %s\n", font_name.c_str(), font_path.c_str());
                } else {
                    fprintf(stderr, "Failed to load font: %s\n", font_path.c_str());
                }
            }
        }
    } catch (const std::filesystem::filesystem_error& ex) {
        fprintf(stderr, "Failed to read font directory %s: %s\n", font_dir.c_str(), ex.what());
        return false;
    }
    
    if (font_cache.empty()) {
        fprintf(stderr, "No .bdf font files found in %s\n", font_dir.c_str());
        return false;
    }
    
    printf("Successfully loaded %zu fonts into cache\n", font_cache.size());
    return true;
}
