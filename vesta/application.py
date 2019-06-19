import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, jsonify, make_response, url_for
from flask_session import Session
from datetime import timedelta
from datetime import datetime
from tempfile import mkdtemp
from werkzeug.utils import secure_filename
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import time
from flask_cors import CORS, cross_origin
from helpers import *

app = Flask(__name__)
CORS(app)

# Define a folder for uploads
UPLOAD_FOLDER = 'static/photos/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    response.headers["Access-Control-Allow-Credentials"] = 'true'
    response.headers["Access-Control-Allow-Methods"] =  "GET, POST, DELETE, PUT, OPTIONS"
    response.headers["access-control-allow-headers"] = "Content-Type, Authorization, Content-Length, X-Requested-With"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=100)
Session(app)


# Route to landing page
@app.route('/')
def index():
    """Pretty user landing page"""
    return render_template("landing.html")
@app.route("/register", methods=["GET", "POST"]) #TODO: add email form, send an email
def register():
    """Register user"""
    if request.method == "POST":
        invalidemail = False
        invalidusername=False
        invalidpword=False
        invalidfname = False
        invalidlname = False
        if (not request.form.get("email")) or 1 != request.form.get("email").count('@') or request.form.get("email").count('.') != 1:
            invalidemail=True
        else:
            email = request.form.get("email")
        if not request.form.get("password"):
            invalidpword=True
        else:
            password = request.form.get("password")
        if not request.form.get("fname").isalpha():
            invalidfname = True
        else:
            fname = request.form.get("fname")
        if not request.form.get("lname").isalpha():
            invalidlname = True
        else:
            lname = request.form.get("lname")
        if invalidlname or invalidfname or invalidpword or invalidemail:
            return render_template("register.html", error = True, invalidfname = invalidfname, invalidlname = invalidlname, invalidpword = invalidpword, invalidemail = invalidemail)
        fullname = str(fname.strip()).capitalize() + " " + str(lname.strip()).capitalize()
        with sqlite3.connect('info.db') as conn:
            user = conn.cursor().execute("SELECT * FROM users WHERE email = :email", {'email': email}).fetchall()
            if len(user) == 0:
                conn.cursor().execute("INSERT INTO users('email', 'hash', 'name') VALUES(:email, :hashed, :fullname)", {'email': email, 'hashed': generate_password_hash(password), 'fullname': fullname})
                user_id = conn.cursor().execute("SELECT id FROM users WHERE email = :email", {'email': email}).fetchall()
                session["user_id"] = user_id[0][0]
                session.permanent = True
                conn.commit()
                if 'redir' in request.cookies:
                    loc = request.cookies.get('redir')
                    return redirect(loc)
                elif 'redir' in request.cookies:
                    loc = request.cookies.get('nrender')
                    return render_template(loc)
                else:
                    return redirect("/")
            else:
                return render_template("register.html", message= 'This email is already in use.')
            return render_template('landing.html')
    else:
        return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":


        # Ensure username was submitted
        if not request.form.get("email") or not request.form.get("password"):
            error = True
            email = False
            if not request.form.get("password"):
                password = False
            else:
                password = True
            return render_template("login.html", error = error, emaile = email, passworde = password)

        # Query database for username
        with sqlite3.connect('info.db') as conn:
            rows = conn.cursor().execute("SELECT * FROM users WHERE email = :email",
                              {'email':request.form.get("email").rstrip()}).fetchall()
            print(rows)

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
                return render_template("login.html", error = True, username = True, password = True, wrong = True)

            # Remember which user has logged in
            session["user_id"] = rows[0][0]
            session.permanent = True

            # Redirect user to home page or preferred page
            if 'redir' in request.cookies:
                loc = request.cookies.get('redir')
                return redirect(loc)
            elif 'redir' in request.cookies:
                loc = request.cookies.get('nrender')
                return render_template(loc)
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route('/me')
@login_required
def me():
    """Hopefully useful user account page"""
    with sqlite3.connect('info.db') as conn:
        user = conn.cursor().execute("SELECT * FROM users WHERE id = :id", {'id': session["user_id"]}).fetchall()
        name = user[0][3]
        return render_template("me.html", name = name)

@app.route('/rent', methods=["POST", "GET"])
def rent():
    """Submit property for renting out inital"""
    if request.method == "GET":
        with sqlite3.connect('info.db') as conn:
            if session.get("user_id") is None:
                if not request.args.get("type") or not request.args.get("access") or not request.args.get("maxguests"):
                    resp = redirect('/login')
                    resp.set_cookie('redir', "/rent")
                    return resp
                else:
                    print(request.args.get("type"), request.args.get("access"), request.args.get("maxguests"))
                    resp = make_response(render_template("login.html"))
                    resp.set_cookie(b'type', request.args.get("type"))
                    resp.set_cookie(b'access', request.args.get("access"))
                    resp.set_cookie(b'maxguests', request.args.get("maxguests"))
                    resp.set_cookie(b'nrender', 'upload.html')
                    if request.args.get("children"):
                        resp.set_cookie(b'children', 'True')
                    else:
                        resp.set_cookie(b'children', 'False')
                    return resp
            else:
                print("signed in")
                with sqlite3.connect('info.db') as conn:
                    print(request.cookies.get('type'))
                    if request.cookies.get('type') and request.cookies.get('access') and request.cookies.get('maxguests') and request.cookies.get('children'):
                        print("in cookies")
                        prop = request.cookies.get('type')
                        access = request.cookies.get('access')
                        max_guests = request.cookies.get('maxguests')
                        children = request.cookies.get('children')
                        return render_template('upload.html', prop = prop, access = access, max_guests = max_guests, children = children)
                    elif request.args.get("type") and request.args.get("access") and request.args.get("maxguests"):
                        print("in args")
                        prop = request.args.get('type')
                        access = request.args.get('access')
                        max_guests = request.args.get('maxguests')
                        if request.args.get('children'):
                            children = True
                        else:
                            children = False
                        return render_template('upload.html', prop = prop, access = access, max_guests = max_guests, children = children)
                    else:
                        print("not in args or cookies")
                        return render_template('upload.html')
    else:
        data = {}
        data['id'] = int(open("counter.txt").read()) + 1
        i = 0
        data['photos'] = ""
        for file in request.files.getlist('photos'):
            file.filename = secure_filename(file.filename)
            file.filename = str(session["user_id"]) + "-" + str(data['id']) + "-" + str(i) + file.filename[file.filename.index('.'):]
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            data['photos'] += file.filename + ","
            i += 1
        data['photos'] = data['photos'][:len(data['photos'])-1]
        data['owner'] = int(session["user_id"])
        data['type'] = request.form.get('type')
        data['access'] = request.form.get('access')
        data['max_guests'] = request.form.get('maxguests')
        if request.form.get('children'):
            data['children'] = True
        else:
            data['children'] = False
        data['beds'] = int(request.form.get('beds'))
        data['baths'] = int(request.form.get('beds'))
        data['country'] = request.form.get('country')
        data['zip'] = request.form.get('zip')
        data['state'] = request.form.get('state')
        data['city'] = request.form.get('city')
        data['address'] = request.form.get('addy')
        zip = request.form.get('zip')
        if request.form.get('furnished'):
            data['furnished'] = True
        else:
            data['furnished'] = False
        if request.form.get('wifi'):
            data['wifi'] = True
        else:
            data['wifi'] = False
        if request.form.get('heat'):
            data['heat'] = True
        else:
            data['heat'] = False
        if request.form.get('ac'):
            data['ac'] = True
        else:
            data['ac'] = False
        if request.form.get('pets'):
            data['pets'] = True
        else:
            data['pets'] = False
        if request.form.get('babies'):
            data['babies'] = True
        else:
            data['babies'] = False
        if request.form.get('parties'):
            data['parties'] = True
        else:
            data['parties'] = False
        if request.form.get('smoking'):
            data['smoking'] = True
        else:
            data['smoking'] = False
        if request.form.get('noise'):
            data['noise'] = True
        else:
            data['noise'] = False
        if request.form.get('workspace'):
            data['workspace'] = True
        else:
            data['workspace'] = False
        if request.form.get('gym'):
            data['gym'] = True
        else:
            data['gym'] = False
        if request.form.get('pool'):
            data['pool'] = True
        else:
            data['pool'] = False
        data['description'] = request.form.get('desc')
        data['location'] = request.form.get('locdescr')
        data['renterdescr'] = request.form.get('renterdescr')
        data['title'] = request.form.get('title')
        data['phone'] = request.form.get('phone')
        data['email'] = request.form.get('email')
        data['rent'] = int(request.form.get('rent'))
        print(data)
        with sqlite3.connect('info.db') as conn:
            conn.cursor().execute("INSERT INTO properties('owner', 'type', 'access', 'max_guests', 'children', 'rent', 'beds', 'baths', 'country', 'state', 'address', 'zip', 'furnished', 'wifi', 'heat', 'ac', 'pets', 'babies', 'parties', 'smoking', 'noise', 'workspace', 'gym', 'pool', 'photos', 'description', 'location', 'renterdescr', 'title', 'email', 'phone', 'id', 'city') VALUES(:owner, :type, :access, :max_guests, :children, :rent, :beds, :baths, :country, :state, :address, :zip, :furnished, :wifi, :heat, :ac, :pets, :babies, :parties, :smoking, :noise, :workspace, :gym, :pool, :photos, :description, :location, :renterdescr, :title, :email, :phone, :id, :city)", data)
        open("counter.txt", "w").write(str(data['id'] + 1))
        return redirect('/')

@app.route('/find', methods=["POST", "GET"])
def find():
    if request.method == "GET":
        with sqlite3.connect('info.db') as conn:
            json = []
            homes = conn.cursor().execute("SELECT * FROM properties WHERE featured = :True", {'True': True}).fetchall()
            i = 0
            while i < len(homes):
                homes[i] = list(homes[i])
                i += 1
            for home in homes:
                if home[1] == 'apt':
                    home[1] = 'apartment'
                if home[2] == 'privroom':
                    home[2] = 'private room'
                if home[2] == 'sharedroom':
                    home[2] = 'shared room'
                if home[2] == 'whole':
                    home[2] = 'full'
                if home[2] == 'privroom':
                    home[2] = 'private room'
                home[24] = home[24].split(',')
            return render_template("browse.html", homes=homes)
    else:
        with sqlite3.connect('info.db') as conn:
            cmd = ""
            filters ={}
            cmd += "SELECT * FROM properties WHERE city = :city"
            filters['city'] = request.form.get('city')
            if request.form.get('numppl'):
                filters['ppl'] = int(request.form.get('numppl'))
                cmd += "INTERSECT SELECT * FROM properties WHERE max_guests <= :ppl"
            if request.form.get('children'):
                filters['children'] = int(request.form.get('numppl'))
                cmd += "INTERSECT SELECT * FROM properties WHERE children"
            if request.form.get('wifi'):
                filters['wifi'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE wifi"
            if request.form.get('heat'):
                filters['heat'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE heat"
            if request.form.get('ac'):
                filters['ac'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE ac"
            if request.form.get('pets'):
                filters['pets'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE pets"
            if request.form.get('babies'):
                filters['babies'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE babies"
            if request.form.get('smoking'):
                filters['smoking'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE smoking"
            if request.form.get('noise'):
                filters['noise'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE noise"
            if request.form.get('baths'):
                filters['baths'] = request.form.get('baths')
                cmd += "INTERSECT SELECT * FROM properties WHERE baths >= :baths"
            if request.form.get('beds'):
                filters['beds'] = request.form.get('beds')
                cmd += "INTERSECT SELECT * FROM properties WHERE baths >= :beds"
            if request.form.get('minrent'):
                filters['minrent'] = request.form.get('minrent')
                cmd += "INTERSECT SELECT * FROM properties WHERE rent >= :minrent"
            if request.form.get('maxrent'):
                filters['maxrent'] = request.form.get('maxrent')
                cmd += "INTERSECT SELECT * FROM properties WHERE rent <= :maxrent"
            if request.form.get('furnished'):
                filters['furnished'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE furnished"
            if request.form.get('elevator'):
                filters['elevator'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE elevator"
            if request.form.get('gym'):
                filters['gym'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE gym"
            if request.form.get('workspace'):
                filters['elevator'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE workspace"
            if request.form.get('pool'):
                filters['pool'] = 1
                cmd += "INTERSECT SELECT * FROM properties WHERE pool"
            if request.form.get('access'):
                if request.form.get('access') != "anyacc":
                    filters['access'] = request.form.get('access')
                    cmd += "INTERSECT SELECT * FROM properties WHERE access = :access"
            if request.form.get('type'):
                if request.form.get('type') != "anytype":
                    filters['type'] = request.form.get('type')
                    cmd += "INTERSECT SELECT * FROM properties WHERE type = :type"
            homes = conn.cursor().execute(cmd, filters).fetchall()
            print(cmd, filters)
            print(homes)
            i = 0
            while i < len(homes):
                homes[i] = list(homes[i])
                i += 1
            for home in homes:
                if home[1] == 'apt':
                    home[1] = 'apartment'
                if home[2] == 'privroom':
                    home[2] = 'private room'
                if home[2] == 'sharedroom':
                    home[2] = 'shared room'
                if home[2] == 'whole':
                    home[2] = 'full'
                if home[2] == 'privroom':
                    home[2] = 'private room'
                home[24] = home[24].split(',')
            return render_template("results.html", homes=homes)











