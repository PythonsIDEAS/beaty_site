from flask import Flask, render_template
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app and required models
from app import app as flask_app
from models import PageContent

app = flask_app

@app.route('/page/<identifier>')
def view_page(identifier):
    # Try to find page by ID first
    if identifier.isdigit():
        page = PageContent.query.get_or_404(int(identifier))
    else:
        # If not numeric, search by page_name
        page = PageContent.query.filter_by(page_name=identifier).first_or_404()
    
    return render_template('page.html', page=page)