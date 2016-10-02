import time
from threading import Thread
from flask import Flask, render_template
from flask_babel import gettext
from flask_babel import Babel
from flask_socketio import SocketIO

app = Flask(__name__, static_folder='static', static_url_path='')
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
babel = Babel(app)
contacts = ["test-alice", "test-bob", "rou.baozi"]


def background_thread():
    """Example of how to send server generated events to clients."""
    time.sleep(10)


@app.route('/')
def index():
    return render_template(
        'index.html', title=gettext(u"explorer")
    )


def main():
    thread = Thread(target=background_thread)
    thread.start()

    socketio.run(app, use_reloader=False)

if __name__ == '__main__':
    main()
