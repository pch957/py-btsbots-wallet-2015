# -*- coding: utf-8 -*-

from bts.api import BTS
import json
import os


class LightWallet(object):
    def __init__(self):
        config_file = os.getenv("HOME") + "/.python-bts/bts_client.json"
        fd_config = open(config_file)
        config_bts = json.load(fd_config)["client_default"]
        fd_config.close()

        self.bts_client = BTS(config_bts["user"], config_bts["password"],
                              config_bts["host"], config_bts["port"])
        self.pusher = None
        self.wallets = {}
        client_info = self.bts_client.get_info()
        self.height = int(client_info["blockchain_head_block_num"])

    def myPublish(self, topic, event):
        if self.pusher:
            self.pusher.emit(topic, event, namespace="")

    def get_wallet(self, address):
        if address not in self.wallets:
            wallet = self.init_wallet(address)
            if not wallet:
                return None
            self.wallets[address] = wallet
        return self.wallets[address]

    def init_wallet(self, address):
        wallet = {}
        wallet["address"] = address
        wallet["account"] = self.get_account(address)
        wallet["balance"] = self.get_balance(address)
        wallet["trx"] = self.get_trx(address)
        wallet["need_update_balance"] = False
        return wallet

    def get_account(self, address):
        account_info = self.bts_client.get_account_info(address)
        if account_info:
            return account_info["name"]
        else:
            return ""

    def get_balance(self, address):
        balances = self.bts_client.get_address_balances(address)
        if balances:
            return balances
        else:
            return {}

    def get_trx(self, address):
        trxs = []
        trxs_info = self.bts_client.request(
            "blockchain_list_address_transactions", [address]
        ).json()["result"]
        for trx_id in trxs_info:
            _trx = trxs_info[trx_id]["trx"]
            _op = _trx["trx"]['operations'][0]
            if _op["type"] == 'update_feed_op_type' or \
                    _op["type"] == 'register_account_op_type' or \
                    _op["type"] == 'update_account_op_type':
                continue
            trx = {}
            owner_from = ""
            owner_to = ""
            trx["memo"] = None
            for _op in _trx["trx"]['operations']:
                if _op["type"] == "withdraw_op_type":
                    balance_id = _op["data"]["balance_id"]
                    balance_info = self.bts_client.request(
                        "blockchain_get_balance", [balance_id]
                    ).json()["result"]
                    owner_from = balance_info["condition"]["data"]["owner"]
                    continue
                if _op["type"] == "deposit_op_type":
                    trx["asset"] = self.bts_client.get_asset_symbol(
                        _op["data"]["condition"]["asset_id"])
                    trx["amount"] = float(_op["data"]["amount"]) / \
                        self.bts_client.get_asset_precision(trx["asset"])
                    if "owner" in _op["data"]["condition"]["data"]:
                        owner_to = _op["data"]["condition"]["data"]["owner"]
                    if "memo" in _op["data"]["condition"]["data"]:
                        trx["memo"] = _op["data"]["condition"]["data"]["memo"]
                    continue
            trx["trx_id"] = trx_id[:8]
            trx["block_num"] = _trx["chain_location"]["block_num"]
            trx["timestamp"] = self.bts_client.get_block_timestamp(
                trx["block_num"])
            trx["fee_asset"] = \
                self.bts_client.get_asset_symbol(_trx["fees_paid"][0][0])
            trx["fee_amount"] = float(_trx["fees_paid"][0][1]) / \
                self.bts_client.get_asset_precision(_trx["fees_paid"][0][0])

            if owner_from == address:
                trx["account"] = self.get_account(owner_to)
                trx["type"] = "send"
            elif owner_to == address:
                trx["account"] = self.get_account(owner_from)
                trx["type"] = "receive"
            trxs.append(trx)
        return sorted(trxs, key=lambda item:item["block_num"])

    #def init_transaction(self):
    #    self.transaction = {}
    #    trxs = self.bts_client.get_transaction_history(limit=-50)
    #    for account in self.get_all_account():
    #        self.transaction[account] = \
    #            self.bts_client.format_transaction_history(account, trxs)

    #def update_transaction(self, start, end):
    #    trxs = self.bts_client.get_transaction_history(
    #        limit=-500, start=start, end=end)
    #    if not trxs:
    #        return
    #    for account in self.get_all_account():
    #        if account not in self.transaction:
    #            self.transaction[account] = []
    #        format_trxs = \
    #            self.bts_client.format_transaction_history(account, trxs)
    #        if not format_trxs:
    #            continue
    #        self.transaction[account].extend(format_trxs)
    #        self.myPublish("user."+account+".transaction", format_trxs)

    def update_trx(self, trxs, virtual_trxs):
        for _trx in trxs:
            _op = _trx[1]["trx"]['operations'][0]
            if _op["type"] == 'update_feed_op_type' or \
                    _op["type"] == 'register_account_op_type' or \
                    _op["type"] == 'update_account_op_type':
                continue
            trx = {}
            owner_from = ""
            owner_to = ""
            trx["memo"] = None
            for _op in _trx[1]["trx"]['operations']:
                if _op["type"] == "withdraw_op_type":
                    balance_id = _op["data"]["balance_id"]
                    balance_info = self.bts_client.request(
                        "blockchain_get_balance", [balance_id]
                    ).json()["result"]
                    owner_from = balance_info["condition"]["data"]["owner"]
                    continue
                if _op["type"] == "deposit_op_type":
                    trx["asset"] = self.bts_client.get_asset_symbol(
                        _op["data"]["condition"]["asset_id"])
                    trx["amount"] = float(_op["data"]["amount"]) / \
                        self.bts_client.get_asset_precision(trx["asset"])
                    if "owner" in _op["data"]["condition"]["data"]:
                        owner_to = _op["data"]["condition"]["data"]["owner"]
                    if "memo" in _op["data"]["condition"]["data"]:
                        trx["memo"] = _op["data"]["condition"]["data"]["memo"]
                    continue
            if owner_from not in self.wallets and owner_to not in self.wallets:
                continue

            trx["trx_id"] = _trx[0][:8]
            trx["block_num"] = _trx[1]["chain_location"]["block_num"]
            trx["timestamp"] = self.bts_client.get_block_timestamp(
                trx["block_num"])
            trx["fee_asset"] = \
                self.bts_client.get_asset_symbol(_trx[1]["fees_paid"][0][0])
            trx["fee_amount"] = float(_trx[1]["fees_paid"][0][1]) / \
                self.bts_client.get_asset_precision(_trx[1]["fees_paid"][0][0])

            if owner_from in self.wallets:
                trx_tmp = trx.copy()
                trx_tmp["account"] = self.get_account(owner_to)
                trx_tmp["type"] = "send"
                self.myPublish("user."+owner_from+".transaction", trx_tmp)
                self.wallets[owner_from]["trx"].append(trx_tmp)
                self.wallets[owner_from]["need_update_balance"] = True

            if owner_to in self.wallets and owner_to != owner_from:
                trx_tmp = trx.copy()
                trx_tmp["account"] = self.get_account(owner_from)
                trx_tmp["type"] = "receive"
                self.myPublish("user."+owner_to+".transaction", trx_tmp)
                self.wallets[owner_to]["trx"].append(trx_tmp)
                self.wallets[owner_to]["need_update_balance"] = True

    def update_balance(self):
        for address in self.wallets:
            if self.wallets[address]["need_update_balance"]:
                self.wallets[address]["balance"] = self.get_balance(address)
                self.wallets[address]["need_update_balance"] = False
                self.myPublish(
                    "user."+address+".balance",
                    self.wallets[address]["balance"])

    def transfer(self, trx):
        pass

    def execute(self):
        client_info = self.bts_client.get_info()
        height_now = int(client_info["blockchain_head_block_num"])
        if(height_now <= self.height):
            return

        time_stamp = client_info["blockchain_head_block_timestamp"]
        self.myPublish(u'bts.blockchain.info',
                       {"height": height_now, "time_stamp": time_stamp})
        while self.height < height_now:
            self.height += 1
            trxs = self.bts_client.get_block_transactions(
                self.height)
            #virtual_trxs = self.market.get_order_deal_rec(self.height)
            virtual_trxs = []
            self.update_trx(trxs, virtual_trxs)
        self.update_balance()
