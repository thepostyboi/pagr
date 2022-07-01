from flask import Blueprint, render_template, flash, request, redirect, url_for
from flask_login import login_required, current_user
from .models import User, ProfilePicture, Listing, Comments, Likes, Page
import postcodes_io_api
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, aliased
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from . import db
import uuid
import os
from bs4 import BeautifulSoup
import requests
import re
import praw


api  = postcodes_io_api.Api(debug_http=True)

views = Blueprint("views", __name__)


#---------------------------------------------------------------------------------------------
##bs4 webscrapin stuff init
#def GETINFO(TKR):
#    def code_to_url(code):
#        finurl = []
#        finurl.append("https://www.marketwatch.com/investing/Stock/%s"%(code))
#        return "".join(finurl)
#
#    url = code_to_url(TKR)
#    data = requests.get(url)
#    soup = BeautifulSoup(data.content, "html.parser")
#
#
#    metatags = soup.find_all('meta',attrs={'name':'price'})
#    fin = []
#    for l in str(metatags).splitlines():
#        if "<meta content=" in l:
#            fin.append(l)
#    return "\n".join(fin)
#
##simplify da scrapin init
#def GETSIMPLEINFO(TKR):
#    fin = {}
#    fin["name"] = str(TKR)
#    fin["price"] = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?!\d)",GETINFO(TKR))[0]
#    fin["change-price"] = re.findall(r".\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?!\d)",GETINFO(TKR))[1]
#    fin["change-percent"] = re.findall(r".\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?!\d)",GETINFO(TKR))[2]
#    return fin
#
#def GETPRICE(TKR):
#    return re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?!\d)",GETINFO(TKR))[0]
#def GETPRICECHANGE(TKR):
#    return re.findall(r".\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?!\d)",GETINFO(TKR))[1]
#def GETCHANGEPERCENTAGE(TKR):
#    return re.findall(r".\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?!\d)",GETINFO(TKR))[2]
#
#global todaystkrs
#todaystkrs = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "FB", "NVDA", "TCEHY", "V", "JNJ", "JPM"]




#---------------------------------------------------------------------------------------------


@views.route("/", methods=["GET","POST"])
@views.route("/home", methods=["GET","POST"])
def home():
    #stockslist = []
    #for tkrs in todaystkrs:
    #    stockslist.append([tkrs,  GETCHANGEPERCENTAGE(tkrs)])
    page = request.args.get("page",1,type=int)
    listing = Listing.query.order_by(desc(Listing.date_created))
    secondlisting = Listing.query.outerjoin(Likes).group_by(Listing.id).order_by(db.func.count(Likes.id).desc(), Listing.date_created.desc())

    if request.method == "POST":
        search = request.form.get("search")
        if search:
            return redirect(url_for("views.search_results", search = search, page = 0))
        else:
            return redirect(url_for("views.home", current_user = current_user, listing = listing))

    return render_template("home.html", current_user = current_user, listing = listing,Page = Page)

@views.route("/search_results/<page>/<search>", methods=["GET","POST"])
def search_results(page,search):
    if page == "0":
        listing = Listing.query.filter(Listing.title.contains(search)).all()
    else:
        listing = Listing.query.filter(Listing.title.contains(search),Listing.Page_id==page).all()
    return render_template("listing.html", current_user = current_user, listing = listing,Page = Page)

@views.route("/upload_listing/<page>", methods=['GET', 'POST'])
@login_required
def upload(page):
    if current_user.banned == 1:
        return redirect(url_for("views.home"))
    pathtwo = os.path.abspath(os.getcwd())
    path = fr'{pathtwo}\website\static\uploads'
    Page_id = page
    if request.method == 'POST':
        file = request.files["input"]
        key = str(uuid.uuid1())
        if file:
            filename = file.filename
            try:
                extension = filename.rsplit('.', 1)[1].lower()
            except:
                extension = "png"
            filename = key + str("." + extension)
            minetype = file.content_type
            file.save(os.path.join(path, filename ))
        else: filename,minetype = "",""
        title = request.form.get("title")
        #postcode = request.form.get("postcode")
        description = request.form.get("description")


        #postcode_is_valid = api.is_postcode_valid(str(postcode))
        #if not postcode_is_valid:
        #    flash("Invalid postcode", category="error")
        if str(title) == "":
            flash("No title", category="error")
        elif not  Page.query.filter_by(id=page).first():
            flash("Invalid page", category="error")
        elif Page.query.filter_by(id=Page_id).first().removed == 1:
            flash("Page removed", category="error")
        else:
            #data = api.get_postcode(postcode)
            #region = (str(data['result']['region']))
            New_listing = Listing(title=title, description=description, user_id = current_user.id, file = filename, minetype = minetype, Page_id = Page_id)
            #New_listing = Listing(title=title, postcode=postcode, description=description, user_id = current_user.id, region = region, file = filename, minetype = minetype, Page_id = Page_id)
            db.session.add(New_listing)
            db.session.commit()


    return render_template("upload_listing.html", current_user = current_user, Page_id = Page_id,Page = Page)


#multiple pages can have same name, need fix
@views.route("/upload_page", methods=['GET', 'POST'])
@login_required
def upload_page():
    if current_user.banned == 0 and current_user.admin == 1:
        if request.method == 'POST':
            title = request.form.get("title")
            description = request.form.get("description")
            if str(title) == "":
                flash("No title", category="error")
            elif Page.query.filter_by(title = str(title)).first():
                flash("Title already taken", category="error")
            else:
                New_page = Page(title=title, description=description, user_id = current_user.id)
                db.session.add(New_page)
                db.session.commit()
    else:
        return redirect(url_for("views.home"))



    return render_template("upload_page.html", current_user = current_user,Page = Page)

#@views.route("/region/<region>")
#def region(region):
#    listing = Listing.query.filter_by(region = str(region)).order_by(desc(Listing.date_created))
#    return render_template("region.html", current_user = current_user, region = region, listing = listing)

@views.route("/page/<page>", methods=["GET", "POST"])
def page(page):
    Page_id = page
    page_check = Page.query.filter_by(id=page).first()
    if page_check:
        page_title = page_check.title
        page_description = page_check.description
        page_creator = User.query.filter_by(id = page_check.user_id).first()
    else:
        page_title = "page not found"
        page_description = "sorry, no description here"
        page_creator = ""

    if request.method == "POST":
        search = request.form.get("search")
        if search:
            return redirect(url_for("views.search_results", search = search, page = page))

    listing = Listing.query.filter_by(Page_id = str(page)).order_by(desc(Listing.date_created))
    return render_template("page.html", current_user = current_user, listing = listing,page_title=page_title, page_description = page_description, Page_id=Page_id,page_check=page_check,Page = Page,page_creator=page_creator)

@views.route("/pagelist")
def pagelist():
    pages = Page.query.order_by(desc(Page.date_created))
    return render_template("pagelist.html", current_user = current_user, pages = pages,Page = Page)

@views.route("/listings/<urlforlisting>", methods=["GET", "POST"])
def listings(urlforlisting):
    if current_user.is_authenticated:
        if current_user.banned == 1:
            return redirect(url_for("views.home"))
    listing = Listing.query.filter_by(id = str(urlforlisting)).all()
    flisting = Listing.query.filter_by(id = str(urlforlisting)).first()
    op = User.query.filter_by(id=flisting.user_id).first()
    if flisting:
        if request.method == "POST":
            cmm = request.form.get("cmm")

            if len(cmm) < 1:
                flash("comment too short", category="error")
            else:
                new_comment = Comments(text=cmm, user_id=current_user.id, Listing_id = flisting.id)
                db.session.add(new_comment)
                db.session.commit()
                flash("added", category="success")
        return render_template("listings.html", current_user = current_user, listing = listing, flisting = flisting, op = op, User = User,Page = Page)
    else:
        flash("Listing not found", category="error")
        return redirect(url_for("views.home"))


#change this code ----------------------------------------------------------------------------------------------------------
@views.route("/like/<urlforlisting>", methods=["POST", "GET"])
def like(urlforlisting):
    if current_user.is_authenticated:
        check_like = Likes.query.filter_by(user_id = current_user.id, Listing_id=urlforlisting).first()

        if Listing.query.filter_by(id = str(urlforlisting)).first():
            if check_like:
                db.session.delete(check_like)
                db.session.commit()

            else:
                new_like = Likes(user_id=current_user.id, Listing_id = urlforlisting)
                db.session.add(new_like)
                db.session.commit()
            return redirect(url_for("views.listings", urlforlisting = urlforlisting,Page = Page))
        else:
            flash("Listing not found", category="error")
            return redirect(url_for("views.home"))
    else:
        flash("Login to like posts", category="error")
        return redirect(url_for("views.listings", urlforlisting = urlforlisting,Page = Page))



# ------------------------------------------------------------------------------------------------------------------------------

@views.route("/remove/<urlforlisting>")
@login_required
def remove(urlforlisting):
    if current_user.admin == 1 and current_user.banned == 0:
        listing = Listing.query.filter_by(id=urlforlisting).first()
        if listing.removed == 1:
            listing.removed = 0

        else:
            listing.removed = 1


        db.session.commit()
        return redirect(url_for("views.listings", urlforlisting = urlforlisting))
    else:
        flash("access denied", category="error")
        return redirect(url_for("views.home"))

@views.route("/removecomment/<idforcomment>")
@login_required
def removecomment(idforcomment):
    if current_user.admin == 1 and current_user.banned == 0:
        comment = Comments.query.filter_by(id=idforcomment).first()
        if comment.removed == 1:
            comment.removed = 0
        else:
            comment.removed = 1
        db.session.commit()
        return redirect(url_for("views.listings", urlforlisting = comment.Listing_id))
    else:
        flash("access denied", category="error")
        return redirect(url_for("views.home"))

@views.route("/removepage/<idforpage>")
@login_required
def removepage(idforpage):
    if current_user.admin == 1 and current_user.banned == 0:
        page = Page.query.filter_by(id=idforpage).first()
        if page.removed == 1:
            page.removed = 0
        else:
            page.removed = 1
        db.session.commit()
        return redirect(url_for("views.pagelist"))
    else:
        flash("access denied", category="error")
        return redirect(url_for("views.home"))



@views.route("/about")
def about():
    return render_template("about.html", current_user = current_user)
