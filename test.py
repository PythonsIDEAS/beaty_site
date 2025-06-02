from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

def test_db_connection():
    try:
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        connection = engine.connect()
        connection.close()
        print("Database connection successful!")
        return True
    except OperationalError as e:
        print(f"Database connection failed: {str(e)}")
        return False

# Add this after db.init_app(app)
with app.app_context():
    test_db_connection()