from flask import Flask,flash, render_template, redirect, url_for, session
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
    DATABASE_URL  = dev['CLEARDB_DATABASE_URL']
    print(DATABASE_URL)

else:
    DATABASE_URL  = os.environ.get("CLEARDB_DATABASE_URL")

user, password, host, db = database_config(DATABASE_URL)

app.config['MYSQL_HOST'] = host
app.config['MYSQL_USER'] = user
app.config['MYSQL_PASSWORD'] = password
app.config['MYSQL_DB'] = db
print(host, user, password, db)
# Session config
app.secret_key = dev['client_secret']
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

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
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only needed if using openId to fetch user info
    client_kwargs={'scope': 'openid email profile'},
)


@app.route("/")
def home():
    # cur = mysql.connection.cursor()
    # cur.execute(
    #     "SELECT * FROM librarian;"
    # )
    # print(cur.fetchall())
    return render_template('dashboard.html')

@app.route("/test")
def updateBooks():
    # cur = mysql.connection.cursor()
    # cur.execute(
    #     "SELECT * FROM librarian;"
    # )
    # print(cur.fetchall())
    return render_template('updateBooks.html')


@app.route("/tables")
def addBooks():
    # cur = mysql.connection.cursor()
    # cur.execute(
    #     "SELECT * FROM librarian;"
    # )
    # print(cur.fetchall())
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
    token = google.authorize_access_token()  # Access token from google (needed to get user info)
    resp = google.get('userinfo')  # userinfo contains stuff u specificed in the scrope
    user_info = resp.json()
    user = oauth.google.userinfo()  
    session['profile'] = user_info
    session.permanent = True  # make the session permanant so it keeps existing after browser gets closed
    signedIn = dict(session).get("signedIn", None)
    if token!='':  
        message = 'You were successfully logged in';
    else:
        message = 'You Please Try Again';
    # return render_template('index.html', message=message)    
    return redirect('/')


@app.errorhandler(404)
def page_not_found(e):
    # print("Page Not Found")
    return render_template('error.html')


if __name__ == "__main__":
    if(env == 'dev'):
        app.run(debug=True)
    else:
        app.run()