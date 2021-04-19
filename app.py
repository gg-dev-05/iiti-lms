from flask import Flask, render_template, redirect, url_for, session, request
from flask_mysqldb import MySQL
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

else:
    DATABASE_URL = os.environ.get("CLEARDB_DATABASE_URL")

user, password, host, db = database_config(DATABASE_URL)

app.config['MYSQL_HOST'] = host
app.config['MYSQL_USER'] = user
app.config['MYSQL_PASSWORD'] = password
app.config['MYSQL_DB'] = db

# Session config
app.secret_key = os.environ.get("client_secret") if (env != 'dev') else dev['client_secret']
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'

mysql = MySQL(app)

clientSecret = os.environ.get("client_secret") if (env != 'dev') else dev['client_secret']
clientId = os.environ.get("client_id") if (env != 'dev') else dev['client_id']

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=clientId,
    client_secret=clientSecret,
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
        # check is this email belongs to admin to normal user
        # if email is of admin (librarian)
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute("SELECT * from librarian WHERE librarian_email='{}';".format(email))
        result = cur.fetchall()
        print(result)
        if (result):
            session["isAdmin"] = True
            print(session)
            return render_template('adminHome.html', details=session["profile"], resutl=result)
        else:
            session["isAdmin"] = False
            return render_template('user.html', details=session["profile"])

    else:
        # add page for sign in
        return render_template('Login.html')
    

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

@app.route('/books')
def allBooks():
    cur = mysql.connection.cursor()
    cur.execute("SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book;")
    books = cur.fetchall()
    return render_template("allBooks.html", books=books)

@app.route("/book", methods=['GET', 'POST'])
def book():
    if request.method == 'GET':
        return "GET";
    if session["isAdmin"] == True:   
        data = request.form
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM book WHERE title='{}'".format(data['book']))
        books = cur.fetchall()
        print(books)
        # return render_template("searchBook.html",books=books);
        return render_template("adminSearchBook.html",books=books);

    if session["isAdmin"] == False:   
        data = request.form
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM book WHERE title='{}'".format(data['book']))
        books = cur.fetchall()
        print(books)
        # return render_template("searchBook.html",books=books);
        return render_template("userSearchBook.html",books=books); 
    return redirect("/");         

# issue details
@app.route("/logs")
def logs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM issue_details;")
    details = cur.fetchall()
    return render_template("issueDetails.html", details=details)

@app.route("/addBook")
def addBook():
    return render_template("addBook.html")


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

    cur.execute(f"SELECT ISBN,title,shelf_id,current_status,avg_rating,book_language,publisher,publish_date FROM book WHERE ISBN in( SELECT ISBN FROM issue_details WHERE reader_id='{person[0]}')")
    books = cur.fetchall()
    print(books)
    # cur.execute(f")
    return render_template('allBooks.html',books=books)

@app.route("/demo")
def demo():
    if "profile" in session:
        email = session["profile"]["email"]
        name = session["profile"]["name"]
    else:
        return "Not signed in <a href='/login'>LOGIN</a>>"
    # Only If he/she is a student
    return render_template("form-wizard.html", email=email,name=name)


@app.route("/recommendedBooks")
def user_BookRecommedation():
    return render_template('user_BookRecommedation.html')


@app.route("/booksWithTags")
def user_booksWithTags():
    return render_template('booksWithTags.html')


@app.route("/friends")
def friends():
    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect("/")

    cur = mysql.connection.cursor()
    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    reader_1=cur.fetchall()
  #  cur.execute(f"SELECT reader_2 FROM friends WHERE reader_1='{reader_1}'")
  #  friendsid = cur.fetchall()
    cur.execute(f"SELECT reader_name,phone_no,books_issued FROM reader WHERE ID IN ( SELECT reader_2 FROM friends WHERE reader_1={reader_1[0][0]} )")
    friendinfo = cur.fetchall()
   # print(f"SELECT reader_name,phone_no,books_issued FROM reader WHERE ID IN ( SELECT reader_2 FROM friends WHERE reader_1={reader_1[0][0]} )")
    print(friendinfo)
    return render_template('allFriends.html',len=len(friendinfo), friendinfo=friendinfo)


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
