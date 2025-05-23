from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Enum
import enum

# Initialize extensions

db = SQLAlchemy()
bcrypt = Bcrypt()

# Enum for CharityApplication status
class ApplicationStatus(enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"

class BaseModel(db.Model, SerializerMixin):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

import re

class User(BaseModel):
    __tablename__ = 'users'

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String, unique=False, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

    charity_application = db.relationship(
        'CharityApplication', back_populates='user', uselist=False,
        cascade="all, delete-orphan"
    )
    donations = db.relationship(
        'Donation', back_populates='user',
        cascade="all, delete-orphan"
    )
    charity_profile = db.relationship(
        'Charity', back_populates='user', uselist=False,
        cascade="all, delete-orphan",  post_update=True
    )

    serialize_rules = ("-charity_application.user","-donations.donor", "-charity_profile.user",)

    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': user_type
    }

    def validate_password(self, password):
        if len(password) <= 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        return True

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
class Donor(User):
    __tablename__ = 'donors'

    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    reminder_enabled = db.Column(db.Boolean, default=False)
    anonymous_donor = db.Column(db.Boolean, default=False)
    donation_frequency = db.Column(db.String, default='one-time')

    donations = db.relationship(
        'Donation', back_populates='donor',
        cascade="all, delete-orphan",
        foreign_keys='Donation.donor_id'
    )

    serialize_rules = ("-donations.donor",)

    __mapper_args__ = {
        'polymorphic_identity': 'donor',
    }

class Donation(BaseModel):
    __tablename__ = 'donations'

    amount = db.Column(db.Integer, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="pending")

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    donor_id = db.Column(db.Integer, db.ForeignKey('donors.id'), nullable=False)
    charity_id = db.Column(db.Integer, db.ForeignKey('charities.id'), nullable=False)

    donor = db.relationship(
        'Donor', back_populates='donations', foreign_keys=[donor_id]
    )
    user = db.relationship(
        'User', back_populates='donations', foreign_keys=[user_id]
    )
    charity = db.relationship(
        'Charity', back_populates='donations', foreign_keys=[charity_id]
    )

    def to_dict_simple(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "donor_name": self.donor.name if not self.is_anonymous else "Anonymous"
        }

    serialize_rules = ("-donor.donations","-user.donations","-charity.donations",)

class Charity(User):
    __tablename__ = 'charities'

   
    id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        primary_key=True
        
    )

    organisation_name = db.Column(db.String(100), nullable=True)
    organisation_description = db.Column(db.String, nullable=True)
    logo_url = db.Column(db.String, nullable=True)
    goal = db.Column(db.String, nullable=True)
    approved = db.Column(db.Boolean, default=False)

    # relationships
    user = db.relationship(
        'User',
        back_populates='charity_profile',
        uselist=False,
        post_update=True
    )
    stories = db.relationship(
        'Story',
        back_populates='charity',
        cascade="all, delete-orphan"
    )
    donations = db.relationship(
        'Donation',
        back_populates='charity',
        cascade="all, delete-orphan"
    )
    inventories = db.relationship(
        'Inventory',
        back_populates='charity',
        cascade="all, delete-orphan"
    )

    serialize_rules = (
        '-stories.charity',
        '-donations.charity',
        '-inventories.charity',
        '-user.charity_profile',
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_name": self.name,
            "organisation_name": self.organisation_name,
            "organisation_description": self.organisation_description,
            "goal": self.goal,
            "logo_url": self.logo_url,
            "approved": self.approved,
            "donations": [donation.to_dict_simple() for donation in self.donations]
        }

    __mapper_args__ = {
        'polymorphic_identity': 'charity',
    }
class Admin(User):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'admin',
    }

class CharityApplication(BaseModel):
    __tablename__ = 'charity_applications'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organisation_name = db.Column(db.String(100), nullable=False)
    organisation_description = db.Column(db.Text, nullable=False)
    status = db.Column(Enum(ApplicationStatus), default=ApplicationStatus.pending, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='charity_application')

    serialize_rules = ("-user.charity_application",)

    def accept(self):
        self.status = ApplicationStatus.accepted
        if not self.user.charity_profile:
            charity = Charity(
                user=self.user,
                organisation_name=self.organisation_name,
                organisation_description=self.organisation_description,
                approved=True
            )
            db.session.add(charity)
        else:
            self.user.charity_profile.approved = True

    def reject(self):
        self.status = ApplicationStatus.rejected

class Story(BaseModel):
    __tablename__ = 'stories'

    charity_id = db.Column(db.Integer, db.ForeignKey('charities.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))

    charity = db.relationship('Charity', back_populates='stories')

    serialize_rules = ("-charity.stories",)

class Inventory(BaseModel):
    __tablename__ = 'inventories'

    charity_id = db.Column(db.Integer, db.ForeignKey('charities.id'), nullable=False)
    product = db.Column(db.String, nullable=False)
    product_quantity = db.Column(db.Integer, nullable=False)
    beneficiary_name = db.Column(db.String(100), nullable=False)

    charity = db.relationship('Charity', back_populates='inventories')

    serialize_rules = ("-charity.inventories",)



