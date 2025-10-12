from datetime import datetime, timedelta, timezone
from flask import Blueprint, abort, json, jsonify, render_template, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from . import db
from .models import User, Pet, AdoptionApplication, Message
from flask_socketio import emit, join_room, disconnect
import uuid
from . import socketio
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

views = Blueprint('views', __name__)

# Constants
MAX_MESSAGE_LENGTH = 1000
MESSAGE_RATE_LIMIT = 10  # messages per minute per user
ALLOWED_STATUSES = ['pending', 'approved', 'rejected', 'archived']

# Rate limiting dictionary - in production, use Redis
user_message_count = {}

def validate_message_content(content):
    """Validate message content"""
    if not content or not content.strip():
        return False, "Message cannot be empty"
    if len(content) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long (max {MAX_MESSAGE_LENGTH} characters)"
    return True, None

def check_rate_limit(user_id):
    """Check if user has exceeded message rate limit"""
    now = datetime.now()
    minute_key = f"{user_id}_{now.strftime('%Y%m%d%H%M')}"
    
    if minute_key not in user_message_count:
        user_message_count[minute_key] = 0
    
    if user_message_count[minute_key] >= MESSAGE_RATE_LIMIT:
        return False
    
    user_message_count[minute_key] += 1
    return True

@views.route('/')
@login_required   
def home():
    try:
        city_id = request.args.get('city', '')

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
        
        selected_city = city_map.get(city_id, '')

        # Base query - only show non-deleted, non-adopted pets
        query = Pet.query.filter(Pet.is_deleted == False, Pet.is_adopted == False)

        # Filter by city if specified
        if city_id and city_id in city_map:
            pets = query.filter_by(city=city_id).all()
        else:
            pets = query.all()

        return render_template('home.html', 
                               user=current_user, 
                               pets=pets,
                               selected_city=selected_city)
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        flash("An error occurred while loading pets", "error")
        return render_template('home.html', user=current_user, pets=[], selected_city='')

@views.route('/add_pet', methods=['GET', 'POST'])
@login_required 
def add_pet():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Only admin users can add posts', 'error')
        return redirect(url_for('views.home'))
    
    if request.method == 'POST':
        try:
            # Get and validate form data 
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            breed = request.form.get('breed', '').strip()
            description = request.form.get('description', '').strip()
            city = request.form.get('city', '').strip()

            # Validation
            if not all([name, age, breed, description, city]):
                flash('All fields are required', 'error')
                return redirect(request.url)

            # Handle file upload
            if 'image' not in request.files:
                flash('No image file uploaded', 'error')
                return redirect(request.url)
            
            image = request.files['image']
            if image.filename == '':
                flash('No selected image', 'error')
                return redirect(request.url)
            
            if image:
                filename = secure_filename(image.filename)
                # Create uploads folder if it doesn't exist
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                image_path = os.path.join(upload_folder, filename)
                image.save(image_path)

                # Create new pet entry
                new_pet = Pet(
                    name=name,
                    age=age,
                    breed=breed,
                    description=description,
                    city=city,
                    image_filename=filename,
                    posted_by=current_user.id
                )

                db.session.add(new_pet)   
                db.session.commit()
                flash('Pet added successfully', 'success')
                return redirect(url_for('views.home'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding pet: {str(e)}")
            flash('An error occurred while adding the pet', 'error')
    
    return render_template('add_pet.html', user=current_user)

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
        
        city_name = city_map.get(str(pet.city), 'Unknown')  # Fixed typo
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
            first_message = Message(
                application_id=new_application.id,
                sender_id=current_user.id,
                content=f"New adoption application submitted for {pet.name}"
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
#Application status management route
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
        
        # Update status
        app.status = status
        db.session.commit()
        
        # Send automatic message
        status_message = f"Application has been {status}"
        auto_message = Message(
            application_id=application_id,
            sender_id=current_user.id,
            content=status_message
        )
        db.session.add(auto_message)
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
    try:
        if current_user.is_authenticated:
            if current_user.is_admin:
                join_room(f'admin{current_user.id}')
            join_room(f'user{current_user.id}')
            logger.info(f"User {current_user.id} connected")

            # Send connection confirmation with user state
            emit('connection_confirmed', {
                'user_id': current_user.id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logger.error(f"Error in connect handler: {str(e)}")
        disconnect()

@socketio.on('join_room')
def handle_join_room(data):
    try:
        application_id = data.get('application_id')
        if not application_id:
            return False
        
        application = AdoptionApplication.query.get(application_id)
        if not application:
            return False

        # permission logic
        has_access = False
        if current_user.id == application.user_id:
            # User is the applicant
            has_access = True
        elif current_user.is_admin and application.pet.posted_by == current_user.id:
            # User is admin who posted the pet
            has_access = True

        if not has_access:
            logger.warning(f"Unauthorized room join attempt by user {current_user.id} for application {application_id}")
            return False
        
        join_room(str(application_id))

        #send room state 
        latest_messages = Message.query.filter_by(
            application_id=application_id,
            is_deleted=False
        ).order_by(Message.sequence_number.desc()).limit(50).all()

        emit('room_joined', {
            'application_id': application_id,
            'message_count': len(latest_messages),
            'last_sequence': latest_messages[0].sequence_number if latest_messages else 0,
            'last_message_id': latest_messages[0].id if latest_messages else 0
        })

        logger.info(f"User {current_user.id} joined room {application_id}")
        return True
    except Exception as e:
        logger.error(f"Error in join_room handler: {str(e)}")
        return False

@socketio.on('sync_messages')
def handle_sync_messages(data):
    """Handle message synchronization requests"""
    try:
        application_id = data.get('application_id')
        last_message_id = data.get('last_message_id', 0)
        last_sequence = data.get('last_sequence', 0)
        
        if not application_id:
            return
        
        application = AdoptionApplication.query.get(application_id)
        if not application:
            return
        
        # Check permissions
        has_access = (current_user.id == application.user_id or 
                     (current_user.is_admin and application.pet.posted_by == current_user.id))
        
        if not has_access:
            return
        
        # Get messages newer than client's last known message
        missed_messages = Message.query.filter(
            Message.application_id == application_id,
            Message.sequence_number > last_sequence,
            Message.is_deleted == False
        ).order_by(Message.sequence_number).all()
        
        messages_data = []
        for msg in missed_messages:
            messages_data.append({
                'id': msg.id,
                'client_id': getattr(msg, 'client_id', None),
                'sender': msg.sender.first_name,
                'sender_id': msg.sender_id,
                'content': msg.content,
                'timestamp': msg.timestamp.strftime('%b %d, %I:%M %p'),
                'sequence_number': msg.sequence_number,
                'is_read': msg.is_read
            })
        
        emit('sync_response', {
            'missed_messages': messages_data,
            'current_sequence': missed_messages[-1].sequence_number if missed_messages else last_sequence
        })
        
    except Exception as e:
        logger.error(f"Error in sync_messages handler: {str(e)}")

@socketio.on('send_message')
def handle_send_message(data):
    try:
        application_id = data.get('application_id')
        content = data.get('content', '').strip()
        client_id = data.get('client_id')  # Client-generated unique ID
        
        if not application_id or not content or not client_id:
            emit('message_failed', {
                'client_id': client_id,
                'error': 'Invalid message data'
            })
            return
        
        # Check for duplicate based on client_id
        existing_message = Message.query.filter_by(client_id=client_id).first()
        if existing_message:
            # Message already exists, send confirmation
            emit('message_confirmed', {
                'client_id': client_id,
                'server_id': existing_message.id,
                'sequence_number': existing_message.sequence_number
            })
            return
        
        # Validate message content
        is_valid, error_msg = validate_message_content(content)
        if not is_valid:
            emit('message_failed', {
                'client_id': client_id,
                'error': error_msg
            })
            return
        
        # Check rate limit
        if not check_rate_limit(current_user.id):
            emit('message_failed', {
                'client_id': client_id,
                'error': 'Rate limit exceeded. Please slow down.'
            })
            return
        
        application = AdoptionApplication.query.get(application_id)
        if not application:
            emit('message_failed', {
                'client_id': client_id,
                'error': 'Application not found'
            })
            return
        
        # Check if application is archived
        if application.status == 'archived':
            emit('message_failed', {
                'client_id': client_id,
                'error': 'Cannot send messages to archived applications'
            })
            return
        
        # Use database transaction for consistency
        try:
            with db.session.begin():
                # Get next sequence number
                last_sequence = db.session.query(db.func.max(Message.sequence_number)).filter_by(
                    application_id=application_id
                ).scalar() or 0
                
                # Create new message
                new_message = Message(
                    application_id=application_id,
                    sender_id=current_user.id,
                    content=content,
                    client_id=client_id,
                    sequence_number=last_sequence + 1
                )
                
                db.session.add(new_message)
                db.session.flush()  # Get the ID without committing
                
                # Prepare message data
                message_data = {
                    'id': new_message.id,
                    'client_id': client_id,
                    'sender': current_user.first_name,
                    'sender_id': current_user.id,
                    'content': content,
                    'timestamp': (new_message.timestamp or datetime.now(timezone.utc)).strftime('%b %d, %I:%M %p'),
                    'sequence_number': new_message.sequence_number,
                    'is_read': False
                }
                
                # Determine recipients
                recipients = [f'user{application.user_id}']
                if current_user.id != application.user_id:
                    recipients.append(f'admin{application.pet.posted_by}')
                
                # Emit to recipients
                for room in recipients:
                    emit('new_message', message_data, room=room)
                
                # Send confirmation to sender
                emit('message_confirmed', {
                    'client_id': client_id,
                    'server_id': new_message.id,
                    'sequence_number': new_message.sequence_number
                })
                
                # Transaction commits automatically here
                
        except Exception as db_error:
            logger.error(f"Database error in send_message: {str(db_error)}")
            emit('message_failed', {
                'client_id': client_id,
                'error': 'Failed to save message'
            })
            return
        
        logger.info(f"Message sent by user {current_user.id} in application {application_id}")
        
    except Exception as e:
        logger.error(f"Error in send_message handler: {str(e)}")
        emit('message_failed', {
            'client_id': data.get('client_id'),
            'error': 'Failed to send message'
        })

@views.route('/messages/<int:application_id>', methods=['GET', 'POST'])
@login_required
def messages(application_id):
    try:
        application = AdoptionApplication.query.get_or_404(application_id)

        # Permission check
        has_access = False
        if current_user.id == application.user_id:
            has_access = True
        elif current_user.is_admin:
            if application.pet and application.pet.posted_by == current_user.id:
                has_access = True

        if not has_access:
            flash("You don't have permission to view these messages.", "error")
            return redirect(url_for('views.home'))

        # Handle POST requests (fallback form submission)
        if request.method == 'POST':
            content = request.form.get('message', '').strip()
            
            # Validate message
            is_valid, error_msg = validate_message_content(content)
            if not is_valid:
                flash(error_msg, 'error')
                return redirect(url_for('views.messages', application_id=application_id))
            
            if application.status != 'archived':
                # Check for recent duplicate (fallback protection)
                recent_duplicate = Message.query.filter(
                    Message.application_id == application_id,
                    Message.sender_id == current_user.id,
                    Message.content == content,
                    Message.timestamp > datetime.now(timezone.utc) - timedelta(seconds=5)
                ).first()
                
                if not recent_duplicate:
                    # Get next sequence number
                    last_sequence = db.session.query(db.func.max(Message.sequence_number)).filter_by(
                        application_id=application_id
                    ).scalar() or 0
                    
                    new_message = Message(
                        application_id=application_id,
                        sender_id=current_user.id,
                        content=content,
                        client_id=str(uuid.uuid4()),  # Generate client_id for form submissions
                        sequence_number=last_sequence + 1
                    )
                    db.session.add(new_message)
                    db.session.commit()
            
            # Redirect to prevent form resubmission on refresh
            return redirect(url_for('views.messages', application_id=application_id))

        # Fetch all non-deleted messages ordered by sequence
        messages = Message.query.filter_by(
            application_id=application_id, 
            is_deleted=False
        ).order_by(Message.sequence_number).all()

        # Mark messages as read
        messages_to_update = []
        for msg in messages:
            if msg.sender_id != current_user.id and not msg.is_read:
                msg.is_read = True
                messages_to_update.append(msg)

        if messages_to_update:
            db.session.commit()

        # Get applications with unread counts
        if current_user.is_admin:
            applications = AdoptionApplication.query.join(Pet).filter(
                Pet.posted_by == current_user.id
            ).order_by(AdoptionApplication.id.desc()).all()
        else:
            applications = AdoptionApplication.query.filter_by(
                user_id=current_user.id
            ).order_by(AdoptionApplication.id.desc()).all()

        # Calculate unread counts efficiently
        for app in applications:
            app.unread = Message.query.filter(
                Message.application_id == app.id,
                Message.sender_id != current_user.id,
                Message.is_read == False,
                Message.is_deleted == False
            ).count()

        return render_template(
            'messages.html',
            user=current_user,
            messages=messages,
            application=application,
            pet=application.pet,
            applications=applications
        )
    except Exception as e:
        logger.error(f"Error in messages route: {str(e)}")
        flash("An error occurred while loading messages", "error")
        return redirect(url_for('views.applications'))

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
        
        # Check if admin owns this pet
        if pet.posted_by != current_user.id:
            abort(403)
        
        if request.method == 'POST':
            # Validate and update pet data
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            breed = request.form.get('breed', '').strip()
            city = request.form.get('city', '').strip()
            description = request.form.get('description', '').strip()
            
            if not all([name, age, breed, city, description]):
                flash('All fields are required', 'error')
                return render_template('edit_pet.html', pet=pet)
            
            pet.name = name
            pet.age = age
            pet.breed = breed
            pet.city = city
            pet.description = description
            
            # Handle image upload (optional)
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
        
        return render_template('edit_pet.html', pet=pet, user=current_user)
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

# NEW: Cleanup endpoint for testing/admin use
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