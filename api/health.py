from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import os
import sys
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add parent directory to path
sys.path.append(BASE_DIR)

# Create standalone Flask app for health check
app = Flask(__name__)

# Configure database
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    # Heroku-style postgres:// to postgresql:// for SQLAlchemy 1.4+
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# For Vercel deployment: use SQLite for local development, PostgreSQL for production
if not database_url:
    # Local development - use SQLite
    database_url = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'beauty_site.db')}"

# Function to create error response with consistent format
def create_error_response(message, status_code):
    response = jsonify({
        "status": "unhealthy", 
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "error_code": status_code
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
    return response, status_code

# Health check route - explicitly public, no auth required
@app.route('/', methods=['GET', 'OPTIONS'])
def health_check():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        return response
        
    try:
        # Log the health check attempt
        logger.info(f"Database health check initiated from IP: {request.remote_addr}")
        
        # Create a SQLAlchemy engine to check DB connection
        connect_args = {}
        if database_url.startswith('sqlite'):
            connect_args = {'check_same_thread': False}
        elif 'postgres' in database_url:
            connect_args = {'sslmode': 'require', 'connect_timeout': 5}
            
        engine = create_engine(
            database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=280
        )
        
        # Check database connection with a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
        
        # Additional database info
        try:
            db_name = engine.url.database or "unknown"
            table_info = f"Database name: {db_name}"
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
            "query_result": result == 1,
            "version": "1.0"
        }
        
        # Add CORS headers and custom headers for health check
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        response.headers.add('X-Health-Check', 'db-connection-verified')
        
        logger.info("Database health check successful")
        return response
        
    except OperationalError as e:
        # Database connection errors
        error_msg = f"Database connection error: {str(e).split(')')[-1].strip()}"
        logger.error(f"Health check failed - DB operational error: {str(e)}")
        return create_error_response(error_msg, 503)  # Service Unavailable
        
    except SQLAlchemyError as e:
        # General SQLAlchemy errors
        logger.error(f"Health check failed - SQLAlchemy error: {str(e)}")
        return create_error_response(f"Database query error: {str(e)}", 500)
        
    except Exception as e:
        # Any other unexpected errors
        logger.error(f"Health check failed - Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(f"Unexpected error: {str(e)}", 500)

