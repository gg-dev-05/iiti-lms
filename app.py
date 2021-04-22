from flask import flash, Flask, render_template, redirect, url_for, session, request, Markup
from flask_mysqldb import MySQL
import yaml
from flask_mail import Mail
import smtplib, ssl, re
from functions.dbConfig import database_config
from authlib.integrations.flask_client import OAuth
import os
from datetime import timedelta
from datetime import date


app = Flask(__name__)

env = "dev" if os.environ.get("ENV") != "PROD" else ""
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


port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = os.environ.get("MAIL_USERNAME") if (env != 'dev') else dev['MAIL_USERNAME']  
password = os.environ.get("MAIL_PASSWORD") if (env != 'dev') else dev['MAIL_PASSWORD']  

# Session config
app.secret_key = os.environ.get("client_secret") if(env != 'dev') else dev['client_secret']
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
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * from librarian WHERE librarian_email='{}';".format(email))
        result = cur.fetchall()
        if (result):
            session["isAdmin"] = True
            return render_template('adminHome.html', details=session["profile"])
        else:
            session["isAdmin"] = False
            cur.execute(
                "SELECT is_faculty from reader WHERE reader_email = '{}';".format(email))
            print(
                "SELECT is_faculty from reader WHERE reader_email = '{}';".format(email))
            result = cur.fetchone()
            if result == None:
                return render_template("register.html", email=session['profile']['email'], name=session['profile']['name'])
            else:
                if result[0] == 1:
                    session["isFaculty"] = True
                else:
                    session["isFaculty"] = False
                    cur.execute("SELECT ID FROM reader WHERE reader_email = '{}'".format(email))
                    user_id = cur.fetchone()[0]
                    cur.execute('SELECT reader_name, reader_email, ID FROM friendrequests INNER JOIN reader ON friendrequests.reader_1 = reader.ID WHERE reader_2 = {};'.format(user_id))
                    friendRequests = cur.fetchall()
                    session['friendRequests'] = friendRequests
                    print(session['friendRequests'])
                return render_template('userHome.html', details=session["profile"], friendRequests=friendRequests)

    else:
        return render_template('Login.html')


@app.route("/sendmail")
def generate():
    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect('/')
    cur = mysql.connection.cursor()
    cur.execute(
        f"select return_date, ISBN, reader_id,last_reminder_sent_date from reminders")
    readers = cur.fetchall()
    for reader in readers:
        [return_date, ISBN, reader_id, last_reminder_sent_date] = reader
        cur.execute(f"SELECT reader_email FROM reader WHERE ID='{reader_id}'")
        person_email = cur.fetchone()
        today = date. today()
        delta = (last_reminder_sent_date-today).days
        mail_sent = []
        cur.execute(f"SELECT * FROM book WHERE ISBN='{ISBN}'")
        book=cur.fetchone()
        print(book)
        if abs(delta) % 1 == 0:
            mail_sent.append(reader_id)
            cur.execute(f"update reminders set last_reminder_sent_date='{today}' where ISBN='{ISBN}'")
            send_mail(person_email[0], "Subject: Reminder for returning book\n\n Your book, {} is overdue.Kindly return it.".format(book[0]))
            flash("Mail sent to {}".format(person_email[0]))
        print(mail_sent)
    return redirect('/')
# Register new student


def send_mail(receiver_email, message):
    print("Sending mail to " + receiver_email)
    print(message)
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)

@app.route("/new", methods=["POST"])
def newStudent():
    data = request.form
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO reader (reader_name, reader_email, reader_address, phone_no, is_faculty) VALUES ('{}', '{}', '{}', {}, {});".format(
        data['Name'], data['Email'], data['Address'], data['Number'], 0))
    mysql.connection.commit()
    return redirect("/")


@app.route("/<memberType>")
def members(memberType):
    if memberType == 'students':
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT reader_name, reader_email, reader_address, phone_no, books_issued, unpaid_fines,ID FROM reader WHERE is_faculty = 0;")
        students = cur.fetchall()
        return render_template("students.html", students=students, details=session["profile"])
    if memberType == 'faculties':
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT reader_name, reader_email, reader_address, phone_no, books_issued, unpaid_fines,ID FROM reader WHERE is_faculty = 1;")
        faculties = cur.fetchall()
        return render_template("faculties.html", faculties=faculties, details=session["profile"])
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
    # print(ID)

    cur.execute(
        "DELETE FROM friends WHERE reader_2 ={} AND reader_1 = {} ;".format(ID, Me[0]))
    cur.execute(
        "DELETE FROM friends WHERE reader_2 ={} AND reader_1 = {} ;".format(Me[0], ID))
    mysql.connection.commit()
    # return render_template("allFriends.html", pop = 1)
    msg = "Friend Table Successfully Updated"
    return redirect("/friends")





@app.route("/addFriend", methods=['GET', 'POST'])
def addFriend():
    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect('/')
    if session["isAdmin"] == True:
        redirect("/")
    if request.method == 'GET':
        return render_template('addFriend.html',msg="", details=session["profile"])

    data = request.form
    if data['email'] == email:
        return render_template("addFriend.html", msg="Enter e-mail address of your friend")
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT ID FROM reader WHERE reader_email='{}'".format(data['email']))
    friend = cur.fetchall()
    cur.execute("SELECT * FROM friends WHERE reader_1='{}' AND reader_2='{}'".format(email, data['email']))
    print("HERE: ", cur.fetchone())
    if cur.fetchone() != None:
        return render_template('addFriend.html', msg="You are already friends with {}".format(data['email']), details=session["profile"])
    if friend == ():
        return render_template('addFriend.html', msg="Sorry no user exits with this email", details=session["profile"])
    else:
        friend = friend[0][0]

    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    Me = cur.fetchone()[0]
    cur.execute("INSERT INTO friendrequests VALUES ({}, {});".format(Me, friend))
    mysql.connection.commit()
    return render_template('addFriend.html', msg="Friend request sent to {}".format(data['email']), details=session["profile"])
    # return render_template('addFriend.html')

@app.route("/request/cnf/<ID>")
def accept_request(ID):
    if "profile" in session:
        if session["isAdmin"] == True:
            return redirect("/")
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute("SELECT ID FROM reader WHERE reader_email = '{}'".format(email))
        reader_id = cur.fetchone()[0]
        cur.execute("DELETE FROM friendrequests WHERE reader_1 = {} AND reader_2 = {}".format(ID, reader_id))
        cur.execute("INSERT INTO friends VALUES ({}, {});".format(reader_id, ID))
        cur.execute("INSERT INTO friends VALUES ({}, {});".format(ID, reader_id))
        mysql.connection.commit()
        flash("Friend request accepted")
        return redirect("/friends")
    return redirect("/")

@app.route("/request/del/<ID>")
def delete_request(ID):
    if "profile" in session:
        if session["isAdmin"] == True:
            return redirect("/")
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute("SELECT ID FROM reader WHERE reader_email = '{}'".format(email))
        reader_id = cur.fetchone()[0]
        cur.execute("DELETE FROM friendrequests WHERE reader_1 = {} AND reader_2 = {}".format(ID, reader_id))
        mysql.connection.commit()
        flash("Friend request deleted")
        return redirect("/friends")
    return redirect("/")

@app.route("/book", methods=['GET', 'POST'])
def book():
    if request.method == 'GET':
        query = ""
        cur = mysql.connection.cursor()
        cur.execute(
            'SELECT ISBN, title, shelf_id, current_status, avg_rating, book_language, publisher, publish_date FROM book')
        books = cur.fetchall()
        if "isAdmin" in session:
            if session["isAdmin"] == True:
                flash("Showing all books")
                return render_template("adminSearchBook.html", books=books, details=session["profile"])
            if session["isAdmin"] == False:
                return render_template("userSearchBook.html", books=books, details=session["profile"])
                
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
        print("is admin: ", session['isAdmin'])
        if "isAdmin" in session:
            if session["isAdmin"] == True:
                flash(Markup("Showing all books LIKE <b>{}</b>".format(query)))
                return render_template("adminSearchBook.html", books=books, details=session["profile"])
            if session["isAdmin"] == False:
                return render_template("userSearchBook.html", books=books, details=session["profile"])
    return redirect("/")


@app.route('/isbn/delete/<isbn>')
def deleteByISBN(isbn):
    if session['isAdmin']:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM book WHERE ISBN = {}".format(isbn))
        flash("Book successfully deleted")
        mysql.connection.commit()
        return redirect("/book")
    return redirect("/")


@app.route('/isbn/hold/<isbn>')
def holdByISBN(isbn):
    if "profile" in session:
        if session["isAdmin"] == True:
            return redirect("/")
        # Only for readers
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT ID, books_issued, unpaid_fines FROM reader WHERE reader_email = '{}'".format(email))
        [reader_id, books_issued, unpaid_fines] = cur.fetchone()
        if session['isFaculty'] == False and books_issued > 3 or unpaid_fines > 1000:
            if books_issued > 3:
                flash(
                    "You already have issued 3 books so now you cannot issue more", "info")
            else:
                flash("Please pay you unpaid fines first", "info")
            return redirect("/")
        cur.execute(
            "UPDATE reader SET books_issued = books_issued+1 WHERE ID={}".format(reader_id))
        cur.execute(
            "UPDATE book SET current_status = 'soldout' WHERE ISBN={}".format(isbn))
        cur.execute("INSERT INTO issue_details VALUES ({}, {}, CURDATE(),0,0)".format(
            reader_id, isbn))
        mysql.connection.commit()
        return redirect("/book")
    return redirect("/")


@app.route('/isbn/putOnhold/<isbn>')
def putOnHoldByISBN(isbn):
    if "profile" in session:
        if session["isAdmin"] == True:
            return redirect("/")
        # Only for readers
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT ID, books_issued, unpaid_fines FROM reader WHERE reader_email = '{}'".format(email))
        [reader_id, books_issued, unpaid_fines] = cur.fetchone()
        if session['isFaculty'] == False and books_issued > 3 or unpaid_fines > 1000:
            if books_issued > 3:
                flash(
                    "You already have issued 3 books.You cannot put the book on hold", "info")
            else:
                flash("Please pay you unpaid fines first", "info")
            return redirect("/")
        cur.execute(
            "UPDATE book SET current_status = 'hold' WHERE ISBN={}".format(isbn))
        cur.execute(
            "INSERT INTO  holds VALUES ({}, {},NOW())".format(isbn, reader_id))
        mysql.connection.commit()
        return redirect("/book")
    return redirect("/")


@app.route('/isbn/unhold/<isbn>')
def unholdByISBN(isbn):
    if "profile" in session:
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT ID, books_issued FROM reader WHERE reader_email = '{}'".format(email))
        [reader_id, books_issued] = cur.fetchone()
        books_issued -= 1
        if books_issued < 0:
            books_issued = 0
        cur.execute("UPDATE reader SET books_issued = {} WHERE ID={}".format(
            books_issued, reader_id))
        cur.execute(
            "select current_status from book WHERE ISBN={}".format(isbn))
        [current_status] = cur.fetchone()
        # if current_status=="hold":
        #     redirect("/isbn/hold/<isbn>")
        cur.execute(
            "UPDATE book SET current_status = 'available' WHERE ISBN={}".format(isbn))
        cur.execute(
            "UPDATE issue_details SET book_returned = 1 WHERE ISBN={}".format(isbn))
        mysql.connection.commit()
        return redirect("/book")
    return redirect("/")


@app.route("/logs")
def logs():
    if "profile" in session:
        if session["isAdmin"] == False:
            return redirect("/")
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM issue_details;")
        details = cur.fetchall()
        return render_template("issueDetails.html", details=details)
    return redirect("/")

@app.route("/previousReadings")
def previousReadings():
    if "profile" in session:
        if session["isAdmin"] == True:
            return redirect("/")
        email = session["profile"]["email"]
        cur = mysql.connection.cursor()
        cur.execute('''
        SELECT book.ISBN, title, avg_rating, borrow_date FROM issue_details
        INNER JOIN reader ON issue_details.reader_id = reader.ID
        INNER JOIN book ON issue_details.ISBN = book.ISBN
        WHERE
        reader_email = "{}";
        '''.format(email))
        details = cur.fetchall()
        return render_template("issueDetailsU.html", details=session["profile"], issueDetails=details)
    return redirect("/")


@app.route("/addBook", methods=['GET', 'POST'])
def addBook():
    if request.method == 'GET':
        return render_template("addBook.html", details=session["profile"])
    else:
        data = request.form
        cur = mysql.connection.cursor()
        cur.execute(
            f"insert into book(title,ISBN,book_language,publisher,publish_date,shelf_id) values('{data['title']}','{data['ISBN']}','{data['language']}','{data['publisher']}','{data['date']}','{data['shelf']}')")
        mysql.connection.commit()

        if data['tag1'] != '':
            cur = mysql.connection.cursor()
            cur.execute(
                f"insert into tags values('{data['ISBN']}','{data['tag1']}')")
            mysql.connection.commit()
        if data['tag2'] != '':
            cur = mysql.connection.cursor()
            cur.execute(
                f"insert into tags values('{data['ISBN']}','{data['tag2']}')")
            mysql.connection.commit()
        if data['tag3'] != '':
            cur = mysql.connection.cursor()
            cur.execute(
                f"insert into tags values('{data['ISBN']}','{data['tag3']}')")
            mysql.connection.commit()
        return render_template("addBook.html", details=session["profile"])
    
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
        f"SELECT ISBN,title,avg_rating,book_language,publisher,publish_date,current_status FROM book WHERE ISBN in( SELECT ISBN FROM issue_details WHERE reader_id='{person[0]}' and book_returned=0)")
    books = cur.fetchall()
    return render_template('myBooks.html', books=books, details=session["profile"])



@app.route("/shelf")
def shelf():
    if session["isAdmin"] == True:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT shelf_id, capacity FROM shelf;")
        shelfs = cur.fetchall()

        return render_template('shelf.html', shelfs = shelfs, details=session["profile"])
    return redirect("/")


@app.route("/demo")
def demo():
    if "profile" in session:
        email = session["profile"]["email"]
        name = session["profile"]["name"]
    else:
        return "Not signed in <a href='/login'>LOGIN</a>>"
    # Only If he/she is a student
    return render_template("register.html", email=email, name=name, details=session["profile"])


@app.route("/recommendedBooks")
def user_BookRecommedation():

    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect("/")
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT ID FROM reader WHERE reader_email='{email}'")
    person = cur.fetchone()
    cur.execute(
        f"select * from book where ISBN in(select ISBN from tags where tag_name in(select tag_name from tags where ISBN in (select ISBN from issue_details where reader_id = '{person[0]}'))) order by avg_rating DESC")
    books = cur.fetchall()
    # cur = mysql.connection.cursor()
    # cur.execute(
    #     f"select tag_name from tags where ISBN in (select ISBN from issue_details where reader_id='{person[0]}'")
    # tags = cur.fetchall()
    # print(tags)
    print(books)
    zeroes = 1 if len(books) == 0 else 0
    return render_template('user_BookRecommedation.html', books=books, zeroes=zeroes, details=session["profile"])



@ app.route("/booksWithTags")
def user_booksWithTags():
    return render_template('booksWithTags.html', details=session["profile"])


@ app.route("/friends")
def friends():
    if "profile" in session:
        email = session["profile"]["email"]
    else:
        return redirect("/")

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT reader_name,phone_no,books_issued,ID  FROM reader WHERE ID IN ( SELECT reader_2 FROM friends WHERE reader_1 IN (SELECT ID FROM reader WHERE reader_email='{}') )".format(email))
    friendinfo = cur.fetchall()

    return render_template('allFriends.html', len=len(friendinfo), friendinfo=friendinfo, details=session["profile"])


@ app.route("/feedback")
def feedback():
    return render_template('userFeedback.html')


@ app.route("/history")
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
    cur.execute(
        f"SELECT ISBN, borrow_date , book_returned FROM issue_details WHERE reader_id='{person[0]}'")
    data = cur.fetchall()

    return render_template('userHistory.html',data = data, details=session["profile"])



@ app.route("/test")
def updateBooks():
    return render_template('updateBooks.html', details=session["profile"])


@ app.route("/tables")
def addBooks():
    return render_template('tables.html', details=session["profile"])


@ app.route("/dashboard")
def dashboard():
    return render_template('dashboard.html', details=session["profile"])


@ app.route('/login')
def login():
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@ app.route('/authorize')
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


@ app.route("/logout")
def logout():
    for key in list(session.keys()):
        session.pop(key)
    flash("You have been logged out", "info")
    return redirect("/")


@ app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html')


if __name__ == "__main__":
    if(env == 'dev'):
        app.run(debug=True)
    else:
        app.run()
