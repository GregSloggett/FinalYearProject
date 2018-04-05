import csv
import datetime
from datetime import timedelta
import math
from decimal import getcontext, Decimal
from flask import Flask, render_template, request, make_response, flash
from flask_googlemaps import GoogleMaps
from flask_sqlalchemy import SQLAlchemy
from stravalib.client import Client
from wtforms import Form, IntegerField, TextField, validators
import pygal
from pygal.style import RotateStyle

app = Flask(__name__)
app.config['GOOGLEMAPS_KEY'] = "AIzaSyCiforLtPDvDY3WzkKeWc2ykgR_Aw9rYk0"
GoogleMaps(app)

# # local db
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql2206541:yS3*wS7%@sql2.freemysqlhosting.net:3306/sql2206541'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# server db
#
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
    """
    Access Tokens Database that stores the access tokens generated in the first time user flow for
    further use on user requests to the Strava API.
    Three columns containing:
    - Athlete ID (Primary Key)
    - Access Token
    - Email Address
    """
    __tablename__ = "access_tokens"
    athlete_id = db.Column(db.String(11), primary_key=True)
    access_token = db.Column(db.String(40))
    email_address = db.column(db.String(40))


class UserActivities(db.Model):
    """
    User Activities Database to store basic activity information when the user first accesses the summary page.
    Stores the Athlete ID (primary key), activity ID, Actviity Type, Date, Distance, Moving Time, Max Speed & Average Speed.
    """
    __tablename__ = "user_activities"
    athlete_id = db.Column(db.String(11), primary_key=True)
    activity_id = db.Column(db.Integer)
    activity_type = db.Column(db.String(32))
    date = db.Column(db.String(64))
    distance = db.Column(db.String(32))
    activity_moving_time = db.Column(db.String(32))
    average_speed = db.Column(db.String(32))
    max_speed = db.Column(db.String(32))


class ReusableForm(Form):
    """
    Reusable Form that is used by all marathon prediction algorithms.
    The fields take in the length of a previously completed race (race_length) and the time it took
    to complete that race (hours, minutes, seconds).
    """
    race_length = TextField('Race Length:', validators=[validators.InputRequired()])
    hours = IntegerField('Hours:')
    minutes = IntegerField('Minutes:')
    seconds = IntegerField('Seconds:')


class AboutForm(Form):
    """
    Simple About Form has fields that take in the users name email and password to process any queries a user may have
    """
    name = TextField('Name:')
    email = TextField('Email:')
    password = TextField('Password:')


MY_ACCESS_TOKEN = 'a6e5a504f806ed79c8a6e25f59da056b440faac5'
MY_CLIENT_ID = 20518
MY_CLIENT_SECRET = 'cf516a44b390c99b6777f771be0103314516931e'
STR_LENGTH = 6
client = Client()


@app.route('/', methods=['GET', 'POST'])
def homepage():
    """
    Homepage of application that displays either a connect to Strava page if the user has not been recognised,
    or the return user page if the user is recognised. Recognised by checking for a cookie.
    """
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("return_user.html", athlete=client.get_athlete(),
                               athlete_stats=client.get_athlete_stats(), athlete_profiler=client.get_athlete().profile,
                               last_activity_id=last_activity())



def check_for_cookie():
    """
    Boolean function that checks to see has a cookie been written to the users browser.
    If that cookie has been written and it is associated with an access token in the database,
    then it returns true, otherwise returning false.
    :return: Boolean if cookie is present or not
    """
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


@app.route('/response_url/', methods=['GET', 'POST'])
def response_url():
    """ The response page for first time authorization.
        - Produces a user access token using Client ID and Client SECRET
        - Commits generated user access token to a database
        - Stores a cookie on the users browser lasting 365 days
        - Responds with a webpage (repsonse.html) displaying an array of choices to the user
     """
    error = request.args.get('error')
    if error == 'access_denied':
        return render_template("access_denied.html", methods=['GET', 'POST'])

    code = request.args.get('code')

    athlete_access_token = client.exchange_code_for_token(client_id=MY_CLIENT_ID, client_secret=MY_CLIENT_SECRET, code=code)
    client.access_token = athlete_access_token

    athlete = client.get_athlete()
    check_code = athlete_access_token
    check_access_token = AccessTokens.query.filter_by(access_token=check_code).first()
    if not check_access_token:
        print(client.get_athlete().email)
        signature = AccessTokens(athlete_id=str(athlete.id), access_token=athlete_access_token,
                                 email_address=client.get_athlete().email)
        db.session.add(signature)
        db.session.commit()
        resp = make_response(
            render_template("response_url.html", athlete_access_token=athlete_access_token, athlete=athlete,
                            athlete_stats=client.get_athlete_stats(), athlete_profiler=athlete.profile,
                            last_activity_id=last_activity()))
        resp.set_cookie('athlete_id', str(athlete.id), expires=datetime.datetime.now() + datetime.timedelta(days=365))
        return resp
    else:
        resp = make_response(
            render_template("return_user.html", athlete_access_token=athlete_access_token, athlete=athlete,
                            athlete_stats=client.get_athlete_stats(), athlete_profiler=athlete.profile,
                            last_activity_id=last_activity()))
        resp.set_cookie('athlete_id', str(athlete.id), expires=datetime.datetime.now() + datetime.timedelta(days=365))
        return resp


@app.route('/activities/<distance_name>', methods=['GET', 'POST'])
def activities(distance_name):
    """
    Activities page(s) that displays a sortable table for any of the selected distances (from the dropdown bar), or all
    distances. The table can be sorted by Activity ID, Name, Distance, Moving Time, Avg and Max Speed and Date.
    """
    print(distance_name)
    activities_ = []
    all_runs = []
    all_rides = []
    activities_data = []
    data_one_five = []
    data_3k = []
    data_4k = []
    data_5k = []
    data_10k = []
    data_5m = []
    data_10m = []
    data_half = []
    data_marathon = []

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        for activity in client.get_activities(before=datetime.datetime.now(),
                                              after=client.get_athlete().created_at, limit=None):
            activity_data = len(activities_data) + 1, '{}'.format(activity.id), '{}'.format(activity.name), \
                            '{}'.format(activity.distance), '{}'.format(activity.moving_time), \
                            '{}'.format(activity.average_speed), '{}'.format(activity.max_speed), \
                            '{}'.format(str(activity.start_date)[0:10])
            activities_.append(activity)

            activities_data.append(activity_data)
            distance = convert_distance_to_integer(activity.distance.__str__())

            if activity.type == 'Run':
                all_runs.append(activity_data)
                if 1400 < distance < 1600:
                    data_one_five.append(activity_data)
                elif 2750 < distance < 3250:
                    data_3k.append(activity_data)
                elif 3750 < distance < 4250:
                    data_4k.append(activity_data)
                elif 4500 < distance < 5500:
                    data_5k.append(activity_data)
                elif 7750 < distance < 8250:
                    data_5m.append(activity_data)
                elif 9500 < distance < 10500:
                    data_10k.append(activity_data)
                elif 15750 < distance < 16250:
                    data_10m.append(activity_data)
                elif 20500 < distance < 21500:
                    data_half.append(activity_data)
                elif 41000 < distance < 43000:
                    data_marathon.append(activity_data)
            elif activity.type == 'Ride':
                all_rides.append(activity_data)

        if distance_name == '1.5K':
            activities_data = data_one_five
        elif distance_name == '3K':
            activities_data = data_3k
        elif distance_name == '4K':
            activities_data = data_4k
        elif distance_name == '5K':
            activities_data = data_5k
        elif distance_name == '5M':
            activities_data = data_5m
        elif distance_name == '10K':
            activities_data = data_10k
        elif distance_name == '10M':
            activities_data = data_10m
        elif distance_name == 'Half':
            activities_data = data_half
        elif distance_name == 'Marathon':
            activities_data = data_marathon
        elif distance_name == 'all_runs':
            activities_data = all_runs
        elif distance_name == 'all_rides':
            activities_data = all_rides
        else:
            activities_data = activities_data

        print(activities_data)
        return render_template("activities.html", activities_data=activities_data)


@app.route('/summary/', methods=['GET', 'POST'])
def summary():
    """
    Summary Page containing several features including:
    - Pygal Weekly statistics and activites.
    - Personal Profile card with basic user information.
    - D3 chart displaying frequent and common race distances in an interactive chart.
    - Latest ten activities.
    - First activity.
    """
    activities = []
    total_activity_distance = 0
    running_distance = 0
    cycling_distance = 0
    other_activity_distance = 0

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        week_runs = [0, 0, 0, 0, 0, 0, 0]
        week_rides = [0, 0, 0, 0, 0, 0, 0]
        week_other = [0, 0, 0, 0, 0, 0, 0]
        prev_day = 7  # not a valid day of the week as needs to be used to check against activity day
        weekly_activities_total, weekly_runs_total, weekly_rides_total, \
        weekly_other_total, distance_covered, time_training = 0, 0, 0, 0, 0, 0

        for activity in client.get_activities(before=datetime.datetime.now(),
                                              after=datetime.datetime.now()-timedelta(days=7), limit=None):
            weekly_activities_total += 1

            month_str = "%02d" % (int(str(activity.start_date)[5:7]),)
            day_str = "%02d" % (int(str(activity.start_date)[8:10]),)

            day_of_week = datetime.datetime(int(str(activity.start_date)[0:4]), int(month_str), int(day_str)).weekday()

            if prev_day != day_of_week:
                todays_runs = 0
                todays_rides = 0
                todays_other = 0

            if activity.type == 'Run':
                todays_runs += 1
                week_runs[day_of_week] = todays_runs
                weekly_runs_total += 1
            elif activity.type == 'Ride':
                todays_rides += 1
                week_rides[day_of_week] = todays_rides
                weekly_rides_total += 1
            else:
                todays_other += 1
                week_other[day_of_week] = todays_other
                weekly_other_total += 1

            hrs, mins, secs = str(activity.moving_time).split(':')
            time_training += get_sec(hrs, mins, secs)

            distance_covered += convert_distance_to_integer(activity.distance.__str__())
            prev_day = day_of_week

    first_activity_val = 100000000000
    first_activity = ''
    for activity in client.get_activities(before=datetime.datetime.now(),
                                          after="2010-01-01T00:00:00Z", limit=None):
        if int(activity.id) < int(first_activity_val):
            first_activity = activity
            first_activity_val = int(first_activity.id)

        activities.append(activity)
        total_activity_distance += convert_distance_to_integer(activity.distance.__str__())

        if activity.type == 'Run':
            running_distance += convert_distance_to_integer(activity.distance.__str__())
        elif activity.type == 'Ride':
            cycling_distance += convert_distance_to_integer(activity.distance.__str__())
        else:
            other_activity_distance += convert_distance_to_integer(activity.distance.__str__())

        activity_present = UserActivities.query.filter_by(activity_id=activity.id).first()

        if activity_present:
            db.session.commit()
            print('already present')
        else:
            print('not present')
            signature = UserActivities(athlete_id=client.get_athlete().id, activity_id=activity.id,
                                       activity_type=activity.type, date=activity.start_date,
                                       distance=convert_distance_to_integer(activity.distance.__str__()),
                                       activity_moving_time=activity.moving_time,
                                       average_speed=activity.average_speed.__str__(),
                                       max_speed=activity.max_speed.__str__())
            db.session.add(signature)
            db.session.commit()

    UserActivities.query.filter_by(athlete_id=client.get_athlete().id)

    pie_chart = total_activities_pie_chart()
    distances_run = distances_ran(activities)

    five_k, ten_k, three_k, one_five_k, four_k, five_m, ten_m, half, marathon = 0, 0, 0, 0, 0, 0, 0, 0, 0

    for id, distance in distances_run.items():
        if distance == "5K":
            five_k += 1
        elif distance == "10K":
            ten_k += 1
        elif distance == "3K":
            three_k += 1
        elif distance == "1.5K":
            one_five_k += 1
        elif distance == "4K":
            four_k += 1
        elif distance == "5M":
            five_m += 1
        elif distance == "10M":
            ten_m += 1
        elif distance == "Half":
            half += 1
        elif distance == "Marathon":
            marathon += 1

    write_distances_csv(five_k, ten_k, three_k, one_five_k, four_k, five_m, ten_m, half, marathon)

    monthly_runs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    monthly_rides = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    monthly_other = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        month = 1
        while month <= 12:
            month_str = "%02d" % (month,)
            for activity in client.get_activities(before="2017-" + month_str + "-28T00:00:00Z",
                                                  after="2017-" + month_str + "-01T00:00:00Z", limit=None):
                if activity.type == 'Run':
                    monthly_runs[int(month_str)-1] += 1
                elif activity.type == 'Ride':
                    monthly_rides[int(month_str)-1] += 1
                elif convert_distance_to_integer(activity.distance.__str__()) > 0:
                    monthly_other[int(month_str)-1] += 1

            month += 1
    print('here')
    print(monthly_runs)
    print(monthly_rides)
    print(monthly_other)

    dark_rotate_style = RotateStyle('#9e6ffe')
    dark_rotate_style.background = 'white'
    line_chart = pygal.Line(legend_at_bottom=True, legend_at_bottom_columns=3, dots_size=6,
                            show_minor_y_labels=False, height=400, style=dark_rotate_style,
                            stroke_style={'width': 3})

    line_chart.title = 'Activities This Week:'
    line_chart.x_labels = (['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
    line_chart.add('Runs', week_runs)
    line_chart.add('Rides', week_rides)
    line_chart.add('Other Activities', week_other)
    line_chart = line_chart.render_data_uri()

    return render_template("summary.html", athlete=client.get_athlete(), athlete_stats=client.get_athlete_stats(),
                           last_ten_rides=last_ten_rides(), athlete_profiler=client.get_athlete().profile,
                           pie_chart=pie_chart, first_activity=first_activity, line_chart=line_chart,
                           total_activity_distance=total_activity_distance, running_distance=running_distance,
                           cycling_distance=cycling_distance, other_activity_distance=other_activity_distance,
                           weekly_activities_total=weekly_activities_total, weekly_runs_total=weekly_runs_total,
                           weekly_rides_total=weekly_rides_total, weekly_others_total=weekly_other_total,
                           distance_covered=distance_covered, time_training=sec_to_time(time_training),
                           join_date=str(client.get_athlete().created_at)[0:4],

                           monthly_runs=monthly_runs, monthly_rides=monthly_rides, monthly_other=monthly_other)


def write_distances_csv(five_k, ten_k, three_k, one_five_k, four_k, five_m, ten_m, half, marathon):
    """
    Function which writes the landmark distances into a csv file for use by the D3 and Pygal charts.
    :param five_k:
    :param ten_k:
    :param three_k:
    :param one_five_k:
    :param four_k:
    :param five_m:
    :param ten_m:
    :param half:
    :param marathon:
    :return: nothing
    """
    with open("/home/GregorySloggett/FinalYearProject/static/csv_files/distances.csv", 'w', newline='') as csvfile:
    # with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\csv_files\\distances.csv",'w', newline='') as csvfile:

        spamwriter = csv.writer(csvfile, delimiter=' ',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)

        spamwriter.writerow(['letter,frequency'])
        spamwriter.writerow(['{},{}'.format('1.5K', one_five_k)])
        spamwriter.writerow(['{},{}'.format('3K', three_k)])
        spamwriter.writerow(['{},{}'.format('4K', four_k)])
        spamwriter.writerow(['{},{}'.format('5K', five_k)])
        spamwriter.writerow(['{},{}'.format('5M', five_m)])
        spamwriter.writerow(['{},{}'.format('10K', ten_k)])
        spamwriter.writerow(['{},{}'.format('10M', ten_m)])
        spamwriter.writerow(['{},{}'.format('Half', half)])
        spamwriter.writerow(['{},{}'.format('Marathon', marathon)])


def convert_distance_to_integer(string_distance):
    """
    Function to convert the distances (as selected by the client) into integer format to be used in calculations.
    :param string_distance:
    :return: integer distance
    """
    dist, redundant = string_distance.split('.')
    integer_distance = int(dist)
    return integer_distance


def distances_ran(activities):
    """
    Function to classify the distances run by a Strava Athlete
    :param activities:
    :return: dictionary of distance values using the activity id as the key
    """
    distances = {}
    for activity in activities:
        if activity.type == 'Run':
            distance = convert_distance_to_integer(activity.distance.__str__())
            if 1400 < distance < 1600:
                distances[activity.id] = "1.5K"
            elif 2750 < distance < 3250:
                distances[activity.id] = "3K"
            elif 3750 < distance < 4250:
                distances[activity.id] = "4K"
            elif 4500 < distance < 5500:
                distances[activity.id] = "5K"
            elif 7750 < distance < 8250:
                distances[activity.id] = "5M"
            elif 9500 < distance < 10500:
                distances[activity.id] = "10K"
            elif 15750 < distance < 16250:
                distances[activity.id] = "10M"
            elif 20500 < distance < 21500:
                distances[activity.id] = "Half"
            elif 41000 < distance < 43000:
                distances[activity.id] = "Marathon"
    return distances


def total_activities_pie_chart():
    """
    Function to display all activities used by a Strava Athlete on a pygal pie chart.
    :return: the pie chart to be displayed
    """
    total_rides = UserActivities.query.filter_by(activity_type='ride', athlete_id=client.get_athlete().id).count()
    total_runs = UserActivities.query.filter_by(activity_type='run', athlete_id=client.get_athlete().id).count()
    total_swims = UserActivities.query.filter_by(activity_type='swim', athlete_id=client.get_athlete().id).count()
    total_ski = UserActivities.query.filter_by(activity_type='alpineski', athlete_id=client.get_athlete().id).count()

    pie_chart = pygal.Pie()  # Then create a bar graph object
    pie_chart.add('Rides', total_rides)  # Add some values
    pie_chart.add('Runs', total_runs)  # Add some values
    pie_chart.add('Swims', total_swims)
    pie_chart.add('Skis', total_ski)
    pie_chart = pie_chart.render_data_uri()
    return pie_chart


@app.route('/return_user/', methods=['GET', 'POST'])
def return_user():
    """
    Return user page that is displayed if a user has previously been to the application and a cookie is stored on their
    browser. Offers the user a variety of avenues to take to analyze their statistics or predict a marathon time.
    :return: return user web page
    """
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:

        return render_template("return_user.html", athlete=client.get_athlete(),
                               athlete_profiler=client.get_athlete().profile, athlete_stats=client.get_athlete_stats(),
                               last_activity_id=last_activity())


@app.route('/activity/<activity_id>', methods=['GET', 'POST'])
def activity(activity_id):
    """
    Individual Activity page for each activity logged by the Strava athlete. Displaying statistics and charts for the
    selected activity.
    :param activity_id:
    :return: activity web page
    """
    types = ['time', 'latlng', 'altitude', 'heartrate', 'temp', 'distance', 'elevation']

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        dist_alt = client.get_activity_streams(activity_id=activity_id, types=['distance', 'altitude'],
                                               resolution='high')

        with open("/home/GregorySloggett/FinalYearProject/static/csv_files/altitude.csv", 'w', newline='') as csvfile:
        # with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\csv_files\\altitude.csv", 'w', newline='') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=' ',
                                    quotechar='', quoting=csv.QUOTE_NONE)

            spamwriter.writerow(['distance,altitude'])

            count = 0
            for each in dist_alt['distance'].data:
                spamwriter.writerow(
                    ['{},{}'.format(dist_alt['distance'].data[count], dist_alt['altitude'].data[count])])
                count += 1

    return render_template("activity.html", athlete=client.get_athlete(),
                           athlete_profiler=client.get_athlete().profile,
                           activity_data=client.get_activity(activity_id=activity_id, include_all_efforts=True),
                           athlete_stats=client.get_athlete_stats(),
                           streams=client.get_activity_streams(activity_id=activity_id, types=types,
                                                               resolution='medium'))


@app.route('/activity/<activity_id>/<activity_map>', methods=['GET', 'POST'])
def map(activity_id, activity_map):
    """
    Map display of each individual activity, usign the Google Maps API to display the latitude and longitude data
    streams that were attained from the Strava API.
    :param activity_id:
    :param activity_map:
    :return: a google maps display with activity route showing
    """
    types = ['time', 'latlng', 'altitude', 'heartrate', 'temp']

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("map.html", activity_data=client.get_activity(activity_id=activity_id),
                               streams=client.get_activity_streams(activity_id=activity_id,
                                                                   types=types, resolution='medium'))


@app.route('/marathon/', methods=['GET', 'POST'])
def marathon():
    """
    Marathon Page that allows a user to estimate their own marathon time and displays their pacing times and charts
    accrodingly.
    :return: Marathon estimation page
    """
    form = ReusableForm(request.form)
    predicted_marathon_time = 0
    # print(form.errors)
    getcontext().prec = 3

    line_chart = pygal.Line()  # Then create a bar graph object
    line_chart.add('Fibonacci', [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55])  # Add some values
    line_chart.x_labels = ['0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2']
    line_chart = line_chart.render_data_uri()

    bar_chart = pygal.Bar()
    bar_chart.add('Fibonacci', [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55])  # Add some values
    bar_chart.x_labels = '0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2'
    bar_chart = bar_chart.render_data_uri()

    if request.method == 'POST':
        if form.validate():
            race_type = request.form['race_length']
            hours = request.form['race_time_hours']
            if hours == '':
                hours = 0
            minutes = request.form['race_time_minutes']
            if minutes == '':
                minutes = 0
            seconds = request.form['race_time_seconds']
            if seconds == '':
                seconds = 0

            print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            distance_run = race_distances(race_type)
            time_run = get_sec(hours, minutes, seconds)

            try:
                pace = get_running_speed(distance_run, time_run)
            except ZeroDivisionError:
                pace = 0

            kilometer__minute = get_kms_per_minute(distance_run, time_run)
            kilometres_per_minute = sec_to_time(get_sec(0, kilometer__minute, 0))

            line_chart = pygal.Line()  # Then create a bar graph object
            line_chart.add('Landmark Splits', [kilometer__minute*0, kilometer__minute*3, kilometer__minute*5, kilometer__minute*8, kilometer__minute*10,
                                               kilometer__minute*15, kilometer__minute*20, kilometer__minute*30, kilometer__minute*40,
                                               kilometer__minute*42])
            line_chart.x_labels = ['0', '3', '5', '8', '10', '15', '20', '30', '40', '42.2']
            line_chart = line_chart.render_data_uri()

            bar_chart = pygal.Bar()
            bar_chart.add('Landmark Splits', [kilometer__minute*3, kilometer__minute*2, kilometer__minute*3, kilometer__minute*2,
                                              kilometer__minute*5, kilometer__minute*5, kilometer__minute*10, kilometer__minute*10,
                                              kilometer__minute*2])
            bar_chart.x_labels = ['3', '5', '8', '10', '15', '20', '30', '40', '42.2']
            bar_chart = bar_chart.render_data_uri()

        else:
            flash('Error: You are required to enter a distance. ')

        return render_template("marathon.html", bar_chart=bar_chart, line_chart=line_chart, form=form, hours=hours,
                               minutes=minutes, seconds=seconds, pace=pace, kilometres_per_minute=kilometres_per_minute,
                               kilometer__minute=kilometer__minute, threek=kilometer__minute*3, fivek=kilometer__minute*2,
                               eightk=kilometer__minute*3, tenk=kilometer__minute*2, fifteenk=kilometer__minute*5,
                               twentyk=kilometer__minute*5, thirtyk=kilometer__minute*10, fortyk=kilometer__minute*10,
                               fortytwok=kilometer__minute*2)
    else:
        return render_template("marathon.html", bar_chart=bar_chart, line_chart=line_chart, form=form)


def get_kms_per_minute(distance, time):
    """
    Function that uses the distance and time entered by a user to calculate the speed they travelled in
    kilometres per minute.
    :param distance:
    :param time:
    :return: kilomtres per minute
    """
    kilometer = (distance / (time / 60))
    kms_per_minute = Decimal(1) / Decimal(kilometer)
    return kms_per_minute


def get_running_speed(distance, time):
    """
    Get the pace of an athlete given the distance and time
    :param distance:
    :param time:
    :return: pace
    """
    pace = (distance * 1000) / (time)
    return pace


@app.route('/marathon/peter_reigel_predictor/', methods=['GET', 'POST'])
def peter_reigel_predictor():
    """
    Marathon prediction page that uses the Peter Riegel marathon prediction formula to predict a users
    marathon time, based on a previous run distance and the corresponding time.
    :return: Peter Riegel prediction page
    """
    form = ReusableForm(request.form)
    predicted_marathon_time = 0

    if request.method == 'POST':
        if form.validate():
            race_type = request.form['race_length']
            hours = request.form['race_time_hours']
            if hours == '':
                hours = 0
            minutes = request.form['race_time_minutes']
            if minutes == '':
                minutes = 0
            seconds = request.form['race_time_seconds']
            if seconds == '':
                seconds = 0

            print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            predicted_marathon_time = sec_to_time(peter_reigel_formula(race_type, hours, minutes, seconds))
        else:
            flash('Error: You are required to enter a distance. ')

    return render_template("peter_reigel_predictor.html", form=form, predicted_marathon_time=predicted_marathon_time)


def get_sec(hours, minutes, seconds):
    """
    Function to convert hours, minutes and seconds into seconds.
    :param hours:
    :param minutes:
    :param seconds:
    :return: total seconds
    """
    return float(hours) * 3600.000 + float(minutes) * 60.000 + float(seconds)


def sec_to_time(seconds):
    """
    Function to convert seconds into a time string.
    :param seconds:
    :return: time string
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    str = "%d:%02d:%02d" % (h, m, s)
    return str


def race_distances(race_type):
    """
    Function to convert the race distances from string format to numerical format
    :param race_type:
    :return: race distances (float)
    """
    if race_type == "Marathon":
        numerical_distance = 42.195
    elif race_type == "Half":
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
    """
    Web page that displays a prediction algorithm based on the andrew vickers half marathon method.
    Takes in half marathon time and computes a marathon time based on it for the athlete.
    :return: Marathon prediction page on vickers' formula
    """
    form = ReusableForm(request.form)
    predicted_marathon_time = 0

    if request.method == 'POST':
        if form.validate():
            race_type = request.form['race_length']
            hours = request.form['race_time_hours']
            if hours == '':
                hours = 0
            minutes = request.form['race_time_minutes']
            if minutes == '':
                minutes = 0
            seconds = request.form['race_time_seconds']
            if seconds == '':
                seconds = 0

            print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            predicted_marathon_time = sec_to_time(andrew_vickers_formula(race_type, hours, minutes, seconds))
        else:
            flash('Error: You are required to enter a distance. ')

    return render_template("andrew_vickers_half_marathon.html", form=form,
                           predicted_marathon_time=predicted_marathon_time)


def peter_reigel_formula(race_type, hours, minutes, seconds):
    """
    Peter Reigel formula used on the Peter Reigel marathon prediction page.
    :param race_type:
    :param hours:
    :param minutes:
    :param seconds:
    :return: predicted finishing time
    """
    distance_run = race_distances(race_type)
    time_run = get_sec(hours, minutes, seconds)
    time = time_run * (42.195 / distance_run) ** 1.06
    return time


def andrew_vickers_formula(race_type, hours, minutes, seconds):
    """
    Andrew vickers half marathon formula to predict marathon race time.
    :param race_type:
    :param hours:
    :param minutes:
    :param seconds:
    :return: predicted finishing time
    """
    time_run = get_sec(hours, minutes, seconds)
    time = time_run * 2.19
    return time


def dave_cameron_formula(race_type, hours, minutes, seconds):
    """
    Dave Cameron's formula to predict a marathon race time.
    :param race_type:
    :param hours:
    :param minutes:
    :param seconds:
    :return: predicted finishing time
    """
    distance_run = race_distances(race_type)
    distance_run = distance_run * 1000
    time_run = get_sec(hours, minutes, seconds)
    a = 13.49681 - (0.000030363 * distance_run) + (835.7114 / (distance_run ** 0.7905))
    b = 13.49681 - (0.000030363 * (42.195 * 1000)) + (835.7114 / ((42.195 * 1000) ** 0.7905))
    time = (time_run / distance_run) * (a / b) * (42.195 * 1000)
    return time


@app.route('/marathon/multiple_marathon_predictor/', methods=['GET', 'POST'])
def multiple_marathon_predictor():
    """
    Multiple marathon prediction time based on the average of the other prediction algorithms.
    :return: page displaying prediction method
    """
    form = ReusableForm(request.form)
    average = 0
    andrew_vickers = 0
    dave_cameron = 0
    peter_reigel = 0
    pace_str = 0
    getcontext().prec = 3

    activities_data = []
    data_one_five = []
    data_3k = []
    data_5k = []
    data_10k = []
    data_5m = []
    data_10m = []
    data_half = []
    data_marathon = []

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        for activity in client.get_activities(before=datetime.datetime.now(),
                                              after=client.get_athlete().created_at, limit=None):
            if activity.type == 'Run':
                activity_data = len(activities_data) + 1, '{}'.format(activity.id), '{}'.format(activity.name), \
                                '{}'.format(activity.distance), u'{}'.format(activity.moving_time)

                distance = convert_distance_to_integer(activity.distance.__str__())

                if 1400 < distance < 1600:
                    data_one_five.append(activity_data)
                    activities_data.append(activity_data)
                elif 2750 < distance < 3250:
                    data_3k.append(activity_data)
                    activities_data.append(activity_data)
                elif 4500 < distance < 5500:
                    data_5k.append(activity_data)
                    activities_data.append(activity_data)
                elif 7750 < distance < 8250:
                    data_5m.append(activity_data)
                    activities_data.append(activity_data)
                elif 9500 < distance < 10500:
                    data_10k.append(activity_data)
                    activities_data.append(activity_data)
                elif 15750 < distance < 16250:
                    data_10m.append(activity_data)
                    activities_data.append(activity_data)
                elif 20500 < distance < 21500:
                    data_half.append(activity_data)
                    activities_data.append(activity_data)
                elif 41000 < distance < 43000:
                    data_marathon.append(activity_data)
                    activities_data.append(activity_data)

        if request.method == 'POST':
            if form.validate():
                race_type = request.form['race_length']
                hours = request.form['race_time_hours']
                if hours == '':
                    hours = 0
                minutes = request.form['race_time_minutes']
                if minutes == '':
                    minutes = 0
                seconds = request.form['race_time_seconds']
                if seconds == '':
                    seconds = 0

                print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

                distance_run = race_distances(race_type)

                peter_reigel = peter_reigel_formula(race_type, hours, minutes, seconds)
                dave_cameron = dave_cameron_formula(race_type, hours, minutes, seconds)
                if distance_run == 21.098:
                    andrew_vickers = andrew_vickers_formula(race_type, hours, minutes, seconds)
                    average = (peter_reigel + andrew_vickers + dave_cameron) / 3
                else:
                    average = (peter_reigel + dave_cameron) / 2

                peter_reigel = sec_to_time(peter_reigel)
                dave_cameron = sec_to_time(dave_cameron)
                andrew_vickers = sec_to_time(andrew_vickers)

                time_run = get_sec(hours, minutes, seconds)

                print(average)
                print(time_run)

                pace = get_kms_per_minute(42.195, average)

                print(pace)


                pace_mins, pace_secs = str(pace).split('.')
                decimal_pace_secs = float("0." + pace_secs)
                pace_secs = int(decimal_pace_secs * 60)

                pace_str = pace_mins + ":" + str("%02d" % (pace_secs,))

                average = sec_to_time(average)

                with open("/home/GregorySloggett/FinalYearProject/static/csv_files/data.csv", 'w', newline='') as csvfile:
                # with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\csv_files\\data.csv", 'w', newline='') as csvfile:

                    spamwriter = csv.writer(csvfile, delimiter=' ',
                                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    landmark_pace = 0
                    i = 0
                    while i < 43:
                        landmark_pace += pace
                        if i == 0:
                            spamwriter.writerow(['kilometre,pace'])
                            landmark_pace = 0
                        elif i == 3:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 5:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 8:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 10:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 15:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 20:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 30:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 40:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0
                        elif i == 42:
                            spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                            landmark_pace = 0

                        i += 1

                        # with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\landmarks.csv", 'w', newline='') as csvfile:
                        #
                        #     spamwriter = csv.writer(csvfile, delimiter=' ',
                        #                             quotechar='|', quoting=csv.QUOTE_MINIMAL)
                        #     spamwriter.writerow(['kilometre,pace'])
                        #
                        #     landmark_pace = 0
                        #     i = 0
                        #     while i < 43:
                        #         landmark_pace += pace
                        #         print(landmark_pace)
                        #         if i % 5 == 0 and i != 0:
                        #             spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                        #             landmark_pace = 0
                        #         elif i == 42:
                        #             spamwriter.writerow(['{},{}'.format(i, landmark_pace)])
                        #             landmark_pace = 0
                        #         i += 1

            else:
                flash('Error: You are required to enter a distance. ')

    return render_template("multiple_marathon_predictor.html", form=form, average=average, andrew_vickers=andrew_vickers,
                           dave_cameron=dave_cameron, peter_reigel=peter_reigel, activities_data=activities_data,
                           data_one_five=data_one_five, data_3k=data_3k, data_5k=data_5k, data_10k=data_10k,
                           data_5m=data_5m, data_1om=data_10m, data_half=data_half, data_marathon=data_marathon,
                           pace_str=pace_str)

@app.route('/about/', methods=['GET', 'POST'])
def about():
    """
    About page to display some information on the web application and allow user emails/responses
    :return: web page displaying website information
    """
    form = AboutForm(request.form)

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

    return render_template("about.html", form=form)


@app.route('/marathon/dave_cameron_predictor/', methods=['GET', 'POST'])
def dave_cameron_predictor():
    """
    Web page to display the dave cameron prediction algorithm for marathons.
    :return: prediction formula page
    """
    form = ReusableForm(request.form)
    predicted_marathon_time = 0
    # print(form.errors)

    if request.method == 'POST':
        if form.validate():
            race_type = request.form['race_length']

            hours = request.form['race_time_hours']
            if hours == '':
                hours = 0
            minutes = request.form['race_time_minutes']
            if minutes == '':
                minutes = 0
            seconds = request.form['race_time_seconds']
            if seconds == '':
                seconds = 0

            print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')

            predicted_marathon_time = sec_to_time(dave_cameron_formula(race_type, hours, minutes, seconds))

        else:
            flash('Error: You are required to enter a distance. ')

    return render_template("dave_cameron_predictor.html", form=form, predicted_marathon_time=predicted_marathon_time)


@app.route('/marathon/daniels_gilbert_vo2_max/', methods=['GET', 'POST'])
def daniels_gilbert_vo2_max():
    """
    Web page to display Daniels and Gilbert's unique vo2 max estimate prediction method with vo2 max table
    :return: display VO2 max table
    """
    form = ReusableForm(request.form)
    vo2max = 0

    if request.method == 'POST':
        if form.validate():
            race_type = request.form['race_length']
            hours = request.form['race_time_hours']
            if hours == '':
                hours = 0
            minutes = request.form['race_time_minutes']
            if minutes == '':
                minutes = 0
            seconds = request.form['race_time_seconds']
            if seconds == '':
                seconds = 0

            print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))

            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            distance_run = race_distances(race_type)
            distance_run = distance_run * 1000
            time_run = get_sec(hours, minutes, seconds)
            time_run = time_run / 60  # divide by 60 to get time in minutes rather than seconds
            v = distance_run / time_run
            top_fraction = 0.000104 * (v * v) + (0.182258 * v) - 4.6
            bottom_fraction = 0.2989558 * math.exp(-0.1932605 * time_run) + 0.1894393 * math.exp(
                -0.012778 * time_run) + 0.8
            vo2max = top_fraction / bottom_fraction


        else:
            flash('Error: You are required to enter a distance. ')

    return render_template("daniels_gilbert_vo2_max.html", form=form, vo2max=vo2max)


def activities_2018():
    """
    Retrieve all clients activities for the year of 2018
    :return: activities for 2018
    """
    activities_from_2018 = {}
    for activity in client.get_activities(before="2019-01-01T00:00:00Z",
                                          after="2018-01-01T00:00:00Z", limit=None):

        if activity.type == 'Ride':
            activities_from_2018['Ride'] = activity.id
        elif activity.type == 'Run':
            activities_from_2018['Run'] = activity.id

    print(activities_from_2018)

    return activities_from_2018;


def activities_2017():
    """
    Retrieve all a clients activities from the year 2017
    :return: activities for 2017
    """
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
    """
    Retrieve the last 10 activities for the client.
    :return: last ten activities
    """
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
    """
    Retrieve the very first activity of the user from the Strava API.
    :return: first activity
    """
    for activity in client.get_activities(before=datetime.datetime.now(),
                                          after=client.get_athlete().created_at, limit=1):
        return activity.id


if __name__ == '__main__':
    app.run(debug=True)
