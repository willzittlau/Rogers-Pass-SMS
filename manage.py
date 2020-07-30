from flask_script import Manager
from app import app

manager = Manager(app)

@manager.command
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

if __name__ == "__main__":
    manager.run()