# Import libraries
import os
from twilio.rest import Client
from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from datetime import datetime, date
import time
import schedule
import requests

# Set up app and environment
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
os.environ['TZ'] = 'UTC'
time.tzset()

# Create dB
db = SQLAlchemy(app)

# Set up Twilio
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
client = Client(account_sid, auth_token)

# Add dB tables
class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String())
    date_time = db.Column(db.DateTime())
    signup_date = db.Column(db.Date())
    
    def __init__(self, number, date_time, signup_date):
        self.number = number
        self.date_time = date_time
        self.signup_date = signup_date

    def __repr__(self):
        return '<id {}>'.format(self.id)

class Info(db.Model):
    __tablename__ = 'Info'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Text())
    status_date = db.Column(db.Date())
    
    def __init__(self, status, status_date):
        self.status = status
        self.status_date = status_date

    def __repr__(self):
        return '<id {}>'.format(self.id)

def webscrape():
    # Get daily udpate page
    get_url = requests.get('https://www.pc.gc.ca/apps/rogers-pass/print?lang=en')
    get_text = get_url.text
    # Save results for dB
    status = 'Result'
    status_date = date.today()
    # Append to dB
    rpdata = Info(status, status_date)
    db.session.add(rpdata)
    db.session.commit()

# Send SMS
def SMS():
    message = client.messages.create(
                    from_= os.environ['TWILIO_NUMBER'],
                    to= +1234567890, # dB numbers
                    body='Testing from Twilio' # Daily update from dB)
                    )

# Schedule daily tasks

schedule.every().day.at("15:04").do(webscrape)
schedule.every().day.at("15:05").do(SMS)

# Home Page
@app.route("/", methods =['GET', 'POST'])
def index():
    # Set dummy variable for Jinja and dB entry
    postsuccess = ''
    # POST request route
    if request.method == 'POST':
        # Get data from form and fill dB variables
        number = request.form.get('number')
        signup_date = date.today()
        posttime = datetime.utcnow()
        date_time = datetime(
                            posttime.year, posttime.month, 
                            posttime.day, posttime.hour, 
                            posttime.minute, posttime.second
                                )
        # Verify number
        if number == '7782159455':
            # Check if user has already signed up for the udpate or not
            if db.session.query(User).filter(and_(User.number == number, User.signup_date == signup_date)).count() == 0:
                # Append to dB
                data = User(number, date_time, signup_date)
                db.session.add(data)
                db.session.commit()
                # Update Jinja variable
                postsuccess = 'posted'
        # Redirects with error flash
            else:
                flash('This number has already been signed up for tomorrow\'s update!', 'error')
                return redirect(url_for('index'))
        else:
            flash('Error: Phone number doesn\'t exist or incorrect format. Please try again!', 'error')
            return redirect(url_for('index'))
    # Return template
    return render_template('index.html', postsuccess=postsuccess)

# On running app.py, run Flask app
if __name__ == "__main__":
    # Still under development, run debug
    app.run(debug=True ,use_reloader=False)


# Keep app running to perform daily webscrape
while True:
    schedule.run_pending()
    time.sleep(1)