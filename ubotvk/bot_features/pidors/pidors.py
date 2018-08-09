import sqlite3
import os
import random
import time
import logging

from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler

from ubotvk import utils
from ubotvk.config import Config

DATABASE_FILE = os.path.join(os.path.dirname(__file__), 'pidors.sqlite3')


class Pidors:
    def __init__(self, vk_api):
        self._vk = vk_api
        self._chats_database = Database()

        scheduler = BackgroundScheduler(timezone=timezone('Europe/Moscow'))
        scheduler.add_job(self.pidors_job, 'cron', minute='*')
        scheduler.start()

        # Long Poll codes that should trigger this feature. More info: https://vk.com/dev/using_longpoll
        self.triggered_by = [4]

    def __call__(self, update):
        if (update[2] & 2) == 0:  # Check if message is inbox
            command = utils.command_in_string(update[5], ['toppidor', 'топпидор', 'njggbljh', 'ещззшвщк',
                                                          'пидор', 'pidor', 'зшвщк', 'njggbljh'])
            if command and command[0] in ['toppidor', 'топпидор', 'njggbljh', 'ещззшвщк']:
                self.top_pidor(int(update[3]-2e9))

    def top_pidor(self, chat_id):
        pidors = self._chats_database.get_pidors(chat_id)
        if pidors:
            response = 'Топ пидоров за все время:\n'
            count = 1
            total_pidor_count = 0
            for pidor in pidors:
                response += '{count}. {name} - {pidor_count}\n'.format(count=count, name=pidor[2], pidor_count=pidor[3])
                count += 1
                total_pidor_count += pidor[3]

            response += '\nСредний показатель пидорства: ' + str(total_pidor_count / (count - 1))
            self._vk.messages.send(peer_id=int(chat_id+2e9), message=response)
        else:
            self._vk.messages.send(peer_id=int(chat_id+2e9), message='Случилась какая-то хуйня, в базе данных пидоров '
                                                                     'не было найдено ни одного пидора из этого чата.\n'
                                                                     'Скорее всего в этом виноват [id{}|он], '
                                                                     'если его нет в чате - напишите ему в ЛС, что он '
                                                                     'долбоеб и попробуйте еще раз.'
                                                                     .format(Config.MAINTAINER_VK_ID))

            logging.warning('Pidors.db is empty for chat {}, but bot.db says that this feature is on. '
                            'Calling Pidors.new_chat method, the Database will be reset'.format(chat_id))
            self.new_chat(chat_id)

    def pidors_job(self):   # TODO use VK execute
        chats = self._chats_database.chats
        start_time, end_time = 0, 1
        for chat in chats:
            time_delta = end_time - start_time
            if time_delta < 1:
                logging.debug('Sleeping for {} seconds'.format(1-time_delta))
                time.sleep(1-time_delta)
            start_time = time.time()
            self.choose_pidor(chat)
            end_time = time.time()

    def choose_pidor(self, chat):
        members = self._vk.messages.getConversationMembers(peer_id=int(chat + 2e9))['profiles']
        pidor = random.choice(members)
        self._chats_database.increment_pidor_count(chat, pidor['id'])
        message = """Пидор сегодняшнего дня: {} {}. Поздравляем!""".format(pidor['first_name'], pidor['last_name']) # TODO push
        self._vk.messages.send(peer_id=int(2e9+chat), message=message)

    def new_chat(self, chat_id):
        if chat_id not in self._chats_database.chats:
            if chat_id not in self._chats_database.get_all_chats():
                members = self._vk.messages.getConversationMembers(peer_id=int(chat_id + 2e9))['profiles']
                for member in members:
                    self._chats_database.add_member(chat_id, member)
                self._chats_database.add_chat(chat_id)
            else:
                self._chats_database.chat_on_again(chat_id)

    def remove_chat(self, chat_id):
        if chat_id in self._chats_database.chats:
            self._chats_database.remove_chat(chat_id)

    def new_member(self, chat_id, user_id):
        members = self._chats_database.get_all_members(chat_id)
        if chat_id in members:
            self._chats_database.member_came_back(chat_id, user_id)
            logging.debug('Member {} came back to chat {}'.format(user_id, chat_id))
        else:
            member = self._vk.users.get(user_ids=user_id)
            self._chats_database.add_member(chat_id, member)
            logging.debug('New member {} in chat {}'.format(user_id, chat_id))

    def remove_member(self, chat_id, user_id):
        self._chats_database.member_left(chat_id, user_id)


class Database:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.create_if_not_exists()
        self.chats = self.get_chats()

    def create_if_not_exists(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS Pidors 
                          (chat_id, user_id, user_name, user_pidor_count, user_is_in_chat)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS Chats (chat_id integer, feature_is_on integer)""")
        conn.commit()
        conn.close()

    def add_member(self, chat_id, member):
        _id = member['id']
        _full_name = member['first_name'] + ' ' + member['last_name']

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO Pidors (chat_id, user_id, user_name, user_pidor_count, user_is_in_chat)
                          VALUES (?, ?, ?, ?, 1)""", (chat_id, _id, _full_name, 0))
        conn.commit()
        conn.close()

    def member_came_back(self, chat_id, user_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""UPDATE Pidors SET user_is_in_chat=1 WHERE chat_id=? AND user_id=?""", (chat_id, user_id))
        conn.commit()
        conn.close()

    def member_left(self, chat_id, user_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""UPDATE Pidors SET user_is_in_chat=0 WHERE chat_id=? AND user_id=?""", (chat_id, user_id))
        conn.commit()
        conn.close()

    def get_all_members(self, chat_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT user_id FROM Pidors WHERE Pidors.chat_id=?""", (chat_id,))
        members = cursor.fetchall()
        conn.close()
        return [member[0] for member in members]

    def get_pidors(self, chat_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM Pidors WHERE Pidors.chat_id=? AND Pidors.user_is_in_chat=1""", (chat_id,))
        pidors = cursor.fetchall()
        conn.close()
        return pidors

    def increment_pidor_count(self, chat_id, user_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""UPDATE Pidors SET user_pidor_count = user_pidor_count + 1 WHERE chat_id=? AND user_id=?""",
                       (chat_id, user_id))
        conn.commit()
        conn.close()

    def get_chats(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT chat_id FROM Chats WHERE feature_is_on=1""")
        chats = cursor.fetchall()
        conn.close()
        return [chat[0] for chat in chats]

    def get_all_chats(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT chat_id FROM Chats""")
        chats = cursor.fetchall()
        conn.close()
        return [chat[0] for chat in chats]

    def add_chat(self, chat_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO Chats (chat_id, feature_is_on) VALUES (?, ?)""", (chat_id, 1))
        conn.commit()
        conn.close()
        self.chats.append(chat_id)

    def chat_on_again(self, chat_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""UPDATE Chats SET feature_is_on=1 WHERE chat_id=?""", (chat_id,))
        conn.commit()
        conn.close()
        self.chats.append(chat_id)

    def remove_chat(self, chat_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""UPDATE Chats SET feature_is_on=0 WHERE chat_id=?""", (chat_id,))
        conn.commit()
        conn.close()
        self.chats.remove(chat_id)

