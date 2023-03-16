from werkzeug.exceptions import HTTPException

import json
from flask import g, make_response
from flask_restful import Resource, Api, fields, marshal_with, reqparse
from sqlalchemy import select
from app import app

from models import *
from util import getFollowers, getFollowing, getPostImages


"""
Global Variables
"""

create_user_parser = reqparse.RequestParser()
create_user_parser.add_argument('username')
create_user_parser.add_argument('first_name')
create_user_parser.add_argument('last_name')
create_user_parser.add_argument('password')

update_user_parser = reqparse.RequestParser()
update_user_parser.add_argument('first_name')
update_user_parser.add_argument('last_name')
update_user_parser.add_argument('username')

create_post_parser = reqparse.RequestParser()
create_post_parser.add_argument('title')
create_post_parser.add_argument('description')

update_post_parser = reqparse.RequestParser()
update_post_parser.add_argument('title')
update_post_parser.add_argument('description')



post_output = {
    'title' : fields.String, 
    'description' : fields.String,
}

api = Api(app)

class NotFoundError(HTTPException):
    def __init__(self, status_code, error_message=''):
        self.response = make_response(error_message, status_code)

class BusinessValidationError(HTTPException):
    def __init__(self, error_code, error_message,status_code = 400):
        message = {'error_code' : error_code, 'error_message' : error_message}
        self.response = make_response(json.dumps(message), status_code)
        
"""
API resources
"""

class UserAPI(Resource):
    
    def get(self, username):
        print('inside get')
        user = User.query.filter_by(username = username).first()

        if user is not None:
            followers = len(getFollowers(username))
            following = len(getFollowing(username))
            post_count = len(db.session.execute(select(Post).where(Post.id.in_(select(UploadedBy.post_id).where(UploadedBy.username == username)))).scalars().all())
            return {
                'username' : user.username,
                'first_name' : user.first_name,
                'last_name' : user.last_name,
                'followers' : followers, 
                'following' : following,
                'post_count' : post_count,
            }, 200
        else:
            raise NotFoundError(status_code = 404, error_message='User not found')
    
    
        
        
    def put(self, username):
        user = User.query.filter_by(username = username).first()
        if user is None:
            raise NotFoundError(status_code = 404, error_message='User not found')
        args = update_user_parser.parse_args()
        first_name = args.get('first_name', None)
        last_name = args.get('last_name', None)
        new_username = args.get('username', None)
       
        if not new_username:
            raise BusinessValidationError(error_code = 'USER004', status_code = 400, error_message = 'Username is required')
        if not first_name:
            raise BusinessValidationError(error_code = 'USER005', status_code = 400, error_message = 'First name is required')
        
        for c in first_name:
            if not c.isalpha():
                raise BusinessValidationError(error_code = 'USER002', status_code = 400, error_message = 'Invalid first name')
        for c in last_name:
            if not c.isalpha():
                raise BusinessValidationError(error_code = 'USER002', status_code = 400, error_message = 'Invalid first name')
        for c in new_username:
            if not c.isalpha() and not c.isdigit() and not c == '_':
                raise BusinessValidationError(error_code = 'USER003', status_code = 400, error_message = 'Special characters not allowed.')
        
        if username!=new_username:
            duplicate_user = User.query.filter_by(username = new_username).first()
            if duplicate_user:
                raise BusinessValidationError(error_code = 'USER001', status_code = 400, error_message = 'Username already exists') 
   
        
        
        user.first_name = first_name
        user.last_name = last_name
        if username!=new_username:
            user.username = new_username
            UploadedBy.query.filter_by(username = username).update(dict(username = new_username))
            Likes.query.filter_by(username = username).update(dict(username = new_username))
            Comments.query.filter_by(username = username).update(dict(username = new_username))
            Followers.query.filter_by(username = username).update(dict(username = new_username))
            Followers.query.filter_by(followed_by = username).update(dict(followed_by = new_username))
        db.session.commit()  
        return {
            'username' : user.username,
            'first_name' : user.first_name,
            'last_name' : user.last_name
        }, 200  

    def delete(self, username):
        user = User.query.filter_by(username = username).first()
        print(user)
        if not user:
            raise NotFoundError(status_code=404)
        
        Followers.query.filter_by(username = username).delete()
        Followers.query.filter_by(followed_by = username).delete()
        Likes.query.filter_by(username = username).delete()
        Comments.query.filter_by(username = username).delete()
        posts = db.session.execute(select(Post).where(Post.id.in_(select(UploadedBy.post_id).where(UploadedBy.username == username)))).scalars().all()
        for post in posts:
            Likes.query.filter_by(post_id = post.id).delete()
            Comments.query.filter_by(post_id = post.id).delete()
            UploadedBy.query.filter_by(post_id = post.id).delete()
            PostImages.query.filter_by(post_id = post.id).delete()
            db.session.delete(post)
            
        User.query.filter_by(username = username).delete()
        db.session.commit()
        raise NotFoundError(status_code=200)
    
api.add_resource(UserAPI, '/api/user/<username>')
    
    
class PostAPI(Resource):
    def get(self, username):
        user = User.query.filter_by(username = username).first()
        if not user:
            raise BusinessValidationError(status_code = 400, error_code='POST003', error_message='No such user exists')
        
        posts = db.session.execute(select(Post).where(Post.id.in_(select(UploadedBy.post_id).where(UploadedBy.username == username)))).scalars().all()
        if not posts:
            raise NotFoundError(status_code=404)
        posts_output = []
        for post in posts:
            post_output = {
                'title' : post.title, 
                'description' : post.description,
                'files_attached' : len(getPostImages(post_id = post.id)),
                'likes' : len(Likes.query.filter_by(post_id = post.id).all()),
                'comments' : len(Comments.query.filter_by(post_id = post.id).all()),
                'author'   : username
            }
            posts_output.append(post_output)
        return posts_output, 200
            
    @marshal_with(post_output)
    def put(self, username, post_id):
        user = User.query.filter_by(username = username).first()
        if not user:
            raise BusinessValidationError(error_code='POST003', error_message='No such user exists')
        post = Post.query.filter_by(id = post_id).first()
        if not post:
            raise NotFoundError(status_code=404)
        args = update_post_parser.parse_args()
        title = args.get('title')
        description = args.get('description')
        if not title:
            raise BusinessValidationError(status_code = 400,error_code='POST001', error_message='Title is required')
        if not description:
            raise BusinessValidationError(status_code = 400,error_code='POST002', error_message='Description is required')
        post.title = title
        post.description = description
        post.time_updated = datetime.now()
        db.session.commit()
        return post
    
    @marshal_with(post_output)
    def post(self, username):
        user = User.query.filter_by(username = username).first()
        if not user:
            raise BusinessValidationError(error_code='POST003', error_message='No such user exists')
        args = update_post_parser.parse_args()
        title = args.get('title')
        description = args.get('description')
        if not title:
            raise BusinessValidationError(status_code = 400,error_code='POST001', error_message='Title is required')
        if not description:
            raise BusinessValidationError(status_code = 400,error_code='POST002', error_message='Description is required')
        
        post = Post(title = title, description = description, time_created = datetime.now())
        db.session.add(post)
        db.session.commit()
        post = Post.query.filter_by(title = title).order_by(Post.time_created.desc()).first()
        new_upload = UploadedBy(post_id = post.id, username = username)
        db.session.add(new_upload)
        db.session.commit()
        return post, 201
    
    def delete(self, username, post_id):
        user = User.query.filter_by(username = username).first()
        if not user:
            raise BusinessValidationError(status_code = 400, error_code='POST003', error_message='No such user exists')
        upload = UploadedBy.query.filter_by(username = username, post_id = post_id)
        post = Post.query.filter_by(id = post_id).first()
        if not post or not upload:
            raise NotFoundError(status_code=404)
        Likes.query.filter_by(post_id = post_id).delete()
        Comments.query.filter_by(post_id = post_id).delete()
        UploadedBy.query.filter_by(post_id = post_id).delete()
        PostImages.query.filter_by(post_id = post_id).delete()
        db.session.delete(post)
        db.session.commit()
        return 200
        

api.add_resource(PostAPI, '/api/user/<username>/post', '/api/user/<username>/delete/<int:post_id>', '/api/user/<username>/put/<post_id>')


