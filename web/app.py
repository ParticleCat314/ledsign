import json
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

# Local imports
import sign
from sign import clear_sign, execute_scheduled_item
from sql import *
from form import *


# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# App configuration
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Initialize scheduler
scheduler = BackgroundScheduler(
    job_defaults=dict(coalesce=True, max_instances=1, misfire_grace_time=10)
)


# Scheduler Integration Functions
def load_scheduled_jobs():
    """
    Load all scheduled jobs from the database and add them to the scheduler.
    This function is called during application startup.
    """

    now = datetime.now()
    clear_expired_scheduled_items(now)

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
                'name': item['name']
            }
            
            # Determine trigger type
            if item['is_recurring'] == 1:
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
            
            print(f"Loaded scheduled job: {item['name']} at {item['scheduled_datetime']}")
            
        except Exception as e:
            print(f"Error loading scheduled job {item['id']}: {e}")




# Flask Routes
@app.route('/')
def index():
    """Main dashboard page"""
    scheduled_items = get_all_scheduled_items()
    templates = get_all_templates()
    # Convert Row objects to dictionaries and add human-readable weekday names

    scheduled_items_list = []
    for item in scheduled_items:
        item_dict = dict(item)
        if item_dict['recurring_weekdays']:
            item_dict['weekday_names'] = get_weekday_names(item_dict['recurring_weekdays'])
        scheduled_items_list.append(item_dict)
    
    return render_template('index.html', scheduled_items=scheduled_items_list, templates=templates, get_weekday_names=get_weekday_names)




@app.route('/purge_schedule', methods=['POST'])
def route_purge_schedule():
    """Purge all scheduled items"""
    try:
        purge_scheduled_items()
        flash('All scheduled items purged successfully', 'success')
    except Exception as e:
        flash(f'Error purging scheduled items: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/manual_control', methods=['POST'])
def route_manual_control():
    """Manually set text on the sign"""
    try:
        text, x, y, color = parseManualControlForm(request.form)
        sign.set_static_text(text, x, y, color)
        flash('Text set on sign successfully', 'success')
    except Exception as e:
        flash(f'Error setting text on sign: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/clear_sign', methods=['POST'])
def route_clear_sign():
    """Clear the sign display"""
    try:
        clear_sign()
        flash('Sign cleared successfully', 'success')
    except Exception as e:
        flash(f'Error clearing sign: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/add_schedule', methods=['POST'])
def route_add_schedule():
    """Add a new scheduled item"""
    form = parseScheduleForm(request.form)
    
    # Validate that we have either datetime OR recurring settings
    if not form['is_recurring'] and not form['scheduled_datetime']:
        flash('Please provide a date and time for one-time schedules', 'error')
        return redirect(url_for('index'))

    if form['text'] is None and form['template_id'] == None:
        flash('Please provide custom text or select a template', 'error')
        return redirect(url_for('index'))

    # If no template is selected, create a custom payload
    if form['template_id'] is None or form['template_id'] == '':
        color_hex = request.form.get('custom_color', '#ffff00')
        color_hex = color_hex.lstrip('#')
        color = [int(color_hex[i:i+2], 16) for i in (0, 2, 4)]
        # Create a custom template for this schedule
        payload = json.dumps({
            "name": f"Custom_{form['schedule_name']}",
            "items": [{
                "type": "static",
                "content": form['text'],
                "x": 0,
                "y": 10,
                "color": color
            }]
        })
        form['template_id'] = add_template(f"Custom_{form['schedule_name']}", payload)
    

    
    item_id = add_scheduled_item(
        name=form['schedule_name'],
        scheduled_datetime=form['scheduled_datetime'],
        is_recurring=form['is_recurring'],
        template_id=form['template_id'],
        recurring_weekdays=form['recurring_weekdays'],
    )

    # Add to scheduler if it's a future time or recurring
    if form['is_recurring'] and form['recurring_weekdays'] and form['scheduled_datetime']:
        # Use weekday-based scheduling
        cron_expr = create_cron_from_weekdays_time(form['recurring_weekdays'], form['scheduled_datetime'])
        if cron_expr:
            trigger = CronTrigger.from_crontab(cron_expr)
        else:
            trigger = CronTrigger.from_crontab('0 9 * * *')  # Fallback: 9 AM daily
            
        scheduler.add_job(
            func=execute_scheduled_item,
            trigger=trigger,
            id=f"schedule_{item_id}",
            kwargs={'schedule_id': item_id, 'name': form['schedule_name']},
            replace_existing=True
        )
    elif not form['is_recurring']:
        # One-time scheduled item
        scheduled_dt = datetime.fromisoformat(form['scheduled_datetime'])
        if scheduled_dt > datetime.now():
            scheduler.add_job(
                func=execute_scheduled_item,
                trigger=DateTrigger(run_date=scheduled_dt),
                id=f"schedule_{item_id}",
                kwargs={'schedule_id': item_id, 'name': form['schedule_name']},
                replace_existing=True
            )

    flash(f'Scheduled item "{form["schedule_name"]}" added successfully', 'success')
    
    return redirect(url_for('index'))


@app.route('/delete_schedule/<int:item_id>', methods=['POST'])
def route_delete_schedule(item_id):
    """Delete a scheduled item"""
    try:
        # Remove from scheduler
        try:
            scheduler.remove_job(f"schedule_{item_id}")
        except:
            pass  # Job might not exist in scheduler
        
        # Remove from database
        success = remove_scheduled_item(item_id)
        if success:
            flash('Scheduled item deleted successfully', 'success')
        else:
            flash('Scheduled item not found', 'error')
    except Exception as e:
        flash(f'Error deleting scheduled item: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/add_template', methods=['POST'])
def route_add_template():
    """Add a new template"""

    try:
        label = request.form.get('template_name', '').strip()
        if not label:
            flash('Template name cannot be empty', 'error')
            return redirect(url_for('index'))
            
        # Build payload from form fields
        form_json = parse_form(request.form)

        if not form_json.get('items'):
            flash('Template must have at least one text item', 'error')
            return redirect(url_for('index'))
            
        payload = json.dumps(form_json)
        template_id = add_template(name=label, payload=payload)
        flash(f'Template "{label}" created successfully', 'success')

    except json.JSONDecodeError:
        flash('Invalid JSON payload', 'error')
    except Exception as e:
        flash(f'Error creating template: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/delete_template/<int:template_id>', methods=['POST'])
def route_delete_template(template_id):
    """Delete a template"""
    try:
        success = remove_template(template_id)
        if success:
            flash('Template deleted successfully', 'success')
        else:
            flash('Template not found', 'error')
    except Exception as e:
        flash(f'Error deleting template: {str(e)}', 'error')
    
    return redirect(url_for('index'))


if __name__ == "__main__":
    print("Initializing LED sign web application...")
    
    # Warn about development secret key
    if app.secret_key == 'dev-key-change-in-production':
        print("Warning: Using development secret key. Set SECRET_KEY environment variable for production!")
    
    print("Initializing database...")
    init_db()
    recover_scheduled_jobs()

    # Load existing scheduled jobs from database and start scheduler
    print("Loading scheduled jobs...")
    load_scheduled_jobs()
    scheduler.start()
    
    # Run Flask app with configurable settings
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Flask app on {host}:{port} (debug={debug})")
    app.run(debug=debug, host=host, port=port, use_reloader=False)