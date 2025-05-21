from datetime import datetime
from flask import Blueprint, abort, json, jsonify, render_template, redirect, url_for, flash, request, current_app
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from . import db
from .models import User, Pet, AdoptionApplication, Message
from flask_socketio import emit, join_room
from . import socketio
import os

views = Blueprint('views', __name__)

@views.route('/home')
@login_required   
def home():
    city = request.args.get('city', '')
    
    if city:
        pets = Pet.query.filter_by(city=city).all()
    else:
        pets = Pet.query.all()
    
    return render_template('home.html', 
                         user=current_user, 
                         pets=pets,
                         selected_city=city)

#####################################################################

@views.route('/add_pet', methods=['GET', 'POST'])
@login_required 
def add_pet():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Only admin users can add posts','error')
        return redirect(url_for('views.home'))
    
    if request.method == 'POST': # here we wnat to see if user wnat to post something
        # get form data 
        name = request.form.get('name')
        age = request.form.get('age')
        breed = request.form.get('breed')
        description = request.form.get('description')

        city = request.form.get('city')

        # handle file apload
        if 'image' not in request.files:
            flash('No image file uploaded', 'error')
            return(redirect(request.url))
        
        image = request.files['image']
        if image.filename == '':
            flash('No selected image', 'error')
            return(redirect(request.url))
        
        if image:
            filename = secure_filename(image.filename)
            # create uploads folder if it soesn't exist
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            image.save(image_path)

            #create new pet entry
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
    return render_template('add_pet.html', user=current_user)

#####################################################################

@views.route('/pet/<int:pet_id>')
@login_required
def pet_detail(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    return render_template('pet_detail.html', user=current_user, pet=pet)

#####################################################################

@views.route('/submit_application/<int:pet_id>', methods=['POST'])
@login_required
def submit_application(pet_id):
    if request.method == 'POST':
        # Get form data
        form_data = {
            'reason': request.form.get('reason'),
            'housing': request.form.get('housing'),
            'landlord_approval': request.form.get('landlord_approval'),
            'other_pets': request.form.get('other_pets'),
            'pets_description': request.form.get('pets_description'),
            'caretaker': request.form.get('caretaker')
        }
        
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
            content=f"New adoption application submitted for pet ID {pet_id}"
        )
        
        db.session.add(first_message)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'redirect_url': url_for('views.messages', application_id=new_application.id)
            })
        
        return redirect(url_for('views.messages', application_id=new_application.id))
    
    return redirect(url_for('views.pet_detail', pet_id=pet_id))

#####################################################################
@socketio.on('connect')
def handle_connect():
    print(f'User {current_user.first_name}, Connected')

#####################################################################
@socketio.on('join_room')
def handle_join_room(data):
    application_id = data['application_id']
    join_room(application_id)
    emit('status_update', {'message': f'Joined room {application_id}'})

#####################################################################
@socketio.on('send_message')
def handle_send_message(data):
    application_id = data['application_id']
    content = data['content']

    # Save to database
    new_message = Message(
        application_id=application_id,
        sender_id=current_user.id,
        content=content  
    )

    db.session.add(new_message)
    db.session.commit()

    emit('new_message', {
        'sender': current_user.first_name,
        'content': content,
        'timestamp': new_message.timestamp.strftime('%b %d, %I:%M %p')
    }, room=application_id)

#####################################################################
@views.route('/messages/<int:application_id>', methods=['GET', 'POST'])
@login_required
def messages(application_id):
    application = AdoptionApplication.query.get_or_404(application_id)
    
    # Ensure the current user is either the applicant or admin
    if current_user.id is None or application.user_id is None or (current_user.id != application.user_id and not current_user.is_admin):
        flash("You don't have permission to view these messages.", "error")
        return redirect(url_for('views.home'))
    
    if request.method == 'POST':
        content = request.form.get('message')
        if content:
            new_message = Message(
                application_id=application_id, 
                sender_id=current_user.id,
                content=content
            )
            db.session.add(new_message)
            db.session.commit()

    # Fetch all messages for this application
    messages = Message.query.filter_by(application_id=application_id).order_by(Message.timestamp).all()
    
    # Mark messages as read if the current user is the recipient
    messages_to_update = []
    for msg in messages:
        if msg.sender_id != current_user.id and not msg.is_read:
            msg.is_read = True
            messages_to_update.append(msg)
    
    if messages_to_update:
        db.session.commit()

    # Count unread messages for all applications of the current user (or all if admin)
    if current_user.is_admin:
        applications = AdoptionApplication.query.order_by(AdoptionApplication.id.desc()).all()
    else:
        applications = AdoptionApplication.query.filter_by(user_id=current_user.id).order_by(AdoptionApplication.id.desc()).all()

    for app in applications:
        app.unread = Message.query.filter(
            Message.application_id == app.id,
            Message.sender_id != current_user.id,
            Message.is_read == False
        ).count()
    
    return render_template(
        'messages.html',
        user=current_user,
        messages=messages,
        application=application,
        pet=application.pet,
        applications=applications  # Pass applications with unread counts
    )

#####################################################################
@views.route('/applications')
@login_required
def applications():
    if current_user.is_admin:
        apps = AdoptionApplication.query.order_by(AdoptionApplication.id.desc()).all()
    else:
        apps = AdoptionApplication.query.filter_by(user_id=current_user.id).order_by(AdoptionApplication.id.desc()).all()

    # Count unread messages for each application
    for app in apps:
        app.unread = Message.query.filter(
            Message.application_id == app.id,
            Message.sender_id != current_user.id,
            Message.is_read == False
        ).count()

    return render_template('applications.html', user=current_user, applications=apps)

#####################################################################
@views.route('/mark_adopted/<int:pet_id>')
@login_required
def mark_adopted(pet_id):
    if not current_user.is_admin:
        abort(403)

    pet = Pet.query.get_or_404(pet_id)
    pet.is_adopted = True
    pet.application_date = datetime.utcnow()
    db.session.commit()
    flash(f'{pet.name} marked as adopted!', 'success')
    return redirect(url_for('views.pet_detail', pet_id=pet.id))

#####################################################################
@views.route('/delete_pet/<int:pet_id>')
@login_required
def delete_pet(pet_id):
    if not current_user.is_admin:
        abort(403)

    pet = Pet.query.get_or_404(pet_id)
    if not pet.is_adopted:
        flash('only adopted pets can be deleted', 'error')
    else:
        db.session.delete(pet)
        db.session.commit()
        flash(f'{pet.name} has been removed', 'info')
        return redirect(url_for('views.home'))
    
#####################################################################
@views.route('/edit_pet/<int:pet_id>', methods=['GET', 'POST'])
@login_required
def edit_pet(pet_id):
    if not current_user.is_admin:
        abort(403)  # Only admins can edit
    
    pet = Pet.query.get_or_404(pet_id)
    
    if request.method == 'POST':
        # Update pet data from form
        pet.name = request.form.get('name')
        pet.age = request.form.get('age')
        pet.breed = request.form.get('breed')
        pet.city = request.form.get('city')
        pet.description = request.form.get('description')
        
        # Handle image upload (optional)
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                filename = secure_filename(image.filename)
                image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                pet.image_filename = filename
        
        db.session.commit()
        flash(f"{pet.name}'s details updated!", "success")
        return redirect(url_for('views.pet_detail', pet_id=pet.id))
    
    return render_template('edit_pet.html', pet=pet)