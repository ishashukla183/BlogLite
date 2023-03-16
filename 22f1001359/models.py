from datetime import datetime
from database import db
from sqlalchemy import func
from flask_security import UserMixin, RoleMixin
from flask_security.forms import LoginForm, RegisterForm, ValidationError
from wtforms import StringField
from wtforms.validators import InputRequired, DataRequired

class ExtendedLoginForm(LoginForm):
    email = StringField('Username', [InputRequired()])

class ExtendedRegisterForm(RegisterForm):
    username = StringField('Username', [InputRequired()])
    first_name = StringField('First Name', [DataRequired()])
    last_name = StringField('Last Name', [DataRequired()])
    def validate_first_name(form, field):
        for c in field.data:
            if not c.isalpha():
                raise ValidationError('Invalid input for name field')
    def validate_last_name(form, field):
        for c in field.data:
            if not c.isalpha():
                raise ValidationError('Invalid input for name field')
    def validate_username(form, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Username not available. Please try a different one')
        
            

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))  

class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String, unique=True)
    description = db.Column(db.String(255))
    
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    username = db.Column(db.String(255), unique=True, index=True)
    password = db.Column(db.String(20), nullable = False)
    first_name = db.Column(db.String(20), nullable = False)
    last_name = db.Column(db.String(20), nullable = True)
    profile_picture = db.Column(db.LargeBinary, nullable = True)
    active = db.Column(db.Boolean())
    roles = db.relationship('Role', secondary=roles_users,backref=db.backref('users', lazy='dynamic'))
    


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, autoincrement = True, primary_key=True)
    title = db.Column(db.String(50), nullable = False)
    description = db.Column(db.String(300), nullable = False)
    time_created = db.Column(db.DateTime, server_default=func.now())
    time_updated = db.Column(db.DateTime, onupdate=datetime.now, nullable = True)
    
class PostImages(db.Model):
    __tablename__ = 'post_images'
    id = db.Column(db.Integer, autoincrement = True, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), primary_key = True)
    image_url = db.Column(db.LargeBinary, nullable = False) 
      
class UploadedBy(db.Model):
    __tablename__ = 'uploaded_by'
    username = db.Column(db.String, db.ForeignKey("user.username"),primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), primary_key = True)
    
class Likes(db.Model):
    __tablename__ = 'likes'
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), primary_key = True)
    username = db.Column(db.String, db.ForeignKey("user.username"),primary_key=True)

class Comments(db.Model):
    __tablename__ = 'comments'
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    username = db.Column(db.String, db.ForeignKey("user.username"),nullable=False)
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    comment = db.Column(db.String(100), nullable = False)
    
class Followers(db.Model):
    __tablename__ = 'followers'
    username = db.Column(db.String, db.ForeignKey("user.username"),primary_key=True)
    followed_by =  db.Column(db.String, db.ForeignKey("user.username"),primary_key=True)
    
