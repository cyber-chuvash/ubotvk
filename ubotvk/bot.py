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


if Config.LOG_DIR:  # Write to file if specified
    pathlib.Path(Config.LOG_DIR).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
        level=logging.getLevelName(Config.LOG_LEVEL),
        filename=Config.LOG_DIR+'ubotvk.log',
        filemode='a'
    )
else:   # Write to stderr if not
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
        level=logging.getLevelName(Config.LOG_LEVEL),
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

        self.logger = logging

        self.features = self.import_features()

        self.key, self.server, self.ts = self.get_long_poll_server()

    def start_loop(self):
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
            logging.info('VK returned lp response with "failed" == 1, updated self.ts value')
            return self.long_poll(self.server, self.key, self.ts)
        elif res['failed'] in [2, 3]:
            self.key, self.server, self.ts = self.get_long_poll_server()
            logging.info(f'VK returned lp response with "failed" == {res["failed"]}, updated Long Poll server')
            return self.long_poll(self.server, self.key, self.ts)
        elif res['failed'] == 4:
            raise ValueError('Wrong Long Poll version')
        else:
            raise Exception('VK returned lp response with unexpected "failed" value. Response: {}'.format(res))

    def handle_update(self, update):
        logging.debug('Got new update: {}'.format(update))

        if not Config.DEBUG:
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

        elif update[0] == 4 and int(update[3] - 2e9) in Config.DEBUG_ALLOWED_CHATS:
            self.check_for_commands(update)
            self.check_for_service_message(update)
            for feature in self.features:
                if update[0] in self.features[feature].triggered_by:
                    if int(update[3] - 2e9) in self.dict_feature_chats[feature]:
                        self.features[feature](update)
                        logging.debug('Called {f} with {u}'.format(f=feature, u=update))

    def import_features(self) -> dict:
        """
        imports and initialises features listed in "installed_features" from config.json or os.environ
        if none specified, imports all modules from ubotvk/bot_features/
        :return: dict(keys: strings from Config.INSTALLED_FEATURES, values: feature objects)
        """
        features = {}
        if not Config.INSTALLED_FEATURES:
            import pkgutil
            import os
            Config.INSTALLED_FEATURES = list(
                module for _, module, _ in pkgutil.iter_modules([os.path.dirname(__file__) + '/bot_features']))

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
                command = utils.command_in_string(update[5].strip(), ['add', 'on', 'remove', 'off', 'help', 'хелп'])
                if command:
                    self.handle_command(command, int(update[3] - 2e9))

    def handle_command(self, command, chat_id):
        if command[0] in ['add', 'on']:
            self.command_add(command[1:], chat_id)

        elif command[0] in ['remove', 'off']:
            self.command_remove(command[1:], chat_id)

        elif command[0] in ['help', 'хелп']:
            self.command_help(chat_id)

    def command_add(self, command, chat_id):
        feature = command[0]
        if feature in Config.INSTALLED_FEATURES:
            if chat_id not in self.dict_feature_chats[feature]:
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
                self.vk_api.messages.send(
                    peer_id=int(chat_id+2e9),
                    message=f'Функция уже включена.\n'
                            f'Доступные функции: {", ".join([f for f in Config.INSTALLED_FEATURES])}.'
                )
        else:
            self.vk_api.messages.send(
                peer_id=int(chat_id+2e9),
                message=f'Нет такой функции.\n'
                f'Доступные функции: {", ".join([f for f in Config.INSTALLED_FEATURES])}.'
            )

    def command_remove(self, command, chat_id):
        feature = command[0]
        if feature in Config.INSTALLED_FEATURES:
            if chat_id in self.dict_feature_chats[feature]:
                if feature not in Config.DEFAULT_FEATURES:
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
                self.vk_api.messages.send(
                    peer_id=int(chat_id + 2e9),
                    message=
                    f'Функция уже отключена.\n'
                    f'Включенные функции: '
                    f'{", ".join([f for f in self.dict_feature_chats if chat_id in self.dict_feature_chats[f]])}.'
                )
        else:
            self.vk_api.messages.send(
                peer_id=int(chat_id+2e9),
                message=f'Нет такой функции.\n'
                f'Включенные функции: '
                f'{", ".join([f for f in self.dict_feature_chats if chat_id in self.dict_feature_chats[f]])}.'
            )

    def command_help(self, chat_id):
        self.vk_api.messages.send(
            peer_id=int(chat_id + 2e9),
            message=f'Включить функцию: @[id{self.vk_id}|bot] on <название функции>\n'
                    f'Отключить функцию: @[id{self.vk_id}|bot] off <название функции>\n'
                    f'Отправить это сообщение еще раз: @[id{self.vk_id}|bot] help\n\n'
                    f'Список доступных функций: {", ".join([f for f in Config.INSTALLED_FEATURES])}.'
        )

    def new_chat(self, chat_id):
        self.db.add_chat(chat_id)
        self._chats.append(chat_id)

        for feature in Config.DEFAULT_FEATURES:
            self.dict_feature_chats[feature].append(chat_id)

        self.vk_api.messages.send(
            peer_id=int(chat_id+2e9),
            message='а'
        )
        self.command_help(chat_id)

        logging.info('Added new chat {}'.format(chat_id))

    def check_for_service_message(self, update):
        try:
            if update[0] == 4 and 'source_act' in update[6]:
                if update[6]['source_act'] == 'chat_invite_user' and not update[6]['source_mid'] == str(self.vk_id):
                    logging.info('User was invited in update {}'.format(update))
                    self.new_member(int(update[3]-2e9), int(update[6]['source_mid']))

                if update[6]['source_act'] == 'chat_kick_user' and not update[6]['source_mid'] == str(self.vk_id):
                    logging.info('User was kicked in update {}'.format(update))
                    self.remove_member(int(update[3]-2e9), int(update[6]['source_mid']))

                if update[6]['source_act'] == 'chat_invite_user_by_link':
                    if update[6]['from'] == str(self.vk_id):
                        logging.info('Bot joined the conversation in update {}'.format(update))
                        if int(update[3] - 2e9) not in self._chats:
                            self.new_chat(int(update[3]-2e9))
                    else:
                        logging.info('User joined the conversation in update {}'.format(update))
                        self.new_member(int(update[3]-2e9), int(update[6]['from']))

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

    def crash_handler(self, exc=None):
        try:
            self.vk_api.messages.send(peer_id=Config.MAINTAINER_VK_ID,
                                      message=f"Bot crashed, check logs. Exception info:\n{exc}")
        except Exception:
            pass

