import collections
import collections.abc
collections.Mapping = collections.abc.Mapping

import jwt.algorithms
jwt.algorithms.requires_cryptography = []

import os
from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, bcrypt
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from utils import redis_client  
from routes.authentication import auth_bp  
from routes.charity import charity_bp  
from routes.admin import admin_bp
from routes.stories import story_bp
from routes.donations import donation_bp
from routes.inventory import inventory_bp
from routes.cloudinary_upload import cloudinary_bp

# Load .env variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*":{
        "origins": ["http://localhost:5173", "http://127.0.0.1:5174"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }})

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'super-secret-key')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', app.config['SECRET_KEY'])

    db.init_app(app)
    bcrypt.init_app(app)
    Migrate(app, db)
    JWTManager(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(charity_bp, url_prefix='/charity')  
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(story_bp, url_prefix='/stories')
    app.register_blueprint(donation_bp, url_prefix='/donations')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(cloudinary_bp, url_prefix='/cloudinary')

    return app

# Create a global WSGI app for Gunicorn
app = create_app()

if __name__ == '__main__':
    # Ensure tables are created when running locally
    with app.app_context():
        db.create_all()
        print("Database tables created.")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
