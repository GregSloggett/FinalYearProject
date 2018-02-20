from flask import Flask, render_template, request, make_response, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.testing.pickleable import User
from stravalib.client import Client
from flask_googlemaps import GoogleMaps, Map
from wtforms import Form, StringField, PasswordField, BooleanField, SubmitField, IntegerField, TextField, validators
from wtforms.validators import DataRequired
from measurement.measures import Speed, Time
from decimal import getcontext, Decimal
import pygal
import math

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

class AccessTokens(db.Model):
    __tablename__ = "access_tokens"
    athlete_id = db.Column(db.String(11), primary_key=True)
    access_token = db.Column(db.String(40))
    email_address = db.column(db.String(40))


class UserBestTimes(db.Model):
    __tablename__ = "user_best_times"
    athlete_id = db.Column(db.String(11), primary_key=True)
    fifteenHundred = db.Column(db.Time)
    oneMile = db.Column(db.Time)
    threeKilometre = db.Column(db.Time)
    fiveKilometre = db.Column(db.Time)
    fiveMile = db.Column(db.Time)
    tenKilometre = db.Column(db.Time)
    tenMile = db.Column(db.Time)
    halfMarathon = db.Column(db.Time)
    marathon = db.Column(db.Time)


class ReusableForm(Form):
    race_length = TextField('Race Length:', validators=[validators.required()])
    hours = IntegerField('Hours:')
    minutes = IntegerField('Minutes:')
    seconds = IntegerField('Seconds:')
    email = TextField('Email:')
    password = TextField('Password:')


#
# class EstimateMarathon(FlaskForm):
#     estimate_time = IntegerField('Estimate', [validators.Required()])


# class PredictMarathon(FlaskForm):
#     athlete_id = StringField('Athlete_ID', [validators.Length(min=1, max = 12)])
#     password = PasswordField('Password', [
#         validators.Required(),
#         validators.EqualTo('confirm_password', message='Passwords do not match')
#     ])
#     confirm_password = PasswordField('Confirm Password')
#     email = TextField('Email', [validators.Length(min=6, max=35)])


MY_ACCESS_TOKEN = 'a6e5a504f806ed79c8a6e25f59da056b440faac5'
MY_CLIENT_ID = 20518
MY_CLIENT_SECRET = 'cf516a44b390c99b6777f771be0103314516931e'
STR_LENGTH=6
client = Client()


# Home page of my application.
@app.route('/', methods=['GET', 'POST'])
def homepage():
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("return_user.html", athlete=client.get_athlete(),
                               athlete_stats=client.get_athlete_stats(), athlete_profiler=client.get_athlete().profile,
                               last_activity_id=last_activity())


def check_for_cookie():
    check = request.cookies.get('athlete_id')
    if 'athlete_id' in request.cookies:
        check_access_tokens_database = AccessTokens.query.filter_by(athlete_id=check).first()
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

    client.access_token = athlete_access_token
    athlete = client.get_athlete()
    check_code = athlete_access_token
    check_access_token = AccessTokens.query.filter_by(access_token=check_code).first()
    if not check_access_token:
        signature = AccessTokens(athlete_id=str(athlete.id), access_token=athlete_access_token)
        db.session.add(signature)
        db.session.commit()
        resp = make_response(render_template("response_url.html", athlete_access_token=athlete_access_token, athlete=athlete,
                                             athlete_stats=client.get_athlete_stats(), athlete_profiler=athlete.profile,
                                             last_activity_id=last_activity()))
        resp.set_cookie('athlete_id', str(athlete.id))
        return resp
    else:
        resp = make_response(render_template("return_user.html", athlete_access_token=athlete_access_token, athlete=athlete,
                                             athlete_stats=client.get_athlete_stats(), athlete_profiler=athlete.profile,
                                             last_activity_id=last_activity()))
        resp.set_cookie('athlete_id', str(athlete.id))
        return resp


@app.route('/summary/', methods=['GET', 'POST'])
def summary():
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        total_rides = 0
        total_runs = 0

        first_activity = ''

        for activity in client.get_activities(before="2018-02-03T00:00:00Z",
                                              after="2000-05-10T00:00:00Z", limit=None):
            first_activity_id = activity.id

            if activity.type == 'Ride':
                total_rides = total_rides + 1
            elif activity.type == 'Run':
                total_runs = total_runs + 1

            first_activity = client.get_activity(activity_id=first_activity_id)

        pie_chart = pygal.Pie()  # Then create a bar graph object
        pie_chart.add('Rides', total_rides)  # Add some values
        pie_chart.add('Runs', total_runs)  # Add some values
        pie_chart = pie_chart.render_data_uri()
        return render_template("summary.html", athlete=client.get_athlete(), athlete_stats=client.get_athlete_stats(),
                               last_ten_rides=last_ten_rides(), athlete_profiler=client.get_athlete().profile,
                               pie_chart=pie_chart, first_activity=first_activity, activities_2017=activities_2017(),
                               activities_2018=activities_2018())


# If the user has already authorized the application this is the page that will be returned (instead of response_url).
@app.route('/return_user/', methods=['GET', 'POST'])
def return_user():

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("return_user.html", athlete=client.get_athlete(),
                               athlete_profiler=client.get_athlete().profile, athlete_stats=client.get_athlete_stats(),
                               last_activity_id=last_activity())


@app.route('/activity/<activity_id>', methods=['GET', 'POST'])
def activity(activity_id):
    types = ['time', 'latlng', 'altitude', 'heartrate', 'temp', 'distance', 'elevation']

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:

        dist_time = client.get_activity_streams(activity_id=activity_id, types=['distance', 'time'],
                                                resolution='medium')
        elevation = client.get_activity_streams(activity_id=activity_id, types=['elevation'],
                                                resolution='medium')
        times = []
        distances = []
        count = 0
        check_count = 0
        for each in dist_time['distance'].data:

            # if each % 1000 <= 5:
            times.append(dist_time['time'].data[count])
            distances.append(dist_time['distance'].data[count])
            count += 1

    line_chart = pygal.Line()  # Then create a bar graph object
    # line_chart.x_labels = ['0', '1000', '2000', '3000', str(distances[-1])]
    line_chart.add('Distance', distances)  # Add some values
    line_chart.add('Time', times)  # Add some values
    line_chart = line_chart.render_data_uri()

    return render_template("activity.html", athlete=client.get_athlete(),
                           athlete_profiler=client.get_athlete().profile,
                           activity_data=client.get_activity(activity_id=activity_id, include_all_efforts=True),
                           athlete_stats=client.get_athlete_stats(),
                           streams=client.get_activity_streams(activity_id=activity_id, types=types,
                                                               resolution='medium'), line_chart=line_chart)


@app.route('/activity/<activity_id>/<activity_map>', methods=['GET', 'POST'])
def map(activity_id, activity_map):
    types = ['time', 'latlng', 'altitude', 'heartrate', 'temp', ]

    line_chart = pygal.Line()  # Then create a bar graph object
    line_chart.add('Fibonacci', [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55])  # Add some values
    line_chart.x_labels = ['0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2']
    line_chart.y_labels = '0', '2', '4', '6', '8', '10'
    line_chart = line_chart.render_data_uri()

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("map.html", activity_data=client.get_activity(activity_id=activity_id),
                               streams=client.get_activity_streams(activity_id=activity_id, types=types, resolution='medium'),
                               line_chart=line_chart)


@app.route('/marathon/', methods=['GET', 'POST'])
def marathon():
    form = ReusableForm(request.form)
    predicted_marathon_time = 0
    # print(form.errors)
    getcontext().prec = 3

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

    if request.method == 'POST':
        race_type = request.form['race_length']
        hours = request.form['race_time_hours']
        minutes = request.form['race_time_minutes']
        seconds = request.form['race_time_seconds']
        # if hours == 'hours':
        #     hours = 0
        # if minutes == 'minutes':
        #     minutes = 0
        # if seconds == 'seconds':
        #     seconds = 0

        print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

        if form.validate():
            # Save the comment here.
            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            distance_run = race_distances(race_type)
            time_run = get_sec(hours, minutes, seconds)
            pace = get_pace(distance_run, time_run)
            predicted_marathon_time = sec_to_time(time_run * (42.195 / distance_run)**1.06)
            kilometer__minute = (42195/time_run)

        else:
            flash('Error: All the form fields are required. ')

        return render_template("marathon.html", bar_chart=bar_chart, line_chart=line_chart,
                               form=form, predicted_marathon_time=predicted_marathon_time,
                               hours=hours, minutes=minutes, seconds=seconds, pace=pace,
                               kilometer__minute=kilometer__minute)
    else:
        return render_template("marathon.html", bar_chart=bar_chart, line_chart=line_chart,
                               form=form, predicted_marathon_time=predicted_marathon_time)


def get_pace(distance, time):
    pace = time/(distance*1000)
    return pace
    # marathon_time = request.form['marathon-time']
    #
    # line_chart = pygal.Line()  # Then create a bar graph object
    # line_chart.x_labels = ('0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2')
    # bar_chart = pygal.Bar()
    # bar_chart.x_labels = '0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2'
    #
    # count = marathon_time.count(':')
    #
    # if True:
    #         total_minutes = int(hours * 60 + minutes)
    #         kilometer__minute = (Decimal(42.195) / Decimal(total_minutes))
    #         try:
    #             pace = Speed(kilometer__minute = (Decimal(42.195) / Decimal(total_minutes)))
    #         except ZeroDivisionError:
    #             pace = 0
    #
    #         kilometres_per_minute = Decimal(1)/Decimal(kilometer__minute)
    #         line_chart.add("pace line chart", [kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
    #                                            kilometres_per_minute, kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
    #                                            kilometres_per_minute, kilometres_per_minute, kilometres_per_minute])
    #         line_chart = line_chart.render_data_uri()
    #
    #         bar_chart.add("pace bar chart", [kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
    #                                          kilometres_per_minute, kilometres_per_minute, kilometres_per_minute, kilometres_per_minute,
    #                                          kilometres_per_minute, kilometres_per_minute, kilometres_per_minute])
    #         bar_chart = bar_chart.render_data_uri()
    #
    #         if count == 2:
    #             return render_template('marathon.html', marathon_time=marathon_time, hours=hours, minutes=minutes,
    #                                    seconds=seconds, total_minutes=total_minutes, pace=pace, line_chart=line_chart,
    #                                    kilometres=kilometres_per_minute, bar_chart=bar_chart)
    #         else:
    #             return render_template('marathon.html', marathon_time=marathon_time, hours=hours, minutes=minutes,
    #                                    seconds="0", total_minutes=total_minutes, pace=pace, line_chart=line_chart,
    #                                    kilometres=kilometres_per_minute, bar_chart=bar_chart)
    #     except ValueError:
    #         this = False


@app.route('/marathon/peter_reigel_predictor/', methods=['GET', 'POST'])
def peter_reigel_predictor():
    form = ReusableForm(request.form)
    predicted_marathon_time = 0
    # print(form.errors)

    if request.method == 'POST':
        race_type = request.form['race_length']
        hours = request.form['race_time_hours']
        minutes = request.form['race_time_minutes']
        seconds = request.form['race_time_seconds']
        print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

        if form.validate():
            # Save the comment here.
            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            distance_run = race_distances(race_type)
            time_run = get_sec(hours, minutes, seconds)
            predicted_marathon_time = sec_to_time(time_run * (42.195 / distance_run)**1.06)
        else:
            flash('Error: All the form fields are required. ')

    return render_template("peter_reigel_predictor.html", form=form, predicted_marathon_time= predicted_marathon_time)


def get_sec(hours, minutes, seconds):
    return float(hours) * 3600.000 + float(minutes) * 60.000 + float(seconds)


def sec_to_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    str = "%d:%02d:%02d" % (h, m, s)
    return str


def race_distances(race_type):
    if race_type == "Marathon":
        numerical_distance = 42.195
    elif race_type == "Half Marathon":
        numerical_distance = 21.098
    elif race_type == "10 Miler":
        numerical_distance = 16.093
    elif race_type == "10 Kilometre":
        numerical_distance = 10.000
    elif race_type == "5 Miler":
        numerical_distance = 8.047
    elif race_type == "5 Kilometre":
        numerical_distance = 5.000
    elif race_type == "3 Kilometre":
        numerical_distance = 3.000
    elif race_type == "Miler":
        numerical_distance = 1.609
    elif race_type == "1500 Metre":
        numerical_distance = 1.500

    return numerical_distance


@app.route('/marathon/andrew_vickers_half_marathon/', methods=['GET', 'POST'])
def andrew_vickers_half_marathon():
    form = ReusableForm(request.form)
    predicted_marathon_time = 0
    # print(form.errors)

    if request.method == 'POST':
        race_type = request.form['race_length']
        hours = request.form['race_time_hours']
        minutes = request.form['race_time_minutes']
        seconds = request.form['race_time_seconds']
        print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

        if form.validate():
            # Save the comment here.
            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            distance_run = race_distances(race_type)
            time_run = get_sec(hours, minutes, seconds)
            predicted_marathon_time = sec_to_time(time_run * 2.19)
        else:
            flash('Error: All the form fields are required. ')

    return render_template("andrew_vickers_half_marathon.html", form=form,
                           predicted_marathon_time=predicted_marathon_time)


@app.route('/marathon/hansons_marathon_method/', methods=['GET', 'POST'])
def hansons_marathon_method():

    return render_template("hansons_marathon_method.html")


@app.route('/contact/', methods=['GET', 'POST'])
def contact():
    form = ReusableForm(request.form)
    # print(form.errors)

    if request.method == 'POST':
        name = request.form['name']

        password = request.form['password']
        email = request.form['email']
        print(name, " ", email, " ", password, " ")

        if form.validate():
            # Save the comment here.
            flash('Thanks for registration ' + name)
        else:
            flash('Error: All the form fields are required. ')

    return render_template("contact.html", form=form)


@app.route('/marathon/dave_cameron_predictor/', methods=['GET', 'POST'])
def dave_cameron_predictor():
    form = ReusableForm(request.form)
    predicted_marathon_time = 0
    # print(form.errors)

    if request.method == 'POST':
        race_type = request.form['race_length']
        hours = request.form['race_time_hours']
        minutes = request.form['race_time_minutes']
        seconds = request.form['race_time_seconds']
        print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

        if form.validate():
            # Save the comment here.
            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            distance_run = race_distances(race_type)
            distance_run = distance_run * 1000
            time_run = get_sec(hours, minutes, seconds)
            a = 13.49681 - (0.000030363 * distance_run) + (835.7114 / (distance_run ** 0.7905))
            b = 13.49681 - (0.000030363 * (42.195 * 1000)) + (835.7114 / ((42.195*1000) ** 0.7905))
            predicted_marathon_time = sec_to_time((time_run / distance_run) * (a / b) * (42.195*1000))

        else:
            flash('Error: All the form fields are required. ')

    return render_template("dave_cameron_predictor.html", form=form, predicted_marathon_time= predicted_marathon_time)


@app.route('/marathon/daniels_gilbert_vo2_max/', methods=['GET', 'POST'])
def daniels_gilbert_vo2_max():
    form = ReusableForm(request.form)
    vo2max = 0
    # print(form.errors)

    if request.method == 'POST':
        race_type = request.form['race_length']
        hours = request.form['race_time_hours']
        minutes = request.form['race_time_minutes']
        seconds = request.form['race_time_seconds']
        print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

        if form.validate():
            # Save the comment here.
            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            distance_run = race_distances(race_type)
            distance_run = distance_run*1000
            time_run = get_sec(hours, minutes, seconds)
            time_run = time_run/60  # divide by 60 to get time in minutes rather than seconds
            v = distance_run/time_run
            top_fraction = 0.000104 * (v * v) + (0.182258 * v) - 4.6
            bottom_fraction = 0.2989558 * math.exp(-0.1932605 * time_run) + 0.1894393 * math.exp(-0.012778 * time_run) + 0.8
            vo2max = top_fraction/bottom_fraction

        else:
            flash('Error: All the form fields are required. ')

    return render_template("daniels_gilbert_vo2_max.html", form=form, vo2max=vo2max)


def activities_2018():
    activities_from_2018 = {}
    for activity in client.get_activities(before="2018-02-06T00:00:00Z",
                                          after="2018-01-01T00:00:00Z", limit=None):

        if activity.type == 'Ride':
            activities_from_2018['Ride'] = activity.id
        elif activity.type == 'Run':
            activities_from_2018['Run'] = activity.id

    print(activities_from_2018)

    return activities_from_2018;


def activities_2017():
    activities_from_2017 = {}
    i = 0
    for activity in client.get_activities(before="2018-01-01T00:00:00Z",
                                          after="2017-01-01T00:00:00Z", limit=None):

        if activity.type == 'Ride':
            activities_from_2017[activity.id] = activity.type

        elif activity.type == 'Run':
            activities_from_2017[activity.id] = activity.type

    print(activities_from_2017)

    return activities_from_2017;


# This displays some details on the summary page of the users last ten rides (ID, Name, Distance)
def last_ten_rides():
    activity_list = []
    i = 0
    for activity in client.get_activities(limit=10):
        i += 1
        activity_id = i, u'{0.id}'.format(activity), u'{0.name}'.format(activity), u'{0.distance}'.format(activity)
        activity_list.append(activity_id)

        # assert len(list(activity_list)) == 10

    return activity_list


# This displays some details on the summary page of the users last ten rides (ID, Name, Distance)
def last_activity():
    for activity in client.get_activities(before="2018-02-09T00:00:00Z",
                                          after="2017-01-01T00:00:00Z", limit=1):
        return activity.id


if __name__ == '__main__':
    app.run(debug=True)
