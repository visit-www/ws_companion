import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from typing import Optional
from werkzeug.security import check_password_hash, generate_password_hash
from . import Base  # Import the Base from __init__.py
from enum import Enum as PyEnum
from datetime import datetime, timezone
import json
#********************************
# * Reusubale defualt values in classes :
# Default values for categories
class CategoryNames(PyEnum):
    GUIDELINES = 'guidelines'
    CLASSIFICATIONS = 'classifications'
    DIFFERENTIAL_DIAGNOSIS = 'differential_diagnosis'
    VETTING_TOOLS = 'vetting_tools'
    ANATOMY = 'anatomy'
    CURATED_CONTENTS = 'curated_contents'
    REPORT_CHECKER = 'report_checker'
    RAD_CALCULATORS = 'rad_calculators'
    TNM_STAGING = 'tnm_staging'
    IMAGE_SEARCH = 'image_search'
    PHYSICS = 'physics'
    GOVERNANCE_AUDITS = 'governance_audits'
    COURSES = 'courses'
    RESEARCH_TOOLS = 'research_tools'
    MUSIC = 'music'    

# * Default values for modules 
class ModuleNames(PyEnum):
    HEAD_AND_NECK = "head_and_neck"
    NEURORADIOLOGY = "neuroradiology"
    CHEST = "chest"
    CARDIOVASCULAR = "cardiovascular"
    BREAST = "breast"
    GASTROINTESTINAL = "gastrointestinal"
    ABDOMINAL = "abdominal"
    GENITOURINARY = "genitourinary"
    MUSCULOSKELETAL = "musculoskeletal"
    VASCULAR = "vascular"
    PEDIATRIC = "pediatric"
    ONCOLOGIC = "oncologic"
    EMERGENCY = "emergency"
    INTERVENTIONAL = "interventional"
    NUCLEAR_MEDICINE = "nuclear_medicine"
    RADIOGRAPHERS = "radiographers"
#*________________________________________________________________
# * Define Models :

# User model:
class User(UserMixin, Base):
    __tablename__ = "users"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True)
    username: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False, index=True)
    password: so.Mapped[str] = sa.Column(sa.String(150), nullable=False)
    email: so.Mapped[str] = sa.Column(sa.String(150), unique=True,nullable=False, index=True)
    is_paid: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    is_admin: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    status: so.Mapped[str] = sa.Column(sa.String(50), default='active', nullable=False)  # Account status
    # Automatically handled by event listeners on update or creation
    created_at: so.Mapped[datetime] = sa.Column(
        sa.DateTime, 
        default=lambda: datetime.now(timezone.utc),  # Correctly uses current UTC time at record creation
        nullable=False
    )

    last_updated: so.Mapped[datetime] = sa.Column(
        sa.DateTime, 
        default=lambda: datetime.now(timezone.utc),  # Set on creation
        onupdate=lambda: datetime.now(timezone.utc),  # Updated whenever the record is modified
        nullable=False
    )
    # Encapsulate functions to hash passwords and to ehck passwords.
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

# Gudeline model:
class Guideline(Base):
    __tablename__ = "guidelines"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True)
    title: so.Mapped[str] = sa.Column(sa.String(500), nullable=False)
    file_type: so.Mapped[Optional[str]] = sa.Column(sa.String(20), nullable=True)
    file_path: so.Mapped[Optional[str]] = sa.Column(sa.String(256), nullable=True)
    url: so.Mapped[Optional[str]] = sa.Column(sa.String(256), nullable=True)
    embed_code: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    last_updated: so.Mapped[datetime] = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Guideline(id={self.id}, title='{self.title}')>"

# Content model
class Content(Base):
    __tablename__ = "contents"

    # * Columns set by admin at the time of content upload
    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, index=True)
    title: so.Mapped[str] = sa.Column(sa.String(565), index=True, nullable=False)
    
    category: so.Mapped[str] = sa.Column(sa.Enum(CategoryNames, name='category_name'), index=True, nullable=False)  # Admin must select from the categories.
    module: so.Mapped[str] = sa.Column(sa.Enum(ModuleNames, name="module_name"), index=True, nullable=False)  # Admin must select from the modules.
    status: so.Mapped[str] = sa.Column(sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='status'), default='DRAFT')
    file:so.Mapped[str] = sa.Column(sa.String(255), index=True,nullable=True)
    filepath:so.Mapped[str] = sa.Column(sa.String(255), index=True,nullable=True) # uploaded files
    external_url: so.Mapped[Optional[str]] = sa.Column(sa.String(2083), nullable=True)  # Maximum URL length
    embed_code: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    keywords: so.Mapped[Optional[str]] = sa.Column(sa.Text, index=True, nullable=True)
    language: so.Mapped[str] = sa.Column(sa.String(20), default='English')
    content_tags: so.Mapped[Optional[str]] = sa.Column(sa.Text, index=True, nullable=True)
    importance_level: so.Mapped[str] = sa.Column(sa.Enum('LOW', 'MEDIUM', 'HIGH', name='importance_level'), default='MEDIUM')
    featured: so.Mapped[bool] = sa.Column(sa.Boolean, default=False)
    paid_access: so.Mapped[bool] = sa.Column(sa.Boolean, default=False)  # True if paid, False if free
    api_endpoint: so.Mapped[Optional[str]] = sa.Column(sa.String(2083), nullable=True)

    # * Columns managed by event listeners
    description: so.Mapped[str] = sa.Column(sa.Text, nullable=True) 
    version: so.Mapped[str] = sa.Column(sa.String(10), default='1.0')
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime,default=datetime.now(timezone.utc))  # Set only once on insert
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime,default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))  # Updated on each modification

    # * Columns managed by session_audit route in routes.py
    last_accessed: so.Mapped[Optional[datetime]] = sa.Column(sa.DateTime, nullable=True) 
    access_count: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # !* Managed by session_audit in the relevant route.
    view_duration: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # Time in seconds, managed in session_audit routes in routes.py
    usage_statistics: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps([{}]))  # * Store as JSON: Managed in session_audit routes in routes.py

    # todo: Columns to be handled by add_content route (yet to be implemented)
    created_by: so.Mapped[str] = sa.Column(sa.String(80), default='Admin')  # todo: To be set in the add_content route in routes.py
    file_path: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)
    file_size: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # todo: To be handled in add_content route
    estimated_reading_time: so.Mapped[int] = sa.Column(sa.Integer, nullable=True)  # In minutes, to be handled later
    bookmark_count: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # todo: To be handled in add_content route or related route
    related_content: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps([]))  # todo: To be handled in add_content route
    related_api_links: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps({}))  # todo: To be handled in add_content route
    accessibility_features: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps([]))  # todo: Multiple features, handled in add_content route (cant be handled by Enum)
    #----------------------------------
    # * Relationships
    # All relations are defined in specialized models.

    def __repr__(self) -> str:
        return f'<Content {self.title}>'
#------------------------------------------------------------------------------

# UserFeedback model :
class UserFeedback(Base):
    __tablename__ = 'user_feedback'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)  # References the 'users' table
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id'), nullable=False)  # References the 'contents' table
    feedback: so.Mapped[str] = sa.Column(sa.Text, nullable=False)
    is_public: so.Mapped[bool] = sa.Column(sa.Boolean, default=False, nullable=False)
    user_display_name: so.Mapped[Optional[str]] = sa.Column(sa.String(100), nullable=True)

    # Relationships: These create convenient access points between models.
    user = so.relationship('User', backref='feedbacks')  # The 'User' class will have an attribute 'feedbacks' for accessing related UserFeedback records
    content = so.relationship('Content', backref='feedbacks')  # The 'Content' class will have an attribute 'feedbacks' for accessing related UserFeedback records

    def __repr__(self) -> str:
        return f"<UserFeedback(id={self.id}, user_display_name='{self.user_display_name}', feedback='{self.feedback[:20]}...')>"
# UserData model: captures user interactions with the contents
class UserData(Base):
    __tablename__ = 'user_data'

    # Primary Key: Unique identifier for each interaction
    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    # Foreign Key: References the unique identifier of the user from the users table
    user_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Foreign Key: References the unique identifier of the content from the contents table
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id', ondelete='CASCADE'), nullable=False)

    # Enum: Type of interaction (viewed, bookmarked, recommended, etc.)
    interaction_type: so.Mapped[str] = sa.Column(sa.Enum('viewed', 'bookmarked', 'recommended', name='interaction_types'), nullable=False, default='viewed')

    # DateTime: Timestamp of when the interaction occurred
    interaction_date: so.Mapped[datetime] = sa.Column(sa.DateTime, nullable=False, default=datetime.now(timezone.utc))

    # Text: Stores user feedback or notes related to the specific interaction
    feedback: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)

    # Integer: User-provided rating for the content (e.g., 1-5 stars)
    content_rating: so.Mapped[Optional[int]] = sa.Column(sa.Integer, nullable=True)

    # Integer: Time spent (in seconds) by the user on the content during the interaction
    time_spent: so.Mapped[int] = sa.Column(sa.Integer, nullable=False)

    # DateTime: Timestamp of the last interaction between the user and the content
    last_interaction: so.Mapped[Optional[datetime]] = sa.Column(sa.DateTime, nullable=True)
    
    # Relationships: Define relationship objects with Users and Content models:
    user = so.relationship('User', backref=so.backref('user_data', lazy='dynamic', cascade="all, delete-orphan"))    
    content = so.relationship('Content', backref=so.backref('user_data', lazy='dynamic', cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<UserData(id={self.id}, user_id={self.user_id}, content_id={self.content_id})>"

# References model:
class Reference(Base):
    __tablename__ = 'references'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id'), nullable=False)  # Foreign Key linking to Contents
    
    title: so.Mapped[str] = sa.Column(sa.String(255), nullable=False)  # Title of the reference
    file_path: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)  # File path if reference is a document
    url: so.Mapped[Optional[str]] = sa.Column(sa.String(2083), nullable=True)  # URL if reference is an online resource
    embed_code: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Embed code for embeddable content
    description: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Optional description or notes
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc))  # Timestamp of creation
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))  # Timestamp of last update
    
    # Define the relationship back to Content
    content = so.relationship('Content', backref='references')  # Using backref to link back to Content

    def __repr__(self) -> str:
        return f"<Reference(id={self.id}, title='{self.title}', content_id={self.content_id})>"

# ********************************

# ! Define event listeners

# Event listener function to populate default values and update relevant columns
@sa.event.listens_for(Content, 'before_insert')
@sa.event.listens_for(Content, 'before_update')

def update_contents_table(mapper, connection, target):
    """Listener to populate default values before inserting or updating."""
    # 2. Populate Description if not provided
    if not target.description:
        target.description = f"Title: This item belongs to {target.category} and {target.module}"
    
    # 3. Update version number
    try:
        target.version = f"{float(target.version) + 0.1}"
    except ValueError:
        target.version = "1.0"
        