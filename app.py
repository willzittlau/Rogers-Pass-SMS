# Import libraries
import os
from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from selenium import webdriver
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import datetime
import time
import re

# Set up app and environment
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
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
    # Selenium init
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ['GOOGLE_CHROME_PATH']
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(executable_path=os.environ['CHROMEDRIVER_PATH'], chrome_options=chrome_options)
    # Scrape
    driver.get('https://www.pc.gc.ca/apps/rogers-pass/print?lang=en')
    time.sleep(3)
    page_source = driver.page_source
    driver.quit()
    # Save data
    tables = pd.read_html(page_source)
    wra_table = pd.DataFrame(tables[0])
    parking_table = pd.DataFrame(tables[1])
    prohibited_table = pd.DataFrame(tables[2])
    # Initialise strings
    title_string = 'Status for ' + str(datetime.datetime.utcnow().date()) + ':'
    wra_open_string = 'Open WRAs: '
    wra_closed_string = 'Closed WRAs: '
    parking_open_string = 'Open Parking: '
    parking_closed_string = 'Closed Parking: '
    prohibited_string = 'Prohibited Areas: '
    # String concatenation for WRA table
    for i in range (0, len(wra_table['Winter restricted area'])):
        if wra_table.at[i, 'Status'].startswith('O'):
            wra_table.at[i, 'Status'] = wra_table.at[i, 'Status'][:4]
            wra_open_string += (wra_table.at[i, 'Winter restricted area'] + ', ')
        if wra_table.at[i, 'Status'].startswith('C'):
            wra_table.at[i, 'Status'] = wra_table.at[i, 'Status'][:6]
            wra_closed_string += wra_table.at[i, 'Status'] + '\n'
    if not wra_open_string.endswith(': '):
        wra_open_string = wra_open_string[:-2]
    if not wra_closed_string.endswith(': '):
        wra_closed_string = wra_closed_string[:-2]
    # String concatenation for Parking table
    for i in range (0, len(parking_table['Parking area'])):
        parking_table.at[i,'Parking area'] = parking_table.at[i,'Parking area'].replace(' Parking', '')
        if parking_table.at[i, 'Status'].startswith('O'):
            parking_table.at[i, 'Status'] = parking_table.at[i, 'Status'][:4]
            parking_open_string += (parking_table.at[i, 'Parking area'] + ', ')
        if parking_table.at[i, 'Status'].startswith('C'):
            parking_table.at[i, 'Status'] = parking_table.at[i, 'Status'][:6]
            parking_closed_string += parking_table.at[i, 'Status'] + '\n'
    if not parking_open_string.endswith(': '):
        parking_open_string = parking_open_string[:-2]
    if not parking_closed_string.endswith(': '):
        parking_closed_string = parking_closed_string[:-2]
    # String concatenation for Prohibited table
    for i in range (0, len(prohibited_table['Winter prohibited area'])):
        prohibited_string += (prohibited_table.at[i, 'Winter prohibited area'] + ', ')
    if not prohibited_string.endswith(': '):
        prohibited_string = prohibited_string[:-2]
    # Concat and save results for dB
    status = (title_string + '\n' + wra_open_string 
                + '\n' + wra_closed_string + '\n' + parking_open_string 
                + '\n' + parking_closed_string + '\n' + prohibited_string)
    status_date = datetime.datetime.utcnow().date()
    # Append to dB
    rpdata = Info(status, status_date)
    db.session.add(rpdata)
    db.session.commit()

# Send SMS
def send_sms():
    # Return contents for sms message
    todays_date = datetime.datetime.utcnow().date()
    daily_update_sms = db.session.query(Info.status).filter(Info.status_date == todays_date).limit(1).scalar()
    daily_update_sms = daily_update_sms.replace('\n', '\n\n')
    # Find list of numbers to send sms to
    query_end_time = datetime.datetime.combine(datetime.datetime.utcnow().date(), datetime.time(15, 5))
    query_start_time = query_end_time - datetime.timedelta(days = 1)
    daily_numbers = db.session.query(User.number.distinct()).filter(
                                        and_(User.date_time >= query_start_time, 
                                            User.date_time <= query_end_time)).all()
    daily_numbers = [r for r, in daily_numbers]
    for number in daily_numbers:
        message = client.messages.create(
                    from_= os.environ['TWILIO_NUMBER'],
                    to=number,
                    body=daily_update_sms 
                    )

def printer():
    print('Testing...') #test

# Schedule daily tasks
scheduler = BackgroundScheduler()

scheduler.add_job(webscrape, 'cron', second = 1) #test
scheduler.add_job(printer, 'cron', second = 30) #test
scheduler.add_job(send_sms, 'cron', second =59) #test

scheduler.add_job(webscrape, 'cron', hour=15, minute=4)
scheduler.add_job(send_sms, 'cron', hour=15, minute=5)

# Home Page
@app.route("/", methods =['GET', 'POST'])
def index():
    # Set dummy variable for Jinja and dB entry
    postsuccess = ''
    # POST request route
    if request.method == 'POST':
        # Get data from form and fill dB variables
        number_in = request.form.get('number')
        signup_date = datetime.datetime.utcnow().date()
        posttime = datetime.datetime.utcnow()
        date_time = datetime.datetime(
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
            if db.session.query(User).filter(
                    and_(User.number == number, User.signup_date == signup_date)).count() == 0:
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
    # Run background tasks
    scheduler.start()
    # Still under development, run debug
    app.run(debug=True ,use_reloader=False)
