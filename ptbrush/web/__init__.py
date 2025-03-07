from flask import Flask
from flask_cors import CORS
import os
from pathlib import Path

def create_app():
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    CORS(app)
    
    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_ptbrush')
    
    # Register blueprints
    from ptbrush.web.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app 