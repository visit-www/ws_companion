import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from typing import Optional
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from enum import Enum as PyEnum
from datetime import datetime, timezone, date
import json
import uuid  # Import the UUID library
import sqlalchemy.orm as so
from typing import Type
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

db = SQLAlchemy()  # Needed for Flask-SQLAlchemy integration
# Initialize the registry and Base class using SQLAlchemy ORM
app_registry: so.registry = so.registry()
Base: Type[so.DeclarativeMeta] = app_registry.generate_base()

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

    id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    username: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False, index=True)
    password: so.Mapped[str] = sa.Column(sa.String(250), nullable=False)
    email: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False, index=True)
    is_paid: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    is_admin: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    status: so.Mapped[str] = sa.Column(sa.String(50), default='active', nullable=False)  # Account status
    created_at: so.Mapped[datetime] = sa.Column(
        sa.DateTime, 
        default=lambda: datetime.now(timezone.utc),  # Correctly uses current UTC time at record creation
        nullable=False
    )
    totp_secret:so.Mapped[Optional[str]] = sa.Column(sa.String(32), nullable=True)
    recovery_phone: so.Mapped[Optional[str]] = sa.Column(sa.String(20), unique=True, nullable=True)  # Updated to Optional
    recovery_email: so.Mapped[Optional[str]] = sa.Column(sa.String(150), unique=True, nullable=True)  # Updated to Optional
    work_sessions: so.Mapped[list["WorkSession"]] = so.relationship("WorkSession", back_populates="user", cascade="all, delete-orphan")
    cpd_logs: so.Mapped[list["CPDLog"]] = so.relationship( "CPDLog", back_populates="user", cascade="all, delete-orphan")
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

# 2. Content Model
class Content(Base):
    __tablename__ = "contents"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, index=True,nullable=False)
    title: so.Mapped[str] = sa.Column(sa.String(565), index=True, nullable=False,default='Imagine')
    category: so.Mapped[str] = sa.Column(sa.Enum(CategoryNames, name='category_name'), index=True, nullable=False, default="music")  # Admin must select from the categories.
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
    description: so.Mapped[str] = sa.Column(sa.Text, nullable=True,default="Welcome to my world of Love and Truth")
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

    id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=True)
    title: so.Mapped[str] = sa.Column(sa.String(255), nullable=False)
    category: so.Mapped[str] = sa.Column(sa.Enum(CategoryNames, name='category_name'), index=True, nullable=False)  # Admin must select from the categories.
    module: so.Mapped[str] = sa.Column(sa.Enum(ModuleNames, name="module_name"), index=True, nullable=False)  # Admin must select from the modules.
    file: so.Mapped[str] = sa.Column(sa.String(255), index=True, nullable=True)
    filepath: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)
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
    template_name: so.Mapped[str] = sa.Column(sa.String(255), nullable=True, unique=True, index=True)
    body_part: so.Mapped[BodyPartEnum] = sa.Column(sa.Enum(BodyPartEnum, name='body_part_enum'), nullable=True, index=True)
    modality: so.Mapped[ModalityEnum] = sa.Column(sa.Enum(ModalityEnum, name='modality_enum'), nullable=True, index=True)
    file: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Path to the uploaded file
    filepath: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Physical location on disk
    tags: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Comma-separated or JSON format
    category: so.Mapped[str] = sa.Column(
        sa.String, 
        nullable=True, 
        index=True, 
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

    id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=True)
    interaction_type: so.Mapped[str] = sa.Column(sa.Enum('viewed', 'bookmarked', 'recommended','registered','logged_in','logged_out','updated_profile_pic',"updated_username",'updated_email','updated_report_templates','updated_category_module_preferences','updated_contents','added_feedback', name='interaction_types'), nullable=False, default='viewed')
    last_interaction: so.Mapped[datetime] = sa.Column(sa.DateTime, nullable=False, default=datetime.now(timezone.utc))
    feedback: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    content_rating: so.Mapped[Optional[int]] = sa.Column(sa.Integer, nullable=True)
    time_spent: so.Mapped[int] = sa.Column(sa.Integer, nullable=False)
    last_login: so.Mapped[Optional[datetime]] = sa.Column(sa.DateTime, nullable=True)
    current_login: so.Mapped[Optional[datetime]] = sa.Column(sa.DateTime, nullable=True)
    session_start_time: so.Mapped[Optional[datetime]] = sa.Column(sa.DateTime, nullable=True)
    login_count: so.Mapped[Optional[int]] = sa.Column(sa.Integer, nullable=True, default=0)
    

    # Relationships
    user = so.relationship('User', backref=so.backref('user_data', lazy='dynamic', cascade="all, delete-orphan"), passive_deletes=True)
    content = so.relationship('Content', backref=so.backref('user_data'))

    def __repr__(self) -> str:
        return f"<UserData(id={self.id}, user_id={self.user_id}, content_id={self.content_id})>"

# 6. UserContentState Model: Saves user content state for future sessions
class UserContentState(Base):
    __tablename__ = 'user_content_states'

    id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=True)
    user_id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    modified_filepath = sa.Column(sa.String(255), nullable=True)
    annotations = sa.Column(sa.Text, nullable=True)  # JSON or text format of annotations
    created_at = sa.Column(sa.DateTime, default=datetime.now(timezone.utc))
    updated_at = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    user = so.relationship('User', backref=so.backref('user_content_states', lazy='dynamic', cascade="all, delete-orphan"), passive_deletes=True)
    content = so.relationship('Content', backref=so.backref('user_content_states'))

# 7. UserReportTemplate Model
class UserReportTemplate(Base):
    __tablename__ = 'user_report_templates'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True,nullable=False)
    
    body_part: so.Mapped[BodyPartEnum] = sa.Column(sa.Enum(BodyPartEnum, name='body_part_enum'), nullable=True, index=True)
    modality: so.Mapped[ModalityEnum] = sa.Column(sa.Enum(ModalityEnum, name='modality_enum'), nullable=True, index=True)
    template_name: so.Mapped[str] = sa.Column(sa.String(255), nullable=True, unique=True, index=True)
    tags: so.Mapped[str] = sa.Column(sa.Text, nullable=True)  # Store tags as comma-separated or JSON format
    is_public: so.Mapped[bool] = sa.Column(sa.Boolean, default=False, nullable=True, index=True)
    created_at = sa.Column(sa.DateTime, default=datetime.now(timezone.utc))
    updated_at = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Foreign keys and relationships
    user_id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, index=True)

    user: so.Mapped['User'] = so.relationship('User', backref=so.backref('report_templates',lazy='dynamic', cascade="all, delete-orphan"), passive_deletes=True)

    # Enum references to match category and module columns in Content model
    category: so.Mapped[CategoryNames] = sa.Column(sa.Enum(CategoryNames, name='category_name'), nullable=True, index=True)
    module: so.Mapped[ModuleNames] = sa.Column(sa.Enum(ModuleNames, name='module_name'), nullable=True, index=True)

    # Template content and file upload
    template_text: so.Mapped[str] = sa.Column(sa.Text, nullable=True)  # For storing copy-paste text of the template
    file: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Path to the uploaded file (docx, txt only)
    filepath: so.Mapped[str] = sa.Column(sa.String(255), nullable=True)  # Path where the file is stored on disk

    # Timestamp columns
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, template_name='{self.template_name}', is_public={self.is_public})>"

# 8. UserProfile Model: stores user preferences and profile information
class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    profile_pic: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)  # Path to profile picture
    profile_pic_path: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)  # Path to profile picture for management
    preferred_categories: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Comma-separated or JSON format
    preferred_modules: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)  # Comma-separated or JSON format
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False)

    # Relationship to User
    user: so.Mapped['User'] = so.relationship('User', backref=so.backref('profile', uselist=False, cascade="all, delete-orphan"), passive_deletes=True)

    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"

# 9. UserFeedback Model: stores user feedbacks
# ----------------------------------------------
from config import ANONYMOUS_USER_ID
class UserFeedback(Base):
    __tablename__ = 'user_feedbacks'
    id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True),sa.ForeignKey('users.id', ondelete='SET DEFAULT', onupdate='CASCADE'),nullable=False,
    server_default=str(ANONYMOUS_USER_ID)
    )

    content_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey('contents.id', onupdate='CASCADE'), nullable=True)  # References the 'users' table
    feedback: so.Mapped[str] = sa.Column(sa.Text, nullable=True)
    is_public: so.Mapped[bool] = sa.Column(sa.Boolean, default=False, nullable=True)
    user_display_name: so.Mapped[Optional[str]] = sa.Column(sa.String(100), nullable=True)
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc),  onupdate=datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = so.relationship(
        'User',
        backref=so.backref('feedbacks', passive_deletes='all'),
        passive_deletes='all'
    ) # The 'User' class will have an attribute 'feedbacks' for accessing related UserFeedback records
    content = so.relationship(
        'Content', 
        backref=so.backref('feedbacks', passive_deletes='all'),
        passive_deletes='all')  # The 'Content' class will have an attribute 'feedbacks' for accessing related UserFeedback records

    def __repr__(self) -> str:
        return f"<UserFeedback(id={self.id}, user_display_name='{self.user_display_name}', feedback='{self.feedback[:20]}...')>"

class WorkSession(Base):
    __tablename__ = 'work_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    num_cases_reported = Column(Integer, nullable=True)
    session_type = Column(String(50), nullable=True)  # e.g., 'remote', 'on-call', 'clinic'
    modalities_handled = Column(String(200), nullable=True)  # e.g., 'CT, MRI, XR'

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="work_sessions")

    def duration(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 3600
        return None
    
class CPDActivityType(Base):
    __tablename__ = "cpd_activity_types"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False)  # e.g., "Distance and online learning"
    default_credits: so.Mapped[str] = sa.Column(sa.String(50), nullable=False)  # e.g., "1/hour", "4", etc.

    def __repr__(self):
        return f"<CPDActivityType(name={self.name}, default_credits={self.default_credits})>"
    
class CPDLog(Base):
    __tablename__ = 'cpd_logs'

    id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False)
    activity_type_id: so.Mapped[int] = sa.Column(sa.Integer, sa.ForeignKey("cpd_activity_types.id"), nullable=False)

    # Dates and Time Periods
    start_date: so.Mapped[datetime] = sa.Column(sa.DateTime, nullable=False)
    end_date: so.Mapped[datetime] = sa.Column(sa.DateTime, nullable=False)
    cpd_year_start: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)  # e.g., "Apr 2024"
    cpd_year_end: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)
    appraisal_cycle_start: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)
    appraisal_cycle_end: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)

    # CPD Activity Info
    title: so.Mapped[str] = sa.Column(sa.String(255), nullable=False)
    description: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    reflection: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    has_reflection: so.Mapped[bool] = sa.Column(sa.Boolean, default=False)

    # CPD Credits
    cpd_points_guideline: so.Mapped[Optional[str]] = sa.Column(sa.String(50), nullable=True)  # e.g., from activity type
    cpd_points_claimed: so.Mapped[Optional[float]] = sa.Column(sa.Float, nullable=True)

    # Certificates
    certificate_filename: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)
    certificate_filepath: so.Mapped[Optional[str]] = sa.Column(sa.String(255), nullable=True)

    tags: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    notes: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)

    # Metadata
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: so.Mapped['User'] = so.relationship("User", back_populates="cpd_logs")
    activity_type: so.Mapped['CPDActivityType'] = so.relationship("CPDActivityType")

    def __repr__(self):
        return f"<CPDLog(title={self.title}, claimed={self.cpd_points_claimed})>"

class UserCPDState(Base):
    __tablename__ = 'user_cpd_states'

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id: so.Mapped[uuid.UUID] = sa.Column(sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    appraisal_cycle_start: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)  # e.g. "May 2022"
    appraisal_cycle_end: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)    # e.g. "May 2027"
    current_cpd_year_start: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)  # e.g. "May 2024"
    current_cpd_year_end: so.Mapped[str] = sa.Column(sa.String(20), nullable=False)    # e.g. "May 2025"
    
    appraisal_cycle_start_date: so.Mapped[date] = sa.Column(sa.Date, nullable=True)
    appraisal_cycle_end_date: so.Mapped[date] = sa.Column(sa.Date, nullable=True)
    current_cpd_year_start_date: so.Mapped[date] = sa.Column(sa.Date, nullable=True)
    current_cpd_year_end_date: so.Mapped[date] = sa.Column(sa.Date, nullable=True)
    
    created_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc))
    updated_at: so.Mapped[datetime] = sa.Column(sa.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    user: so.Mapped['User'] = sa.orm.relationship("User", backref=so.backref("cpd_state", uselist=False, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<UserCPDState(user_id={self.user_id}, current_cpd_year={self.current_cpd_year_start}-{self.current_cpd_year_end})>"

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
        
