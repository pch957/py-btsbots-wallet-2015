# -*- coding: utf-8 -*-

#from bts.api import BTS
#import json
#import os


class BTSWallet(object):
    def __init__(self, client):
        self.bts_client = client
        self.pusher = None
        self.account = None
        self.balance = None
        client_info = self.bts_client.get_info()
        self.height = int(client_info["blockchain_head_block_num"])
        self.accounts = None
        self.update_accounts()
        self.trx = None
        self.update_trx()

    def myPublish(self, topic, event):
        if self.pusher:
            self.pusher.emit(topic, event, namespace="")

    def get_account(self):
        if self.account in self.accounts:
            return self.account
        else:
            return None

    def get_all_account(self):
        return self.accounts

    def set_account(self, account):
        if account in self.accounts:
            if account != self.account:
                self.account = account
                self.update_balance()
            return True
        else:
            return False

    def update_balance(self):
        account = self.get_account()
        if account is None:
            return None
        balance = self.bts_client.get_balance(account)
        if balance != self.balance:
            self.myPublish("balance", balance)
            self.balance = balance

    def update_accounts(self):
        accounts = self.bts_client.list_accounts()
        if accounts != self.accounts:
            self.myPublish("account_list", accounts)
            self.accounts = accounts

    def update_trx(self, start=0, end=-1):
        pass
        #trx = self.bts_client.get_trx()
        #if trx is not None:
        #    self.trx.extend(trx)
        #    self.myPublish("trx", trx)

    def execute(self):
        client_info = self.bts_client.get_info()
        height_now = int(client_info["blockchain_head_block_num"])
        if(height_now <= self.height):
            return

        self.update_balance()
        self.update_accounts()
        self.update_trx()
        self.height = height_now
