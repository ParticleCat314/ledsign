# Helpers for validation of form data

def parseManualControlForm(form):
    """Parse and validate manual control form data"""
    text = form.get('text', '').strip()
    x = int(form.get('x', 0))
    y = int(form.get('y', 10))
    color_hex = form.get('color', '#ffff00').lstrip('#')
    
    if len(color_hex) != 6:
        raise ValueError("Invalid color format")
        
    color = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    
    return text, x, y, color

def parseTemplateForm(form):
    """Parse and validate template form data"""
    label = form.get('template_name', '').strip()
    if not label:
        raise ValueError("Template name cannot be empty")
    
    # Further parsing can be added here as needed
    return label

def parseScheduleForm(form):
    """Parse and validate schedule form data"""
    schedule_name = form.get('schedule_name', '').strip()
    scheduled_datetime = form.get('scheduled_datetime', '')
    is_recurring = 'is_recurring' in form
    template_id = form.get('template_id', None)
    recurring_weekdays = None
    text = form.get('custom_text', None).strip()
    
    if is_recurring:
        weekdays = form.getlist('weekdays')
        if weekdays:
            recurring_weekdays = ','.join(weekdays)
        scheduled_datetime = form.get('recurring_time', '')
        if not scheduled_datetime:
            scheduled_datetime = None
        
    # Further parsing can be added here as needed
    return {
        'schedule_name': schedule_name,
        'scheduled_datetime': scheduled_datetime,
        'is_recurring': is_recurring,
        'template_id': template_id,
        'recurring_weekdays': recurring_weekdays,
        'text': text,
    }


def parse_form(form):
    """Parse form data into JSON payload"""
    template_type = "static"
    payload = {
        'name': form.get('template_name', 'Unnamed_Template'),
        'items': [],
    }


    # Loop through all "text_content_X" fields
    i = 0
    while f'text_content_{i}' in form:
        content = form.get(f'text_content_{i}', '').strip()
        if not content:  # Skip empty content
            i += 1
            continue
            
        try:
            x = int(form.get(f'text_x_{i}', 0))
            y = int(form.get(f'text_y_{i}', 10))
            color_hex = form.get(f'text_color_{i}', "#95ff00").lstrip('#')
            
            # Validate color format
            if len(color_hex) != 6:
                raise ValueError(f"Invalid color format for item {i}")
                
            color = [int(color_hex[j:j+2], 16) for j in (0, 2, 4)]
            element_type = form.get(f'element_type_{i}', 'static')

            item = {
                'type': element_type,
                'content': content,
                'x': x,
                'y': y,
                'color': color,
            }
            
            if element_type == 'mixed':
                speed = int(form.get(f'text_speed_{i}', 1))
                item = {
                    'type': 'mixed',
                    'content': content,
                    'x': x,
                    'y': y,
                    'color': color,
                    'speed': speed,
                }

            payload['items'].append(item)
            
        except (ValueError, TypeError) as e:
            # Skip malformed items but continue processing
            pass
            
        i += 1

    return payload


