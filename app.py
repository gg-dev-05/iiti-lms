from flask import Flask
from flask_mysqldb import MySQL
# import MySQLdb
import yaml
from functions.dbConfig import database_config


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

# mysql = MySQL(app)

@app.route("/")
def home():
	return "HELLO WORLD"

@app.errorhandler(404)
def page_not_found(e):
    print("Page Not Found")
    return render_template('error.html')


if __name__ == "__main__":
    if(env == 'dev'):
        app.run(debug=True)
    else:
        app.run()