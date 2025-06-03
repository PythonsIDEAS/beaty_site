from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, current_app, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
from chatbot import get_ai_response
from flask_migrate import Migrate
from flask_cors import CORS
import calendar as cal
import json
import os
import sys
import logging
import sqlalchemy.exc
from forms import RegistrationForm

from models import db
from admin_routes import admin

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create Flask app with absolute paths for templates and static folders
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# Enable CORS for the health check endpoint
CORS(app, resources={r"/db-health": {"origins": "*"}})

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key-for-development')

# Database configuration - handle both development and production
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    # Heroku-style postgres:// to postgresql:// for SQLAlchemy 1.4+
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Configure database with error handling
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Check connection before using it
    'pool_recycle': 280,    # Recycle connections after 280 seconds
    'connect_args': {
        'sslmode': 'require'  # Enable SSL mode for Render PostgreSQL
    }
}

# For SQLite, we need to add special connect args
if database_url.startswith('sqlite'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args'] = {'check_same_thread': False}


# Initialize database
db.init_app(app)
migrate = Migrate(app, db)
app.register_blueprint(admin, url_prefix='/') # Register the admin blueprint

@app.route('/page/<identifier>')
def view_page(identifier):
    from models import PageContent
    
    # Try to find page by ID first
    if identifier.isdigit():
        page = PageContent.query.get_or_404(int(identifier))
    else:
        # If not numeric, search by page_name
        page = PageContent.query.filter_by(page_name=identifier).first_or_404()
    
    return render_template('page.html', page=page)

# Function to initialize database tables safely
def init_db():
    try:
        with app.app_context():
            # db.create_all() # Removed for Vercel deployment; use migrations instead
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        # In a serverless environment, we should not crash on DB init failure

# Authentication bypass for specific routes
@app.before_request
def handle_public_routes():
    # Check if the route is public and should bypass authentication
    if request.path == "/db-health":
        # Allow the health check endpoint to bypass authentication
        logger.info(f"Public route accessed: {request.path}")
        return None

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='author', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    user = db.relationship('User', backref=db.backref('purchases', lazy=True))
    service = db.relationship('Service', backref=db.backref('purchases', lazy=True))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('appointments', lazy=True))
    service = db.relationship('Service', backref=db.backref('appointments', lazy=True))

@app.context_processor
def utility_processor():
    def get_current_user():
        if 'user_id' in session:
            return User.query.get(session['user_id'])
        return None
    return dict(current_user=get_current_user())

# Add a database health check route - no authentication required
@app.route('/db-health', methods=['GET', 'OPTIONS'])
def db_health():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = current_app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        return response
        
    try:
        # Log the health check attempt
        logger.info(f"Database health check initiated from IP: {request.remote_addr}")
        
        # Check database connection with a simple query that doesn't require existing tables
        result = db.session.execute("SELECT 1").scalar()
        
        # Additional database info - try to count tables
        table_count = 0
        try:
            if isinstance(db.engine.url.database, str):
                table_info = f"Database name: {db.engine.url.database}"
            else:
                table_info = "Using in-memory database"
            logger.info(f"Database info: {table_info}")
        except Exception as table_err:
            logger.warning(f"Could not get database info: {str(table_err)}")
            table_info = "Database info not available"
        
        # Build response with database details
        response_data = {
            "status": "healthy", 
            "message": "Database connection successful",
            "timestamp": datetime.utcnow().isoformat(),
            "database_info": table_info,
            "query_result": result == 1
        }
        
        # Add CORS headers and custom headers for health check
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        response.headers.add('X-Health-Check', 'db-connection-verified')
        
        logger.info("Database health check successful")
        return response
        
    except sqlalchemy.exc.OperationalError as e:
        # Database connection errors
        error_msg = f"Database connection error: {str(e).split(')')[-1].strip()}"
        logger.error(f"Health check failed - DB operational error: {str(e)}")
        return create_error_response(error_msg, 503)  # Service Unavailable
        
    except sqlalchemy.exc.SQLAlchemyError as e:
        # General SQLAlchemy errors
        logger.error(f"Health check failed - SQLAlchemy error: {str(e)}")
        return create_error_response(f"Database query error: {str(e)}", 500)
        
    except Exception as e:
        # Any other unexpected errors
        logger.error(f"Health check failed - Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(f"Unexpected error: {str(e)}", 500)

# Helper function to create error responses with consistent format and headers
def create_error_response(message, status_code):
    response = jsonify({
        "status": "unhealthy", 
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "error_code": status_code
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
    return response, status_code

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Этот email уже зарегистрирован')
            return redirect(url_for('register'))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешно завершена!')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Вход выполнен успешно!')
            return redirect(url_for('index'))
        
        flash('Неверное имя пользователя или пароль')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Выход выполнен успешно!')
    return redirect(url_for('index'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/services')
def services():
    services = Service.query.all()
    reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    return render_template('services.html', services=services, reviews=reviews)

@app.route('/discounts')
def discounts():
    return render_template('discounts.html')

# Removed duplicate route to resolve conflict

@app.route('/submit_appointment', methods=['POST'])
@login_required
def submit_appointment():
    data = request.get_json()
    service_id = data.get('service_id')
    appointment_date = datetime.strptime(f"{data.get('date')} {data.get('time')}", '%Y-%m-%d %H:%M')
    notes = data.get('notes', '')

    appointment = Appointment(
        user_id=session['user_id'],
        service_id=service_id,
        appointment_date=appointment_date,
        notes=notes
    )

    db.session.add(appointment)
    db.session.commit()

    return jsonify({'message': 'Appointment scheduled successfully!'}), 201

@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    rating = data.get('rating')
    text = data.get('text')
    
    if not rating or not text:
        return jsonify({'error': 'Missing required fields'}), 400
    
    review = Review(
        rating=rating,
        text=text,
        user_id=session['user_id']
    )
    
    db.session.add(review)
    db.session.commit()
    
    return jsonify({'message': 'Review added successfully'}), 201

@app.route('/purchases')
def purchases():
    if 'user_id' not in session:
        flash('Please login to view your purchases')
        return redirect(url_for('login'))
    user_purchases = Purchase.query.filter_by(user_id=session['user_id']).order_by(Purchase.purchase_date.desc()).all()
    return render_template('purchases.html', purchases=user_purchases)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему.')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()
    services = Service.query.all()
    reviews = Review.query.all()
    purchases = Purchase.query.all()
    appointments = Appointment.query.all()
    return render_template('admin/dashboard.html', users=users, services=services, reviews=reviews, purchases=purchases, appointments=appointments)

@app.route('/admin/services', methods=['GET', 'POST'])
@admin_required
def admin_services():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        
        service = Service(name=name, description=description, price=price)
        db.session.add(service)
        db.session.commit()
        flash('Service added successfully!')
        return redirect(url_for('admin_services'))
    
    services = Service.query.all()
    return render_template('admin/services.html', services=services)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'Admin status updated for {user.username}')
    return redirect(url_for('admin_users'))

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    reviews = Review.query.all()
    return render_template('admin/reviews.html', reviews=reviews)



@app.route('/appointment', methods=['GET', 'POST'])
@app.route('/appointment/<int:service_id>', methods=['GET', 'POST'])
def appointment(service_id=None):
    # Require login
    if not session.get('user_id'):
        return redirect(url_for('login', next=request.url))

    # Get all services
    services = Service.query.all()
    
    # Handle invalid service_id
    if service_id and not Service.query.get(service_id):
        flash('Selected service not found.', 'error')
        return redirect(url_for('services'))
    
    # If no services exist, redirect to services page with a message
    if not services:
        flash('No services available for booking.', 'error')
        return redirect(url_for('services'))

    # Get the selected service if service_id is provided
    selected_service = None
    if service_id:
        selected_service = Service.query.get_or_404(service_id)
    elif request.method == 'GET':
        # If no service_id provided, redirect to services page
        return redirect(url_for('services'))

    now = datetime.now()

    if request.method == 'POST':
        service_id = request.form.get('service_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        notes = request.form.get('notes')

        # Validate required fields
        if not service_id or not appointment_date or not appointment_time:
            flash('Please fill in all required fields.', 'error')
            return render_template('appointment.html', services=services, now=now, selected_service=selected_service)

        # Try to parse datetime
        try:
            date_time_str = f"{appointment_date} {appointment_time}"
            appointment_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('Invalid date or time format.', 'error')
            return render_template('appointment.html', services=services, now=now, selected_service=selected_service)

        # Check for existing conflicting appointments
        existing = Appointment.query.filter_by(
            appointment_date=appointment_datetime,
            service_id=int(service_id)
        ).first()
        if existing:
            flash('This time slot is already booked for the selected service. Please choose another time.', 'error')
            return render_template('appointment.html', services=services, now=now, selected_service=selected_service)

        # Create new appointment
        appointment = Appointment(
            user_id=session['user_id'],
            service_id=int(service_id),
            appointment_date=appointment_datetime,
            status='pending',
            notes=notes
        )

        try:
            db.session.add(appointment)
            db.session.commit()
            flash('Appointment request submitted successfully! We will confirm your appointment soon.')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while booking your appointment. Please try again.', 'error')
            return render_template('appointment.html', services=services, now=now, selected_service=selected_service)

    return render_template('appointment.html', services=services, now=now, selected_service=selected_service)


@app.route('/my-appointments')
@login_required
def my_appointments():
    appointments = Appointment.query.filter_by(user_id=session['user_id']).order_by(Appointment.appointment_date).all()
    return render_template('my_appointments.html', appointments=appointments)

@app.route('/admin/appointments')
@admin_required
def admin_appointments():
    appointments = Appointment.query.order_by(Appointment.appointment_date).all()
    return render_template('admin/appointments.html', appointments=appointments)

@app.route('/admin/calendar')
@admin_required
def admin_calendar():
    # Get current month and year
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    
    # Create current_date object
    current_date = datetime(year, month, 1)
    today = datetime.now().date()
    
    # Get all appointments for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    appointments = Appointment.query.filter(
        Appointment.appointment_date >= start_date,
        Appointment.appointment_date < end_date
    ).all()
    
    # Create calendar data
    calendar_data = {}
    for appointment in appointments:
        day = appointment.appointment_date.day
        if day not in calendar_data:
            calendar_data[day] = []
        calendar_data[day].append({
            'id': appointment.id,
            'time': appointment.appointment_date.strftime('%H:%M'),
            'service': appointment.service.name,
            'client': appointment.user.username,
            'status': appointment.status
        })
    
    # Get month name and calendar
    month_name = cal.month_name[month]
    cal_month = cal.monthcalendar(year, month)
    
    # Create calendar days with date objects
    calendar_days = []
    for week in cal_month:
        week_days = []
        for day in week:
            if day != 0:
                date = datetime(year, month, day).date()
                week_days.append({'date': date})
            else:
                # For days not in this month
                if len(week_days) == 0:
                    # If it's the first week, show days from previous month
                    prev_month = month - 1 if month > 1 else 12
                    prev_year = year - 1 if month == 1 else year
                    prev_month_days = cal.monthcalendar(prev_year, prev_month)[-1]
                    day_index = len(week_days)
                    if day_index < len(prev_month_days):
                        day = prev_month_days[day_index]
                        if day != 0:
                            date = datetime(prev_year, prev_month, day).date()
                        else:
                            # Fallback to first day of current month
                            date = datetime(year, month, 1).date()
                    else:
                        # Fallback to first day of current month
                        date = datetime(year, month, 1).date()
                else:
                    # If it's the last week, show days from next month
                    next_month = 1 if month == 12 else month + 1
                    next_year = year + 1 if month == 12 else year
                    next_month_days = cal.monthcalendar(next_year, next_month)[0]
                    day_index = len(week_days) % 7
                    if day_index < len(next_month_days):
                        day = next_month_days[day_index]
                        if day != 0:
                            date = datetime(next_year, next_month, day).date()
                        else:
                            # Fallback to last day of current month
                            last_day = cal.monthrange(year, month)[1]
                            date = datetime(year, month, last_day).date()
                    else:
                        # Fallback to last day of current month
                        last_day = cal.monthrange(year, month)[1]
                        date = datetime(year, month, last_day).date()
                week_days.append({'date': date})
        calendar_days.append(week_days)
    
    # Previous and next month links
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
        
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    
    return render_template(
        'admin/calendar.html',
        current_date=current_date,
        today=today,
        calendar_days=calendar_days,
        appointments=calendar_data,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year
    )

@app.route('/admin/appointment/<int:appointment_id>', methods=['GET', 'POST'])
@admin_required
def admin_appointment_detail(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if request.method == 'POST':
        status = request.form.get('status')
        notes = request.form.get('admin_notes')
        send_email = request.form.get('send_email') == 'true'
        
        # Update appointment status
        appointment.status = status
        
        # Add admin notes if provided
        if notes and notes.strip():
            if appointment.notes:
                appointment.notes += f"\n\nAdmin ({datetime.now().strftime('%Y-%m-%d %H:%M')}): {notes}"
            else:
                appointment.notes = f"Admin ({datetime.now().strftime('%Y-%m-%d %H:%M')}): {notes}"
        
        db.session.commit()
        
        # Send email notification if requested
        if send_email:
            try:
                email_subject = request.form.get('email_subject', 'Информация о вашей записи в BeautyDoc')
                email_message = request.form.get('email_message')
                
                if not email_message:
                    # Default message if none provided
                    status_text = {
                        'pending': 'ожидает подтверждения',
                        'confirmed': 'подтверждена',
                        'cancelled': 'отменена',
                        'completed': 'завершена'
                    }.get(status, '')
                    
                    email_message = f"""Уважаемый(ая) {appointment.user.username},

Ваша запись на {appointment.service.name} ({appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')}) была {status_text}.

С уважением,
Команда BeautyDoc"""
                
                # Here you would integrate with your email sending service
                # For example with Flask-Mail:
                # msg = Message(email_subject, recipients=[appointment.user.email])
                # msg.body = email_message
                # mail.send(msg)
                
                flash('Appointment updated and notification sent successfully!')
            except Exception as e:
                flash(f'Appointment updated but failed to send notification: {str(e)}', 'error')
        else:
            flash('Appointment updated successfully!')
            
        return redirect(url_for('admin_appointments'))
    
    return render_template('admin/appointment_detail.html', appointment=appointment)

@app.route('/api/appointments')
@admin_required
def api_appointments():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if start_date and end_date:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        appointments = Appointment.query.filter(
            Appointment.appointment_date >= start,
            Appointment.appointment_date <= end
        ).all()
    else:
        appointments = Appointment.query.all()
    
    events = []
    for appointment in appointments:
        color = {
            'pending': '#FFA500',  # Orange
            'confirmed': '#28a745',  # Green
            'cancelled': '#dc3545'   # Red
        }.get(appointment.status, '#007bff')  # Default blue
        
        events.append({
            'id': appointment.id,
            'title': f"{appointment.service.name} - {appointment.user.username}",
            'start': appointment.appointment_date.isoformat(),
            'end': (appointment.appointment_date + timedelta(hours=1)).isoformat(),
            'color': color,
            'url': url_for('admin_appointment_detail', appointment_id=appointment.id)
        })
    
    return json.dumps(events)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400
    
    result = get_ai_response(message)
    return jsonify(result)

@app.route('/admin/delete_service/<int:service_id>')
@admin_required
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash('Service deleted successfully!')
    return redirect(url_for('admin_services'))

@app.route('/admin/delete_review/<int:review_id>')
@admin_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully!')
    return redirect(url_for('admin_reviews'))

# Only initialize database in development, not in serverless environment
if 'VERCEL' not in os.environ and __name__ == '__main__':
    init_db()
    app.run(debug=True)
