from gevent import monkey
monkey.patch_all()

#import datetime
import time
from threading import Thread
#from flask import Flask, render_template, session, request
from flask import Flask, render_template, request, redirect, url_for
from flask.ext.babel import gettext
#from flask import send_from_directory
#from flask import flash
from flask.ext.socketio import SocketIO, emit
from flask.ext.babel import Babel
from light_wallet import LightWallet
#from pprint import pprint

app = Flask(__name__, static_folder='static', static_url_path='')
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
babel = Babel(app)
contacts = ["test-alice", "test-bob", "rou.baozi"]
bts_wallet = LightWallet()
bts_wallet.pusher = socketio


@babel.localeselector
def get_locale():
    lang = ["en", "zh"]
    return request.accept_languages.best_match(lang)


def background_thread():
    """Example of how to send server generated events to clients."""
    while True:
        time.sleep(10)
        bts_wallet.execute()


@app.template_filter()
def datetimefilter(value, format='%Y/%m/%d %H:%M'):
    """convert a datetime to a different format."""
    return value.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter


@app.route('/')
def index():
    address = request.cookies.get('address')
    print("address is ", address)
    if not address:
        return redirect(url_for('login'))
    wallet_info = bts_wallet.get_wallet(address)
    current_height = bts_wallet.height
    return render_template(
        'index.html', title=gettext(u"Wallet"), current_height=current_height,
        wallet_info=wallet_info
    )


@app.route('/transfer', methods=['Get', 'POST'])
def transfer():
    address = request.cookies.get('address')
    if not address:
        return redirect(url_for('login'))
    wallet_info = bts_wallet.get_wallet(address)
    _contacts = contacts
    msg = ""
    return render_template(
        'transfer.html', title=gettext(u"Transfer"), contacts=_contacts,
        wallet_info=wallet_info, msg=msg
    )


@app.route('/login')
def login():
    return render_template(
        'login.html', title="Login", action="login")


@app.route('/logout')
def logout():
    return render_template(
        'login.html', title="Login", action="logout")


@app.route('/new')
def new():
    return render_template(
        'new.html', title="Create account")


@app.route('/contact')
def contact():
    _contacts = contacts
    return render_template(
        'contact.html', title="contact list",
        contacts=_contacts)


@app.route('/market')
def market():
    current_height = bts_wallet.height
    return render_template(
        'market.html', title=gettext("Market"), current_height=current_height
    )


@socketio.on('connect', namespace='')
def test_connect():
    emit('my response', {'data': 'Connected', 'count': 0})


def main():
    thread = Thread(target=background_thread)
    thread.start()

    socketio.run(
        app, use_reloader=False, heartbeat_interval=10, heartbeat_timeout=15)

if __name__ == '__main__':
    main()
