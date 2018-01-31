from flask import Flask, render_template, request, make_response, redirect
from flask_sqlalchemy import SQLAlchemy
from stravalib.client import Client
from flask_googlemaps import GoogleMaps, Map
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from measurement.measures import Speed, Time
from decimal import getcontext, Decimal
import pygal


app = Flask(__name__)
# app.config['GOOGLEMAPS_KEY'] = "AIzaSyBUV6YEpG7xjxJ8s9ZjIZP8A56L4TxAK7k"
app.config['GOOGLEMAPS_KEY'] = "AIzaSyCiforLtPDvDY3WzkKeWc2ykgR_Aw9rYk0"
GoogleMaps(app)


# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql2206541:yS3*wS7%@sql2.freemysqlhosting.net:3306/sql2206541'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="GregorySloggett",
    password="Xavi6legend",
    hostname="GregorySloggett.mysql.pythonanywhere-services.com",
    databasename="GregorySloggett$access_tokens",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


app.config.update(dict(
    SECRET_KEY="powerful secretkey",
    WTF_CSRF_SECRET_KEY="a csrf secret key"
))

db = SQLAlchemy(app)


class MyForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])


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
    # check = request.cookies.get('username')
    # if 'username' in request.cookies:
    #     check_access_tokens_database = AccessTokens.query.filter_by(name=check).first()
    #     if not check_access_tokens_database:
    #         return render_template("homepage.html")
    #     else:
    #         client.access_token = check_access_tokens_database.access_token
    #         return render_template("return_user.html", athlete=client.get_athlete(),
    #                     athlete_stats=client.get_athlete_stats(), athlete_profiler=client.get_athlete().profile)
    # else:
    #     return render_template("homepage.html")

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("return_user.html", athlete=client.get_athlete(),
                               athlete_stats=client.get_athlete_stats(), athlete_profiler=client.get_athlete().profile)


def check_for_cookie():
    check = request.cookies.get('username')
    if 'username' in request.cookies:
        check_access_tokens_database = AccessTokens.query.filter_by(name=check).first()
        if not check_access_tokens_database:
            return False
        else:
            client.access_token = check_access_tokens_database.access_token
            return True
    else:
        return False

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
        resp = make_response(render_template("response_url.html", athlete_access_token=athlete_access_token, athlete=athlete,
                                             athlete_stats=client.get_athlete_stats(), athlete_profiler=athlete.profile))
        resp.set_cookie('username', client.get_athlete().username)
        return resp
    else:
        print('user exists already')
        resp = make_response(render_template("return_user.html", athlete_access_token=athlete_access_token, athlete=athlete,
                                             athlete_stats=client.get_athlete_stats(), athlete_profiler=athlete.profile))
        resp.set_cookie('username', client.get_athlete().username)
        return resp


@app.route('/summary/', methods=['GET', 'POST'])
def summary():
    # accessed_athlete_activities_list = requests.get('https://www.strava.com/api/v3/athlete/activities',
    #                                                 data={'access_token': client.access_token})
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("summary.html", athlete=client.get_athlete(), athlete_stats=client.get_athlete_stats(),
                               last_ten_rides=last_ten_rides(), athlete_profiler=client.get_athlete().profile)


# If the user has already authorized the application this is the page that will be returned (instead of response_url).
@app.route('/return_user/', methods=['GET', 'POST'])
def return_user():
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("return_user.html", athlete=client.get_athlete(), athlete_stats=client.get_athlete_stats())


@app.route('/activity/<activity_id>', methods=['GET', 'POST'])
def activity(activity_id):
    # activity_photos = client.get_activity(activity_id=1341714581).full_photos
    #activity_photos = client.get_activity_photos(activity_id=activity_id, only_instagram=False)

    types = ['time', 'latlng', 'altitude', 'heartrate', 'temp', ]

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("activity.html", athlete=client.get_athlete(),
                               athlete_profiler=client.get_athlete().profile,
                               activity_data=client.get_activity(activity_id=activity_id, include_all_efforts=True),
                               athlete_stats=client.get_athlete_stats(),
                               streams=client.get_activity_streams(activity_id=activity_id, types=types, resolution='medium'))


@app.route('/activity/<activity_id>/<activity_map>', methods=['GET', 'POST'])
def map(activity_id, activity_map):
    types = ['time', 'latlng', 'altitude', 'heartrate', 'temp', ]

    # creating a map in the view
    mymap = Map(
        identifier="view-side",
        lat=37.4419,
        lng=-122.1419,
        markers=[(37.4419, -122.1419)]
    )
    sndmap = Map(
        identifier="sndmap",
        lat=37.4419,
        lng=-122.1419,
        markers=[
            {
                'icon': 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                'lat': 37.4419,
                'lng': -122.1419,
                'infobox': "<b>Hello World</b>"
            },
            {
                'icon': 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                'lat': 37.4300,
                'lng': -122.1400,
                'infobox': "<b>Hello World from other place</b>"
            }
        ]
    )
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        print(client.get_activity(activity_id).start_latitude)
        print(client.get_activity(activity_id).start_longitude)
        return render_template("map.html", activity_data=client.get_activity(activity_id=activity_id),
                               mymap=mymap, sndmap=sndmap,
                               streams=client.get_activity_streams(activity_id=activity_id, types=types, resolution='medium'))


@app.route('/marathon/')
def marathon():
    form = MyForm()
    line_chart = pygal.Line()  # Then create a bar graph object
    line_chart.add('Fibonacci', [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55])  # Add some values
    line_chart.x_labels = ['0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2']
    line_chart.y_labels = '0', '2', '4', '6', '8', '10'
    line_chart = line_chart.render_data_uri()

    bar_chart = pygal.Bar()
    bar_chart.add('Fibonacci', [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55])  # Add some values
    bar_chart.x_labels = '0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2'
    bar_chart.y_labels = '0', '2', '4', '6', '8', '10'
    bar_chart = bar_chart.render_data_uri()
    return render_template('marathon.html', form=form, line_chart=line_chart, bar_chart=bar_chart)


@app.route('/marathon/', methods=['POST'])
def marathon_time_retrieval():

    marathon_time = request.form['marathon-time']
    getcontext().prec = 3

    line_chart = pygal.Line()  # Then create a bar graph object
    line_chart.x_labels = ('0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2')
    bar_chart = pygal.Bar()
    bar_chart.x_labels = '0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2'

    count = marathon_time.count(':')

    if True:
        try:
            if count == 2:
                hours, minutes, seconds = marathon_time.split(':')
                hours = int(hours)
                minutes = int(minutes)
                seconds = int(seconds)
            else:
                hours, minutes = marathon_time.split(':')
                hours = int(hours)
                minutes = int(minutes)

            total_minutes = int(hours * 60 + minutes)
            kilometer__minute = (Decimal(42.195) / Decimal(total_minutes))
            try:
                pace = Speed(kilometer__minute = (Decimal(42.195) / Decimal(total_minutes)))
            except ZeroDivisionError:
                pace = 0

            kilometres_per_minute = Decimal(1)/Decimal(kilometer__minute)
            line_chart.add("pace line chart", [kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
                           kilometres_per_minute, kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
                           kilometres_per_minute, kilometres_per_minute, kilometres_per_minute])
            line_chart = line_chart.render_data_uri()

            bar_chart.add("pace bar chart", [kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
                           kilometres_per_minute, kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
                           kilometres_per_minute, kilometres_per_minute, kilometres_per_minute])
            bar_chart = bar_chart.render_data_uri()

            if count == 2:
                return render_template('marathon.html', marathon_time=marathon_time, hours=hours, minutes=minutes,
                                       seconds=seconds, total_minutes=total_minutes, pace=pace, line_chart=line_chart,
                                       kilometres=kilometres_per_minute, bar_chart=bar_chart)
            else:
                return render_template('marathon.html', marathon_time=marathon_time, hours=hours, minutes=minutes,
                                       seconds="0", total_minutes=total_minutes, pace=pace, line_chart=line_chart,
                                       kilometres=kilometres_per_minute, bar_chart=bar_chart)
        except ValueError:
            print("problem")
            this = False


def calculate_pace():
    pace = 0

    return pace


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
