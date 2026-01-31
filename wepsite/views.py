from datetime import datetime, timedelta, timezone
from flask import Blueprint, abort, json, jsonify, render_template, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from . import db, socketio
from .models import User, Pet, AdoptionApplication, Message
from flask_socketio import emit, join_room, disconnect
import uuid
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

views = Blueprint('views', __name__)

# Constants
MAX_MESSAGE_LENGTH = 1000
MESSAGE_RATE_LIMIT = 20

# Moved City Map here to be accessible by all routes
CITY_MAP = {
    "1": "Riyadh", "2": "Jeddah", "3": "Mecca", "4": "Medina", "5": "Dammam",
    "6": "Khobar", "7": "Dhahran", "8": "Tabuk", "9": "Abha", "10": "Khamis Mushait",
    "11": "Hail", "12": "Buraidah", "13": "Najran", "14": "Al Bahah", "15": "Sakakah",
    "16": "Arar", "17": "Jazan", "18": "Yanbu", "19": "Taif", "20": "Al Hofuf",
    "21": "Al Mubarraz", "22": "Al Qatif", "23": "Al Khafji", "24": "Al Jubail",
    "25": "Al Wajh", "26": "Rabigh", "27": "Bisha", "28": "Al Qurayyat",
    "29": "Sharurah", "30": "Turaif", "31": "Rafha", "32": "Al Ula", "33": "Samtah",
    "34": "Dawadmi", "35": "Mahd adh Dhahab", "36": "Wadi ad-Dawasir", "37": "Al Lith",
    "38": "Hotat Bani Tamim", "39": "Al Bukayriyah", "40": "Al Kharj"
}

def validate_message_content(content):
    if not content or not content.strip():
        return False, "Message cannot be empty"
    if len(content) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long (max {MAX_MESSAGE_LENGTH} characters)"
    return True, None

@views.route('/')
@login_required   
def home():
    try:
        city_id = request.args.get('city', '')
        selected_city = CITY_MAP.get(city_id, '')
        query = Pet.query.filter(Pet.is_deleted == False)
        
        if city_id and city_id in CITY_MAP:
            pets = query.filter_by(city=city_id).all()
        else:
            pets = query.all()

        return render_template('home.html', user=current_user, pets=pets, selected_city=selected_city, city_map=CITY_MAP)
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        return render_template('home.html', user=current_user, pets=[], selected_city='')

@views.route('/add_pet', methods=['GET', 'POST'])
@login_required 
def add_pet():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Only admin users can add posts', 'error')
        return redirect(url_for('views.home'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            breed = request.form.get('breed', '').strip()
            description = request.form.get('description', '').strip()
            city = request.form.get('city', '').strip()

            if not all([name, age, breed, description, city]):
                flash('All fields are required', 'error')
                return redirect(request.url)

            if 'image' not in request.files:
                flash('No image file uploaded', 'error')
                return redirect(request.url)
            
            image = request.files['image']
            if image.filename == '':
                flash('No selected image', 'error')
                return redirect(request.url)
            
            if image:
                filename = secure_filename(image.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                image_path = os.path.join(upload_folder, filename)
                image.save(image_path)

                new_pet = Pet(
                    name=name, age=age, breed=breed, description=description,
                    city=city, image_filename=filename, posted_by=current_user.id
                )
                db.session.add(new_pet)   
                db.session.commit()
                flash('Pet added successfully', 'success')
                return redirect(url_for('views.home'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding pet: {str(e)}")
            flash('An error occurred while adding the pet', 'error')
    
    # Pass city_map to template
    return render_template('add_pet.html', user=current_user, city_map=CITY_MAP)

@views.route('/pet/<int:pet_id>')
@login_required
def pet_detail(pet_id):
    try:
        pet = Pet.query.get_or_404(pet_id)
        
        city_map = {
            "1": "Riyadh", "2": "Jeddah", "3": "Mecca", "4": "Medina", "5": "Dammam",
            "6": "Khobar", "7": "Dhahran", "8": "Tabuk", "9": "Abha", "10": "Khamis Mushait",
            "11": "Hail", "12": "Buraidah", "13": "Najran", "14": "Al Bahah", "15": "Sakakah",
            "16": "Arar", "17": "Jazan", "18": "Yanbu", "19": "Taif", "20": "Al Hofuf",
            "21": "Al Mubarraz", "22": "Al Qatif", "23": "Al Khafji", "24": "Al Jubail",
            "25": "Al Wajh", "26": "Rabigh", "27": "Bisha", "28": "Al Qurayyat",
            "29": "Sharurah", "30": "Turaif", "31": "Rafha", "32": "Al Ula", "33": "Samtah",
            "34": "Dawadmi", "35": "Mahd adh Dhahab", "36": "Wadi ad-Dawasir", "37": "Al Lith",
            "38": "Hotat Bani Tamim", "39": "Al Bukayriyah", "40": "Al Kharj"
        }
        
        city_name = city_map.get(str(pet.city), 'Unknown')
        return render_template('pet_detail.html', user=current_user, pet=pet, city_name=city_name)
    except Exception as e:
        logger.error(f"Error in pet_detail: {str(e)}")
        flash("Pet not found", "error")
        return redirect(url_for('views.home'))

@views.route('/submit_application/<int:pet_id>', methods=['POST'])
@login_required
def submit_application(pet_id):
    try:
        # Check if pet exists and is available
        pet = Pet.query.get_or_404(pet_id)
        if pet.is_deleted or pet.is_adopted:
            flash('This pet is no longer available for adoption', 'error')
            return redirect(url_for('views.home'))

        # Check if user already applied
        existing_application = AdoptionApplication.query.filter_by(
            user_id=current_user.id,
            pet_id=pet_id
        ).first()

        if existing_application:
            flash('You have already applied for this pet', 'error')
            return redirect(url_for('views.pet_detail', pet_id=pet_id))
        
        if request.method == 'POST':
            # Get and validate form data
            form_data = {
                'similarity': request.form.get('similarity', '').strip(),
                'housing': request.form.get('housing', '').strip(),
                'confirmation': request.form.get('confirmation', '').strip(),
                'is_the_cat_alone': request.form.get('is_the_cat_alone', '').strip(),
                'financial': request.form.get('financial', '').strip(),
                'planning_to_move': request.form.get('planning_to_move', '').strip(),
                'deal_with_behavioral_problems': request.form.get('deal_with_behavioral_problems', '').strip(),
                'committed_caring': request.form.get('committed_caring', '').strip(),
                'backup_plan': request.form.get('backup_plan', '').strip()
            }
            
            # Validate required fields
            if not all(form_data.values()):
                flash('Please fill in all required fields', 'error')
                return redirect(url_for('views.pet_detail', pet_id=pet_id))
            
            # Create new application
            new_application = AdoptionApplication(
                pet_id=pet_id,
                user_id=current_user.id,
                answers=json.dumps(form_data),
                status='pending'
            )
            
            db.session.add(new_application)
            db.session.commit()
            
            # Create first message (automatic)
            # FIX: Added sequence_number and client_id
            first_message = Message(
                application_id=new_application.id,
                sender_id=current_user.id,
                content=f"New adoption application submitted for {pet.name}",
                sequence_number=1,  # <--- REQUIRED
                client_id=str(uuid.uuid4()) # <--- Good practice
            )
            
            db.session.add(first_message)
            db.session.commit()
            
            flash('Application submitted successfully!', 'success')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'redirect_url': url_for('views.messages', application_id=new_application.id)
                })
            
            return redirect(url_for('views.messages', application_id=new_application.id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting application: {str(e)}")
        flash('An error occurred while submitting your application', 'error')
    
    return redirect(url_for('views.pet_detail', pet_id=pet_id))

@views.route('/update_application_status/<int:application_id>/<status>')
@login_required
def update_application_status(application_id, status):
    try:
        if not current_user.is_admin:
            abort(403)
        
        if status not in ['approved', 'rejected']:
            flash('Invalid status', 'error')
            return redirect(url_for('views.applications'))
        
        app = AdoptionApplication.query.get_or_404(application_id)
        
        # Check if admin owns the pet
        if app.pet.posted_by != current_user.id:
            abort(403)
        
        # 1. Update status
        app.status = status
        
        # 2. Prepare the Automatic Message
        last_msg = Message.query.filter_by(application_id=application_id).order_by(Message.sequence_number.desc()).first()
        next_seq = (last_msg.sequence_number + 1) if last_msg else 1

        status_message = f"Application has been {status}"
        auto_message = Message(
            application_id=application_id,
            sender_id=current_user.id,
            content=status_message,
            sequence_number=next_seq,   
            client_id=str(uuid.uuid4())  
        )
        
        db.session.add(auto_message)
        
        # Save EVERYTHING in one single commit (Atomic Transaction)
        db.session.commit()
        
        flash(f"Application {status} successfully", "success")
        return redirect(url_for('views.messages', application_id=application_id))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating application status: {str(e)}")
        flash('An error occurred while updating the application', 'error')
        return redirect(url_for('views.applications'))


@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # Join a personal notification room (optional, for future global alerts)
        join_room(f'user_{current_user.id}')
        logger.info(f"User {current_user.id} connected to socket")
        emit('status_update', {'status': 'connected'})

@socketio.on('join_application')
def handle_join_application(data):
    """
    Client explicitly joins the chat room for a specific application.
    """
    try:
        application_id = data.get('application_id')
        if not application_id:
            return
        
        app = AdoptionApplication.query.get(application_id)
        if not app:
            return

        # Security: Only the applicant or the pet owner (admin) can join
        is_applicant = (current_user.id == app.user_id)
        is_owner = (current_user.is_admin and app.pet.posted_by == current_user.id)

        if is_applicant or is_owner:
            room_name = f"application_{application_id}"
            join_room(room_name)
            logger.info(f"User {current_user.id} joined room {room_name}")
            emit('room_joined', {'room': room_name})
        else:
            logger.warning(f"Unauthorized join attempt: User {current_user.id} -> App {application_id}")

    except Exception as e:
        logger.error(f"Error in join_application: {e}")

@socketio.on('send_message_socket')
def handle_socket_message(data):
    """
    Handles incoming messages via WebSocket.
    """
    try:
        if not current_user.is_authenticated:
            return

        application_id = data.get('application_id')
        content = data.get('content', '').strip()
        client_id = data.get('client_id')

        # 1. Validation
        is_valid, error = validate_message_content(content)
        if not is_valid:
            emit('message_error', {'client_id': client_id, 'error': error})
            return

        app = AdoptionApplication.query.get(application_id)
        if not app:
            return
        
        if app.status == 'archived':
            emit('message_error', {'client_id': client_id, 'error': 'Chat is archived.'})
            return

        # 2. Database Entry
        # Calculate sequence number for ordering
        last_msg = Message.query.filter_by(application_id=application_id).order_by(Message.sequence_number.desc()).first()
        next_seq = (last_msg.sequence_number + 1) if last_msg else 1

        new_msg = Message(
            application_id=application_id,
            sender_id=current_user.id,
            content=content,
            client_id=client_id,
            sequence_number=next_seq,
            timestamp=datetime.now(timezone.utc),
            is_read=False
        )
        
        db.session.add(new_msg)
        db.session.commit()

        # 3. Construct Payload
        message_payload = {
            'id': new_msg.id,
            'client_id': client_id,
            'content': new_msg.content,
            'sender_id': current_user.id,
            'sender_name': current_user.first_name,
            'timestamp': new_msg.timestamp.strftime('%b %d, %I:%M %p'),
            'sequence_number': new_msg.sequence_number
        }

        # 4. Broadcast to the specific application room
        room_name = f"application_{application_id}"
        emit('new_message', message_payload, room=room_name)

        # 5. Acknowledge sender (in case they aren't in the room for some reason, though they should be)
        emit('message_sent_ack', {'client_id': client_id, 'server_id': new_msg.id})

    except Exception as e:
        logger.error(f"Socket message error: {e}")
        db.session.rollback()
        emit('message_error', {'client_id': data.get('client_id'), 'error': 'Server error. Try again.'})

# --- REWRITTEN MESSAGES ROUTE ---

@views.route('/messages/<int:application_id>', methods=['GET', 'POST'])
@login_required
def messages(application_id):
    try:
        application = AdoptionApplication.query.get_or_404(application_id)

        # Permission Check
        is_applicant = (current_user.id == application.user_id)
        is_owner = (current_user.is_admin and application.pet.posted_by == current_user.id)

        if not (is_applicant or is_owner):
            flash("Unauthorized access.", "error")
            return redirect(url_for('views.home'))

        # Handle POST (Fallback for non-JS users, though JS will prevent this)
        if request.method == 'POST':
            content = request.form.get('message', '').strip()
            if content:
                last_msg = Message.query.filter_by(application_id=application_id).order_by(Message.sequence_number.desc()).first()
                next_seq = (last_msg.sequence_number + 1) if last_msg else 1
                
                msg = Message(
                    application_id=application_id, 
                    sender_id=current_user.id, 
                    content=content,
                    sequence_number=next_seq,
                    client_id=str(uuid.uuid4())
                )
                db.session.add(msg)
                db.session.commit()
                # Redirect to avoid form resubmission on refresh
                return redirect(url_for('views.messages', application_id=application_id))

        # Mark messages as read (if viewing)
        unread = Message.query.filter_by(application_id=application_id, is_read=False).filter(Message.sender_id != current_user.id).all()
        for m in unread:
            m.is_read = True
        if unread:
            db.session.commit()

        # Fetch conversation
        messages = Message.query.filter_by(application_id=application_id, is_deleted=False).order_by(Message.sequence_number).all()

        # Sidebar list (applications)
        if current_user.is_admin:
            sidebar_apps = AdoptionApplication.query.join(Pet).filter(Pet.posted_by == current_user.id).order_by(AdoptionApplication.updated_at.desc()).all()
        else:
            sidebar_apps = AdoptionApplication.query.filter_by(user_id=current_user.id).order_by(AdoptionApplication.updated_at.desc()).all()

        return render_template(
            'messages.html',
            user=current_user,
            messages=messages,
            application=application,
            pet=application.pet,
            applications=sidebar_apps
        )

    except Exception as e:
        logger.error(f"Error loading messages: {e}")
        flash("Could not load chat.", "error")
        return redirect(url_for('views.home'))

@views.route('/applications')
@login_required
def applications():
    try:
        if current_user.is_admin:
            # Admin sees applications for pets they posted
            apps = AdoptionApplication.query \
                .options(db.joinedload(AdoptionApplication.user))\
                .join(Pet) \
                .filter(Pet.posted_by == current_user.id) \
                .order_by(AdoptionApplication.id.desc()) \
                .all()
        else:
            # Regular users see their own applications
            apps = AdoptionApplication.query \
                .options(db.joinedload(AdoptionApplication.user))\
                .filter_by(user_id=current_user.id) \
                .order_by(AdoptionApplication.id.desc()) \
                .all()

        # Process each application
        for app in apps:
            # Count unread messages efficiently
            app.unread = Message.query.filter(
                Message.application_id == app.id,
                Message.sender_id != current_user.id,
                Message.is_read == False,
                Message.is_deleted == False
            ).count()
            
            # Attach recent messages (last 5)
            app.recent_messages = Message.query.filter_by(
                application_id=app.id,
                is_deleted=False
            ).order_by(Message.timestamp.desc()).limit(5).all()

        return render_template('applications.html', user=current_user, applications=apps)
    except Exception as e:
        logger.error(f"Error in applications route: {str(e)}")
        flash("An error occurred while loading applications", "error")
        return render_template('applications.html', user=current_user, applications=[])

@views.route('/mark_adopted/<int:pet_id>')
@login_required
def mark_adopted(pet_id):
    if not current_user.is_admin:
        abort(403)

    try:
        pet = Pet.query.get_or_404(pet_id)
        
        # Check if admin owns this pet
        if pet.posted_by != current_user.id:
            abort(403)
        
        pet.is_adopted = True
        pet.adoption_date = datetime.now(timezone.utc)
        db.session.commit()
        
        flash(f'{pet.name} marked as adopted - will be archived after two days', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking pet as adopted: {str(e)}")
        flash(f"Error: {str(e)}", "error")

    return redirect(url_for('views.pet_detail', pet_id=pet_id))

@views.route('/delete_pet/<int:pet_id>')
@login_required
def delete_pet(pet_id):
    if not current_user.is_admin:
        abort(403)

    try:
        pet = Pet.query.get_or_404(pet_id)
        
        # Check if admin owns this pet
        if pet.posted_by != current_user.id:
            abort(403)
        
        # Soft delete (archive)
        pet.is_deleted = True
        db.session.commit()
        
        flash(f"{pet.name} has been archived", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error archiving pet: {str(e)}")
        flash(f"Error archiving pet: {str(e)}", "error")
    
    return redirect(url_for('views.home'))

def clean_up_adopted_pets():
    """Clean up pets that have been adopted for more than 2 days"""
    try:
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        adopted_pets = Pet.query.filter(
            Pet.is_adopted == True,
            Pet.adoption_date <= two_days_ago,
            Pet.is_deleted == False
        ).all()

        for pet in adopted_pets:
            pet.is_deleted = True
            # Archive related applications
            AdoptionApplication.query.filter_by(pet_id=pet.id).update({'status': 'archived'})

        db.session.commit()
        logger.info(f"Cleaned up {len(adopted_pets)} adopted pets")
        return len(adopted_pets)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in cleanup: {str(e)}")
        return 0

@views.route('/edit_pet/<int:pet_id>', methods=['GET', 'POST'])
@login_required
def edit_pet(pet_id):
    if not current_user.is_admin:
        abort(403)
    
    try:
        pet = Pet.query.get_or_404(pet_id)
        
        if pet.posted_by != current_user.id:
            abort(403)
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            breed = request.form.get('breed', '').strip()
            city = request.form.get('city', '').strip()
            description = request.form.get('description', '').strip()
            
            # This check fails if the form sends empty strings for unchanged fields
            if not all([name, age, breed, city, description]):
                flash('All fields are required', 'error')
                # IMPORTANT: Return the template WITH the data so user doesn't lose progress
                return render_template('edit_pet.html', pet=pet, user=current_user, city_map=CITY_MAP)
            
            pet.name = name
            pet.age = age
            pet.breed = breed
            pet.city = city
            pet.description = description
            
            if 'image' in request.files:
                image = request.files['image']
                if image.filename != '':
                    filename = secure_filename(image.filename)
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    image_path = os.path.join(upload_folder, filename)
                    image.save(image_path)
                    pet.image_filename = filename
            
            db.session.commit()
            flash(f"{pet.name}'s details updated!", "success")
            return redirect(url_for('views.pet_detail', pet_id=pet.id))
        
        # Pass city_map here
        return render_template('edit_pet.html', pet=pet, user=current_user, city_map=CITY_MAP)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing pet: {str(e)}")
        flash("An error occurred while editing the pet", "error")
        return redirect(url_for('views.home'))

@views.route('/my_applications')
@login_required
def my_applications():
    try:
        applications = AdoptionApplication.query.filter_by(
            user_id=current_user.id
        ).join(Pet).filter(
            Pet.is_deleted == False
        ).order_by(AdoptionApplication.id.desc()).all()
        
        return render_template('applications.html', applications=applications, user=current_user)
    except Exception as e:
        logger.error(f"Error in my_applications: {str(e)}")
        flash("An error occurred while loading your applications", "error")
        return render_template('applications.html', applications=[], user=current_user)

@views.route('/delete_application/<int:application_id>')
@login_required
def delete_application(application_id):
    try:
        app = AdoptionApplication.query.get_or_404(application_id)

        # Permission checks
        has_permission = False
        if current_user.id == app.user_id:
            has_permission = True
        elif current_user.is_admin and current_user.id == app.pet.posted_by:
            has_permission = True

        if not has_permission:
            abort(403)

        # Soft delete all related messages
        Message.query.filter_by(application_id=application_id).update({'is_deleted': True})

        # Hard delete the application (as intended)
        db.session.delete(app)
        db.session.commit()
        
        flash("Application and its messages have been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting application: {str(e)}")
        flash(f"Failed to delete: {str(e)}", "error")

    return redirect(url_for('views.applications'))

@views.route('/admin/cleanup')
@login_required
def admin_cleanup():
    if not current_user.is_admin:
        abort(403)
    
    try:
        cleaned_count = clean_up_adopted_pets()
        flash(f"Cleaned up {cleaned_count} adopted pets", "success")
    except Exception as e:
        logger.error(f"Error in admin cleanup: {str(e)}")
        flash("Error during cleanup", "error")
    
    return redirect(url_for('views.home'))