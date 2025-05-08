from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from forms import RegistrationForm, LoginForm, ScheduleForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os
import atexit

app = Flask(__name__)
app.secret_key = 'your_secret_key'

load_dotenv()

# Database Configurationp
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reminder.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail Configuration (Replace with your credentials)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')


mail = Mail(app)

# Init Extensions
db = SQLAlchemy(app)

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Background Scheduler
background_scheduler = BackgroundScheduler()
background_scheduler.add_job(func=lambda: send_schedule_reminders(), trigger="interval", minutes=1)
background_scheduler.start()
atexit.register(lambda: background_scheduler.shutdown())

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def repr(self):
        return f'<User {self.email}>'

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)  # Store time as 'HH:MM'
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Email Reminder Function
def send_reminder(schedule, email):
    print(f"Reminder: {schedule.task} at {schedule.time} on {schedule.date}")
    print(f"Description: {schedule.description}")

    msg = Message(
        subject=f"Reminder: {schedule.task}",
        recipients=[email],
        body=f"Your schedule task '{schedule.task}' is set for {schedule.date} at {schedule.time}.\n\nDescription: {schedule.description}\n\nReminder triggered by the Digital Schedule Reminder App."
    )

    try:
        mail.send(msg)
        print("Reminder email sent!")
    except Exception as e:
        print(f"Error sending email: {e}")

# In the send_schedule_reminders function, update the call to send_reminder:
def send_schedule_reminders():
    now = datetime.now()
    upcoming_time = now + timedelta(minutes=10)
    schedules = Schedule.query.filter(Schedule.date == now.date()).all()

    for schedule in schedules:
        try:
            schedule_time = datetime.strptime(schedule.time, '%H:%M').time()
            full_datetime = datetime.combine(schedule.date, schedule_time)
            if now < full_datetime <= upcoming_time:
                user = User.query.get(schedule.user_id)
                if user:
                    send_reminder(schedule, user.email)
        except Exception as e:
            print(f"Error processing schedule ID {schedule.id}: {e}")
# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        new_user = User(email=form.email.data, password=generate_password_hash(form.password.data))
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('view_schedules'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/add_schedule', methods=['GET', 'POST'])
@login_required
def add_schedule():
    form = ScheduleForm()
    if form.validate_on_submit():
        task = form.title.data
        date_str = form.date.data
        time_str = form.time.data
        description = form.description.data
        try:
            date = datetime.strptime(str(date_str), '%Y-%m-%d').date()
            time = time_str
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('add_schedule'))
        new_schedule = Schedule(task=task, date=date, time=time, description=description, user_id=current_user.id)
        db.session.add(new_schedule)
        db.session.commit()
        flash('Schedule added!', 'success')
        return redirect(url_for('view_schedules'))
    return render_template('add.html', form=form)

@app.route('/view_schedules')
@login_required
def view_schedules():
    schedules = Schedule.query.filter_by(user_id=current_user.id).all()
    return render_template('view_schedules.html', schedules=schedules)

@app.route('/test_email')
def test_email():
    try:
        msg = Message('Test Email', sender='sahanarudresh2004@gmail.com', recipients=['sahanarudresh2004@gmail.com'])  # Use your email as the recipient for testing
        msg.body = "This is a test email from Flask"
        mail.send(msg)
        return "Test email sent successfully!"
    except Exception as e:
        return str(e)

@app.route('/send-test-email')
def send_test_email():
    msg = Message('Test Email from Digital Schedule Reminder',
                  recipients=[os.getenv('MAIL_USERNAME')])
    msg.body = 'This is a test email to confirm your email setup is working.'
    try:
        mail.send(msg)
        return 'Test email sent successfully!'
    except Exception as e:
        return f'Failed to send email: {e}'

@app.route('/edit_schedule/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    if schedule.user_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('view_schedules'))

    form = ScheduleForm()

    if form.validate_on_submit():
        schedule.task = form.title.data

        # Ensure proper conversion of date and time
        try:
            schedule.date = datetime.strptime(str(form.date.data), '%Y-%m-%d').date()
            schedule.time = form.time.data  # Already a string like 'HH:MM'
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('edit_schedule', id=id))

        schedule.description = form.description.data
        db.session.commit()
        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('view_schedules'))

    # Pre-fill the form with existing schedule data
    form.title.data = schedule.task
    form.date.data = schedule.date
    form.time.data = schedule.time
    form.description.data = schedule.description

    return render_template('edit_schedule.html', form=form, schedule=schedule)

@app.route('/delete_schedule/<int:id>', methods=['POST'])
@login_required
def delete_schedule(id):
    schedule = Schedule.query.get_or_404(id)
    if schedule.user_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('view_schedules'))
    db.session.delete(schedule)
    db.session.commit()
    flash('Schedule deleted.', 'success')
    return redirect(url_for('view_schedules'))

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
