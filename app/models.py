import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from typing import Optional
from werkzeug.security import check_password_hash, generate_password_hash
from . import Base  # Import the Base from __init__.py
from enum import Enum as PyEnum
from datetime import datetime, timezone
import json

# ********************************
# * Reusable Enums:

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
    REPORT_TEMPLATE = 'report_template'  # Default category for report templates

# Default values for modules
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
    OTHERS = "others"

# Enum for body parts
class BodyPartEnum(PyEnum):
    NEURO = 'neuro'
    HEAD_AND_NECK = 'head and neck'
    ENT = 'ent'
    PEDIATRICS = 'pediatrics'
    MSK = 'msk'
    LUNG = 'lung'
    CARDIAC = 'cardiac'
    ENDOCRINE = 'endocrine'
    HEPATOBILIARY = 'hepatobiliary'
    UROLOGY = 'urology'
    GYNAECOLOGY = 'gynaecology'
    UPPER_GI = 'upper gi'
    VASCULAR = 'vascular'
    ONCOLOGY = 'oncology'
    MISCELLANEOUS = 'miscellaneous'
    BREAST = 'breast'
    OTHERS = 'others'

# Enum for modalities
class ModalityEnum(PyEnum):
    CT = 'ct'
    X_RAY = 'x-ray'
    MRI = 'mri'
    ULTRASOUND = 'ultrasound'
    NUCLEAR_MEDICINE = 'nuclear medicine'
    MAMMOGRAPHY = 'mammography'
    OTHERS = 'others'

# ********************************
# * Models:

# 1. User Model
class User(UserMixin, Base):
    __tablename__ = "users"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True)
    username: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False, index=True)
    password: so.Mapped[str] = sa.Column(sa.String(150), nullable=False)
    email: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False, index=True)
    is_paid: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    is_admin: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    status: so.Mapped[str] = sa.Column(sa.String(50), default='active', nullable=False)  # Account status
    created_at: so.Mapped[datetime] = sa.Column(
        sa.DateTime, 
        default=lambda: datetime.now(timezone.utc),  # Correctly uses current UTC time at record creation
        nullable=False
    )

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

# 2. Content Model
class Content(Base):
    __tablename__ = "contents"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, index=True)
    title: so.Mapped[str] = sa.Column(sa.String(565), index=True, nullable=False)
    category: so.Mapped[str] = sa.Column(sa.Enum(CategoryNames, name='category_name'), index=True, nullable=False)  # Admin must select from the categories.
    module: so.Mapped[str] = sa.Column(sa.Enum(ModuleNames, name="module_name"), index=True, nullable=False)  # Admin must select from the modules.
    status: so.Mapped[str] = sa.Column(sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='status'), default='DRAFT')
    file: so.Mapped[str] = sa.Column(sa.String(255), index=True, nullable=True)
    filepath: so.Mapped[str] = sa.Column(sa.String(255), index=True, nullable=True)  # Uploaded files
    external_url: so.Mapped[Optional[str]] = sa.Column(sa.String(2083), nullable=True)  # Maximum URL length
    embed_code: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    keywords: so.Mapped[Optional[str]] = sa.Column(sa.Text, index=True, nullable=True)
    language: so.Mapped[str] = sa.Column(sa.String(20), default='English')
    content_tags: so.Mapped[Optional[str]] = sa.Column(sa.Text, index=True, nullable=True)
    importance_level: so.Mapped[str] = sa.Column(sa.Enum('LOW', 'MEDIUM', 'HIGH', name='importance_level'), default='MEDIUM')
    featured: so.Mapped[bool] = sa.Column(sa.Boolean, default=False)
    paid_access: so.Mapped[bool] = sa.Column(sa.Boolean, default=False)  # True if paid, False if free
    api_endpoint: so.Mapped[Optional[str]] = sa.Column(sa.String(2083), nullable=True)

    # Columns managed by event listeners
    description: so.Mapped[str] = sa.Column(sa.Text, nullable=True)
    version: so.Mapped[float] = sa.Column(sa.Float, default=1.0)
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc))  # Set only once on insert
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))  # Updated on each modification

    # Columns managed by session_audit route in routes.py
    last_accessed: so.Mapped[Optional[datetime]] = sa.Column(sa.DateTime, nullable=True)
    access_count: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # Managed by session_audit in the relevant route.
    view_duration: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # Time in seconds, managed in session_audit routes in routes.py
    usage_statistics: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps([{}]))  # Store as JSON: Managed in session_audit routes in routes.py

    # Columns to be handled by add_content route (yet to be implemented)
    created_by: so.Mapped[str] = sa.Column(sa.String(80), default='Admin')  # To be set in the add_content route in routes.py
    file_path: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)
    file_size: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # To be handled in add_content route
    estimated_reading_time: so.Mapped[int] = sa.Column(sa.Integer, nullable=True)  # In minutes, to be handled later
    bookmark_count: so.Mapped[int] = sa.Column(sa.Integer, default=0)  # To be handled in add_content route or related route
    related_content: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps([]))  # To be handled in add_content route
    related_api_links: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps({}))  # To be handled in add_content route
    accessibility_features: so.Mapped[str] = sa.Column(sa.Text, default=json.dumps([]))  # Multiple features, handled in add_content route

    def __repr__(self) -> str:
        return f'<Content {self.title}>'

# 3. Reference Model
class Reference(Base):
    __tablename__ = 'references'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id',ondelete='CASCADE', onupdate='CASCADE'),nullable=False)
    title: so.Mapped[str] = sa.Column(sa.String(255), nullable=False)
    category: so.Mapped[str] = sa.Column(sa.Enum(CategoryNames, name='category_name'), index=True, nullable=False)  # Admin must select from the categories.
    module: so.Mapped[str] = sa.Column(sa.Enum(ModuleNames, name="module_name"), index=True, nullable=False)  # Admin must select from the modules.
    file: so.Mapped[str] = sa.Column(sa.String(255), index=True, nullable=True)
    file_path: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)
    url: so.Mapped[Optional[str]] = sa.Column(sa.String(2083), nullable=True)
    embed_code: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    description: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc))
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationship back to Content
    content = so.relationship('Content', backref='references')

    def __repr__(self) -> str:
        return f"<Reference(id={self.id}, title='{self.title}', content_id={self.content_id})>"

# 4. AdminReportTemplate Model
class AdminReportTemplate(Base):
    __tablename__ = 'admin_report_templates'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    template_name: so.Mapped[str] = sa.Column(sa.String(255), nullable=False, unique=True, index=True)
    body_part: so.Mapped[BodyPartEnum] = sa.Column(sa.Enum(BodyPartEnum, name='body_part_enum'), nullable=False, index=True)
    modality: so.Mapped[ModalityEnum] = sa.Column(sa.Enum(ModalityEnum, name='modality_enum'), nullable=False, index=True)
    file: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Path to the uploaded file
    file_path: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Physical location on disk
    tags: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Comma-separated or JSON format
    category: so.Mapped[str] = sa.Column(
        sa.String, 
        nullable=False, 
        index=True, 
        default=CategoryNames.REPORT_TEMPLATE  # Default category
    )
    module: so.Mapped[Optional[ModuleNames]] = sa.Column(
        sa.Enum(ModuleNames, name='module_name'), 
        nullable=True, 
        index=True
    )
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<AdminReportTemplate(id={self.id}, template_name='{self.template_name}')>"

# ----------------------------------------------------------------
# Models for User Data and Preferences:

# 5. UserData Model: captures user interactions with the contents
class UserData(Base):
    __tablename__ = 'user_data'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    interaction_type: so.Mapped[str] = sa.Column(sa.Enum('viewed', 'bookmarked', 'recommended','registered','logged_in','loged_out','updated_profile_pic',"updated_username",'updated_email','updated_report_templates','updated_category_module_preferences','updated_contents','added_feedback', name='interaction_types'), nullable=False, default='viewed')
    last_interaction: so.Mapped[datetime] = sa.Column(sa.DateTime, nullable=False, default=datetime.now(timezone.utc))
    feedback: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    content_rating: so.Mapped[Optional[int]] = sa.Column(sa.Integer, nullable=True)
    time_spent: so.Mapped[int] = sa.Column(sa.Integer, nullable=False)
    last_login: so.Mapped[Optional[datetime]] = sa.Column(sa.DateTime, nullable=True)

    # Relationships
    user = so.relationship('User', backref=so.backref('user_data', lazy='dynamic', cascade="all, delete-orphan"))
    content = so.relationship('Content', backref=so.backref('user_data', lazy='dynamic', cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<UserData(id={self.id}, user_id={self.user_id}, content_id={self.content_id})>"

# 6. UserContentState Model: Saves user content state for future sessions
class UserContentState(Base):
    __tablename__ = 'user_content_states'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id',ondelete='CASCADE', onupdate='CASCADE'))
    content_id = sa.Column(sa.Integer, sa.ForeignKey('contents.id',ondelete='CASCADE', onupdate='CASCADE'))
    modified_file_path = sa.Column(sa.String(255), nullable=True)
    annotations = sa.Column(sa.Text, nullable=True)  # JSON or text format of annotations
    created_at = sa.Column(sa.DateTime, default=datetime.now(timezone.utc))
    updated_at = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    user = so.relationship('User', backref=so.backref('user_content_states', lazy='dynamic', cascade="all, delete-orphan"))
    content = so.relationship('Content', backref=so.backref('user_content_states', lazy='dynamic', cascade="all, delete-orphan"))

# 7. UserReportTemplate Model
class UserReportTemplate(Base):
    __tablename__ = 'user_report_templates'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    body_part: so.Mapped[BodyPartEnum] = sa.Column(sa.Enum(BodyPartEnum, name='body_part_enum'), nullable=False, index=True)
    modality: so.Mapped[ModalityEnum] = sa.Column(sa.Enum(ModalityEnum, name='modality_enum'), nullable=False, index=True)
    template_name: so.Mapped[str] = sa.Column(sa.String(255), nullable=False, unique=True, index=True)
    tags: so.Mapped[str] = sa.Column(sa.Text, nullable=True)  # Store tags as comma-separated or JSON format
    is_public: so.Mapped[bool] = sa.Column(sa.Boolean, default=False, nullable=False, index=True)

    # Foreign keys and relationships
    user_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('users.id',ondelete='CASCADE', onupdate='CASCADE'), nullable=False, index=True)
    user: so.Mapped['User'] = so.relationship('User', backref='report_templates')

    # Enum references to match category and module columns in Content model
    category: so.Mapped[CategoryNames] = sa.Column(sa.Enum(CategoryNames, name='category_name'), nullable=True, index=True)
    module: so.Mapped[ModuleNames] = sa.Column(sa.Enum(ModuleNames, name='module_name'), nullable=True, index=True)

    # Template content and file upload
    template_text: so.Mapped[str] = sa.Column(sa.Text, nullable=True)  # For storing copy-paste text of the template
    file: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Path to the uploaded file (docx, txt only)
    file_path: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Path where the file is stored on disk

    # Timestamp columns
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, template_name='{self.template_name}', is_public={self.is_public})>"

# 8. UserProfile Model: stores user preferences and profile information
class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('users.id',ondelete='CASCADE', onupdate='CASCADE'), nullable=False, unique=True, index=True)
    profile_pic: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)  # Path to profile picture
    profile_pic_path: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)  # Path to profile picture for management
    preferred_categories: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Comma-separated or JSON format
    preferred_modules: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Comma-separated or JSON format
    report_templates: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # JSON list of template references
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to User
    user: so.Mapped['User'] = so.relationship('User', backref=so.backref('profile', uselist=False, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"

# 9. UserFeedback Model: stores user feedbacks
# ----------------------------------------------
class UserFeedback(Base):
    __tablename__ = 'user_feedbacks'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('users.id',ondelete='CASCADE', onupdate='CASCADE'), nullable=False)  # References the 'users' table
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id',ondelete='CASCADE', onupdate='CASCADE'), nullable=False)  # References the 'contents' table
    feedback: so.Mapped[str] = sa.Column(sa.Text, nullable=False)
    is_public: so.Mapped[bool] = sa.Column(sa.Boolean, default=False, nullable=False)
    user_display_name: so.Mapped[Optional[str]] = sa.Column(sa.String(100), nullable=True)

    # Relationships
    user = so.relationship('User', backref='feedbacks')  # The 'User' class will have an attribute 'feedbacks' for accessing related UserFeedback records
    content = so.relationship('Content', backref='feedbacks')  # The 'Content' class will have an attribute 'feedbacks' for accessing related UserFeedback records

    def __repr__(self) -> str:
        return f"<UserFeedback(id={self.id}, user_display_name='{self.user_display_name}', feedback='{self.feedback[:20]}...')>"

#----------------------------------------------------------------
# Define event listeners
@sa.event.listens_for(Content, 'before_insert')
@sa.event.listens_for(Content, 'before_update')
def update_contents_table(mapper, connection, target):
    """Listener to populate default values before inserting or updating."""
    # Populate Description if not provided
    if not target.description:
        target.description = f"Title: This content belongs to {target.category} and the module name is {target.module}"
    
    # Update version number
    try:
        # Convert to float if it's not already a float
        target.version = float(target.version) + 0.1
    except (ValueError, TypeError):
        # Initialize version as float
        target.version = 1.0