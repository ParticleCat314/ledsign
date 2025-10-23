"""
LED sign communication interface.

This module provides a Python interface to communicate with the LED sign hardware
through a Unix domain socket. It handles:
- Sending commands to the LED sign server
- Setting text with position and color
- Clearing the display
- Executing scheduled items from templates

The module acts as a bridge between the web application and the underlying
C++ LED sign control system.
"""

import socket
from sql import *

def send_command(command):
    """Send a command to the LED sign server and return the response."""
    SOCK_PATH = "/tmp/ledsign.sock"
    try:
        # Create Unix domain socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        
        # Connect to server
        sock.connect(SOCK_PATH)
        
        # Send command with newline
        command_line = command + "\n"
        sock.sendall(command_line.encode('utf-8'))
        
        # Read response until newline
        response = ""
        while True:
            data = sock.recv(1)
            if not data:
                break
            char = data.decode('utf-8')
            if char == '\n':
                break
            response += char
        
        sock.close()
        return response
        
    except FileNotFoundError:
        return "ERROR: LED sign server not running (socket not found)"
    except ConnectionRefusedError:
        return "ERROR: Connection refused by LED sign server"
    except Exception as e:
        return f"ERROR: {str(e)}"


def clear_sign():
    """Clear the LED sign display."""
    return send_command("CLEAR")


def set_text(text, x=0, y=10, color=(255, 255, 0)):
    """Set text on the LED sign with position and color."""
    r, g, b = color
    command = f"SETSTATIC;{text};{x};{y};{r},{g},{b};END;"
    return send_command(command)


def set(text, x=0, y=10, color=(255, 255, 0)):
    """Alias for set_text for backward compatibility."""
    return set_text(text, x, y, color)



def execute_scheduled_item(schedule_id, name, **kwargs):
    """
    Execute a scheduled item. This function is called by the scheduler.
    Args:
        schedule_id (int): ID of the scheduled item
        label (str): Label of the scheduled item
        **kwargs: Additional parameters for the scheduled action
    """
    
    #try:
    print(f"Executing scheduled item {schedule_id} with name '{name}'")
    scheduled_item = get_scheduled_item(schedule_id)

    # Get template data
    template = get_template(scheduled_item['template_id'])

    if not template:
        print(f"Template not found for schedule {schedule_id}")
        return

    
    template_data = parseJSONPayload(template['payload'])

    if not template_data:
        print(f"Invalid payload for template {template['id']}")
        return

    sign_name = template_data.get('name', 'LED Sign template?')
    sign_config = template_data.get('items', {})
    command = "SET"

    for item in sign_config:
        print(f"Processing item: {item}")
        if item.get('type') == 'static':
            text = item.get('content', name)
            x = item.get('x', 0)
            y = item.get('y', 10)
            color = tuple(item.get('color', [255, 255, 0]))
            print(f"Setting text on LED sign: '{text}' at ({x},{y}) with color {color}")

            command += f"STATIC;{text};{x};{y};({color[0]},{color[1]},{color[2]});END;"

        if item.get('type') == 'scrolling':
            text = item.get('content', name)
            x = item.get('x', 0)
            y = item.get('y', 10)
            color = tuple(item.get('color', [255, 255, 0]))
            speed = item.get('speed', 1)
            print(f"Setting scrolling text on LED sign: '{text}' at ({x},{y}) with color {color} and speed {speed}")
            command += f"SCROLL;{text};{x};{y};({color[0]},{color[1]},{color[2]});{speed};END;"

    response = send_command(command)
    print(f"LED sign response: {response}")


