from sign import s 
from sql import *
import os
import signal
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, render_template, request, redirect, url_for, flash
import json


# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

scheduler = BackgroundScheduler(
    job_defaults=dict(coalesce=True, max_instances=1, misfire_grace_time=10)
)


### Flask Routes ###

@app.route('/')
def index():
    """Main dashboard page"""
    scheduled_items = get_all_scheduled_items()
    templates = get_all_templates()
    print(scheduled_items)
    
    # Convert Row objects to dictionaries and add human-readable weekday names
    scheduled_items_list = []
    for item in scheduled_items:
        item_dict = dict(item)
        if item_dict['recurring_weekdays']:
            item_dict['weekday_names'] = get_weekday_names(item_dict['recurring_weekdays'])
        scheduled_items_list.append(item_dict)
    
    return render_template('index.html', scheduled_items=scheduled_items_list, templates=templates, get_weekday_names=get_weekday_names)


@app.route('/set_text', methods=['POST'])
def route_set_text():
    """Manually set text on the sign"""
    text = request.form.get('text', '')
    x = int(request.form.get('x', 0))
    y = int(request.form.get('y', 10))
    color_hex = request.form.get('color', '#ffff00')
    
    # Convert hex color to RGB tuple
    color_hex = color_hex.lstrip('#')
    color = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    
    try:
        set_text(text=text, x=x, y=y, color=color)
        flash(f'Sign updated with text: "{text}"', 'success')
    except Exception as e:
        flash(f'Error updating sign: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/clear_sign', methods=['POST'])
def route_clear_sign():
    """Clear the sign display"""
    try:
        from sign import s
        s.clear()
        flash('Sign cleared successfully', 'success')
    except Exception as e:
        flash(f'Error clearing sign: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/add_schedule', methods=['POST'])
def route_add_schedule():
    """Add a new scheduled item"""
    label = request.form.get('label', '')
    scheduled_datetime = request.form.get('scheduled_datetime', '')
    is_recurring = 'is_recurring' in request.form
    template_id = request.form.get('template_id', None)
    
    # Handle weekday selection for recurring items
    recurring_weekdays = None
    recurring_time = None
    
    if is_recurring:
        weekdays = request.form.getlist('weekdays')
        if weekdays:
            recurring_weekdays = ','.join(weekdays)
        recurring_time = request.form.get('recurring_time', '')
        if not recurring_time:
            recurring_time = None
        
        # For recurring items, we don't need a specific datetime
        # Use a placeholder datetime - it won't be used for scheduling
        if not scheduled_datetime:
            scheduled_datetime = '2024-01-01 00:00:00'
    
    # Validate that we have either datetime OR recurring settings
    if not is_recurring and not scheduled_datetime:
        flash('Please provide a date and time for one-time schedules', 'error')
        return redirect(url_for('index'))
    
    if is_recurring and (not recurring_weekdays or not recurring_time):
        flash('Please select weekdays and time for recurring schedules', 'error')
        return redirect(url_for('index'))
    
    # Convert empty string to None for template_id
    if template_id == '':
        template_id = None
    else:
        template_id = int(template_id)
    
    try:
        # If no template is selected, create a custom payload
        if template_id is None:
            custom_text = request.form.get('custom_text', '')
            color_hex = request.form.get('custom_color', '#ffff00')
            color_hex = color_hex.lstrip('#')
            color = [int(color_hex[i:i+2], 16) for i in (0, 2, 4)]
            
            # Create a custom template for this schedule
            payload = json.dumps({
                "type": "static",
                "text": [{
                    "content": custom_text,
                    "x": 0,
                    "y": 10,
                    "color": color
                }]
            })
            template_id = add_template(f"Custom_{label}", payload, 'static')
        
        item_id = add_scheduled_item(
            label=label,
            scheduled_datetime=scheduled_datetime,
            is_recurring=is_recurring,
            template_id=template_id,
            recurring_weekdays=recurring_weekdays,
            recurring_time=recurring_time
        )
        
        # Add to scheduler if it's a future time or recurring
        from datetime import datetime
        if is_recurring and recurring_weekdays and recurring_time:
            # Use weekday-based scheduling
            from apscheduler.triggers.cron import CronTrigger
            
            cron_expr = create_cron_from_weekdays_time(recurring_weekdays, recurring_time)
            if cron_expr:
                trigger = CronTrigger.from_crontab(cron_expr)
            else:
                trigger = CronTrigger.from_crontab('0 9 * * *')  # Fallback: 9 AM daily
                
            scheduler.add_job(
                func=execute_scheduled_item,
                trigger=trigger,
                id=f"schedule_{item_id}",
                kwargs={'schedule_id': item_id, 'label': label},
                replace_existing=True
            )
        elif not is_recurring:
            # One-time scheduled item
            scheduled_dt = datetime.fromisoformat(scheduled_datetime)
            if scheduled_dt > datetime.now():
                from apscheduler.triggers.date import DateTrigger
                
                scheduler.add_job(
                    func=execute_scheduled_item,
                    trigger=DateTrigger(run_date=scheduled_dt),
                    id=f"schedule_{item_id}",
                    kwargs={'schedule_id': item_id, 'label': label},
                    replace_existing=True
                )
        
        flash(f'Scheduled item "{label}" added successfully', 'success')
    except Exception as e:
        flash(f'Error adding scheduled item: {str(e)}', 'error')
    
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
    label = request.form.get('label', '')
    template_type = request.form.get('template_type', 'static')
    payload_manual = request.form.get('payload_manual', '')
    
    try:
        # If manual payload is provided, use it
        if payload_manual.strip():
            payload = payload_manual
            # Validate JSON
            json.loads(payload)
        else:
            # Build payload from form fields
            payload = build_template_payload(request.form, template_type)
        
        template_id = add_template(label=label, payload=payload, template_type=template_type)
        flash(f'Template "{label}" created successfully', 'success')
    except json.JSONDecodeError:
        flash('Invalid JSON payload', 'error')
    except Exception as e:
        flash(f'Error creating template: {str(e)}', 'error')
    
    return redirect(url_for('index'))


def build_template_payload(form_data, template_type):
    """Build template payload from form data"""
    text_items = []
    
    # Find all text items
    index = 0
    while f'text_content_{index}' in form_data:
        content = form_data.get(f'text_content_{index}', '')
        if content:
            x = int(form_data.get(f'text_x_{index}', 0))
            y = int(form_data.get(f'text_y_{index}', 10))
            color_hex = form_data.get(f'text_color_{index}', '#ffff00').lstrip('#')
            color = [int(color_hex[i:i+2], 16) for i in (0, 2, 4)]
            
            text_item = {
                'content': content,
                'x': x,
                'y': y,
                'color': color
            }
            
            # Add special fields based on template type
            if template_type == 'scrolling':
                speed = int(form_data.get(f'text_speed_{index}', 50))
                direction = form_data.get(f'text_direction_{index}', 'left')
                text_item.update({
                    'speed': speed,
                    'direction': direction
                })
            elif template_type == 'animation':
                effect = form_data.get(f'text_effect_{index}', 'blink')
                duration = int(form_data.get(f'text_duration_{index}', 5))
                text_item.update({
                    'effect': effect,
                    'duration': duration
                })
            
            text_items.append(text_item)
        index += 1
    
    # Create payload
    payload = {
        'type': template_type,
        'text': text_items
    }
    
    return json.dumps(payload)


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


def recover_scheduled_jobs():
    ### Rerun the last job or the next job if ready
    ### Will fail for various reasons lol. Just gonna assume it works for now
    last_run = get_last_run()
    if last_run:
        last_run_time = datetime.fromisoformat(last_run['last_run_datetime'])
        schedule_id = last_run['schedule_id']
        schedule = get_scheduled_item(schedule_id)
        if schedule:
            # Re-execute the last job
            print(f"Re-executing last job: {schedule['label']}")
            execute_scheduled_item(schedule_id=schedule_id, label=schedule['label'])
            return

   


def main():
    print("Initializing database…")
    init_db()
    recover_scheduled_jobs()

    # Load existing scheduled jobs from database
    load_scheduled_jobs()

    scheduler.start()

    print("Starting Flask web server on http://localhost:5000")
    print("Ctrl+C to exit")
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)


if __name__ == "__main__":
    main()
