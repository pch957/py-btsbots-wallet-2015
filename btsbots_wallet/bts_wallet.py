# -*- coding: utf-8 -*-

#from bts.api import BTS
#import json
#import os


class BTSWallet(object):
    def __init__(self, client):
        self.bts_client = client
        self.pusher = None
        self.balance = self.get_balance()
        client_info = self.bts_client.get_info()
        self.height = int(client_info["blockchain_head_block_num"])
        self.trx = self.get_trx()

    def myPublish(self, topic, event):
        if self.pusher:
            self.pusher.emit(topic, event, namespace="")

    def get_balance(self):
        return self.bts_client.get_balance()

    def get_account(self):
        return "baozi"

    def get_trx(self, start=0, end=-1):
        pass
        #return self.bts_client.get_trx()

    def execute(self):
        client_info = self.bts_client.get_info()
        height_now = int(client_info["blockchain_head_block_num"])
        if(height_now <= self.height):
            return
        balance = self.get_balance()
        if balance != self.balance:
            self.myPublish("balance", balance)
            self.balance = balance
        trx = self.get_trx(self.height+1, height_now)
        if trx is not None:
            self.trx.extend(trx)
            self.myPublish("trx", trx)
        self.height = height_now
