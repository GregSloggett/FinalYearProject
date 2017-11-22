from flask import Flask, render_template, request

app = Flask(__name__)


# Home page of my application.
@app.route('/')
def homepage():

    return render_template("homepage.html")


# The response page that the user is presented with when they authorize the app for the first time.
@app.route('/response_url/')
def response_url():
    error = request.args.get('error')
    if error == 'access_denied':
        return render_template("access_denied.html")

    return render_template("response_url.html")


@app.route('/summary/')
def summary():

    return render_template("summary.html")


# If the user has already authorized the application this is the page that will be returned (instead of response_url).
@app.route('/return_user/')
def return_user():

    return render_template("return_user.html")


if __name__ == '__main__':
    app.run()
