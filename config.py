import os
basedir=os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY=os.getenv('SECRET_KEY') or '7ebfffbf75e406f1b63739a0c5e487496be74113d2fd3a672fc45b4a120f571b'
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'radiology.db')
    SQLALCHEMY_TRACK_MODIFICATIONS=False
