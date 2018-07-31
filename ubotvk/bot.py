#!/usr/bin/env python

from importlib import import_module
import sqlite3
import json
import os

import requests
import vk_requests
from vk_requests.exceptions import VkAPIError


class Config:
    _conf = json.loads(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.json'), 'r').read())

    LOGIN = str(_conf['login'])
    PASSWORD = str(_conf['password'])
    APP_ID = int(_conf['app_id'])
    INSTALLED_FEATURES = tuple(_conf['installed_features'])


class Bot:
    """
    Creates vk-requests.API instance with credentials from config.json,
    Gets Long Poll server,
    Continuously gets updates from VK,
    Calls features from config.INSTALLED_FEATURES on update
    """

    def __init__(self):
        self.vk_api = vk_requests.create_api(login=Config.LOGIN, password=Config.PASSWORD,
                                             app_id=Config.APP_ID, api_version='5.80', scope='messages,offline')
        self.db = Database('bot_db.sqlite3')
        self.dict_feature_chats = self.db.get_feature_chats_dict()

        self.features = self.import_features()

        self.key, self.server, self.ts = self.get_long_poll_server()

        while True:
            try:
                response = self.long_poll(self.server, self.key, self.ts)
                self.ts = response['ts']

                for update in response['updates']:
                    self.handle_update(update)

            except VkAPIError as api_err:
                print(api_err)
                # if api_err.code == TODO: Proper handling of VK API errors

    def get_long_poll_server(self):
        lps = self.vk_api.messages.getLongPollServer(need_pts=0, lp_version=3)
        return lps['key'], lps['server'], lps['ts']

    def long_poll(self, server, key, ts, wait=25, mode=2, version=3):
        """
        Gets updates from VK Long Poll server
        :param server: str: VK Long Poll server URI returned by messages.getLongPollServer()
        :param key: str: Secret session key returned by messages.getLongPollServer()
        :param ts: int: Last event id
        :param wait: int: Seconds to wait before returning empty updates list
        :param mode: int: Additional options for request. More info: https://vk.com/dev/using_longpoll
        :param version: int: Long Poll version. More info: https://vk.com/dev/using_longpoll
        :return: dict: {'ts': 00000000, 'updates': [list of updates]}
        """

        payload = {'act': 'a_check', 'key': key, 'ts': ts, 'wait': wait, 'mode': mode, 'version': version}
        request = requests.get('https://{server}?'.format(server=server), params=payload)
        res = request.json()

        if 'failed' not in res.keys():
            return res

        elif res['failed'] == 1:
            self.ts = res['ts']
        elif res['failed'] in [2, 3]:
            self.key, self.server, self.ts = self.get_long_poll_server()
        elif res['failed'] == 4:
            raise ValueError('Wrong Long Poll version')
        else:
            raise Exception

    def handle_update(self, update):
        for feature in self.features:
            if update[0] in feature.triggered_by:
                feature(update)

    def import_features(self) -> list:
        """
        imports and initialises features listed in "installed_features" from config.json
        :return: list of feature objects
        """
        features = []
        for feature in Config.INSTALLED_FEATURES:
            features.append(import_module('bot_features.'+feature).__init__(self.vk_api,
                                                                            self.dict_feature_chats[feature]))
        return features


class Database:
    def __init__(self, db_file):
        self._db_file = db_file
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self):
        conn = sqlite3.connect(self._db_file)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS features (chat_id integer, enabled_features text)""")
        conn.commit()
        conn.close()

    def get_feature_chats_dict(self, installed_features=Config.INSTALLED_FEATURES) -> dict:
        conn = sqlite3.connect(self._db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT chat_id, enabled_features FROM features""")
        features = cursor.fetchall()

        features_dict = {}
        for item in features:
            features_dict[item[0]] = json.loads(item[1])

        feature_chats_dict = {}
        for feature in installed_features:
            feature_chats_dict[feature] = [chat for chat in features_dict.keys()
                                           if feature in features_dict[chat]]

        return feature_chats_dict

    def add_chat(self, chat_id: int):
        assert isinstance(chat_id, int)

        conn = sqlite3.connect(self._db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT chat_id FROM features WHERE chat_id=?""", (chat_id,))
        sel = cursor.fetchone()
        if sel is None or chat_id not in sel[0]:
            cursor.execute("""INSERT INTO features (chat_id, enabled_features) VALUES (?, ?)""",
                           (chat_id, json.dumps([])))
            conn.commit()
        conn.close()

    def add_feature(self, chat_id: int, feature: str):
        assert isinstance(chat_id, int)
        assert isinstance(feature, str)

        conn = sqlite3.connect(self._db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (chat_id,))
        enabled_features = cursor.fetchone()
        if enabled_features[0]:
            features = json.loads(enabled_features[0])
            if feature not in features:
                features.append(feature)
            else:
                conn.close()
                return
        else:
            features = [feature]

        cursor.execute("""UPDATE features SET enabled_features=? WHERE chat_id=?""", (json.dumps(features), chat_id))
        conn.commit()
        conn.close()

    def remove_feature(self, chat_id: int, feature: str):
        assert isinstance(chat_id, int)
        assert isinstance(feature, str)

        conn = sqlite3.connect(self._db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (chat_id,))
        enabled_features = json.loads(cursor.fetchone()[0])
        if enabled_features and feature in enabled_features:
            enabled_features.remove(feature)
        else:
            raise AttributeError

        cursor.execute("""UPDATE features SET enabled_features=? WHERE chat_id=?""",
                       (json.dumps(enabled_features), chat_id))
        conn.commit()
        conn.close()


if __name__ == '__main__':

    bot = Bot()
