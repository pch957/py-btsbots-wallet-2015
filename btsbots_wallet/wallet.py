from gevent import monkey
monkey.patch_all()

#import datetime
import time
from threading import Thread
#from flask import Flask, render_template, session, request
from flask import Flask, render_template, request, redirect, url_for
from flask.ext.socketio import SocketIO, emit
from flask.ext.babel import Babel
from bts_wallet import BTSWallet
from bts_orderbook import BTSOrderBook

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
babel = Babel(app)
bts_orderbook = BTSOrderBook()
bts_orderbook.pusher = socketio
bts_wallet = BTSWallet(bts_orderbook.bts_client)
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
        bts_orderbook.execute()


def check_wallet_account():
    _account = request.cookies.get('account')
    account_list = bts_wallet.get_all_account()
    if _account and _account in account_list:
        bts_wallet.set_account(_account)
        return True
    else:
        return False


@app.template_filter()
def datetimefilter(value, format='%Y/%m/%d %H:%M'):
    """convert a datetime to a different format."""
    return value.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter


@app.route('/')
def index():
    if not check_wallet_account():
        return redirect(url_for('login'))
    current_height = bts_orderbook.height
    #current_time = datetime.datetime.now()
    return render_template(
        'index.html', title="BTS wallet", current_height=current_height)


@app.route('/login')
def login():
    account_list = bts_wallet.get_all_account()
    return render_template(
        'login.html', title="BTS wallet/choose account",
        account_list=account_list)


@app.route('/wallet')
def wallet():
    if not check_wallet_account():
        return redirect(url_for('login'))
    current_height = bts_orderbook.height
    balance = bts_wallet.balance
    return render_template(
        'wallet.html', title="BTS wallet", current_height=current_height,
        balance=balance
    )


@app.route('/market')
def market():
    current_height = bts_orderbook.height
    order_book = bts_orderbook.order_book["CNY_BTS"]
    deal_trx = bts_orderbook.deal_trx["CNY_BTS"]
    place_trx = bts_orderbook.place_trx["CNY_BTS"]
    return render_template(
        'market.html', title="BTS market", current_height=current_height,
        order_book=order_book, deal_trx=deal_trx, place_trx=place_trx
    )


@socketio.on('connect', namespace='')
def test_connect():
    emit('my response', {'data': 'Connected', 'count': 0})


def main():
    thread = Thread(target=background_thread)
    thread.start()

    socketio.run(app, use_reloader=False)

if __name__ == '__main__':
    main()
