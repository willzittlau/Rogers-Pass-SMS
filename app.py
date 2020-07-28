# Import libraries
import os
from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from datetime import datetime, date
import time
import schedule
import requests
import re

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

# Twilio number verification
def is_valid_number(number):
    try:
        response = client.lookups.phone_numbers(number).fetch(type="carrier")
        return True
    except TwilioRestException as e:
        if e.code == 20404:
            return False

# Convert input to e.164 format
def format_e164(number):
    number = number.replace('(','')
    number = number.replace(')','')
    number = number.replace('-','')
    number = number.replace('+','')
    number = number.replace('[','')
    number = number.replace(']','')
    number = number.replace('.','')
    number = number.replace(' ','')
    number = number.replace('·','')
    if len(number) > 10:
        if number.startswith('1'):
            number = '+' + number
        else:
            number = '+1' + number
    if len(number) == 10:
        number = '+1' + number
    return (number)

# Webscrape data and add to dB
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
                    to='', # dB numbers
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
        number_in = request.form.get('number')
        signup_date = datetime.utcnow().date()
        posttime = datetime.utcnow()
        date_time = datetime(
                            posttime.year, posttime.month, 
                            posttime.day, posttime.hour, 
                            posttime.minute, posttime.second
                                )
        # Verify number and prevent incorrect form entries
        num_regex = re.findall(r'''[^a-zA-Z@$&%!=:;/|}{#^*_\\><,?"']''', number_in)
        number_out = ''.join(num_regex)
        # Format to e.164 for dB entry
        number = format_e164(number_out)
        if is_valid_number(number) and number != '':
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