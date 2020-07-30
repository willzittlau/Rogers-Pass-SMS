from flask_script import Manager
from app import app
from app import send_sms

manager = Manager(app)

@manager.command
def sms():
    send_sms()

if __name__ == "__main__":
    manager.run()