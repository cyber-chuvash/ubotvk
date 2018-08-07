#!/usr/bin/env python

from importlib import import_module

import requests
import vk_requests
from vk_requests.exceptions import VkAPIError

from ubotvk import utils
from ubotvk.database import Database
from ubotvk.config import Config


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
        self.vk_id = self.vk_api.users.get()[0]['id']
        print(self.vk_id)

        self.db = Database('bot_db.sqlite3')
        self.dict_feature_chats = self.db.get_feature_chats_dict()
        self._chats = self.db.get_chats()

        self.features = self.import_features()

        self.key, self.server, self.ts = self.get_long_poll_server()

        while True:
            response = self.long_poll(self.server, self.key, self.ts)
            self.ts = response['ts']
            for update in response['updates']:
                self.handle_update(update)

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
        self.check_for_commands(update)

        for feature in self.features.keys():
            try:
                if update[0] in self.features[feature].triggered_by:
                    if int(update[3] - 2e9) in self.dict_feature_chats[feature]:
                        self.features[feature](update)

            except VkAPIError as api_err:
                print(api_err)
                # if api_err.code == TODO: Proper handling of VK API errors

    def import_features(self) -> dict:
        """
        imports and initialises features listed in "installed_features" from config.json
        :return: dict(keys: strings from Config.INSTALLED_FEATURES, values: feature objects)
        """
        features = {}
        for feature in Config.INSTALLED_FEATURES:
            features[feature] = (import_module('bot_features.' + feature).__init__(self.vk_api))
        return features

    def check_for_commands(self, update):
        if update[0] == 4 and (update[2] & 2) == 0:
            if int(update[3] - 2e9) not in self._chats:
                self.new_chat(int(update[3] - 2e9))

            if update[5].strip()[:len(str(self.vk_id))+4] == '[id{}|'.format(self.vk_id):
                command = utils.command_in_string(update[5].strip(), ['add', 'remove'])
                if command:
                    self.handle_command(command, int(update[3] - 2e9))

    def handle_command(self, command, chat_id):
        if command[0] == 'add':
            self.command_add(command[1:], chat_id)

        elif command[0] == 'remove':
            self.command_remove(command[1:], chat_id)

    def command_add(self, command, chat_id):
        feature = command[0]
        if feature in Config.INSTALLED_FEATURES:
            self.db.add_feature(chat_id, feature)
            self.dict_feature_chats[feature].append(chat_id)
            print('Added new feature {f} to chat {c}'.format(f=command[0], c=str(chat_id)))

    def command_remove(self, command, chat_id):
        feature = command[0]
        if feature in Config.INSTALLED_FEATURES and \
                feature in self.dict_feature_chats.keys():
            self.db.remove_feature(chat_id, feature)
            self.dict_feature_chats[feature].remove(chat_id)
            print('Removed feature {f} from chat {c}'.format(f=command[0], c=str(chat_id)))

    def new_chat(self, chat_id):
        self.db.add_chat(chat_id)
        self._chats.append(chat_id)

        for feature in Config.DEFAULT_FEATURES:
            self.dict_feature_chats[feature].append(chat_id)

        for feature in self.features.keys():
            try:
                self.features[feature].new_chat(chat_id)
            except AttributeError:
                print('{} has no new_chat method'.format(feature))

        print('Added new chat {c}'.format(c=str(chat_id)))


if __name__ == '__main__':
    bot = Bot()
