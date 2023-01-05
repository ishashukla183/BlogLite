import base64
from flask import redirect, request, url_for
from flask_login import current_user
from sqlalchemy import select
from models import Comments, Followers, Likes, Post, PostImages, UploadedBy, User
from database import db

def redirect_url(default='home'):
    return request.args.get('next') or \
           request.referrer or \
           redirect(url_for(default))
           
def getFollowers(username):
    followers = db.session.execute(select(User).where(User.username.in_(select(Followers.followed_by).where(Followers.username == username)))).scalars().all()
    for follower in followers:
        if follower.profile_picture:
            if(type(follower.profile_picture) != type('somestring')): 
            
               follower.profile_picture = base64.b64encode(follower.profile_picture).decode("utf-8")
    return followers

def getFollowing(username):
    following = db.session.execute(select(User).where(User.username.in_(select(Followers.username).where(Followers.followed_by == username)))).scalars().all()
    for follower in following:
        if follower.profile_picture:
            if(type(follower.profile_picture) != type('somestring')): 
            
               follower.profile_picture = base64.b64encode(follower.profile_picture).decode("utf-8")
    return following

def getComments(post_id):
    comments = Comments.query.filter_by(post_id = post_id).all()
    return comments

def getLikes(post_id):
    liked_by = db.session.execute(select(User).where(User.username.in_(select(Likes.username).where(Likes.post_id == post_id)))).scalars().all()
    for user in liked_by:
        if user.profile_picture:
            if(type(user.profile_picture) != type('somestring')): 
            
               user.profile_picture = base64.b64encode(user.profile_picture).decode("utf-8")
    return liked_by

def getPostImages(post_id):
    images = PostImages.query.filter_by(post_id = post_id).all()
    post_images = []
    for image in images:
        if type(image.image_url)!= type('somestring'):
            post_images.append(base64.b64encode(image.image_url).decode("utf-8"))
    return post_images
        
def isLikedByUser(post_id, username):
    if Likes.query.filter_by(post_id = post_id, username = username).first():
        return True
    return False

def followedByUser(username, current_user_username):
    if Followers.query.filter_by(username = username, followed_by = current_user_username).first():
        return True
    return False

def getUser(username):
    if type(username) == type(['listelem']):
        username = username[0]
    user=User.query.filter_by(username=username).first()
    if user and user.profile_picture and type(user.profile_picture)!=type('somestring'):
        user.profile_picture = base64.b64encode(user.profile_picture).decode("utf-8")
    return user

def getUserFeed(username, forHomePage = False):
    post_likes = {}
    post_comments = {}
    isLiked = {}
    user = {}
    post_images = {}
    if forHomePage:
        posts = db.session.execute(select(Post).where(Post.id.in_(select(UploadedBy.post_id).where(UploadedBy.username.in_(select(Followers.username).where(Followers.followed_by == username))))).order_by(Post.time_created.desc())).scalars().all()
    else:
        posts = db.session.execute(select(Post).where(Post.id.in_(select(UploadedBy.post_id).where(UploadedBy.username == username))).order_by(Post.time_created.desc())).scalars().all()
   
    for post in posts:
        if forHomePage:
            user[post.id] = getUser(db.session.execute(select(UploadedBy.username).where(UploadedBy.post_id == post.id)).scalars().all())
        post_likes[post.id] = getLikes(post_id = post.id)
        post_comments[post.id] = getComments(post_id = post.id)
        post_images[post.id] = getPostImages(post_id = post.id)
        isLiked[post.id] = isLikedByUser(post_id = post.id, username = current_user.username)
        
        post.time_created = pretty_date(post.time_created)
        if post.time_updated:
            post.time_updated = pretty_date(post.time_updated)
    if forHomePage:
        return posts, post_likes, post_comments, post_images, isLiked, user
    return posts, post_likes, post_comments, post_images, isLiked


    
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = 0
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + "s"
        if second_diff < 120:
            return "1m"
        if second_diff < 3600:
            return str(second_diff // 60) + "m"
        if second_diff < 7200:
            return "1h"
        if second_diff < 86400:
            return str(second_diff // 3600) + "h"
    if day_diff == 1:
        return "1d"
    if day_diff < 7:
        return str(day_diff) + "d"
    if day_diff < 31:
        return str(day_diff // 7) + "w"
    if day_diff < 365:
        return str(day_diff // 30) + "m"
    return str(day_diff // 365) + "y"
