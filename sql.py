import sqlite3
import time
import json
from datetime import datetime
from pathlib import Path
from threading import Event


DB_PATH = Path(__file__).with_name("schedule.db")
STOP = Event()


### Cursed decorator to manage DB connection ###
def with_conn(fn):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)  # autocommit
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.row_factory = sqlite3.Row
            return fn(conn, *args, **kwargs)
        finally:
            conn.close()

    return wrapper


@with_conn
def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            payload TEXT NOT NULL,
            template_type TEXT NOT NULL DEFAULT 'static'
        );


        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            scheduled_datetime TEXT NOT NULL,
            is_recurring INTEGER NOT NULL DEFAULT 0,
            recurring_weekdays TEXT,
            recurring_time TEXT,
            end_time TEXT DEFAULT NULL,
            template_id INTEGER,
            FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
        );
        """
    )
    

    # Store the last run job for graceful recovery upon restarting
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS last_run (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_run_datetime TEXT,
            schedule_id INTEGER,
            FOREIGN KEY (schedule_id) REFERENCES schedule(id) ON DELETE SET NULL
        );
        """
    )




### We store the exact sign configuration as JSON payloads in the DB
### There are probably better ways to do this, but I'm lazy.
'''
Static Template:
{
    "type": "static",
    "text": [
        {
            "content": "Hello World",
            "x": 0,
            "y": 10,
            "color": [255, 255, 0],
            "size": 1
        },
        {
            "content": "Line 2",
            "x": 0,
            "y": 20,
            "color": [0, 255, 0],
            "size": 1
        }
    ]
}

Scrolling Template:
{
    "type": "scrolling",
    "text": [
        {
            "content": "This text will scroll across the screen",
            "y": 10,
            "color": [255, 255, 0],
            "speed": 50,
            "direction": "left"
        }
    ]
}

Animation Template:
{
    "type": "animation",
    "text": [
        {
            "content": "FLASH!",
            "x": 10,
            "y": 10,
            "color": [255, 0, 0],
            "effect": "blink",
            "duration": 5
        }
    ]
}
'''


def parseJSONPayload(payload):
    try:
        data = json.loads(payload)
        return data
    except json.JSONDecodeError:
        print("Invalid JSON payload")
        return None


### Schedule Management Functions ###

@with_conn
def add_scheduled_item(conn, label, scheduled_datetime, is_recurring=False, template_id=None, recurring_weekdays=None, recurring_time=None):
    """
    Add a new scheduled item to the database.
    
    Args:
        label (str): Human-readable label for the scheduled item
        scheduled_datetime (str): ISO format datetime string (e.g., '2024-01-01 12:00:00')
        is_recurring (bool): Whether this is a recurring item
        template_id (int, optional): ID of the template to use
        recurring_weekdays (str, optional): Comma-separated weekdays (0=Monday, 6=Sunday) e.g., "0,2,4"
        recurring_time (str, optional): Time for recurring items (HH:MM format) e.g., "09:30"
    
    Returns:
        int: The ID of the newly created scheduled item
    """
    cursor = conn.execute(
        "INSERT INTO schedule (label, scheduled_datetime, is_recurring, template_id, recurring_weekdays, recurring_time) VALUES (?, ?, ?, ?, ?, ?)",
        (label, scheduled_datetime, int(is_recurring), template_id, recurring_weekdays, recurring_time)
    )
    return cursor.lastrowid


@with_conn
def remove_scheduled_item(conn, item_id):
    """
    Remove a scheduled item from the database.
    
    Args:
        item_id (int): ID of the scheduled item to remove
    
    Returns:
        bool: True if item was removed, False if item didn't exist
    """
    cursor = conn.execute("DELETE FROM schedule WHERE id = ?", (item_id,))
    return cursor.rowcount > 0


@with_conn
def update_scheduled_item(conn, item_id, label=None, scheduled_datetime=None, is_recurring=None, template_id=None, recurring_weekdays=None, recurring_time=None):
    """
    Update an existing scheduled item.
    
    Args:
        item_id (int): ID of the scheduled item to update
        label (str, optional): New label
        scheduled_datetime (str, optional): New scheduled datetime
        is_recurring (bool, optional): New recurring status
        template_id (int, optional): New template ID
        recurring_weekdays (str, optional): New recurring weekdays
        recurring_time (str, optional): New recurring time
    
    Returns:
        bool: True if item was updated, False if item didn't exist
    """
    updates = []
    params = []
    
    if label is not None:
        updates.append("label = ?")
        params.append(label)
    if scheduled_datetime is not None:
        updates.append("scheduled_datetime = ?")
        params.append(scheduled_datetime)
    if is_recurring is not None:
        updates.append("is_recurring = ?")
        params.append(int(is_recurring))
    if template_id is not None:
        updates.append("template_id = ?")
        params.append(template_id)
    if recurring_weekdays is not None:
        updates.append("recurring_weekdays = ?")
        params.append(recurring_weekdays)
    if recurring_time is not None:
        updates.append("recurring_time = ?")
        params.append(recurring_time)
    
    if not updates:
        return False
    
    params.append(item_id)
    query = f"UPDATE schedule SET {', '.join(updates)} WHERE id = ?"
    cursor = conn.execute(query, params)
    return cursor.rowcount > 0


@with_conn
def get_scheduled_item(conn, item_id):
    """
    Get a specific scheduled item by ID.
    
    Args:
        item_id (int): ID of the scheduled item
    
    Returns:
        sqlite3.Row or None: The scheduled item data or None if not found
    """
    cursor = conn.execute("SELECT * FROM schedule WHERE id = ?", (item_id,))
    return cursor.fetchone()


@with_conn
def get_all_scheduled_items(conn):
    """
    Get all scheduled items from the database.
    
    Returns:
        list[sqlite3.Row]: List of all scheduled items
    """
    cursor = conn.execute("SELECT * FROM schedule ORDER BY scheduled_datetime")
    return cursor.fetchall()


@with_conn
def get_scheduled_items_by_datetime(conn, start_datetime, end_datetime=None):
    """
    Get scheduled items within a datetime range.
    
    Args:
        start_datetime (str): Start datetime (ISO format)
        end_datetime (str, optional): End datetime (ISO format). If None, gets items after start_datetime
    
    Returns:
        list[sqlite3.Row]: List of scheduled items in the range
    """
    if end_datetime is None:
        cursor = conn.execute(
            "SELECT * FROM schedule WHERE scheduled_datetime >= ? ORDER BY scheduled_datetime",
            (start_datetime,)
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM schedule WHERE scheduled_datetime >= ? AND scheduled_datetime <= ? ORDER BY scheduled_datetime",
            (start_datetime, end_datetime)
        )
    return cursor.fetchall()


@with_conn
def get_recurring_scheduled_items(conn):
    """
    Get all recurring scheduled items.
    
    Returns:
        list[sqlite3.Row]: List of recurring scheduled items
    """
    cursor = conn.execute("SELECT * FROM schedule WHERE is_recurring = 1 ORDER BY scheduled_datetime")
    return cursor.fetchall()


@with_conn
def clear_expired_scheduled_items(conn, before_datetime):
    """
    Remove all non-recurring scheduled items that are before the specified datetime.
    
    Args:
        before_datetime (str): Datetime string (ISO format)
    
    Returns:
        int: Number of items removed
    """
    cursor = conn.execute(
        "DELETE FROM schedule WHERE scheduled_datetime < ? AND is_recurring = 0",
        (before_datetime,)
    )
    return cursor.rowcount


### Template Management Functions ###

@with_conn
def add_template(conn, label, payload, template_type='static'):
    """
    Add a new template to the database.
    
    Args:
        label (str): Human-readable label for the template
        payload (str): JSON payload containing sign configuration
        template_type (str): Type of template ('static', 'scrolling', 'animation')
    
    Returns:
        int: The ID of the newly created template
    """
    cursor = conn.execute(
        "INSERT INTO templates (label, payload, template_type) VALUES (?, ?, ?)",
        (label, payload, template_type)
    )
    return cursor.lastrowid


@with_conn
def remove_template(conn, template_id):
    """
    Remove a template from the database.
    
    Args:
        template_id (int): ID of the template to remove
    
    Returns:
        bool: True if template was removed, False if template didn't exist
    """
    cursor = conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    return cursor.rowcount > 0


@with_conn
def update_template(conn, template_id, label=None, payload=None, template_type=None):
    """
    Update an existing template.
    
    Args:
        template_id (int): ID of the template to update
        label (str, optional): New label
        payload (str, optional): New JSON payload
        template_type (str, optional): New template type
    
    Returns:
        bool: True if template was updated, False if template didn't exist
    """
    updates = []
    params = []
    
    if label is not None:
        updates.append("label = ?")
        params.append(label)
    if payload is not None:
        updates.append("payload = ?")
        params.append(payload)
    if template_type is not None:
        updates.append("template_type = ?")
        params.append(template_type)
    
    if not updates:
        return False
    
    params.append(template_id)
    query = f"UPDATE templates SET {', '.join(updates)} WHERE id = ?"
    cursor = conn.execute(query, params)
    return cursor.rowcount > 0


@with_conn
def get_template(conn, template_id):
    """
    Get a specific template by ID.
    
    Args:
        template_id (int): ID of the template
    
    Returns:
        sqlite3.Row or None: The template data or None if not found
    """
    cursor = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    return cursor.fetchone()


@with_conn
def get_all_templates(conn):
    """
    Get all templates from the database.
    
    Returns:
        list[sqlite3.Row]: List of all templates
    """
    cursor = conn.execute("SELECT * FROM templates ORDER BY label")
    return cursor.fetchall()


@with_conn
def get_template_by_label(conn, label):
    """
    Get a template by its label.
    
    Args:
        label (str): Label of the template
    
    Returns:
        sqlite3.Row or None: The template data or None if not found
    """
    cursor = conn.execute("SELECT * FROM templates WHERE label = ?", (label,))
    return cursor.fetchone()


### Helper Functions for Weekday Scheduling ###

def create_cron_from_weekdays_time(weekdays_str, time_str):
    """
    Create a cron expression from weekdays string and time string.
    
    Args:
        weekdays_str (str): Comma-separated weekdays (0=Monday, 6=Sunday) e.g., "0,2,4"
        time_str (str): Time in HH:MM format e.g., "09:30"
    
    Returns:
        str: Cron expression
    """
    if not weekdays_str or not time_str:
        return None
    
    try:
        # Parse time
        hour, minute = map(int, time_str.split(':'))
        
        # Convert weekdays (0=Monday to 6=Sunday) to cron format (0=Sunday to 6=Saturday)
        weekdays = weekdays_str.split(',')
        cron_weekdays = []
        for day in weekdays:
            day_int = int(day.strip())
            # Convert: 0(Mon)→1, 1(Tue)→2, ..., 6(Sun)→0
            cron_day = 0 if day_int == 6 else day_int + 1
            cron_weekdays.append(str(cron_day))
        
        # Create cron expression: minute hour * * weekdays
        cron_expression = f"{minute} {hour} * * {','.join(cron_weekdays)}"
        return cron_expression
    except (ValueError, IndexError):
        return None


def get_weekday_names(weekdays_str):
    """
    Convert weekdays string to human-readable names.
    
    Args:
        weekdays_str (str): Comma-separated weekdays (0=Monday, 6=Sunday)
    
    Returns:
        str: Human-readable weekday names
    """
    if not weekdays_str:
        return ""
    
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    try:
        weekdays = weekdays_str.split(',')
        names = [weekday_names[int(day.strip())] for day in weekdays]
        return ', '.join(names)
    except (ValueError, IndexError):
        return weekdays_str


### Scheduler Integration Functions ###

def load_scheduled_jobs():
    """
    Load all scheduled jobs from the database and add them to the scheduler.
    This function is called during application startup.
    """
    from app import scheduler  # Import here to avoid circular imports
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.cron import CronTrigger
    
    scheduled_items = get_all_scheduled_items()
    
    for item in scheduled_items:
        try:
            # Parse the scheduled datetime
            scheduled_dt = datetime.fromisoformat(item['scheduled_datetime'])
            
            # Skip past items unless they're recurring
            if not item['is_recurring'] and scheduled_dt < datetime.now():
                continue
            
            # Get template payload if template_id is specified
            payload_data = None
            if item['template_id']:
                template = get_template(item['template_id'])
                if template:
                    payload_data = parseJSONPayload(template['payload'])
            
            # Create job kwargs
            job_kwargs = {
                'schedule_id': item['id'],
                'label': item['label']
            }
            
            # Add payload data if available
            if payload_data and 'text' in payload_data:
                for text_item in payload_data['text']:
                    job_kwargs.update({
                        'text': text_item.get('content', ''),
                        'x': text_item.get('x', 0),
                        'y': text_item.get('y', 10),
                        'color': tuple(text_item.get('color', [255, 255, 0]))
                    })
                    break  # Use first text item for now
            
            # Determine trigger type
            if item['is_recurring']:
                # For recurring items, use weekday/time if available
                if item['recurring_weekdays'] and item['recurring_time']:
                    cron_expr = create_cron_from_weekdays_time(item['recurring_weekdays'], item['recurring_time'])
                    if cron_expr:
                        trigger = CronTrigger.from_crontab(cron_expr)
                    else:
                        trigger = CronTrigger.from_crontab('0 * * * *')  # Fallback: every hour
                else:
                    trigger = CronTrigger.from_crontab('0 * * * *')  # Default: every hour
            else:
                # One-time scheduled item
                trigger = DateTrigger(run_date=scheduled_dt)
            
            # Add job to scheduler
            scheduler.add_job(
                func=execute_scheduled_item,
                trigger=trigger,
                id=f"schedule_{item['id']}",
                kwargs=job_kwargs,
                replace_existing=True
            )
            
            print(f"Loaded scheduled job: {item['label']} at {item['scheduled_datetime']}")
            
        except Exception as e:
            print(f"Error loading scheduled job {item['id']}: {e}")


def execute_scheduled_item(schedule_id, label, **kwargs):
    """
    Execute a scheduled item. This function is called by the scheduler.
    
    Args:
        schedule_id (int): ID of the scheduled item
        label (str): Label of the scheduled item
        **kwargs: Additional parameters for the scheduled action
    """
    print(f"Executing scheduled item: {label} (ID: {schedule_id})")
    
    try:
        # Get the scheduled item and its template
        scheduled_item = get_scheduled_item(schedule_id)
        if not scheduled_item or not scheduled_item['template_id']:
            # Fallback to simple text display
            text = kwargs.get('text', label)
            x = kwargs.get('x', 0)
            y = kwargs.get('y', 10)
            color = kwargs.get('color', (255, 255, 0))
            set_text(text=text, x=x, y=y, color=color)
            return
        
        # Get template data
        template = get_template(scheduled_item['template_id'])
        if not template:
            print(f"Template not found for schedule {schedule_id}")
            return
        
        payload_data = parseJSONPayload(template['payload'])
        if not payload_data:
            print(f"Invalid payload for template {template['id']}")
            return
        
        # Execute based on template type
        template_type = template.get('template_type', 'static')
        
        if template_type == 'scrolling':
            execute_scrolling_template(payload_data)
        elif template_type == 'animation':
            execute_animation_template(payload_data)
        else:  # static or unknown
            execute_static_template(payload_data)
            
    except Exception as e:
        print(f"Error executing scheduled item {schedule_id}: {e}")
        # Fallback to simple display
        text = kwargs.get('text', label)
        set_text(text=text, x=0, y=10, color=(255, 255, 0))


def execute_static_template(payload_data):
    """Execute a static template with multiple text items."""
    from sign import s
    
    # Clear the sign first
    s.clear()
    
    # Display all text items
    if 'text' in payload_data:
        for text_item in payload_data['text']:
            content = text_item.get('content', '')
            x = text_item.get('x', 0)
            y = text_item.get('y', 10)
            color = tuple(text_item.get('color', [255, 255, 0]))
            
            # For static templates, we'll display all text items simultaneously
            # In a real implementation, you might want to render them all to the same canvas
            s.set_text(content, x, y, color)


def execute_scrolling_template(payload_data):
    """Execute a scrolling template."""
    from sign import s
    
    # For scrolling, we'll use the first text item
    if 'text' in payload_data and payload_data['text']:
        text_item = payload_data['text'][0]
        content = text_item.get('content', '')
        y = text_item.get('y', 10)
        color = tuple(text_item.get('color', [255, 255, 0]))
        speed = text_item.get('speed', 50)
        direction = text_item.get('direction', 'left')
        
        # Use the scrolling function from sign.py
        scroll_text(content, y, color, speed, direction)


def execute_animation_template(payload_data):
    """Execute an animation template."""
    from sign import s
    
    # For animation, we'll use the first text item
    if 'text' in payload_data and payload_data['text']:
        text_item = payload_data['text'][0]
        content = text_item.get('content', '')
        x = text_item.get('x', 0)
        y = text_item.get('y', 10)
        color = tuple(text_item.get('color', [255, 255, 0]))
        effect = text_item.get('effect', 'blink')
        duration = text_item.get('duration', 5)
        
        # Use the animation function from sign.py
        animate_text(content, x, y, color, effect, duration)


def get_last_run():
    """
    Get the last run scheduled item.
    
    Returns:
        dict or None: Dictionary with 'last_run_datetime' and 'schedule_id', or None if not set
    """
    from sign import s  # Import here to avoid circular imports
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM last_run WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'last_run_datetime': row['last_run_datetime'],
            'schedule_id': row['schedule_id']
        }
    return None


def set_text(text, x=0, y=10, color=(255, 255, 0)):
    """
    Set text on the LED sign.
    
    Args:
        text (str): Text to display
        x (int): X position
        y (int): Y position  
        color (tuple): RGB color tuple
    """
    from sign import s  # Import here to avoid circular imports
    s.set_text(text, x, y, color)


def scroll_text(text, y=10, color=(255, 255, 0), speed=50, direction='left'):
    """
    Scroll text on the LED sign.
    
    Args:
        text (str): Text to scroll
        y (int): Y position
        color (tuple): RGB color tuple
        speed (int): Scroll speed
        direction (str): Scroll direction ('left' or 'right')
    """
    from sign import s
    # For now, just display the text - scrolling would need threading
    # In a real implementation, this would start a scrolling animation
    s.set_text(f"[SCROLL {direction.upper()}] {text}", 0, y, color)


def animate_text(text, x=0, y=10, color=(255, 255, 0), effect='blink', duration=5):
    """
    Animate text on the LED sign.
    
    Args:
        text (str): Text to animate
        x (int): X position
        y (int): Y position
        color (tuple): RGB color tuple
        effect (str): Animation effect ('blink', 'fade', 'rainbow')
        duration (int): Animation duration in seconds
    """
    from sign import s
    # For now, just display the text with effect prefix
    # In a real implementation, this would start an animation
    s.set_text(f"[{effect.upper()}] {text}", x, y, color)