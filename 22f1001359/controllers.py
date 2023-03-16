from flask import redirect, render_template, request
from flask_login import current_user, login_required
from flask_security import url_for_security
from app import app
from util import *  
from models import *
import base64
from datetime import datetime
import flask_excel as excel    


"""
User feed
"""

@app.route("/", methods = ['GET', 'POST'])
@login_required  
def home():
    posts, post_likes,post_comments, post_images,isLiked, user = getUserFeed(current_user.username, forHomePage=True)
    flag = False
    results=None
    isFollowing = {}
    q = None
    if request.method == 'POST':
        q = request.form['q']
        isFollowing = {}
        if q:
            query = "%" + q + "%"
            results = User.query.filter(User.username.like(query)).all()
            for r in results:
                if r.profile_picture and type(r.profile_picture)!=type('somestring'):
                    r.profile_picture = base64.b64encode(r.profile_picture).decode("utf-8")
                if r.username != current_user.username:    
                    isFollowing[r.username] = followedByUser(r.username, current_user_username=current_user.username)
                    print(r.username, isFollowing[r.username])
            flag = True
    
    return render_template('homepage.html',  posts_comments = post_comments, post_images = post_images,posts = posts, posts_likes = post_likes, isLikedByUser = isLiked, user = user, results = results, flag = flag, q=q, isFollowing = isFollowing) 
          

"""
CRUD for user
"""


@app.route('/<username>', methods = ['GET'])
@login_required  
def profile(username):
 
    if request.method == 'GET':
        user = getUser(username)
        if user is None:
            return render_template('error_page.html')
        posts, post_likes, post_comments, post_images, isLiked = getUserFeed(username)
        
        followers = getFollowers(username)
        isFollowing = {}
        for follower in followers:
            if follower.username != current_user.username:
                  isFollowing[follower.username] = followedByUser(follower.username, current_user.username)
        following = getFollowing(username)
        for follower in following:
            if follower.username != current_user.username:
                  isFollowing[follower.username] = followedByUser(follower.username, current_user.username)
            
        
        if username == current_user.username:
            return render_template('profile_page.html',  posts_comments = post_comments,isLikedByUser = isLiked, posts_likes = post_likes, post_images = post_images,posts = posts, user=user, flag = True, followers = followers, following = following, isFollowing = isFollowing)
        isFollower = followedByUser(current_user_username= current_user.username, username=username)
        return render_template('profile_page.html', posts_comments = post_comments, post_images = post_images, posts = posts,user=user, flag = False, following_flag = isFollower, followers = followers, following = following, isLikedByUser = isLiked, posts_likes = post_likes, isFollowing = isFollowing)
    
    
        

@app.route('/edit_profile/<username>', methods = ['POST', 'GET'])
@login_required
def edit_profile(username):
    if request.method == 'GET':
        return render_template('edit_profile.html', username = current_user.username, error_message = None)
    elif request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        remove_photo = request.form.get('remove_photo')
        new_username = request.form.get('username')
        if not first_name:
            return render_template('edit_profile.html', username = current_user.username, error_message = 'First name cannot be empty')
        if not new_username:
            return render_template('edit_profile.html', username = current_user.username, error_message = 'Username cannot be empty')
        for c in first_name:
            if not c.isalpha():
                return render_template('edit_profile.html', username = current_user.username, error_message = 'Special characters and numbers not allowed in name field.')
        for c in last_name:
            if not c.isalpha():
                return render_template('edit_profile.html', username = current_user.username, error_message = 'Special characters and numbers not allowed in name field.')
        for c in new_username:
            if not c.isalpha() and not c.isdigit() and not c == '_':
                  return render_template('edit_profile.html', username = current_user.username, error_message = 'Special characters not allowed in username.')
        if username!=new_username:
            duplicate_user = User.query.filter_by(username = new_username).first()
            if duplicate_user:
                return render_template('edit_profile.html', username = current_user.username, error_message = 'Username is already in use. Please choose a different one.')
        
        
        if request.files['profile_picture']:
            profile_picture = request.files['profile_picture'].read()
            current_user.profile_picture = profile_picture
        elif remove_photo:
            current_user.profile_picture = None
        current_user.first_name = first_name
        current_user.last_name = last_name
        if username!=new_username:
            current_user.username = new_username
            UploadedBy.query.filter_by(username = username).update(dict(username = new_username))
            Likes.query.filter_by(username = username).update(dict(username = new_username))
            Comments.query.filter_by(username = username).update(dict(username = new_username))
            Followers.query.filter_by(username = username).update(dict(username = new_username))
            Followers.query.filter_by(followed_by = username).update(dict(followed_by = new_username))
        
        db.session.commit()
       
        return redirect('/'+new_username)

@app.route('/delete_profile')
@login_required
def delete_profile():
    Followers.query.filter_by(username = current_user.username).delete()
    Followers.query.filter_by(followed_by = current_user.username).delete()
    Likes.query.filter_by(username = current_user.username).delete()
    Comments.query.filter_by(username = current_user.username).delete()
    posts = db.session.execute(select(Post).where(Post.id.in_(select(UploadedBy.post_id).where(UploadedBy.username == current_user.username)))).scalars().all()
    for post in posts:
        Likes.query.filter_by(post_id = post.id).delete()
        Comments.query.filter_by(post_id = post.id).delete()
        UploadedBy.query.filter_by(post_id = post.id).delete()
        PostImages.query.filter_by(post_id = post.id).delete()
        db.session.delete(post)
        
    User.query.filter_by(username = current_user.username).delete()
    db.session.commit()
    return redirect(url_for_security('login'))
        

"""
 CRUD for posts
"""       
        

@app.route('/add_post', methods = ['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        username= current_user.username
        title = request.form['title']
        description = request.form['description']
        image_urls = request.files.getlist('file')
        if not title or not description:
            return redirect('/' + current_user.username, code=400)
        new_post = Post(title = title, description = description, time_created = datetime.now())
        db.session.add(new_post)
        db.session.commit()
        
        post_id = Post.query.filter_by(title = title).order_by(Post.time_created).all()[-1].id
        for image in image_urls:
            db.session.add(PostImages(post_id = post_id, image_url = image.read()))
        new_upload = UploadedBy(username = username, post_id = post_id)
        db.session.add(new_upload)
        db.session.commit()
        return redirect('/' + current_user.username)
    
@app.route('/edit_post/<int:id>',  methods = ['GET', 'POST'])
@login_required
def edit_post(id : int):
    post = Post.query.filter_by(id = id).first()

    if request.method == 'POST':
        post.title = request.form['title']
        post.description = request.form['description']
        if not post.title or not post.description:
               redirect('/' + current_user.username, code=400)
        post.time_updated = datetime.now()
        db.session.commit()
        return redirect('/' + current_user.username)
        
        
@app.route('/delete_post/<int:id>',  methods = ['GET'])
@login_required
def delete_post(id:int):
    UploadedBy.query.filter_by(post_id = id).delete()
    Likes.query.filter_by(post_id = id).delete()
    Comments.query.filter_by(post_id = id).delete()
    PostImages.query.filter_by(post_id = id).delete()
    Post.query.filter_by(id = id).delete()
    
    db.session.commit()
   
    return redirect('/' + current_user.username)

@app.route('/post/<post_id>')
@login_required  
def view_post(post_id):
    post =  Post.query.filter_by(id = post_id).first()
    
    if not post:
        return render_template('error_page.html')
    username = UploadedBy.query.filter_by(post_id = post_id).first()
    user= getUser(username.username)
    images = getPostImages(post_id=post_id)
    post.time_created = pretty_date(post.time_created)
    if post.time_updated:
            post.time_updated = pretty_date(post.time_updated)
    comments = getComments(post.id)
    commenter = {}
    for comment in comments:
        commenter[comment] = getUser(comment.username)

    liked_by = getLikes(post.id)
    isLiked = isLikedByUser(post.id, current_user.username)
    return render_template('post.html', post = post, user = user, likes = liked_by, comments = comments, isLikedByUser = isLiked, commenter = commenter, images = images)

"""
Blog interactions
"""
@app.route('/follow/<username>')
@login_required
def follow(username):
    follow_req = Followers(username = username, followed_by = current_user.username)
    db.session.add(follow_req)
    db.session.commit()
    return redirect(redirect_url())

@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    follow_req = Followers.query.filter_by(username = username, followed_by = current_user.username).first()
    db.session.delete(follow_req)
    db.session.commit()
    return redirect(redirect_url())

           
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
    
@app.route('/download/<post_id>')
@login_required  
def download_blog(post_id):
    post =  Post.query.filter_by(id = post_id).first()
    
    if not post:
        return render_template('error_page.html')
    excel.init_excel(app)
    extension_type = "csv"
    filename = "blog" + "." + extension_type
    data = {"title" : post.title, "description" : post.description}
    return excel.make_response_from_dict(data, file_type=extension_type, file_name=filename)
