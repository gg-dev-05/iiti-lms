from flask import Flask, flash, render_template, redirect, url_for, session
from flask_mysqldb import MySQL
# import MySQLdb
import yaml
from functions.dbConfig import database_config
from authlib.integrations.flask_client import OAuth
import os
from datetime import timedelta


app = Flask(__name__)

env = "dev"
DATABASE_URL = ""
if env == "dev":
    dev = yaml.load(open('db.yaml'), Loader=yaml.FullLoader)
    DATABASE_URL = dev['CLEARDB_DATABASE_URL']
    print(DATABASE_URL)

else:
    DATABASE_URL = os.environ.get("CLEARDB_DATABASE_URL")

user, password, host, db = database_config(DATABASE_URL)

app.config['MYSQL_HOST'] = host
app.config['MYSQL_USER'] = user
app.config['MYSQL_PASSWORD'] = password
app.config['MYSQL_DB'] = db
print(host, user, password, db)
# Session config
app.secret_key = dev['client_secret']
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'

mysql = MySQL(app)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=dev['client_id'],
    client_secret=dev['client_secret'],
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    # This is only needed if using openId to fetch user info
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)


@app.route("/")
def home():
    if "profile" in session:
        print(session["profile"])
        # check is this email belongs to admin to normal user
        # if email is of admin (librarian)
        # session["isAdmin"] = True

    else:
        # add page for sign in
        return "Not signed in <a href='/login'>LOGIN</a>>"
    return render_template('dashboard.html')

@app.route("/<memberType>")
def members(memberType):
    if memberType == 'students':
        cur = mysql.connection.cursor()
        cur.execute("SELECT reader_name, reader_email, reader_address, phone_no, books_issued, unpaid_fines FROM reader WHERE is_faculty = 0;")
        students = cur.fetchall()
        return render_template("students.html", students=students)
    if memberType == 'faculties':
        cur = mysql.connection.cursor()
        cur.execute("SELECT reader_name, reader_email, reader_address, phone_no, books_issued, unpaid_fines FROM reader WHERE is_faculty = 1;")
        faculties = cur.fetchall()
        return render_template("faculties.html", faculties=faculties)
    return redirect("/")

@app.route("/user")
def userDashboard():
    return render_template('user.html')


@app.route("/allBooks")
def user_allBooks():
    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect("/")
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    person = cur.fetchone()
    print(cur.fetchall())
    cur.execute(f"SELECT ISBN FROM issue_details WHERE reader_id='{person}'")
    books = cur.fetchall()
    # cur.execute(f")
    return render_template('allBooks.html')


@app.route("/recommendedBooks")
def user_BookRecommedation():
    return render_template('user_BookRecommedation.html')


@app.route("/booksWithTags")
def user_booksWithTags():
    return render_template('booksWithTags.html')


@app.route("/friends")
def friends():
    return render_template('allFriends.html')


@app.route("/feedback")
def feedback():
    return render_template('userFeedback.html')


@app.route("/history")
def user_History():
    return render_template('userHistory.html')


@app.route("/test")
def updateBooks():
    return render_template('updateBooks.html')


@app.route("/tables")
def addBooks():
    return render_template('tables.html')


@app.route("/dashboard")
def dashboard():
    return render_template('dashboard.html')


@app.route('/login')
def login():
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/authorize')
def authorize():
    message = None
    google = oauth.create_client('google')
    # Access token from google (needed to get user info)
    token = google.authorize_access_token()
    # userinfo contains stuff u specificed in the scrope
    resp = google.get('userinfo')
    user_info = resp.json()
    user = oauth.google.userinfo()
    session['profile'] = user_info
    # make the session permanant so it keeps existing after browser gets closed
    session.permanent = True
    if token != '':
        message = 'You were successfully logged in'
    else:
        message = 'You Please Try Again'
    return redirect('/')


@app.route("/logout")
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect("/")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html')


if __name__ == "__main__":
    if(env == 'dev'):
        app.run(debug=True)
    else:
        app.run()
