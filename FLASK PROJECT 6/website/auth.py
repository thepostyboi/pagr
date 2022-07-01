from flask import Blueprint, render_template, redirect, url_for, request, flash
from . import db
from .models import User, ProfilePicture, Listing, Ratings, Reports, Likes, Page
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc
import re
import uuid
import os
auth = Blueprint("auth", __name__)


@auth.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash("Logged in!", category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Password is incorrect.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", current_user = current_user)


@auth.route("/sign-up", methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get("email")
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()

        if email_exists:
            flash('Email is already in use.', category='error')
        elif username_exists:
            flash('Username is already in use.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match!', category='error')
        elif len(username) < 2:
            flash('Username is too short.', category='error')
        elif len(password1) < 6:
            flash('Password is too short.', category='error')

        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email) or len(email) < 4:
            flash("Email is invalid.", category='error')
        else:
            new_user = User(email=email, username=username, password=generate_password_hash(
                password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('User created!')
            return redirect(url_for('views.home'))

    return render_template("signup.html", current_user = current_user)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("views.home"))



@auth.route("/user/<userid>", methods = ["GET", "POST"])
def user(userid):
    if request.method == "POST":
        pass
    user = User.query.filter_by(id=userid).first()
    profile_pictures_ = ProfilePicture.query.filter_by(user_id=userid).first()
    danger_rating = Ratings.query.filter_by(rated_user_id=userid).all()

    ratingslist = []
    for i in danger_rating:
        if str(i.rating).isnumeric():
            ratingslist.append(i.rating)
    if ratingslist == []:
        the_rating = 0
    else:
        the_rating = round(sum(ratingslist)/len(ratingslist), 1)

    if user:
        listing = Listing.query.filter_by(user_id = userid).order_by(desc(Listing.date_created))
        if current_user.is_authenticated:
            if int(current_user.id) == int(userid):
                foreign_profile = False
            else: foreign_profile = True
        else: foreign_profile = True
        if request.method == "POST":
            if foreign_profile:
                if current_user.banned == 1:
                    return redirect(url_for("auth.user", userid=userid))
                rate = request.form.get("form_rating")
                new_rating = Ratings(rater_user_id = current_user.id, rated_user_id = user.id, rating = rate)
                checkrating = Ratings.query.filter_by(rater_user_id = current_user.id, rated_user_id = user.id).first()
                if checkrating:
                    db.session.delete(checkrating)
                    db.session.add(new_rating)
                else:
                    db.session.add(new_rating)
                db.session.commit()
            else:
                pass
        return render_template("user.html", current_user = current_user, userid = userid, foreign_profile = foreign_profile, user = user, profile_pictures_ = profile_pictures_, listing = listing, the_rating = the_rating, Reports = Reports, Likes = Likes, Page=Page)
    else:
        flash("Profile not found", category='error')
        return redirect(url_for("views.home"))


@auth.route("/profile_picture_upload")
@login_required
def profile_picture_upload():
    if current_user.banned == 1:
        return redirect(url_for("views.home"))
    return render_template("profile_picture_upload.html", current_user=current_user)

@auth.route("/uploaded_pfp", methods = ["POST"])
@login_required
def uploaded_pfp():
    if current_user.banned == 1:
        return redirect(url_for("views.home"))
    pathtwo = os.path.abspath(os.getcwd())
    path = fr'{pathtwo}\website\static\PROFILEPICS'
    profile_pictures_ = ProfilePicture.query.filter_by(user_id=current_user.id).first()
    if profile_pictures_:
        db.session.delete(profile_pictures_)
        db.session.commit()
        os.remove(os.path.join(path, profile_pictures_.filename))
    if request.method == "POST":
        file = request.files["input"]
        if file:
            key = str(uuid.uuid1())
            filename = file.filename
            minetype = file.content_type
            if str(minetype) in ["image/png", "image/jpeg"]:
                filename = key + str("." + "png")
                img = ProfilePicture(filename=filename, user_id=current_user.id, )
                file.save(os.path.join(path, filename ))
                db.session.add(img)
                db.session.commit()
                flash("uploaded", category="success")
            else:
                flash("wrong minetype")
                flash(minetype)
    return render_template("profile_picture_upload.html", current_user=current_user)

@auth.route("/report/<userid>", methods = ["POST", "GET"])
@login_required
def report(userid):
    if current_user.banned == 1:
        return redirect(url_for("views.home"))
    user = User.query.filter_by(id=userid).first()
    if request.method == "POST":
        rep = request.form.get("rep")
        if user and rep and current_user.id != user.id:
            new_report = Reports(reporter_user_id = current_user.id, reported_user_id = user.id, report = rep)
            db.session.add(new_report)
            db.session.commit()
    return render_template("report.html", current_user=current_user, user = user)

@auth.route("/admin")
@login_required
def admin():
    if current_user.admin == 1 and current_user.banned == 0:
        users = User.query.order_by(desc(User.date_created))
        return render_template("admin.html", current_user=current_user, users = users)
    else:
        flash("access denied", category="error")
        return redirect(url_for("views.home"))

@auth.route("/ban/<userid>")
@login_required
def ban(userid):
    if current_user.admin ==1 and current_user.banned == 0:
        user = User.query.filter_by(id=userid).first()
        if user.banned == 1:
            user.banned = 0
        else:
            user.banned = 1
        db.session.commit()
        return redirect(url_for("auth.admin"))
    else:
        flash("access denied", category="error")
        return redirect(url_for("views.home"))

@auth.route("/giveadmin/<userid>")
@login_required
def giveadmin(userid):
    if current_user.admin ==1 and current_user.banned == 0:
        user = User.query.filter_by(id=userid).first()
        if user.admin == 1:
            user.admin = 0
        else:
            user.admin = 1
        db.session.commit()
        return redirect(url_for("auth.admin"))
    else:
        flash("access denied", category="error")
        return redirect(url_for("views.home"))
