# -*- coding: utf-8 -*-

from bts.api import BTS
from bts.market import BTSMarket
import json
import os


def get_prefix(quote, base):
    prefix = "%s_%s" % (quote, base)
    prefix = prefix.replace('.', '-')
    return prefix


class BTSOrderBook(object):
    def __init__(self):
        self.market_list = [
            ["BOTSCNY", "BTS"], ["CNY", "BTS"], ["USD", "BTS"],
            ["GOLD", "BTS"], ["BTC", "BTS"], ["BDR.AAPL", "CNY"],
            ["NOTE", "BTS"]]
        self.init_done = False
        self.pusher = None
        self.order_book = {}
        self.deal_trx = {}
        self.place_trx = {}
        for quote, base in self.market_list:
            prefix = get_prefix(quote, base)
            self.order_book[prefix] = {}
            self.deal_trx[prefix] = []
            self.place_trx[prefix] = []
        self.init_market()
        self.execute()
        self.init_done = True

    def init_market(self):
        config_file = os.getenv("HOME") + "/.python-bts/bts_client.json"
        fd_config = open(config_file)
        config_bts = json.load(fd_config)["client_default"]
        fd_config.close()

        self.bts_client = BTS(config_bts["user"], config_bts["password"],
                              config_bts["host"], config_bts["port"])
        self.market = BTSMarket(self.bts_client)
        client_info = self.bts_client.get_info()
        self.height = int(client_info["blockchain_head_block_num"]) - 180

    def myPublish(self, topic, event):
        if self.pusher and self.init_done:
            self.pusher.emit(topic, event, namespace="")

    def publish_deal_trx(self, deal_trx):
        for trx in deal_trx:
            if trx["type"] == "bid":
                deal_type = "buy"
            else:
                deal_type = "sell"
            prefix = get_prefix(trx["quote"], trx["base"])
            format_trx = [prefix, trx["block"], trx["timestamp"],
                          deal_type, trx["price"], trx["volume"]]
            self.myPublish(
                u'bts.orderbook.%s.trx' % (format_trx[0]), format_trx[1:])
            self.myPublish(u'bts.orderbook.trx', format_trx)
            market = format_trx[0]
            if market not in self.deal_trx:
                self.deal_trx[market] = []
            self.deal_trx[market].append(format_trx[1:])
            print(format_trx)

    def publish_place_trx(self, place_trx):
        trx_id = ""
        for trx in place_trx:
            if trx_id == trx["trx_id"]:
                continue
            prefix = get_prefix(trx["quote"], trx["base"])
            trx_id = trx["trx_id"]
            if trx["cancel"]:
                trx["type"] = "cancel " + trx["type"]
            format_trx = [prefix, trx["block"], trx["timestamp"],
                          trx["type"], trx["price"], trx["amount"]]
            self.myPublish(
                u'bts.orderbook.%s.order' % (format_trx[0]), format_trx[1:])
            self.myPublish(u'bts.orderbook.order', format_trx)
            market = format_trx[0]
            if market not in self.place_trx:
                self.place_trx[market] = []
            self.place_trx[market].append(format_trx[1:])
            print(format_trx)

    def publish_order_book(self):
        for quote, base in self.market_list:
            prefix = get_prefix(quote, base)
            order_book = self.market.get_order_book(
                quote, base)
            order_book["bids"] = order_book["bids"][:10]
            order_book["asks"] = order_book["asks"][:10]
            if (prefix not in self.order_book or
               self.order_book[prefix] != order_book):
                self.order_book[prefix] = order_book
                self.myPublish(
                    u'bts.orderbook.%s' % prefix, order_book)

    def execute(self):
        client_info = self.bts_client.get_info()
        height_now = int(client_info["blockchain_head_block_num"])
        if(self.height < height_now):
            time_stamp = client_info["blockchain_head_block_timestamp"]
            self.myPublish(u'bts.blockchain.info',
                           {"height": height_now, "time_stamp": time_stamp})
            self.publish_order_book()
        # disable trx publish, get from pusher.btsbots.com
        #while self.height < height_now:
        #    self.height += 1
        #    trxs = self.bts_client.get_block_transactions(
        #        self.height)
        #    recs = self.market.get_order_deal_rec(self.height)
        #    self.publish_deal_trx(recs)
        #    recs = self.market.get_order_place_rec(trxs)
        #    self.publish_place_trx(recs)
        #    self.market.update_order_owner(recs)
