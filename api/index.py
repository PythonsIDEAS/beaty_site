from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import sys

# Add the parent directory to sys.path to import app from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from app.py
from app import app as flask_app

# This is the handler that Vercel will use
app = flask_app

# For local development
if __name__ == '__main__':
    app.run(debug=True)

