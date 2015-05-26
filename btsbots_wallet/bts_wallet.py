# -*- coding: utf-8 -*-

#from bts.api import BTS
#import json
#import os


class BTSWallet(object):
    def __init__(self, client, protect_account=[]):
        self.protect_account = protect_account
        self.bts_client = client
        self.pusher = None
        self.balance = {}
        client_info = self.bts_client.get_info()
        self.height = int(client_info["blockchain_head_block_num"])
        self.accounts = None
        self.update_accounts()
        self.update_balance()
        self.trx = None
        self.update_trx()
        self.init_transaction()

    def myPublish(self, topic, event):
        if self.pusher:
            self.pusher.emit(topic, event, namespace="")

    def update_accounts(self):
        accounts = self.bts_client.list_accounts()
        for account in list(accounts):
            if account in self.protect_account:
                accounts.remove(account)
        if accounts != self.accounts:
            self.myPublish("account_list", accounts)
            self.accounts = accounts

    def get_all_account(self):
        return self.accounts

    def get_balance(self, account):
        if account not in self.balance:
            return {}
        else:
            return self.balance[account]

    def init_transaction(self):
        self.transaction = {}
        trxs = self.bts_client.get_transaction_history(limit=-50)
        for account in self.get_all_account():
            self.transaction[account] = \
                self.bts_client.format_transaction_history(account, trxs)

    def update_transaction(self, start, end):
        trxs = self.bts_client.get_transaction_history(
            limit=-500, start=start, end=end)
        if not trxs:
            return
        for account in self.get_all_account():
            if account not in self.transaction:
                self.transaction[account] = []
            format_trxs = \
                self.bts_client.format_transaction_history(account, trxs)
            if not format_trxs:
                continue
            self.transaction[account].extend(format_trxs)
            self.myPublish("user."+account+".transaction", format_trxs)

    def get_transaction(self, account):
        if account in self.transaction:
            return self.transaction[account]
        else:
            return []

    def update_balance(self):
        balance = self.bts_client.get_balance()
        for _account in self.get_all_account():
            if _account not in self.balance:
                self.balance[_account] = {"BTS":0}
            if _account not in balance:
                balance[_account] = {"BTS":0}
            if balance[_account] != self.balance[_account]:
                self.myPublish("user."+_account+".balance", balance[_account])
                self.balance[_account] = balance[_account]

    def transfer(self, trx):
        return self.bts_client.transfer(trx)

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
        self.update_transaction(self.height+1, height_now)
        self.height = height_now
