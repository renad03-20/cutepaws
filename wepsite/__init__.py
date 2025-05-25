from flask import Flask
import os
from dotenv import load_dotenv
import click
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from flask_migrate import Migrate
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler 
from datetime import datetime, timedelta, timezone
# from flask_mail import Mail

socketio = SocketIO() 
db = SQLAlchemy()
migrate = Migrate() 
DB_NAME = 'database.db'
load_dotenv()

@click.command('create-admin')
@with_appcontext
def create_admin():
    """Create an admin user."""
    from .models import User  # ✅ Moved here to avoid circular import

    email = input('Enter email: ')
    password = input('Enter password: ')
    first_name = input('Enter first name: ')

    user = User.query.filter_by(email=email).first()
    if user:
        print('User already exists')
        return
    
    new_user = User(
        email=email,
        password=generate_password_hash(password, method='pbkdf2:sha256'),
        first_name=first_name,
        is_admin=True
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        print(f"Admin user {email} created successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {str(e)}")

def delete_old_adoptions(app):
    with app.app_context():
        from .models import Pet
        from datetime import datetime, timedelta
        
        expired_pets = Pet.query.filter(
            Pet.is_adopted == True,
            Pet.adoption_date <= datetime.now(timezone.utc) - timedelta(minutes=2)
        ).all()
        for pet in expired_pets:
            db.session.delete(pet)
        db.session.commit()

def create_app():
    app = Flask(__name__)

    # Handle secret key based on environment
    secret_key = os.getenv('SECRET_KEY')
    if os.getenv('FLASK_ENV') == 'production':
        if not secret_key:
            raise RuntimeError("SECRET_KEY environment variable is not set in production!")
        app.config['SECRET_KEY'] = secret_key
    else:
        app.config['SECRET_KEY'] = 'dev_secret_key'  # For development

    # Database and file settings
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':  # Prevents duplicate jobs in dev
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=delete_old_adoptions,
            trigger='interval',
            hours=24,  # Runs daily
            args=[app]  # Pass app for context
        )
        scheduler.start()

    #  # Email settings
    # app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    # app.config['MAIL_PORT'] = 587
    # app.config['MAIL_USE_TLS'] = True
    # app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
    # app.config['MAIL_PASSWORD'] = 'your-app-password'  # Use an App Password

    db.init_app(app)
    migrate.init_app(app, db) 

    socketio.init_app(app) # Initialize SocketIO

    # Mail.init_app(app)

    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    #create_database(app) ###############################

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User  # ✅ Delayed import
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None

    app.cli.add_command(create_admin)



    return app
# def create_database(app):
#     from .models import User  # ✅ Moved here too (in case you do model stuff during db creation)
                                                     
#     db_path = os.path.join(app.root_path, DB_NAME)
#     if not os.path.exists(db_path):
#         with app.app_context():
#             db.create_all()
#             print('Created Database')