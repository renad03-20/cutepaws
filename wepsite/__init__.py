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
from flask import Flask
import json

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
        from .models import Pet, AdoptionApplication
        from datetime import datetime, timedelta, timezone
        
        expired_pets = Pet.query.filter(
            Pet.is_adopted == True,
            Pet.adoption_date <= datetime.now(timezone.utc) - timedelta(days=2),
            Pet.is_deleted == False  # Only process active records
        ).all()

        for pet in expired_pets:
            try:
                #soft delete pet 
                pet.is_deleted = True

                AdoptionApplication.query.filter_by(pet_id=pet.id).update(
                    {'status': 'archived'}
                )
                db.session.commit()
                print(f'✅ erchived pet {pet.id} - {pet.name}') #this only for development in Deploying I'll use import logging, logger = logging.getLogger(__name__), logger.info(f"Archived pet {pet.id} ({pet.name})")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error archiving pet {pet.id}: {str(e)}")
        

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
            hours=6,  # Runs daily
            id='pet_cleanup_job',
            args=[app]  # Pass app for context
        )
        scheduler.start()
        print("⏰ Scheduler started: Pet cleanup job active")#for testing

    db.init_app(app)
    migrate.init_app(app, db) 

    socketio.init_app(app) # Initialize SocketIO



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

    @app.template_filter('from_json')
    def from_json_filter(s):
        return json.loads(s)

    return app
