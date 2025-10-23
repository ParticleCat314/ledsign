"""
Database management for LED sign scheduling system.

This module handles all database operations for the LED sign web application:
- Template storage and management (text, colors, positioning)
- Schedule storage and management (one-time and recurring schedules)
- Database initialization and maintenance
- Helper functions for weekday scheduling and cron expressions

Uses SQLite with a connection decorator pattern for automatic connection management.
"""

# Standard library imports
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("schedule.db")

def parseJSONPayload(payload):
    try:
        data = json.loads(payload)
        return data
    except json.JSONDecodeError:
        print("Invalid JSON payload")
        return None

# Database connection decorator
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
            name TEXT NOT NULL,
            payload TEXT NOT NULL
        );


        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scheduled_datetime TEXT NOT NULL,
            is_recurring INTEGER NOT NULL DEFAULT 0,
            recurring_weekdays TEXT,
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


# Schedule Management Functions
@with_conn
def add_scheduled_item(conn, name, scheduled_datetime, is_recurring=False, template_id=None, recurring_weekdays=None):
    """
    Add a new scheduled item to the database.
    
    Args:
        name (str): Human-readable label for the scheduled item
        scheduled_datetime (str): ISO format datetime string (e.g., '2024-01-01 12:00:00')
        is_recurring (bool): Whether this is a recurring item
        template_id (int, optional): ID of the template to use
        recurring_weekdays (str, optional): Comma-separated weekdays (0=Monday, 6=Sunday) e.g., "0,2,4"
    
    Returns:
        int: The ID of the newly created scheduled item
    """
    cursor = conn.execute(
        "INSERT INTO schedule (name, scheduled_datetime, is_recurring, template_id, recurring_weekdays) VALUES (?, ?, ?, ?, ?)",
        (name, scheduled_datetime, int(is_recurring), template_id, recurring_weekdays)
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


# Template Management Functions

@with_conn
def add_template(conn, name, payload):
    """
    Add a new template to the database.
    
    Args:
        name (str): Human-readable label for the template
        payload (str): JSON payload containing sign configuration
        template_type (str): Type of template ('static', 'scrolling', 'animation')
    
    Returns:
        int: The ID of the newly created template
    """
    cursor = conn.execute(
        "INSERT INTO templates (name, payload) VALUES (?, ?)",
        (name, payload)
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
def update_template(conn, template_id, name=None, payload=None, template_type=None):
    """
    Update an existing template.
    
    Args:
        template_id (int): ID of the template to update
        name (str, optional): New label
        payload (str, optional): New JSON payload
        template_type (str, optional): New template type
    
    Returns:
        bool: True if template was updated, False if template didn't exist
    """
    updates = []
    params = []
    
    if name is not None:
        updates.append("name= ?")
        params.append(name)
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
    cursor = conn.execute("SELECT * FROM templates ORDER BY name")
    return cursor.fetchall()


@with_conn
def get_template_by_name(conn, name):
    """
    Get a template by its name.
    
    Args:
        name (str): name of the template
    
    Returns:
        sqlite3.Row or None: The template data or None if not found
    """
    cursor = conn.execute("SELECT * FROM templates WHERE name = ?", (name,))
    return cursor.fetchone()


# Helper Functions for Weekday Scheduling

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

def get_last_run():
    """
    Get the last run scheduled item.
    
    Returns:
        dict or None: Dictionary with 'last_run_datetime' and 'schedule_id', or None if not set
    """
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


def recover_scheduled_jobs():
    """Rerun the last job or the next job if ready."""
    from sign import execute_scheduled_item
        
    last_run = get_last_run()
    if last_run:
        last_run_time = datetime.fromisoformat(last_run['last_run_datetime'])
        schedule_id = last_run['schedule_id']
        schedule = get_scheduled_item(schedule_id)
        if schedule:
            # Re-execute the last job
            print(f"Re-executing last job: {schedule['name']}")
            execute_scheduled_item(schedule_id=schedule_id, name=schedule['name'])
            return





def debug_schedule():
    """Insert test scheduled items for debugging purposes."""
    from datetime import timedelta

    # Add 5 test scheduled items in the next 5 minutes
    now = datetime.now()
    for i in range(50):
        scheduled_time = now + timedelta(seconds=i+2)
        add_scheduled_item(
            name=f"Test Item {i+1}",
            template_id=1,
            scheduled_datetime=scheduled_time.isoformat(sep=' ', timespec='seconds'),
            is_recurring=True,
            recurring_weekdays="0,1,2,3,4,5,6",
        )


    print("Inserted test scheduled items.")

