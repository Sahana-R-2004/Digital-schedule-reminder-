from datetime import datetime, timedelta

def send_reminder(schedule):
    print(f"Reminder: {schedule.task} at {schedule.date} {schedule.time}")

def send_schedule_reminders():
    from app import Schedule  # Move import here to avoid circular import

    current_time = datetime.now()
    schedules = Schedule.query.all()

    for schedule in schedules:
        try:
            schedule_time = datetime.strptime(schedule.date + ' ' + schedule.time, '%Y-%m-%d %H:%M')
            if current_time < schedule_time < current_time + timedelta(minutes=10):
                send_reminder(schedule)
        except ValueError as e:
            print(f"Error parsing schedule time for task '{schedule.task}':", e)
