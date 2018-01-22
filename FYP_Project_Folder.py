import random
import string

from flask import Flask, render_template, request, make_response
from flask_sqlalchemy import SQLAlchemy
from stravalib.client import Client
import requests

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql2206541:yS3*wS7%@sql2.freemysqlhosting.net:3306/sql2206541'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
#     username="GregorySloggett",
#     password="Xavi6legend",
#     hostname="GregorySloggett.mysql.pythonanywhere-services.com",
#     databasename="GregorySloggett$access_tokens",
# )
# app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
# app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class AccessTokens(db.Model):
    __tablename__ = "access_tokens"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    access_token = db.Column(db.String(40))


MY_ACCESS_TOKEN = 'a6e5a504f806ed79c8a6e25f59da056b440faac5'
MY_CLIENT_ID = 20518
MY_CLIENT_SECRET = 'cf516a44b390c99b6777f771be0103314516931e'
STR_LENGTH=6
client = Client()

# Home page of my application.
@app.route('/', methods=['GET', 'POST'])
def homepage():
    check = request.cookies.get('username')
    if 'username' in request.cookies:
        check_access_tokens_database = AccessTokens.query.filter_by(name=check).first()
        if not check_access_tokens_database:
            return render_template("homepage.html")
        else:
            client.access_token = check_access_tokens_database.access_token
            return render_template("return_user.html", athlete=client.get_athlete(),
                               athlete_stats=client.get_athlete_stats())
    else:
        return render_template("homepage.html")

# The response page that the user is presented with when they authorize the app for the first time.
@app.route('/response_url/', methods=['GET', 'POST'])
def response_url():
    error = request.args.get('error')
    if error == 'access_denied':
        return render_template("access_denied.html", methods=['GET', 'POST'])

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
        signature = AccessTokens(name=athlete.username, access_token=athlete_access_token)
        db.session.add(signature)
        db.session.commit()
        photo = athlete.profile

        resp = make_response(render_template("response_url.html", athlete_access_token=athlete_access_token, athlete=athlete,
                               athlete_stats=client.get_athlete_stats(), photo=photo))
        resp.set_cookie('username', client.get_athlete().username)
        return resp
    else:
        print('user exists already')
        photo = athlete.profile
        resp = make_response(render_template("return_user.html", athlete_access_token=athlete_access_token, athlete=athlete,
                               athlete_stats=client.get_athlete_stats(), photo=photo))
        resp.set_cookie('username', client.get_athlete().username)
        return resp


@app.route('/summary/', methods=['GET', 'POST'])
def summary():
    athlete = client.get_athlete()

    athlete_profiler = athlete.profile
    # accessed_athlete_activities_list = requests.get('https://www.strava.com/api/v3/athlete/activities',
    #                                                 data={'access_token': client.access_token})

    return render_template("summary.html", athlete=athlete, athlete_stats=client.get_athlete_stats(),
                           last_ten_rides=last_ten_rides(), athlete_profiler=athlete_profiler)


# If the user has already authorized the application this is the page that will be returned (instead of response_url).
@app.route('/return_user/', methods=['GET', 'POST'])
def return_user():
    username = request.cookies.get('username')

    return render_template("return_user.html", athlete=client.get_athlete(), athlete_stats=client.get_athlete_stats())


@app.route('/activity/<activity_id>', methods=['GET', 'POST'])
def activity(activity_id):
    athlete = client.get_athlete()
    activity_data = client.get_activity(activity_id=1341714581)
    # activity_photos = client.get_activity(activity_id=1341714581).full_photos
    activity_photos = client.get_activity_photos(activity_id=1341714581, only_instagram=False)

    athlete_profiler = athlete.profile
    return render_template("activity.html", activity_id_number=activity_id, activity_photos=activity_photos,
                           athlete=athlete, athlete_profiler=athlete_profiler, activity_data=activity_data, athlete_stats=client.get_athlete_stats())


# This displays some details on the summary page of the users last ten rides (ID, Name, Distance)
def last_ten_rides():
    activity_list = []
    i = 0
    for activity in client.get_activities(limit=10):
        i += 1
        activity_id = i, u'{0.id}'.format(activity), u'{0.name}'.format(activity), u'{0.distance}'.format(activity)
        activity_list.append(activity_id)

   # assert len(list(activity_list)) == 10

    print(*activity_list, sep='\n')

    return activity_list




if __name__ == '__main__':
    app.run(debug=True)
