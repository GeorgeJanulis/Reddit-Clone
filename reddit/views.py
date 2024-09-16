from datetime import datetime
from flask import request, render_template, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required 
from reddit import app, db, lm
from .models import *
from sqlalchemy import desc

@app.route('/')
@app.route('/hello')
@app.route('/', methods=['GET'])
def home():
    if request.method == 'GET':
        top_posts = PostDB.query.order_by(desc(PostDB.num_likes)).limit(50).all()

        if top_posts is None:
            return render_template('header.html')

        return render_template('header.html', posts=top_posts)

def index():
    return "Hello World!"

@app.route('/write', methods=['GET', 'POST'])
@login_required
def write():
    if request.method == 'GET':
        #print("hello")
        return render_template('write.html')
    if request.method == 'POST':
        #fields
        title = request.form.get('title')
        content = request.form.get('content')
        new_tag = request.form.get('tag')

        post = PostDB(title=title, author=current_user.username, content=content, num_likes=0, time=datetime.now())
        db.session.add(post)

        #Create and add tag
        tag = TagDB(name=new_tag)
        db.session.add(tag)

        db.session.commit()

        #Connect the post and the tag
        existing_tag = TagDB.query.filter_by(name=new_tag).first()

        if existing_tag is None:
            post_tag = PostTagDB(tag_id=tag.id, post_id=post.id)
        else:
            post_tag = PostTagDB(tag_id=existing_tag.id, post_id=post.id)

        db.session.add(post_tag)
        db.session.commit()
        return redirect(url_for('home'))
    
@lm.user_loader
def load_user(id):
    return UserDB.query.get(int(id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        if request.form.get('login_or_signup') == 'signup': 

            user = UserDB.query.filter_by(email=email).first()
            if user is not None:
                return render_template('error.html', error='Email exists!')
            
            user = UserDB.query.filter_by(username=username).first()
            if user is not None:
                return render_template('error.html', error='Username already exists!')

            user = UserDB(email=email, username=username, password=password)
            db.session.add(user)
            db.session.commit()
            login_user(user, True)

            return redirect(url_for('home'))
        
        else:
            user = UserDB.query.filter_by(username=username, password=password).first()

            if user is None:
                return render_template('error.html', error='Yikes! Either your username or password is incorrect!')
            
            login_user(user, True)
            return redirect(url_for('home'))

@app.route('/tags/<tag_name>', methods=['GET'])
def tag(tag_name):
    tag = TagDB.query.filter_by(name=tag_name).first()
    if tag is None:
        return render_template('error.html', error='Tag does not exist!')
    
    #get all of the items in PostTagDB that are of ___ tag
    post_tags = PostTagDB.query.filter_by(tag_id=tag.id).all()

    #get all post_ids of queried posts from above
    post_ids = map(lambda x: x.post_id, post_tags)

    #get all posts of the ids collected above
    posts = map(lambda x: PostDB.query.filter_by(id=x).first(), post_ids)

    return render_template('tags.html', tag=tag_name, posts=posts)

@app.route('/posts/<post_id>', methods=['GET', 'POST'])
def post(post_id):
    if request.method == 'GET':
        post = PostDB.query.filter_by(id=post_id).first()

        if post is None:
            return render_template('error.html', error="Post doesn't exist")

        comments = CommentDB.query.filter_by(post_id=post_id).all()
        return render_template('post.html', post=post, comments=comments)
    if request.method == 'POST':
        #Adding to LikesDB - selection
        selection =request.form.get('selection')

        # content of comment
        content = request.form.get('content')

        if selection is not None and selection.startswith("post"):
            like_type=True
            if selection == 'post_dislike':
                like_type=False

            #query the like, if it exists
            like = LikeDB.query.filter_by(username=current_user.username, post_id=post_id).first()

            if like is not None and like.like_type is like_type:
                return redirect(url_for('post', post_id=post_id))

            if like is None:
                like = LikeDB(username=current_user.username, post_or_comment=1, post_id=post_id, like_type=like_type)
                db.session.add(like)
                db.session.commit()

            #update the like if different type of like
            like.like_type = like_type

            #update the posts' number of likes
            post=PostDB.query.filter_by(id=post_id).first()
            if like_type:
                post.num_likes += 1
                if post.num_likes is 0:
                    post.num_likes += 1

            else:
                post.num_likes -= 1
                if post.num_likes is 0:
                    post.num_likes -= 1
            db.session.commit()
            return redirect(url_for('post', post_id=post_id))
        
        #print('hello')
        
        if selection is not None:
            like_type=True
            if selection.startswith('comment_dislike'):
                like_type=False
            
            grab = selection.split("_")
            grab2 = grab[2]

            like = LikeDB.query.filter_by(username=current_user.username, comment_id=grab2).first()

            if like is not None and like.like_type is like_type:
                return redirect(url_for('post', post_id=post_id))
            
            if like is None:
                newgrab = selection.split("_")
                newgrab2 = newgrab[2]

                like = LikeDB(username=current_user.username, post_or_comment=0, comment_id=newgrab2, like_type=like_type)
                db.session.add(like)
                db.session.commit()

            like.like_type = like_type

            thenewgrab = selection.split("_")
            thenewgrab2 = thenewgrab[2]

            comment = CommentDB.query.filter_by(id=thenewgrab2).first()

            if like_type:
                comment.num_likes += 1
                if comment.num_likes is 0:
                    comment.num_likes += 1
            
            else:
                comment.num_likes -= 1
                if comment.num_likes is 0:
                    comment.num_likes -= 1

            db.session.commit()

        else:
            author = current_user.username
            time = datetime.now()
            comment = CommentDB(content=content, author=author, post_id=post_id, num_likes=0, time=time)
            db.session.add(comment)
            db.session.commit()
        return redirect(url_for('post', post_id=post_id))
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/users/<username>', methods=['GET', 'POST'])
def profile(username):
    if request.method == 'GET':
        user = UserDB.query.filter_by(username=username).first()
        if user is None:
            return render_template('error.html', error='User does not exist!')

        posts = PostDB.query.filter_by(author=username).all()
        return render_template('profile.html', posts=posts)
    
    if request.method == 'POST':

        selection = request.form.get('selection')

        if selection == 'posts':
            posts = PostDB.query.filter_by(author=username).all()

            #if no posts exist
            if posts is None:
                return render_template('profile.html', message='This user has not written anything')
            
            return render_template('profile.html', posts=posts, user=username)
        
        if selection == 'comments':
            comments = CommentDB.query.filter_by(author=username).all()
            post_ids = map(lambda x: x.post_id, comments)
            posts = map(lambda x: PostDB.query.filter_by(id=x).all(), post_ids)

            #returns the list of all the coments taht the current user has written
            return render_template('profile.html', comments=comments, PostDB=PostDB, user=username)
        
        if selection == 'likes':
            post_ids = map(lambda x: x.post_id, LikeDB.query.filter_by(username=username, post_or_comment=1).all())
            posts = map(lambda x: PostDB.query.filter_by(id=x).all(), post_ids)

            #returns the list of all the posts that the curtrent user has liked
            return render_template('profile.html', post_like=posts, user=username)
        
        if selection == None:
            return render_template('profile.html')