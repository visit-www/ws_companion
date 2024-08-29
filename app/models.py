import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from typing import Optional
from werkzeug.security import check_password_hash
from . import Base  # Import the Base from __init__.py

class User(UserMixin, Base):
    __tablename__ = "user"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True)
    username: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False)
    password: so.Mapped[str] = sa.Column(sa.String(150), nullable=False)
    is_paid: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    is_admin: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    last_updated: so.Mapped[sa.DateTime] = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"

class Guideline(Base):
    __tablename__ = "guideline"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True)
    title: so.Mapped[str] = sa.Column(sa.String(500), nullable=False)
    file_type: so.Mapped[Optional[str]] = sa.Column(sa.String(20), nullable=True)
    file_path: so.Mapped[Optional[str]] = sa.Column(sa.String(256), nullable=True)
    url: so.Mapped[Optional[str]]=sa.Column(sa.String(256), nullable=True)
    embed_code: so.Mapped[Optional[str]] = sa.Column(sa.Text, nullable=True)
    last_updated: so.Mapped[sa.DateTime] = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Guideline(id={self.id}, title='{self.title}')>"

# * Create model for contents tables