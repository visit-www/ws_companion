import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from typing import Type, Optional
from werkzeug.security import check_password_hash

from . import Base  # Import the Base from __init__.py

class User(UserMixin, Base):
    __tablename__ = "user"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True)
    username: so.Mapped[str] = sa.Column(sa.String(150), unique=True, nullable=False)
    password: so.Mapped[str] = sa.Column(sa.String(150), nullable=False)
    is_paid: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)
    is_admin: so.Mapped[Optional[bool]] = sa.Column(sa.Boolean, default=False, nullable=True)


    def check_password(self, password):
        """Check if the provided password matches the stored password."""
        return check_password_hash(self.password, password)



    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"

class Guideline(Base):
    __tablename__ = "guideline"

    id: so.Mapped[int] = sa.Column(sa.Integer, primary_key=True)
    title: so.Mapped[str] = sa.Column(sa.String(500), nullable=False)
    file_type: so.Mapped[Optional[str]] = sa.Column(sa.String(10), nullable=True)
    file_path: so.Mapped[Optional[str]] = sa.Column(sa.String(256), nullable=True)

    def __repr__(self) -> str:
        return f"<Guideline(id={self.id}, title='{self.title}')>"