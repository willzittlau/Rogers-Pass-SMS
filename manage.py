from flask_script import Manager
from app import app
from app import send_sms, webscrape
import time

manager = Manager(app)

@manager.command
def sms():
    time.sleep(300)
    send_sms()

@manager.command
def scrape():
    time.sleep(240)
    webscrape()

@manager.command
def both():
    time.sleep(240)
    webscrape()
    time.sleep(60)
    send_sms()

if __name__ == "__main__":
    manager.run()