from . import db
from flask_login import UserMixin 
from sqlalchemy.sql import func #get the currnt date and time Automatically 
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

class User(db.Model, UserMixin): 
    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    is_admin   = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Pet(db.Model): 
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100))
    age            = db.Column(db.Integer)
    breed          = db.Column(db.String(100))
    description    = db.Column(db.Text)
    city           = db.Column(db.String(100))  # Changed from location to city
    image_filename = db.Column(db.String(200))
    is_adopted     = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    adoption_date = db.Column(db.DateTime)
    posted_by      = db.Column(db.Integer, db.ForeignKey('user.id'))
    poster = db.relationship('User', foreign_keys=[posted_by]) 
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Relationships with cascade delete
    applications = db.relationship(
        'AdoptionApplication', 
        backref="pet", 
        lazy=True,
        cascade="all, delete-orphan"
    )

class AdoptionApplication(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    application_date = db.Column(db.DateTime, default=func.now())
    answers = db.Column(db.Text)  
    status = db.Column(db.String(20), default='pending')
    user = db.relationship('User',backref='applications')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # is_deleted = db.Column(db.Boolean, default=False)  in case i want to soft delete the application
    messages = db.relationship(
        'Message', 
        backref='application', 
        lazy=True,
        cascade="all, delete-orphan"
    )


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('adoption_application.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=func.now())
    is_read = db.Column(db.Boolean, default=False)
    sender = db.relationship('User', foreign_keys=[sender_id])
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
