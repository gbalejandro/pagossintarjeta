from flask_script import Manager
from main import *

manager = Manager(app)

if __name__ == '__main__':
    manager.run()