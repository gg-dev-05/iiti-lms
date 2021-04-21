from flask import flash, Flask, render_template, redirect, url_for, session, request
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
app.secret_key = os.environ.get("client_secret") if (
    env != 'dev') else dev['client_secret']
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'

mysql = MySQL(app)

clientSecret = os.environ.get("client_secret") if (
    env != 'dev') else dev['client_secret']
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
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute("SELECT * from librarian WHERE librarian_email='{}';".format(email))
        result = cur.fetchall()
        if (result):
            session["isAdmin"] = True
            return render_template('adminHome.html', details=session["profile"])
        else:
            session["isAdmin"] = False
            cur.execute("SELECT is_faculty from reader WHERE reader_email = '{}';".format(email))
            print("SELECT is_faculty from reader WHERE reader_email = '{}';".format(email))
            result = cur.fetchone()
            if result == None:
                return render_template("register.html", email=session['profile']['email'], name=session['profile']['name'])
            else:
                if result[0] == 1:
                    session["isFaculty"] = True
                else:
                    session["isFaculty"] = False
                return render_template('userHome.html', details=session["profile"])

    else:
        return render_template('Login.html')

# Register new student
@app.route("/new", methods=["POST"])
def newStudent():
    data = request.form
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO reader (reader_name, reader_email, reader_address, phone_no, is_faculty) VALUES ('{}', '{}', '{}', {}, {});".format(data['Name'], data['Email'], data['Address'], data['Number'], 0))
    mysql.connection.commit()
    return redirect("/")

@app.route("/<memberType>")
def members(memberType):
    if memberType == 'students':
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT reader_name, reader_email, reader_address, phone_no, books_issued, unpaid_fines,ID FROM reader WHERE is_faculty = 0;")
        students = cur.fetchall()
        return render_template("students.html", students=students)
    if memberType == 'faculties':
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT reader_name, reader_email, reader_address, phone_no, books_issued, unpaid_fines,ID FROM reader WHERE is_faculty = 1;")
        faculties = cur.fetchall()
        return render_template("faculties.html", faculties=faculties)
    return redirect("/")


@app.route("/<memberType>/delete/<ID>")
def members1(memberType, ID):
    if session['isAdmin']:
        if memberType == 'faculties' or memberType == 'students':
            cur = mysql.connection.cursor()
            cur.execute("DELETE FROM reader WHERE ID ={};".format(ID))
            mysql.connection.commit()
            return redirect("/{}".format(memberType))
    return redirect("/")

@app.route("/friend/delete/<ID>")
def friendDelete(ID):
    if "profile" in session:
        if session["isAdmin"] == True:
            redirect("/")
    else:
        redirect("/")
    email = session["profile"]["email"]
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    Me = cur.fetchone()  
         
    # Only For Users         
    print(ID)
    

    
    cur.execute("DELETE FROM friends WHERE reader_2 ={} AND reader_1 = {} ;".format(ID,Me[0]))
    mysql.connection.commit()
    # return render_template("allFriends.html", pop = 1)
    msg="Friend Table Successfully Updated"
    return redirect("/friends")


@app.route('/books')
def allBooks():
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book;")
    books = cur.fetchall()
    if session['isAdmin']:
        return render_template("allBooksA.html", books=books)
    return render_template("allBooksU.html", books=books)

@app.route("/addFriend", methods=['GET', 'POST'])
def addFriend():
    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect('/')    
    if session["isAdmin"] == True:
        redirect("/")
    if request.method == 'GET':
        return render_template('addFriend.html',msg="")

    data = request.form
    cur = mysql.connection.cursor()
    cur.execute("SELECT ID FROM reader WHERE reader_email='{}'".format(data['email']))
    # cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    friend = cur.fetchall()
    # print(friend)
    if friend == ():
        # print("sorry no friend exits with this email")
        return render_template('addFriend.html', msg="Sorry no user exits with this email")
    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    Me = cur.fetchone()    
    cur.execute("DELETE FROM friends WHERE reader_2 ={} AND reader_1 = {} ;".format(friend[0][0],Me[0]))    
    

    # print(friend[0][0])
    # print(Me[0]) 
    # cur.execute("SELECT COUNT(*) AS total FROM friends WHERE reader_1 ='{friend[0][0]}';")
    # count = cur.fetchall()
    # print("checking that if he is already friend or not")
    # print(count)

    # have to Add cond that they r already frnd
    cur.execute(
            f"insert into friends(reader_1, reader_2) values('{Me[0]}','{friend[0][0]}')")
    mysql.connection.commit()
    return render_template('addFriend.html', msg="Your Friend is successfully added in your friend list")
    # return render_template('addFriend.html')

@app.route("/book", methods=['GET', 'POST'])
def book():
    if request.method == 'GET':
        query = ""
        cur = mysql.connection.cursor()
        cur.execute(
            '''
            SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book WHERE title LIKE '%{}%'
            UNION
            SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book WHERE book_language LIKE '%{}%'
            UNION
            SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book WHERE publisher LIKE '%{}%'
            '''.format(query, query, query)
        )
        books = cur.fetchall()
        if "isAdmin" in session:
            if session["isAdmin"] == True:
                return render_template("adminSearchBook.html", books=books, query=query)
            if session["isAdmin"] == False:
                return render_template("userSearchBook.html", books=books)
                
    if request.method == 'POST':
        data = request.form
        query = data['book']
        cur = mysql.connection.cursor()
        cur.execute(
            '''
            SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book WHERE title LIKE '%{}%'
            UNION
            SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book WHERE book_language LIKE '%{}%'
            UNION
            SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book WHERE publisher LIKE '%{}%'
            '''.format(query, query, query)
        )
        books = cur.fetchall()
        if "isAdmin" in session:
            if session["isAdmin"] == True:
                return render_template("adminSearchBook.html", books=books, query=query)
            if session["isAdmin"] == False:
                return render_template("userSearchBook.html", books=books)
    return redirect("/")

@app.route('/isbn/delete/<isbn>')
def deleteByISBN(isbn):
    if session['isAdmin']:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM book WHERE ISBN = {}".format(isbn))
        mysql.connection.commit()
        return redirect("/books")
    return redirect("/")

@app.route('/isbn/hold/<isbn>')
def holdByISBN(isbn):
    if "profile" in session:
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute("SELECT ID, books_issued, unpaid_fines FROM reader WHERE reader_email = '{}'".format(email))
        [reader_id, books_issued, unpaid_fines] = cur.fetchone()
        if session['isFaculty'] == False and books_issued > 10 or unpaid_fines > 1000:
            return redirect("/")
        cur.execute("UPDATE reader SET books_issued = books_issued+1 WHERE ID={}".format(reader_id))
        cur.execute("UPDATE book SET current_status = 'soldout' WHERE ISBN={}".format(isbn))
        cur.execute("INSERT INTO issue_details VALUES ({}, {}, NOW  (), 0, 0)".format(reader_id, isbn))
        mysql.connection.commit()
        return redirect("/book")
    return redirect("/")

@app.route('/isbn/unhold/<isbn>')
def unholdByISBN(isbn):
    if "profile" in session:
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute("SELECT ID, books_issued FROM reader WHERE reader_email = '{}'".format(email))
        [reader_id, books_issued] = cur.fetchone()
        books_issued -= 1
        if books_issued < 0:
            books_issued = 0
        cur.execute("UPDATE reader SET books_issued = {} WHERE ID={}".format(books_issued, reader_id))
        cur.execute("UPDATE book SET current_status = 'available' WHERE ISBN={}".format(isbn))
        cur.execute("UPDATE issue_details SET book_returned = 1 WHERE ISBN={}".format(isbn))
        mysql.connection.commit()
        return redirect("/book")
    return redirect("/")

@app.route("/logs")
def logs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM issue_details;")
    details = cur.fetchall()
    return render_template("issueDetails.html", details=details)


@app.route("/addBook")
def addBook():
    if request.method == 'GET':
        return render_template("addBook.html")
    else:
        data = request.form
        cur = mysql.connection.cursor()
        cur.execute(
            f"insert into book(title,ISBN,book_language,publisher,publish_date,shelf_id) values('{data['title']}','{data['ISBN']}','{data['language']}','{data['publisher']}','{data['date']}','{data['shelf']}')")
        mysql.connection.commit()
        return render_template("addBook.html")


@app.route("/myBooks")
def myBooks():
    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect("/")
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    person = cur.fetchone()
    cur.execute(
        f"SELECT ISBN,title,avg_rating,book_language,publisher,publish_date,current_status FROM book WHERE ISBN in( SELECT ISBN FROM issue_details WHERE reader_id='{person[0]}')")
    books = cur.fetchall()
    return render_template('myBooks.html', books=books)

@app.route("/shelf")
def shelf():
    if session["isAdmin"] == True:
        cur = mysql.connection.cursor()
        cur.execute(
        "SELECT shelf_id, capacity FROM shelf;")
        shelfs = cur.fetchall()
        return render_template('shelf.html', shelfs = shelfs)
    return redirect("/")

@app.route("/demo")
def demo():
    if "profile" in session:
        email = session["profile"]["email"]
        name = session["profile"]["name"]
    else:
        return "Not signed in <a href='/login'>LOGIN</a>>"
    # Only If he/she is a student
    return render_template("register.html", email=email, name=name)


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
    cur.execute(
        "SELECT reader_name,phone_no,books_issued,ID  FROM reader WHERE ID IN ( SELECT reader_2 FROM friends WHERE reader_1 IN (SELECT ID FROM reader WHERE reader_email='{}') )".format(email))
    friendinfo = cur.fetchall()
    # print(f"SELECT reader_name,phone_no,books_issued FROM reader WHERE ID IN ( SELECT reader_2 FROM friends WHERE reader_1={reader_1[0][0]} )")
    # print(friendinfo[0][2])
    # friend_id = friendinfo[0][2]
    return render_template('allFriends.html', msg="", len=len(friendinfo), friendinfo = friendinfo)

@app.route("/history")
def user_History():
    if "profile" in session:
        email = session["profile"]["email"]
        if session["isAdmin"] == True:
            return redirect("/")
    else:
        return redirect("/")
    # user and logged
    # fetch ID from email of user
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    person = cur.fetchone()
    print(person[0])
    cur.execute(f"SELECT ISBN, borrow_date , book_returned FROM issue_details WHERE reader_id='{person[0]}'")
    data = cur.fetchall()
    return render_template('userHistory.html',data = data)



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
    flash("You were successfully logged in", "info")    
    return redirect('/')


@app.route("/logout")
def logout():
    for key in list(session.keys()):
        session.pop(key)
    flash("You have been logged out", "info")
    return redirect("/")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html')


if __name__ == "__main__":
    if(env == 'dev'):
        app.run(debug=True)
    else:
        app.run()
