#!/usr/bin/env python

from importlib import import_module
import logging
import pathlib

import requests
import vk_requests
from vk_requests.exceptions import VkAPIError

from ubotvk import utils
from ubotvk.database import Database
from ubotvk.config import Config


pathlib.Path(Config.LOG_DIR).mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
    level=logging.WARNING,
    filename=Config.LOG_DIR+'bot',
    filemode='a'
)


class Bot:
    """
    Creates vk-requests.API instance with credentials from config.json,
    Gets Long Poll server,
    Continuously gets updates from VK,
    Calls features from config.INSTALLED_FEATURES on update
    """

    def __init__(self):
        print('Bot instance was initialized.')
        self.vk_api = vk_requests.create_api(login=Config.LOGIN, password=Config.PASSWORD,
                                             app_id=Config.APP_ID, api_version='5.80', scope='messages,offline')
        self.vk_id = self.vk_api.users.get()[0]['id']
        logging.info('Created VK API session. Bot`s ID = {}'.format(self.vk_id))
        print('Created VK API session. Bot`s ID = {}'.format(self.vk_id))

        self.db = Database('data/bot_db.sqlite3')
        self.dict_feature_chats = self.db.get_feature_chats_dict()
        self._chats = self.db.get_chats()
        print('Database loaded.')
        logging.debug('Database loaded. chats = {chats}; dict_feature_chats = {d_f_c}'.
                      format(chats=self._chats, d_f_c=self.dict_feature_chats))

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

        if 'failed' not in res:
            return res

        elif res['failed'] == 1:
            self.ts = res['ts']
            logging.warning('VK returned lp response with "failed" == 1, updated self.ts value')
        elif res['failed'] in [2, 3]:
            self.key, self.server, self.ts = self.get_long_poll_server()
            logging.warning('VK returned lp response with "failed" == 2, updated Long Poll server')
        elif res['failed'] == 4:
            raise ValueError('Wrong Long Poll version')
        else:
            raise Exception('VK returned lp response with unexpected "failed" value. Response: {}'.format(res))

    def handle_update(self, update):
        logging.info('Got new update: {}'.format(update))

        self.check_for_commands(update)

        self.check_for_service_message(update)

        for feature in self.features:
            try:
                if update[0] in self.features[feature].triggered_by:
                    if int(update[3] - 2e9) in self.dict_feature_chats[feature]:
                        self.features[feature](update)
                        logging.debug('Called {f} with {u}'.format(f=feature, u=update))

            except VkAPIError as api_err:
                logging.error('VkAPIError occurred, was caught, but not handled.', exc_info=True)
                # if api_err.code == TODO: Proper handling of VK API errors

    def import_features(self) -> dict:
        """
        imports and initialises features listed in "installed_features" from config.json
        :return: dict(keys: strings from Config.INSTALLED_FEATURES, values: feature objects)
        """
        features = {}
        for feature in Config.INSTALLED_FEATURES:
            features[feature] = (import_module('ubotvk.bot_features.' + feature).__init__(self.vk_api))
            logging.debug('Initialized {}'.format(feature))
        logging.info('Initialized all {} features'.format(len(features)))
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
        if feature in Config.INSTALLED_FEATURES and chat_id not in self.dict_feature_chats[feature]:
            self.db.add_feature(chat_id, feature)
            self.dict_feature_chats[feature].append(chat_id)
            try:
                self.features[feature].new_chat(chat_id)
                logging.debug('{}.new_chat() was called'.format(feature))
            except AttributeError:
                logging.debug('{} has no new_chat method'.format(feature))

            self.vk_api.messages.send(peer_id=int(chat_id+2e9), message='Включил {} для этого чата'.format(feature))
            logging.info('Added new feature {f} to chat {c}'.format(f=command[0], c=str(chat_id)))

        else:
            self.vk_api.messages.send(peer_id=int(chat_id+2e9),
                                      message='Нет такой функции или она уже включена: "{}"'.format(feature))
            # TODO отправлять список доступных фич

    def command_remove(self, command, chat_id):
        feature = command[0]
        if feature in Config.INSTALLED_FEATURES and chat_id in self.dict_feature_chats[feature]:
            self.db.remove_feature(chat_id, feature)
            self.dict_feature_chats[feature].remove(chat_id)
            try:
                self.features[feature].remove_chat(chat_id)
                logging.debug('{}.remove_chat() was called'.format(feature))
            except AttributeError:
                logging.debug('{} has no remove_chat method'.format(feature))

            self.vk_api.messages.send(peer_id=int(chat_id+2e9), message='Отключил {} для этого чата'.format(feature))
            logging.info('Removed feature {f} from chat {c}'.format(f=command[0], c=str(chat_id)))
        else:
            self.vk_api.messages.send(peer_id=int(chat_id+2e9),
                                      message='Нет такой функции или она уже отключена: "{}"'.format(feature))
            # TODO отправлять список включенных фич

    def new_chat(self, chat_id):
        self.db.add_chat(chat_id)
        self._chats.append(chat_id)

        for feature in Config.DEFAULT_FEATURES:
            self.dict_feature_chats[feature].append(chat_id)
        logging.info('Added new chat {}'.format(chat_id))

    def check_for_service_message(self, update):
        try:
            if update[0] == 4 and 'source_act' in update[6]:
                if update[6]['source_act'] == 'chat_invite_user':
                    logging.info('User was invited in update {}'.format(update))
                    self.new_member(int(update[3]-2e9), update[6]['source_mid'])

                if update[6]['source_act'] == 'chat_kick_user':
                    logging.info('User was kicked in update {}'.format(update))
                    self.remove_member(int(update[3]-2e9), update[6]['source_mid'])

        except IndexError as er:
            logging.warning('VK returned Long Poll update with code 4, but update[6] raised IndexError: {}'.format(er))

    def new_member(self, chat_id, user_id):
        for feature in Config.INSTALLED_FEATURES:
            try:
                self.features[feature].new_member(chat_id, user_id)
                logging.debug('Called new_member method of {}'.format(feature))

            except AttributeError:
                logging.debug('{} has no new_member method'.format(feature))

    def remove_member(self, chat_id, user_id):
        for feature in Config.INSTALLED_FEATURES:
            try:
                self.features[feature].remove_member(chat_id, user_id)
                logging.debug('Called remove_member method of {}'.format(feature))

            except AttributeError:
                logging.debug('{} has no remove_member method'.format(feature))

