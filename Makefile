# Makefile

# Compiler
CXX := g++

# Source files
SRCS := src/app.cpp src/sign.cpp src/parsecommand.cpp
CLIENT_SRCS := src/client.cpp

# Include and library directories
INCLUDES := -I rpi-rgb-led-matrix/include/
LIBDIRS := -L rpi-rgb-led-matrix/lib/

# Libraries
LIBS := -l:librgbmatrix.a

# Output executables
TARGET := sign
CLIENT_TARGET := client_app

# Compilation flags
CXXFLAGS := -Wall -Wextra

# Build rules
all: $(TARGET) $(CLIENT_TARGET)

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(LIBDIRS) -o $@ $^ $(LIBS)

$(CLIENT_TARGET): $(CLIENT_SRCS)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(LIBDIRS) -o $@ $^ $(LIBS)

# Clean rule
clean:
	rm -f $(TARGET) $(CLIENT_TARGET)
