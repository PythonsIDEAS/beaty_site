from flask import Blueprint, render_template, request, jsonify, current_app
from models import db, PageContent, PageLayout, PageSection
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

admin = Blueprint('admin', __name__)

@admin.route('/admin/pages')
def admin_pages():
    pages = PageContent.query.all()
    return render_template('admin/pages.html', pages=pages)

@admin.route('/admin/page-builder/new')
def new_page():
    layouts = PageLayout.query.all()
    return render_template('admin/page_builder.html', page=None, layouts=layouts)

@admin.route('/admin/page-builder/<int:page_id>')
def edit_page(page_id):
    page = PageContent.query.get_or_404(page_id)
    layouts = PageLayout.query.all()
    return render_template('admin/page_builder.html', page=page, layouts=layouts)

@admin.route('/admin/api/pages', methods=['POST'])
def create_page():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['page_name', 'title', 'layout_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Check for duplicate page name
    existing_page = PageContent.query.filter_by(page_name=data['page_name']).first()
    if existing_page:
        return jsonify({'error': 'A page with this name already exists'}), 400
    
    try:
        page = PageContent(
            page_name=data['page_name'],
            title=data['title'],
            content=data.get('content', ''),
            meta_description=data.get('meta_description', ''),
            layout_id=data['layout_id']
        )
        
        db.session.add(page)
        db.session.commit()
        
        # Create sections
        for section_data in data.get('sections', []):
            # Validate required section fields
            required_section_fields = ['type', 'content', 'order']
            for field in required_section_fields:
                if field not in section_data:
                    db.session.rollback()
                    return jsonify({'error': f'Missing required section field: {field}'}), 400
            
            section = PageSection(
                page_id=page.id,
                section_type=section_data['type'],
                content=json.dumps(section_data['content']),
                order=section_data['order'],
                style_config=json.dumps(section_data.get('style', {}))
            )
            db.session.add(section)
        
        db.session.commit()
        return jsonify({'id': page.id, 'message': 'Page created successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin.route('/admin/api/pages/<int:page_id>', methods=['PUT'])
def update_page(page_id):
    try:
        page = PageContent.query.get_or_404(page_id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'layout_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # If page_name is being updated, check for duplicates
        if 'page_name' in data and data['page_name'] != page.page_name:
            existing_page = PageContent.query.filter_by(page_name=data['page_name']).first()
            if existing_page:
                return jsonify({'error': 'A page with this name already exists'}), 400
            page.page_name = data['page_name']
        
        page.title = data['title']
        page.content = data.get('content', '')
        page.meta_description = data.get('meta_description', '')
        page.layout_id = data['layout_id']
        page.updated_at = datetime.utcnow()
        
        # Update sections
        # First, remove all existing sections
        PageSection.query.filter_by(page_id=page.id).delete()
        
        # Then create new sections
        for section_data in data.get('sections', []):
            # Validate required section fields
            required_section_fields = ['type', 'content', 'order']
            for field in required_section_fields:
                if field not in section_data:
                    db.session.rollback()
                    return jsonify({'error': f'Missing required section field: {field}'}), 400
            
            section = PageSection(
                page_id=page.id,
                section_type=section_data['type'],
                content=json.dumps(section_data['content']),
                order=section_data['order'],
                style_config=json.dumps(section_data.get('style', {}))
            )
            db.session.add(section)
        
        db.session.commit()
        return jsonify({'message': 'Page updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin.route('/admin/api/pages/<int:page_id>', methods=['DELETE'])
def delete_page(page_id):
    try:
        page = PageContent.query.get_or_404(page_id)
        
        # Delete all sections first
        PageSection.query.filter_by(page_id=page.id).delete()
        
        # Then delete the page
        db.session.delete(page)
        db.session.commit()
        return jsonify({'message': 'Page deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'message': 'Page deleted successfully'})

@admin.route('/admin/api/layouts', methods=['GET'])
def get_layouts():
    layouts = PageLayout.query.all()
    return jsonify([
        {
            'id': layout.id,
            'name': layout.name,
            'description': layout.description,
            'config': layout.get_config()
        }
        for layout in layouts
    ])

@admin.route('/admin/api/layouts', methods=['POST'])
def create_layout():
    data = request.get_json()
    
    layout = PageLayout(
        name=data['name'],
        description=data.get('description', ''),
        layout_config=json.dumps(data['config'])
    )
    
    db.session.add(layout)
    db.session.commit()
    
    return jsonify({
        'id': layout.id,
        'message': 'Layout created successfully'
    })

@admin.route('/admin/api/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        # Ensure upload directory exists
        upload_dir = os.path.join(current_app.static_folder, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Return the URL for the uploaded image
        return jsonify({
            'url': f'/static/uploads/{filename}',
            'message': 'Image uploaded successfully'
        })
        
    return jsonify({'error': 'Invalid file type'}), 400

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS