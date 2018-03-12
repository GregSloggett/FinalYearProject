import csv
import datetime
import math
from decimal import getcontext, Decimal

import pygal
from flask import Flask, render_template, request, make_response, flash
from flask_googlemaps import GoogleMaps
from flask_sqlalchemy import SQLAlchemy
from stravalib.client import Client
from wtforms import Form, IntegerField, TextField, validators

app = Flask(__name__)
# app.static_url_path='/static'
# app.config['GOOGLEMAPS_KEY'] = "AIzaSyBUV6YEpG7xjxJ8s9ZjIZP8A56L4TxAK7k"
app.config['GOOGLEMAPS_KEY'] = "AIzaSyCiforLtPDvDY3WzkKeWc2ykgR_Aw9rYk0"
GoogleMaps(app)

# # local db
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql2206541:yS3*wS7%@sql2.freemysqlhosting.net:3306/sql2206541'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# server db

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


class UserActivities(db.Model):
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
    race_length = TextField('Race Length:', validators=[validators.InputRequired()])
    hours = IntegerField('Hours:')
    minutes = IntegerField('Minutes:')
    seconds = IntegerField('Seconds:')


class AboutForm(Form):
    name = TextField('Name:')
    email = TextField('Email:')
    password = TextField('Password:')


MY_ACCESS_TOKEN = 'a6e5a504f806ed79c8a6e25f59da056b440faac5'
MY_CLIENT_ID = 20518
MY_CLIENT_SECRET = 'cf516a44b390c99b6777f771be0103314516931e'
STR_LENGTH = 6
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


activity_routes = ['five_k', 'ten_k', 'three_k', 'one_five_k', 'four_k',
                   'five_m', 'ten_m', 'half', 'marathon', 'activities']


@app.route('/activities/<distance_name>', methods=['GET', 'POST'])
def activities(distance_name):
    print(distance_name)
    activities_ = []
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
                            '{}'.format(activity.distance), u'{}'.format(activity.moving_time)
            activities_.append(activity)

            activities_data.append(activity_data)
            distance = convert_distance_to_integer(activity.distance.__str__())

            if activity.type == 'Run':
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
        elif distance_name == 'Half-Marathon':
            activities_data = data_half
        elif distance_name == 'Marathon':
            activities_data = data_marathon
        else:
            activities_data = activities_data

        print(activities_data)
        return render_template("activities.html", activities_data=activities_data)


@app.route('/summary/', methods=['GET', 'POST'])
def summary():
    activities = []
    total_activity_distance = 0
    running_distance = 0
    cycling_distance = 0
    other_activity_distance = 0
    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        for activity in client.get_activities(before=datetime.datetime.now(),
                                              after=client.get_athlete().created_at, limit=None):
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
        first_activity = UserActivities.query.filter_by(athlete_id=client.get_athlete().id).order_by(
            UserActivities.date).first()

        pie_chart = total_activities_pie_chart()
        distances_run = distances_ran(activities)
        five_k, ten_k, three_k, one_five_k, four_k, five_m, ten_m, half, marathon = total_distances(distances_run)
        write_distances_csv(five_k, ten_k, three_k, one_five_k, four_k, five_m, ten_m, half, marathon)

        jan_run = 0
        feb_run = 0
        mar_run = 0
        apr_run = 0
        may_run = 0
        jun_run = 0
        jul_run = 0
        aug_run = 0
        sep_run = 0
        oct_run = 0
        nov_run = 0
        dec_run = 0

        jan_ride = 0
        feb_ride = 0
        mar_ride = 0
        apr_ride = 0
        may_ride = 0
        jun_ride = 0
        jul_ride = 0
        aug_ride = 0
        sep_ride = 0
        oct_ride = 0
        nov_ride = 0
        dec_ride = 0

        jan = 0
        feb = 0
        mar = 0
        apr = 0
        may = 0
        jun = 0
        jul = 0
        aug = 0
        sep = 0
        oct = 0
        nov = 0
        dec = 0

        if check_for_cookie() is False:
            return render_template("homepage.html")
        else:
            month = 1
            while month <= 12:
                month_str = "%02d" % (month,)
                for activity in client.get_activities(before="2017-" + month_str + "-28T00:00:00Z",
                                                      after="2017-" + month_str + "-01T00:00:00Z", limit=None):
                    if (activity.type == 'Run'):
                        if month == 1:
                            jan_run += 1
                        elif month == 2:
                            feb_run += 1
                        elif month == 3:
                            mar_run += 1
                        elif month == 4:
                            apr_run += 1
                        elif month == 5:
                            may_run += 1
                        elif month == 6:
                            jun_run += 1
                        elif month == 7:
                            jul_run += 1
                        elif month == 8:
                            aug_run += 1
                        elif month == 9:
                            sep_run += 1
                        elif month == 10:
                            oct_run += 1
                        elif month == 11:
                            nov_run += 1
                        elif month == 12:
                            dec_run += 1
                    elif (activity.type == 'Ride'):
                        if month == 1:
                            jan_ride += 1
                        elif month == 2:
                            feb_ride += 1
                        elif month == 3:
                            mar_ride += 1
                        elif month == 4:
                            apr_ride += 1
                        elif month == 5:
                            may_ride += 1
                        elif month == 6:
                            jun_ride += 1
                        elif month == 7:
                            jul_ride += 1
                        elif month == 8:
                            aug_ride += 1
                        elif month == 9:
                            sep_ride += 1
                        elif month == 10:
                            oct_ride += 1
                        elif month == 11:
                            nov_ride += 1
                        elif month == 12:
                            dec_ride += 1
                    elif convert_distance_to_integer(activity.distance.__str__()) > 0:
                        if month == 1:
                            jan += 1
                        elif month == 2:
                            feb += 1
                        elif month == 3:
                            mar += 1
                        elif month == 4:
                            apr += 1
                        elif month == 5:
                            may += 1
                        elif month == 6:
                            jun += 1
                        elif month == 7:
                            jul += 1
                        elif month == 8:
                            aug += 1
                        elif month == 9:
                            sep += 1
                        elif month == 10:
                            oct += 1
                        elif month == 11:
                            nov += 1
                        elif month == 12:
                            dec += 1

                month += 1


        return render_template("summary.html", athlete=client.get_athlete(), athlete_stats=client.get_athlete_stats(),
                               last_ten_rides=last_ten_rides(), athlete_profiler=client.get_athlete().profile,
                               pie_chart=pie_chart, first_activity=first_activity,
                               total_activity_distance=total_activity_distance, running_distance=running_distance,
                               cycling_distance=cycling_distance, other_activity_distance=other_activity_distance,

                               jan=jan, feb=feb, mar=mar, apr=apr, may=may, jun=jun, jul=jul, aug=aug, sep=sep
                               , oct=oct, nov=nov, dec=dec,
                               jan_run=jan_run, feb_run=feb_run, mar_run=mar_run, apr_run=apr_run, may_run=may_run,
                               jun_run=jun_run, jul_run=jul_run, aug_run=aug_run, sep_run=sep_run, oct_run=oct_run,
                               nov_run=nov_run, dec_run=dec_run,
                               jan_ride=jan_ride, feb_ride=feb_ride, mar_ride=mar_ride, apr_ride=apr_ride,
                               may_ride=may_ride,
                               jun_ride=jun_ride, jul_ride=jul_ride, aug_ride=aug_ride, sep_ride=sep_ride,
                               oct_ride=oct_ride,
                               nov_ride=nov_ride, dec_ride=dec_ride
                               )


def total_distances(distances_run):
    five_k = 0
    ten_k = 0
    three_k = 0
    one_five_k = 0
    four_k = 0
    five_m = 0
    ten_m = 0
    half = 0
    marathon = 0

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

    return five_k, ten_k, three_k, one_five_k, four_k, five_m, ten_m, half, marathon


def write_distances_csv(five_k, ten_k, three_k, one_five_k, four_k, five_m, ten_m, half, marathon):
    with open("/home/GregorySloggett/FinalYearProject/static/distances.csv", 'w', newline='') as csvfile:
    # with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\distances.csv", 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=' ',
                                quotechar='', quoting=csv.QUOTE_NONE)

        spamwriter.writerow(['letter,frequency'])
        spamwriter.writerow(['1.5K,{}'.format(one_five_k)])
        spamwriter.writerow(['3K,{}'.format(three_k)])
        spamwriter.writerow(['4K,{}'.format(four_k)])
        spamwriter.writerow(['5K,{}'.format(five_k)])
        spamwriter.writerow(['5M,{}'.format(five_m)])
        spamwriter.writerow(['10K,{}'.format(ten_k)])
        spamwriter.writerow(['10M,{}'.format(ten_m)])
        spamwriter.writerow(['Half-Marathon,{}'.format(half)])
        spamwriter.writerow(['Marathon,{}'.format(marathon)])


def convert_distance_to_integer(string_distance):
    dist, redundant = string_distance.split('.')
    integer_distance = int(dist)
    return integer_distance


def distances_ran(activities):
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
        dist_alt = client.get_activity_streams(activity_id=activity_id, types=['distance', 'altitude'],
                                               resolution='high')

        with open("/home/GregorySloggett/FinalYearProject/static/altitude.csv", 'w', newline='') as csvfile:
        # with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\altitude.csv", 'w', newline='') as csvfile:
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

# @app.route('/index/', methods=['GET', 'POST'])
# def index():
#     form = ReusableForm(request.form)
#     average = 0
#     andrew_vickers = 0
#     dave_cameron = 0
#     peter_reigel = 0
#     pace = 0
#     wasActivitySelected = False
#     activities_ = []
#     activities_data = []
#     data_one_five = []
#     data_3k = []
#     data_4k = []
#     data_5k = []
#     data_10k = []
#     data_5m = []
#     data_10m = []
#     data_half = []
#     data_marathon = []
#
#     if check_for_cookie() is False:
#         return render_template("homepage.html")
#     else:
#         for activity in client.get_activities(before=datetime.datetime.now(),
#                                               after=client.get_athlete().created_at, limit=None):
#             if activity.type == 'Run':
#                 activity_data = len(activities_data) + 1, '{}'.format(activity.id), '{}'.format(activity.name), \
#                                 '{}'.format(activity.distance), u'{}'.format(activity.moving_time)
#                 activities_data.append(activity_data)
#
#         if request.method == 'POST':
#             if form.validate():
#                 race_type = request.form['race_length']
#                 hours = request.form['race_time_hours']
#                 if hours == '':
#                     hours = 0
#                 minutes = request.form['race_time_minutes']
#                 if minutes == '':
#                     minutes = 0
#                 seconds = request.form['race_time_seconds']
#                 if seconds == '':
#                     seconds = 0
#
#                 print(race_type, " ", float(hours), " ", float(minutes), " ", float(seconds))
#
#                 distance_run = race_distances(race_type)
#
#                 peter_reigel = peter_reigel_formula(race_type, hours, minutes, seconds)
#                 dave_cameron = dave_cameron_formula(race_type, hours, minutes, seconds)
#                 if distance_run == 21.098:
#                     andrew_vickers = andrew_vickers_formula(race_type, hours, minutes, seconds)
#                     average = (peter_reigel + andrew_vickers + dave_cameron) / 3
#                 else:
#                     average = (peter_reigel + dave_cameron) / 2
#
#                 average = sec_to_time(average)
#                 peter_reigel = sec_to_time(peter_reigel)
#                 dave_cameron = sec_to_time(dave_cameron)
#                 andrew_vickers = sec_to_time(andrew_vickers)
#
#                 time_run = get_sec(hours, minutes, seconds)
#
#                 pace = get_kms_per_minute(distance_run, time_run)
#
#                 # with open("/home/GregorySloggett/FinalYearProject/static/data.csv", 'w', newline='') as csvfile:
#                 with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\data.csv", 'w',
#                           newline='') as csvfile:
#
#                     spamwriter = csv.writer(csvfile, delimiter=' ',
#                                             quotechar='|', quoting=csv.QUOTE_MINIMAL)
#                     i = 0
#                     while (i < 43):
#                         if (i == 0):
#                             spamwriter.writerow(['kilometre,pace'])
#                         else:
#                             spamwriter.writerow(['{},{}'.format(i, pace)])
#                         i += 1
#             elif wasActivitySelected==True:
#                 if 1400 < activities < 1600:
#                     data_one_five.append(activity_data)
#                 elif 2750 < distance < 3250:
#                     data_3k.append(activity_data)
#                 elif 3750 < distance < 4250:
#                     data_4k.append(activity_data)
#                 elif 4500 < distance < 5500:
#                     data_5k.append(activity_data)
#                 elif 7750 < distance < 8250:
#                     data_5m.append(activity_data)
#                 elif 9500 < distance < 10500:
#                     data_10k.append(activity_data)
#                 elif 15750 < distance < 16250:
#                     data_10m.append(activity_data)
#                 elif 20500 < distance < 21500:
#                     data_half.append(activity_data)
#                 elif 41000 < distance < 43000:
#                     data_marathon.append(activity_data)
#
#             else:
#                 flash('Error: You are required to enter a distance. ')
#
#             print(data_4k)
#
#     return render_template("index.html", form=form, average=average, andrew_vickers=andrew_vickers,
#                            dave_cameron=dave_cameron, peter_reigel=peter_reigel,
#                            data_one_five=data_one_five, data_3k=data_3k, data_4k=data_4k, data_5k=data_5k, data_10k=data_10k,
#                            data_5m=data_5m, data_1om=data_10m, data_half=data_half, data_marathon=data_marathon)


@app.route('/activity/<activity_id>/<activity_map>', methods=['GET', 'POST'])
def map(activity_id, activity_map):
    types = ['time', 'latlng', 'altitude', 'heartrate', 'temp']

    if check_for_cookie() is False:
        return render_template("homepage.html")
    else:
        return render_template("map.html", activity_data=client.get_activity(activity_id=activity_id),
                               streams=client.get_activity_streams(activity_id=activity_id,
                                                                   types=types, resolution='medium'))


@app.route('/marathon/', methods=['GET', 'POST'])
def marathon():
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

            # line_chart = pygal.Line()  # Then create a bar graph object
            # line_chart.add('Fibonacci', [kilometer, kilometer, kilometer, kilometer, kilometer, kilometer, kilometer,
            #                              kilometer, kilometer, kilometer, kilometer])  # Add some values
            # line_chart.x_labels = ['0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2']
            # line_chart = line_chart.render_data_uri()
            #
            # bar_chart = pygal.Bar()
            # bar_chart.add('Fibonacci', [kilometer, kilometer, kilometer, kilometer, kilometer, kilometer, kilometer,
            #                             kilometer, kilometer, kilometer, kilometer])  # Add some values
            # bar_chart.x_labels = '0', '5', '10', '15', '20', '25', '30', '35', '40', '42.2'
            # bar_chart = bar_chart.render_data_uri()

        else:
            flash('Error: You are required to enter a distance. ')

        return render_template("marathon.html", bar_chart=bar_chart, line_chart=line_chart, form=form, hours=hours,
                               minutes=minutes, seconds=seconds, pace=pace, kilometres_per_minute=kilometres_per_minute,
                               kilometer__minute=kilometer__minute)
    else:
        return render_template("marathon.html", bar_chart=bar_chart, line_chart=line_chart, form=form)


def get_kms_per_minute(distance, time):
    kilometer = (distance / (time / 60))
    kms_per_minute = Decimal(1) / Decimal(kilometer)
    return kms_per_minute


def get_running_speed(distance, time):
    pace = (distance * 1000) / (time)
    return pace


@app.route('/marathon/peter_reigel_predictor/', methods=['GET', 'POST'])
def peter_reigel_predictor():
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

            # Save the comment here.
            flash('Your expected Marathon time based on your ' + race_type + ' time is shown below.')
            predicted_marathon_time = sec_to_time(peter_reigel_formula(race_type, hours, minutes, seconds))
        else:
            flash('Error: You are required to enter a distance. ')

    return render_template("peter_reigel_predictor.html", form=form, predicted_marathon_time=predicted_marathon_time)


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
    distance_run = race_distances(race_type)
    time_run = get_sec(hours, minutes, seconds)
    time = time_run * (42.195 / distance_run) ** 1.06
    return time


def andrew_vickers_formula(race_type, hours, minutes, seconds):
    time_run = get_sec(hours, minutes, seconds)
    time = time_run * 2.19
    return time


def dave_cameron_formula(race_type, hours, minutes, seconds):
    distance_run = race_distances(race_type)
    distance_run = distance_run * 1000
    time_run = get_sec(hours, minutes, seconds)
    a = 13.49681 - (0.000030363 * distance_run) + (835.7114 / (distance_run ** 0.7905))
    b = 13.49681 - (0.000030363 * (42.195 * 1000)) + (835.7114 / ((42.195 * 1000) ** 0.7905))
    time = (time_run / distance_run) * (a / b) * (42.195 * 1000)
    return time


@app.route('/marathon/hansons_marathon_method/', methods=['GET', 'POST'])
def hansons_marathon_method():
    form = ReusableForm(request.form)
    average = 0
    andrew_vickers = 0
    dave_cameron = 0
    peter_reigel = 0
    pace = 0

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

            average = sec_to_time(average)
            peter_reigel = sec_to_time(peter_reigel)
            dave_cameron = sec_to_time(dave_cameron)
            andrew_vickers = sec_to_time(andrew_vickers)

            time_run = get_sec(hours, minutes, seconds)

            pace = get_kms_per_minute(distance_run, time_run)

            with open("/home/GregorySloggett/FinalYearProject/static/data.csv", 'w', newline='') as csvfile:
            # with open("C:\\Users\\Greg Sloggett\\Dropbox\\FinalYearProject\\FYP_Project_Folder\\static\\data.csv", 'w',newline='') as csvfile:

                spamwriter = csv.writer(csvfile, delimiter=' ',
                                        quotechar='|', quoting=csv.QUOTE_MINIMAL)
                i = 0
                while (i < 43):
                    if (i == 0):
                        spamwriter.writerow(['kilometre,pace'])
                    else:
                        spamwriter.writerow(['{},{}'.format(i, pace)])
                    i += 1


        else:
            flash('Error: You are required to enter a distance. ')

    return render_template("hansons_marathon_method.html", form=form, average=average, andrew_vickers=andrew_vickers,
                           dave_cameron=dave_cameron, peter_reigel=peter_reigel)


@app.route('/about/', methods=['GET', 'POST'])
def about():
    form = AboutForm(request.form)
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

    return render_template("about.html", form=form)


@app.route('/marathon/dave_cameron_predictor/', methods=['GET', 'POST'])
def dave_cameron_predictor():
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
    form = ReusableForm(request.form)
    vo2max = 0
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
    for activity in client.get_activities(before=datetime.datetime.now(),
                                          after=client.get_athlete().created_at, limit=1):
        return activity.id


if __name__ == '__main__':
    app.run(debug=True)
