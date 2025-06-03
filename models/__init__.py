from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models after db initialization to avoid circular imports
from models.page import PageContent, PageLayout, PageSection