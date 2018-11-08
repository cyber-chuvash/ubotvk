import sqlite3
import random
import time
import logging

from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from vk_requests.exceptions import VkAPIError

from ubotvk import utils
# from ubotvk.config import Config

DATABASE_FILE = 'data/pidors.sqlite3'
TOP_EMOJI = {1: '🏳‍🌈️🔥', 2: '🍑🍌', 3: '👬💖', 4: '🌚🌝', 5: '🐔💞'}


class Pidors:
    def __init__(self, vk_api):
        self._vk = vk_api
        self._vk_id = self._vk.users.get()[0]['id']
        self._chats_database = Database()

        scheduler = BackgroundScheduler(timezone=timezone('Europe/Moscow'))
        scheduler.add_job(self.pidors_job, 'cron', hour='8')
        scheduler.start()

        # Long Poll codes that should trigger this feature. More info: https://vk.com/dev/using_longpoll
        self.triggered_by = [4]

    def __call__(self, update):
        if (update[2] & 2) == 0:  # Check if message is inbox
            command = utils.command_in_string(update[5], ['toppidor', 'топпидор', 'njggbljh', 'ещззшвщк',
                                                          'пидор', 'pidor', 'зшвщк', 'gbljh'])
            if command:
                if command[0] in ['toppidor', 'топпидор', 'njggbljh', 'ещззшвщк']:
                    self.top_pidor(int(update[3]-2e9))

                if command[0] in ['пидор', 'pidor', 'зшвщк', 'gbljh']:
                    self.pidor(int(update[3]-2e9))

    def top_pidor(self, chat_id):
        pidors = self._vk.messages.getConversationMembers(peer_id=int(chat_id+2e9), fields='id')['profiles']

        for pidor in pidors:
            pidor['pidor_count'] = self._chats_database.get_user_count(pidor['id'])

        pidors = sorted(pidors, key=lambda x: x['pidor_count'], reverse=True)

        response = 'Рейтинг пидоров за все время:\n'
        count = 1
        for p in pidors:
            response += \
                f'{TOP_EMOJI.get(count, str(count)+".")} {p["first_name"]} {p["last_name"]} - {p["pidor_count"]}\n'
            count += 1

        self._vk.messages.send(peer_id=int(chat_id + 2e9), message=response)

        # pidors = self._chats_database.get_pidors(chat_id)   # TODO get list from vk
        # if pidors:
        #     response = 'Рейтинг пидоров за все время:\n'
        #     count = 1
        #     total_pidor_count = 0
        #     for pidor in pidors:
        #         response += f'{TOP_EMOJI.get(count, str(count)+".")} {pidor[2]} - {pidor[3]}\n'
        #         count += 1
        #         total_pidor_count += pidor[3]
        #     # response += '\nСредний показатель пидорства: ' + str(total_pidor_count / (count - 1))
        #     self._vk.messages.send(peer_id=int(chat_id+2e9), message=response)
        # else:
        #     self._vk.messages.send(peer_id=int(chat_id+2e9), message='Случилась какая-то хуйня, в базе данных пидоров '
        #                                                              'не было найдено ни одного пидора из этого чата.\n'
        #                                                              'Скорее всего в этом виноват [id{}|он], '
        #                                                              'если его нет в чате - напишите ему в ЛС, что он '
        #                                                              'долбоеб и попробуйте еще раз.'
        #                                                              .format(Config.MAINTAINER_VK_ID))
        #
        #     logging.warning('{db} is empty for chat {c}, but bot.db says that this feature is on. '
        #                     'Calling Pidors.new_chat method, the Database will be reset'.format(db=DATABASE_FILE,
        #                                                                                         c=chat_id))
        #     self.new_chat(chat_id)

    def pidor(self, chat_id):
        pidor_id = self._chats_database.get_last_pidor(chat_id)
        if pidor_id is not None:
            count = self._chats_database.get_user_count(pidor_id)
            user = self._vk.users.get(user_ids=pidor_id)[0]
            response = """Сегодня пидором в {c} раз был избран {f_name} {l_name}."""\
                       .format(c=count, f_name=user['first_name'], l_name=user['last_name'])
        else:
            response = "В этом чате еще никто не был избран пидором"

        self._vk.messages.send(peer_id=int(chat_id+2e9), message=response)

    def pidors_job(self):   # TODO use VK execute
        chats = self._chats_database.chats
        logging.debug(f'Contents of chats list: {chats}')
        start_time, end_time = 0, 1
        for chat in chats:
            time_delta = end_time - start_time
            if time_delta < 1:
                logging.debug('Sleeping for {} seconds'.format(1-time_delta))
                time.sleep(1-time_delta)
            start_time = time.time()
            try:
                logging.debug(f'Choosing pidor for chat {chat}')
                self.choose_pidor(chat)
            except VkAPIError as err:
                logging.info(f'choose_pidor() for chat {chat} resulted in VkAPIError: {err}')
            end_time = time.time()
                
    def choose_pidor(self, chat):
        members = self._vk.messages.getConversationMembers(peer_id=int(chat + 2e9), fields='id')['profiles']
        members = list(filter(lambda x: not x['id'] == self._vk_id, members))
        logging.debug(f'Got conversation members for chat {chat}: {members}')
        random.seed()
        pidor = random.choice(members)
        if pidor['id'] not in self._chats_database.users:
            self._chats_database.add_user(pidor['id'])
        self._chats_database.increment_pidor_count(pidor['id'])
        self._chats_database.set_last_pidor(chat, pidor['id'])
        message = """Пидор сегодняшнего дня: [id{id}|{f_name} {l_name}]. Поздравляем!"""\
                  .format(id=pidor['id'], f_name=pidor['first_name'], l_name=pidor['last_name'])
        logging.info(f'Chose new pidor for chat {chat}: {pidor["id"]} {pidor["first_name"]} {pidor["last_name"]}')
        res = self._vk.messages.send(peer_id=int(2e9+chat), message=message)
        logging.debug(f'Sent a message with new pidor, response: {res}')

    def new_chat(self, chat_id):
        if chat_id not in self._chats_database.chats:
            if chat_id not in self._chats_database.get_all_chats():
                # members = self._vk.messages.getConversationMembers(peer_id=int(chat_id + 2e9))['profiles']
                # for member in members:
                #     self._chats_database.add_member(chat_id, member)
                self._chats_database.add_chat(chat_id)
            else:
                self._chats_database.chat_on_again(chat_id)

    def remove_chat(self, chat_id):
        if chat_id in self._chats_database.chats:
            self._chats_database.remove_chat(chat_id)

    # def new_member(self, chat_id, user_id):
    #     members = self._chats_database.get_all_members(chat_id)
    #     if user_id in members:
    #         self._chats_database.member_came_back(chat_id, user_id)
    #         logging.debug('Member {} came back to chat {}'.format(user_id, chat_id))
    #     elif int(user_id) > 0:
    #         member = self._vk.users.get(user_ids=user_id)[0]
    #         self._chats_database.add_member(chat_id, member)
    #         logging.debug('New member {} in chat {}'.format(user_id, chat_id))
    #
    # def remove_member(self, chat_id, user_id):
    #     self._chats_database.member_left(chat_id, user_id)


class Database:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.create_if_not_exists()
        self.chats = self.get_chats()

    def create_if_not_exists(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        # cursor.execute("""CREATE TABLE IF NOT EXISTS Pidors
        #                   (chat_id, user_id, user_name, user_pidor_count, user_is_in_chat)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS Pidors_2 
                          (user_id, pidor_count)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS Chats 
                      (chat_id integer, feature_is_on integer, last_pidor_id integer)""")
        conn.commit()
        conn.close()

    @property
    def users(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT user_id FROM Pidors_2""")
        users = cursor.fetchall()
        conn.close()
        return (x[0] for x in users)

    # def add_member(self, chat_id, member):
    #     _id = member['id']
    #     _full_name = member['first_name'] + ' ' + member['last_name']
    #
    #     conn = sqlite3.connect(self.db_file)
    #     cursor = conn.cursor()
    #     cursor.execute("""INSERT INTO Pidors (chat_id, user_id, user_name, user_pidor_count, user_is_in_chat)
    #                       VALUES (?, ?, ?, ?, 1)""", (chat_id, _id, _full_name, 0))
    #     conn.commit()
    #     conn.close()
    #
    # def member_came_back(self, chat_id, user_id):
    #     conn = sqlite3.connect(self.db_file)
    #     cursor = conn.cursor()
    #     cursor.execute("""UPDATE Pidors SET user_is_in_chat=1 WHERE chat_id=? AND user_id=?""", (chat_id, user_id))
    #     conn.commit()
    #     conn.close()
    #
    # def member_left(self, chat_id, user_id):
    #     conn = sqlite3.connect(self.db_file)
    #     cursor = conn.cursor()
    #     cursor.execute("""UPDATE Pidors SET user_is_in_chat=0 WHERE chat_id=? AND user_id=?""", (chat_id, user_id))
    #     conn.commit()
    #     conn.close()
    #
    # def get_all_members(self, chat_id):
    #     conn = sqlite3.connect(self.db_file)
    #     cursor = conn.cursor()
    #     cursor.execute("""SELECT user_id FROM Pidors WHERE Pidors.chat_id=?""", (chat_id,))
    #     members = cursor.fetchall()
    #     conn.close()
    #     return [member[0] for member in members]

    def add_user(self, user_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO Pidors_2 (user_id, pidor_count) VALUES (?, 0)""", (user_id,))
        conn.commit()
        conn.close()

    def get_user_count(self, user_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT pidor_count FROM Pidors_2 WHERE user_id=?""", (user_id,))
        count = cursor.fetchone()
        conn.close()
        return count[0] if count else 0

    # def get_pidors(self, chat_id):
    #     conn = sqlite3.connect(self.db_file)
    #     cursor = conn.cursor()
    #     cursor.execute("""SELECT * FROM Pidors WHERE Pidors.chat_id=? AND Pidors.user_is_in_chat=1
    #                       ORDER BY Pidors.user_pidor_count DESC""", (chat_id,))
    #     pidors = cursor.fetchall()
    #     conn.close()
    #     return pidors
    #
    # def get_users_pidor_count(self, chat_id, user_id):
    #     conn = sqlite3.connect(self.db_file)
    #     cursor = conn.cursor()
    #     cursor.execute("""SELECT user_pidor_count FROM Pidors WHERE Pidors.chat_id=? AND Pidors.user_id=?""",
    #                    (chat_id, user_id))
    #     pidor_count = cursor.fetchone()
    #     conn.close()
    #     return pidor_count[0] if pidor_count is not None else None

    def get_last_pidor(self, chat_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT last_pidor_id FROM Chats WHERE chat_id=?""", (chat_id,))
        pidor = cursor.fetchone()
        conn.close()
        return pidor[0]

    def set_last_pidor(self, chat_id, new_pidor_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""UPDATE Chats SET last_pidor_id=? WHERE chat_id=?""",
                       (new_pidor_id, chat_id))
        conn.commit()
        conn.close()

    def increment_pidor_count(self, user_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""UPDATE Pidors_2 SET pidor_count = pidor_count + 1 WHERE user_id=?""",
                       (user_id,))
        conn.commit()
        conn.close()

    # def increment_pidor_count(self, chat_id, user_id):
    #     conn = sqlite3.connect(self.db_file)
    #     cursor = conn.cursor()
    #     cursor.execute("""UPDATE Pidors SET user_pidor_count = user_pidor_count + 1 WHERE chat_id=? AND user_id=?""",
    #                    (chat_id, user_id))
    #     conn.commit()
    #     conn.close()

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
