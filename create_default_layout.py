import sys
sys.path.append('/Users/tarhanutegenov/beauty_site/beaty_site')

from app import app
from models import db, PageLayout

with app.app_context():
    layout = PageLayout(
        name='Default Layout',
        description='Default layout for pages',
        layout_config='{"sections": []}'
    )
    db.session.add(layout)
    db.session.commit()
    print(f'Created layout with ID: {layout.id}')