from datetime import datetime
import json
from models import db

class PageContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_name = db.Column(db.String(100), nullable=False, unique=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    meta_description = db.Column(db.String(300))
    layout_id = db.Column(db.Integer, db.ForeignKey('page_layout.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    layout = db.relationship('PageLayout', backref=db.backref('pages', lazy=True))
    
    def __repr__(self):
        return f'<PageContent {self.page_name}>'

class PageLayout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    layout_config = db.Column(db.Text, nullable=False)  # Stores JSON configuration
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_config(self):
        """Returns the layout configuration as a Python dictionary"""
        return json.loads(self.layout_config)
    
    def set_config(self, config):
        """Sets the layout configuration from a Python dictionary"""
        self.layout_config = json.dumps(config)
    
    def __repr__(self):
        return f'<PageLayout {self.name}>'

class PageSection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('page_content.id'), nullable=False)
    section_type = db.Column(db.String(50), nullable=False)  # header, text, image, gallery, etc.
    content = db.Column(db.Text, nullable=False)  # Stores JSON content
    order = db.Column(db.Integer, nullable=False)
    style_config = db.Column(db.Text)  # Stores JSON styling configuration
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    page = db.relationship('PageContent', backref=db.backref('sections', lazy=True, order_by='PageSection.order'))
    
    def get_content(self):
        """Returns the section content as a Python dictionary"""
        return json.loads(self.content)
    
    def set_content(self, content):
        """Sets the section content from a Python dictionary"""
        self.content = json.dumps(content)
    
    def get_style(self):
        """Returns the style configuration as a Python dictionary"""
        return json.loads(self.style_config) if self.style_config else {}
    
    def set_style(self, style):
        """Sets the style configuration from a Python dictionary"""
        self.style_config = json.dumps(style)
    
    def __repr__(self):
        return f'<PageSection {self.section_type} for page {self.page_id}>'