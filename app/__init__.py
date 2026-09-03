from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

    # Determine deployment mode and configure database accordingly
    deployment_mode = os.getenv('DEPLOYMENT_MODE', 'local').lower()

    # Database configuration - supports all three scenarios
    if deployment_mode == 'aws' and os.getenv('RDS_ENDPOINT'):
        # AWS RDS MySQL configuration
        rds_endpoint = os.getenv('RDS_ENDPOINT')
        rds_user = os.getenv('RDS_USER', 'admin')
        rds_password = os.getenv('RDS_PASSWORD')
        rds_database = os.getenv('RDS_DATABASE', 'image_gallery')
        rds_port = os.getenv('RDS_PORT', '3306')

        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f'mysql+pymysql://{rds_user}:{rds_password}@'
            f'{rds_endpoint}:{rds_port}/{rds_database}'
        )

        app.logger.info('🔵 Connected to AWS RDS MySQL')

    elif deployment_mode == 'docker' and os.getenv('MYSQL_USER'):
        # Docker MySQL configuration
        mysql_user = os.getenv('MYSQL_USER', 'gallery_user')
        mysql_password = os.getenv('MYSQL_PASSWORD')
        mysql_database = os.getenv('MYSQL_DATABASE', 'image_gallery')

        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f'mysql+pymysql://{mysql_user}:{mysql_password}@'
            f'mysql:3306/{mysql_database}'
        )

        app.logger.info('🐳 Connected to Docker MySQL')

    else:
        # Default to SQLite for local development
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///image_gallery.db'
        app.logger.info('📁 Using SQLite local database')

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = int(
        os.getenv('MAX_FILE_SIZE', 16777216)
    )

    # Debug mode (convert string to boolean)
    debug_env = os.getenv('DEBUG', 'True').lower()
    app.config['DEBUG'] = debug_env in ('true', '1', 'yes')

    # AWS S3 Configuration (IAM role-based)
    app.config['S3_BUCKET_NAME'] = os.getenv('S3_BUCKET_NAME')
    app.config['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-1')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.gallery import gallery_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(admin_bp)

    # Load user for login_manager
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Health check endpoint for ALB
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200

    # Create database tables
    with app.app_context():
        db.create_all()

        # Validate S3 bucket access ONLY if using S3 (DEBUG=False)
        debug = app.config.get('DEBUG', True)

        if not debug:
            s3_bucket = app.config.get('S3_BUCKET_NAME')

            if s3_bucket:
                from app.utils.s3 import check_s3_bucket_access

                if not check_s3_bucket_access(s3_bucket):
                    app.logger.warning(
                        f'Warning: Cannot access S3 bucket '
                        f'"{s3_bucket}". Check IAM role permissions.'
                    )

    return app
