from flask_script import Manager
from app import app
from app import send_sms, webscrape

manager = Manager(app)

@manager.command
def sms():
    send_sms()

@manager.command
def scrape():
    webscrape()

if __name__ == "__main__":
    manager.run()