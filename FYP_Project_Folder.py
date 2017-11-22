from flask import Flask, render_template

app = Flask(__name__)


# Home page of my application.
@app.route('/')
def homepage():

    return render_template("homepage.html")


# The response page that the user is presented with when they authorize the app for the first time.
@app.route('/response_url/')
def response_url():

    return render_template("response_url.html")


@app.route('/summary/')
def summary():

    return render_template("summary.html")

if __name__ == '__main__':
    app.run()
