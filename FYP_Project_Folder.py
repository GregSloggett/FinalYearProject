from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from stravalib.client import Client


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql2206541:yS3*wS7%@sql2.freemysqlhosting.net:3306/sql2206541'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class AccessTokens(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    access_token = db.Column(db.String(40))


MY_ACCESS_TOKEN = 'a6e5a504f806ed79c8a6e25f59da056b440faac5'
MY_CLIENT_ID = 20518
MY_CLIENT_SECRET = 'cf516a44b390c99b6777f771be0103314516931e'
client = Client()

# Home page of my application.
@app.route('/', methods=['GET', 'POST'])
def homepage():



    return render_template("homepage.html")


# The response page that the user is presented with when they authorize the app for the first time.
@app.route('/response_url/')
def response_url():
    error = request.args.get('error')
    if error == 'access_denied':
        return render_template("access_denied.html")

    code = request.args.get('code')
    athlete_access_token = client.exchange_code_for_token(client_id=MY_CLIENT_ID,
                                                          client_secret=MY_CLIENT_SECRET, code=code)

    # athlete_access_token = 'cc1a2bde123b3868d588fdee5ddec8f1da595903'  ##DELETE THIS LINE TO REMOVE IAN M ACCESS

    client.access_token = athlete_access_token
    athlete = client.get_athlete()

    check_code = athlete_access_token
    check_access_token = AccessTokens.query.filter_by(access_token=check_code).first()
    if not check_access_token:
        print('user does not exist already')
        signature = AccessTokens(name=athlete.firstname, access_token=athlete_access_token)
        db.session.add(signature)
        db.session.commit()
    else:
        print('user exists already')

    return render_template("response_url.html")


@app.route('/summary/')
def summary():

    return render_template("summary.html")


# If the user has already authorized the application this is the page that will be returned (instead of response_url).
@app.route('/return_user/')
def return_user():

    return render_template("return_user.html")


if __name__ == '__main__':
    app.run(debug=True)
