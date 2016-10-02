import time
from threading import Thread
from flask import Flask, render_template, request
from flask_babel import gettext
from flask_babel import Babel
from flask_socketio import SocketIO, emit

from bts.ws.base_protocol import BaseProtocol
import datetime

try:
    import asyncio
except ImportError:
    import trollius as asyncio

app = Flask(__name__, static_folder='static', static_url_path='')
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
babel = Babel(app)
contacts = ["test-alice", "test-bob", "rou.baozi"]


def id_to_int(id):
    return int(id.split('.')[-1])


def next_id(id):
    id_array = id.split('.')
    id_next = "%s.%s.%d" % (id_array[0], id_array[1], int(id_array[2])+1)
    return id_next


class ChainMonitor(BaseProtocol):
    op_id_last = None
    object_info = {}
    last_fill_order = None
    lock = asyncio.Lock()

    @asyncio.coroutine
    def get_object_info(self, id):
        if id not in self.object_info:
            response = yield from self.rpc(
                [self.database_api, "get_objects", [[id]]])
            self.object_info[id] = response[0]
        return self.object_info[id]

    @asyncio.coroutine
    def handle_op_transfer(self, notify):
        _info = notify["op"][1]
        _transfer_info = {}
        response = yield from self.get_object_info(_info["from"])
        _transfer_info["from"] = response["name"]
        response = yield from self.get_object_info(_info["to"])
        _transfer_info["to"] = response["name"]
        _asset_info = yield from self.get_object_info(
            _info["amount"]["asset_id"])
        _transfer_info["symbol"] = _asset_info["symbol"]
        _transfer_info["amount"] = float(
            _info["amount"]["amount"])/10**_asset_info["precision"]
        print(
            "[33m[%s] %s sent %s %s to %s[m" % (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                _transfer_info["from"], _transfer_info["amount"],
                _transfer_info["symbol"], _transfer_info["to"]))

    @asyncio.coroutine
    def handle_op_borrow(self, notify):
        _info = notify["op"][1]
        _borrow_info = {}
        response = yield from self.get_object_info(_info["funding_account"])
        _borrow_info["account"] = response["name"]
        for _type in ["delta_collateral", "delta_debt"]:
            _balance = _info[_type]
            _asset_info = yield from self.get_object_info(_balance["asset_id"])
            _balance["symbol"] = _asset_info["symbol"]
            _balance["amount"] = float(
                _balance["amount"])/10**_asset_info["precision"]
            _borrow_info[_type] = _balance
        print("[31m[%s] %s adjust collateral by %s %s, debt by %s %s[m" % (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            _borrow_info["account"],
            _borrow_info["delta_collateral"]["amount"],
            _borrow_info["delta_collateral"]["symbol"],
            _borrow_info["delta_debt"]["amount"],
            _borrow_info["delta_debt"]["symbol"]))

    @asyncio.coroutine
    def handle_op_fill(self, notify):
        _info = notify["op"][1]
        if self.last_fill_order is None:
            self.last_fill_order = _info
            return
        if _info["pays"] != self.last_fill_order["receives"] or _info[
                "receives"] != self.last_fill_order["pays"]:
            print("error1: %s" % self.last_fill_order)
            print("error2: %s" % _info)
            self.last_fill_order = _info
            return
        _trade_info = {}
        _order_info = self.last_fill_order
        self.last_fill_order = None
        response = yield from self.get_object_info(_order_info["account_id"])
        _trade_info["account1"] = response["name"]
        response = yield from self.get_object_info(_info["account_id"])
        _trade_info["account2"] = response["name"]
        for _type in ["pays", "receives"]:
            _balance = _order_info[_type]
            _asset_info = yield from self.get_object_info(_balance["asset_id"])
            _balance["symbol"] = _asset_info["symbol"]
            _balance["amount"] = float(
                _balance["amount"])/10**_asset_info["precision"]
            _trade_info[_type] = _balance

        print("[32m[%s] %s bought %s %s with %s %s from %s[m" % (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            _trade_info["account1"], _trade_info["receives"]["amount"],
            _trade_info["receives"]["symbol"], _trade_info["pays"]["amount"],
            _trade_info["pays"]["symbol"], _trade_info["account2"]))

    handles = {
        0: handle_op_transfer,
        3: handle_op_borrow,
        4: handle_op_fill}

    @asyncio.coroutine
    def handle_operation(self, notify):
        _op_type = notify["op"][0]
        print(notify["id"])
        if _op_type in self.handles:
            yield from self.handles[_op_type](self, notify)

    def onOperation(self, notify):
        asyncio.async(self._onOperation(notify))

    @asyncio.coroutine
    def _onOperation(self, notify):
        yield from self.lock
        op_id_cur = notify["id"]
        if self.op_id_last is None:
            self.op_id_last = op_id_cur
        op_id_last = self.op_id_last
        if id_to_int(op_id_last) > id_to_int(op_id_cur):
            self.lock.release()
            return
        while id_to_int(op_id_last) < id_to_int(op_id_cur):
            response = yield from self.rpc(
                [self.database_api, "get_objects", [[op_id_last]]])
            _notify = response[0]
            yield from self.handle_operation(_notify)
            op_id_last = next_id(op_id_last)
        yield from self.handle_operation(notify)
        self.op_id_last = next_id(op_id_last)
        self.lock.release()

    @asyncio.coroutine
    def onOpen(self):
        yield from super().onOpen()
        self.subscribe("1.11.", self.onOperation)


@babel.localeselector
def get_locale():
    lang = ["en", "zh"]
    return request.accept_languages.best_match(lang)


def background_thread():
    """Example of how to send server generated events to clients."""
    time.sleep(10)


@app.template_filter()
def datetimefilter(value, format='%Y/%m/%d %H:%M'):
    """convert a datetime to a different format."""
    return value.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter


@app.route('/')
def index():
    return render_template(
        'index.html', title=gettext(u"explorer")
    )


@socketio.on('connect', namespace='')
def test_connect():
    emit('my response', {'data': 'Connected', 'count': 0})


def main():
    thread = Thread(target=background_thread)
    thread.start()

    socketio.run(
        app, use_reloader=False)

if __name__ == '__main__':
    main()
