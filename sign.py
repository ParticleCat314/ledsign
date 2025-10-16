''' 
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics


options = RGBMatrixOptions()
options.rows = 16
options.cols = 32
options.chain_length = 4
options.parallel = 1
options.hardware_mapping = 'regular'  # If you have an Adafruit HAT: 'adafruit-hat'
matrix = RGBMatrix(options=options)
offscreen_canvas = matrix.CreateFrameCanvas()
font = graphics.Font()
font.LoadFont("./fonts/7x13.bdf")

class Sign:
    def __init__(self, text, color=(255, 255, 0), speed=50):
        self.text = text
        self.color = graphics.Color(*color)
        self.speed = speed
        self.pos = offscreen_canvas.width
        self.color = (255, 255, 0)
        self.clear()

    def clear(self):
        offscreen_canvas.Clear()
        matrix.SwapOnVSync(offscreen_canvas)


    def set_text(self, text, x=0, y=10, color=self.color):
        self.text = text
        self.pos = offscreen_canvas.width
        self.color = graphics.Color(*color)
        self.clear()
        graphics.DrawText(offscreen_canvas, font, x, y, self.color, self.text)
'''


# Dummy class
class Sign:
    def __init__(self, text, color=(255, 255, 0), speed=50):
        self.text = text
        self.color = color
        self.speed = speed

    def clear(self):
        print("Sign cleared")

    def set_text(self, text, x=0, y=10, color=(255, 255, 0)):
        self.text = text
        self.color = color
        print( f"Sign text set to: {text} with color {color}" )

