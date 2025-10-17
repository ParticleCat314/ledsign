// Led matrix code
/*
#include "led-matrix.h"
#include "graphics.h"
#include <string>
#include <getopt.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

using namespace rgb_matrix;
const char* bdf_font_file = "fonts/6x10.bdf";
volatile bool interrupt_received = false;

static void InterruptHandler(int signo) {
  interrupt_received = true;
}

struct Sign {
    int width;
    int height;


    RGBMatrix::Options matrix_options;
    rgb_matrix::RuntimeOptions runtime_opt;

    RGBMatrix *canvas;

    Sign() {
        width = 64;
        height = 32;
    }

    static Sign create() {
        return Sign();
    }

    int Initialize() {
        this->matrix_options.hardware_mapping = "regular";  // or e.g. "adafruit-hat"
        this->matrix_options.rows = 16;
        this->matrix_options.cols = 32;
        this->matrix_options.chain_length = 4;
        this->matrix_options.parallel = 1;
        // Initialization code here
        rgb_matrix::Font font;

        if (!font.LoadFont(bdf_font_file)) {
          fprintf(stderr, "Couldn't load font '%s'\n", bdf_font_file);
          return 1;
        }
        this->canvas = RGBMatrix::CreateFromOptions(matrix_options, runtime_opt);
        if (canvas == NULL) {
          printf("This shouldn't happen lol");
          return 1;
        }
        return 0;
    }

    void clear() {
        // Clear the display
        canvas->Clear();
    }

    void drawText(const std::string &text, int x, int y, const Color &color) {
        // Draw text on the display at position (x, y) with the given color
        rgb_matrix::Font font;
        if (!font.LoadFont(bdf_font_file)) {
          fprintf(stderr, "Couldn't load font '%s'\n", bdf_font_file);
          return;
        }
        rgb_matrix::DrawText(canvas, font, x, y, color, nullptr, text.c_str());
    }

    void scrollingText(const std::string &text, int speed, const Color &color) {
        // Scroll text across the display at the given speed with the given color
        rgb_matrix::Font font;
        if (!font.LoadFont(bdf_font_file)) {
          fprintf(stderr, "Couldn't load font '%s'\n", bdf_font_file);
          return;
        }

        FrameCanvas *offscreen_canvas = canvas->CreateFrameCanvas();
        int x = offscreen_canvas->width();
        int y = (offscreen_canvas->height() + font.baseline()) / 2;

        int length = rgb_matrix::DrawText(offscreen_canvas, font, 0, y, color, nullptr, text.c_str());

        while (x + length > 0) {
            offscreen_canvas->Fill(0, 0, 0); // Clear
            rgb_matrix::DrawText(offscreen_canvas, font, x, y, color, nullptr, text.c_str());
            offscreen_canvas = canvas->SwapOnVSync(offscreen_canvas);
            usleep(1000000 / speed);
            x -= 1;
        }
    }
};
*/

#include <string>
#include <unistd.h>
#include <stdio.h>
#include "sign.h"
#include <stdint.h>

Sign Sign::create() {
    return Sign();
}

int Sign::Initialize() {
    return 0;
}


void Sign::clear() {

}


void Sign::drawText(const std::string &text, int x, int y, const Color &color) {
    printf("Drawing text at (%d, %d): %s\n", x, y, text.c_str());
    // Dummy drawText
}


void Sign::scrollingText(const std::string &text, int speed) {
    // Dummy scrollingText
    while (!interrupt_received) {
        // Simulate scrolling
        usleep(100000);
        printf("Scrolling: %s\n", text.c_str());
    }
}
void Sign::swapBuffers() {

}
void TextObject::render(Sign &sign) {
    printf("Rendering TextObject: text='%s', x=%d, y=%d, color=(%d,%d,%d)\n",
           text.c_str(), x, y, color.r, color.g, color.b);

    sign.drawText(text, x, y, color);
}
