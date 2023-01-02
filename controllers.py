from flask import redirect, render_template, request
from flask_login import current_user, login_required
from app import app
from util import *  
from models import *
import base64
from datetime import datetime
    

@app.route("/", methods = ['GET', 'POST'])
@login_required  
def home():
    posts, post_likes,post_comments, isLiked, user = getPosts(current_user.username, forHomePage=True)
    flag = False
    results=None
    invalid = False
    q = None
    if request.method == 'POST':
        q = request.form['q']
        
        if q:
            for c in q:
                if not c.isalpha() and not c.isdigit() and not c == '_':
                    invalid = True
                    
            query = "%" + q + "%"
            results = User.query.filter(User.username.like(query)).all()
            for r in results:
                if r.profile_picture and type(r.profile_picture)!=type('somestring'):
                    r.profile_picture = base64.b64encode(r.profile_picture).decode("utf-8")
            flag = True
    
    return render_template('homepage.html',  posts_comments = post_comments,posts = posts, posts_likes = post_likes, isLikedByUser = isLiked, user = user, results = results, flag = flag, q=q) 
          

@app.route('/<username>', methods = ['GET', 'POST'])
def profile(username):
    if request.method == 'GET':
        posts, post_likes, post_comments, isLiked = getPosts(username)
        user = getUser(username)
        followers = getFollowers(username)
        following = getFollowing(username)
        if username == current_user.username:
            return render_template('profile_page.html',  posts_comments = post_comments,isLikedByUser = isLiked, posts_likes = post_likes, posts = posts, user=user, flag = True, followers = followers, following = following)
        isFollower = followedByUser(current_user_username= current_user.username, username=username)
        return render_template('profile_page.html', posts_comments = post_comments, posts = posts,user=user, flag = False, following_flag = isFollower, followers = followers, following = following, isLikedByUser = isLiked, posts_likes = post_likes,)
    
    
    elif request.method == 'POST' and current_user.username == username:
        if request.files['profile_picture']:
            profile_picture = request.files['profile_picture'].read()
            current_user.profile_picture = profile_picture
            db.session.commit()
        else:
            profile_picture = open('static/placeholder.png', 'rb').read()
            current_user.profile_picture = profile_picture
            db.session.commit()
       
        return redirect('/' + username)


@app.route('/add_post', methods = ['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'GET':
        return render_template('add_post.html')
    if request.method == 'POST':
        username= current_user.username
        title = request.form['title']
        description = request.form['description']
        print(title, description)
        image_url = request.files['file'].read()
       
        new_post = Post(title = title, description = description, image_url = image_url, time_created = datetime.now())
        db.session.add(new_post)
        db.session.commit()
        post_id = Post.query.filter_by(title = title).order_by(Post.time_created).all()[-1].id
        new_upload = UploadedBy(username = username, post_id = post_id)
        db.session.add(new_upload)
        db.session.commit()
        return redirect('/' + current_user.username)
    
@app.route('/edit_post/<int:id>',  methods = ['GET', 'POST'])
@login_required
def edit_post(id : int):
    post = Post.query.filter_by(id = id).first()
    if request.method == 'GET':
        return render_template('edit_post.html', post = post)
    if request.method == 'POST':
        post.title = request.form['title']
        post.description = request.form['description']
        post.time_updated = datetime.now()
        if request.files['image_url']:
            post.image_url = request.files['image_url'].read()
        
        db.session.commit()
        return redirect('/profile/' + current_user.username)
        
        
@app.route('/delete_post/<int:id>',  methods = ['GET'])
@login_required
def delete_post(id:int):
    post = Post.query.filter_by(id = id).first()
    uploaded_by_post = UploadedBy.query.filter_by(post_id = id).all()
    for p in uploaded_by_post:
        db.session.delete(p)
    db.session.commit()
    db.session.delete(post)
    db.session.commit()
    return redirect('/profile/' + current_user.username)

@app.route('/post/<post_id>')
def view_post(post_id):
    post =  Post.query.filter_by(id = post_id).first()
    username = UploadedBy.query.filter_by(post_id = post_id).first()
    user= getUser(username.username)
   
    if post.image_url:
        post.image_url = base64.b64encode(post.image_url).decode("utf-8")
    post.time_created = pretty_date(post.time_created)
    comments = getComments(post.id)
    commenter = {}
    for comment in comments:
        commenter[comment] = getUser(comment.username)

    liked_by = getLikes(post.id)
    isLiked = isLikedByUser(post.id, current_user.username)
    return render_template('post.html', post = post, user = user, liked_by = liked_by, comments = comments, isLikedByUser = isLiked, commenter = commenter)


@app.route('/follow/<username>')
@login_required
def follow(username):
    follow_req = Followers(username = username, followed_by = current_user.username)
    db.session.add(follow_req)
    db.session.commit()
    return redirect('/'+username)

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    follow_req = Followers.query.filter_by(username = username, followed_by = current_user.username).first()
    db.session.delete(follow_req)
    db.session.commit()
    return redirect('/'+username)

           
@app.route('/like/<post_id>')
@login_required
def like(post_id):
        isLiked = isLikedByUser(post_id=post_id, username=current_user.username)
        if not isLiked:
            like = Likes(username = current_user.username, post_id = post_id)
            db.session.add(like)
            db.session.commit()
        return redirect(redirect_url())
    
@app.route('/unlike/<post_id>')
@login_required
def unlike(post_id):
    isLiked = isLikedByUser(post_id=post_id, username=current_user.username)
    if isLiked:
        db.session.delete(Likes.query.filter_by(post_id = post_id, username = current_user.username).first())
        db.session.commit()
    return redirect(redirect_url())

@app.route('/comment/<post_id>', methods = ['GET', 'POST'])
@login_required
def comment(post_id):
    if request.method == 'POST':
        comment_text = request.form['comment']
        username = current_user.username
        new_comment = Comments(comment = comment_text, username = username, post_id = post_id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(redirect_url())
    

