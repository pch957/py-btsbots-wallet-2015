from gevent import monkey
monkey.patch_all()

#import datetime
import time
from threading import Thread
#from flask import Flask, render_template, session, request
from flask import Flask, render_template, request, redirect, url_for
from flask.ext.babel import gettext#, ngettext
#from flask import send_from_directory
from flask import flash
from flask.ext.socketio import SocketIO, emit
from flask.ext.babel import Babel
from bts_wallet import BTSWallet
from bts_orderbook import BTSOrderBook
from pprint import pprint

app = Flask(__name__, static_folder='static', static_url_path='')
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
babel = Babel(app)
bts_orderbook = BTSOrderBook()
bts_orderbook.pusher = socketio
contacts = ["test-alice", "test-bob", "rou.baozi"]
protect_account = ["pls.btsbots", "alice.btsbots", "bob.btsbots"]
bts_wallet = BTSWallet(bts_orderbook.bts_client, protect_account)
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


def get_wallet_account():
    _account = request.cookies.get('account')
    account_list = bts_wallet.get_all_account()
    if _account and _account in account_list:
        return _account
    else:
        return None


@app.template_filter()
def datetimefilter(value, format='%Y/%m/%d %H:%M'):
    """convert a datetime to a different format."""
    return value.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter


@app.route('/')
def index():
    account = get_wallet_account()
    if not account:
        return redirect(url_for('waccount'))
    current_height = bts_orderbook.height
    balance = bts_wallet.get_balance(account)
    transaction = bts_wallet.get_transaction(account)
    return render_template(
        'index.html', title=gettext(u"Wallet"), current_height=current_height,
        account=account, balance=balance, transaction=transaction
    )


@app.route('/transfer', methods=['Get', 'POST'])
def transfer():
    account = get_wallet_account()
    if not account:
        return redirect(url_for('waccount'))
    balance = bts_wallet.get_balance(account)
    _contacts = contacts
    msg = ""
    if request.method == "POST":
        print(request.form)
        amount = request.form["amount"]
        if amount:
            amount = float(amount)
        else:
            amount = 0.0
        asset = request.form["asset"]
        receiver = request.form["receiver"]
        memo = request.form["memo"]
        if amount <= 0.0 or amount > balance[asset]:
            msg = "Error: amount invalid %s %s" % (amount, balance[asset])
        elif receiver not in _contacts:
            msg = "Error: account %s invalid" % receiver
        else:
            result = bts_wallet.transfer([amount, asset, account, receiver, memo])
            if "Error" in result:
                msg = "Error: %s" % result["error"]["message"]
            else:
                msg = "Success: transfer %s %s from %s to %s %s" % (
                    amount, asset, account, receiver, memo)

    return render_template(
        'transfer.html', title=gettext(u"Transfer"), contacts=_contacts,
        account=account, balance=balance, msg=msg
    )


@app.route('/waccount')
def waccount():
    account_list = bts_wallet.get_all_account()
    return render_template(
        'waccount.html', title="choose account",
        account_list=account_list)


@app.route('/contact')
def contact():
    #account_list = bts_wallet.get_all_account()
    _contacts = contacts
    return render_template(
        'contact.html', title="contact list",
        contacts=_contacts)


@app.route('/market')
def market():
    current_height = bts_orderbook.height
    order_book = bts_orderbook.order_book["CNY_BTS"]
    deal_trx = bts_orderbook.deal_trx["CNY_BTS"]
    place_trx = bts_orderbook.place_trx["CNY_BTS"]
    return render_template(
        'market.html', title=gettext("Market"), current_height=current_height,
        order_book=order_book, deal_trx=deal_trx, place_trx=place_trx
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
