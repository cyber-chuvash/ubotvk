import sqlite3
import os


DATABASE_FILE = os.path.join(os.path.dirname(__file__), 'pidors.sqlite')


class Pidors(object):
    def __init__(self, vk_api, list_of_chats):
        self._chat_databases = {}
        for chat in list_of_chats:
            self._chat_databases[chat] = Database(chat)

        self._vk = vk_api

        # Long Poll codes that should trigger this feature. More info: https://vk.com/dev/using_longpoll
        self.triggered_by = [4]

        # List of chats this feature is enabled in
        self.enabled_in_chats = list_of_chats

    def __call__(self, update):
        if (update[2] & 2) == 0:  # Check if message is inbox
            if int(update[3] - 2e9) in self.enabled_in_chats:
                if update[5] in ['/toppidor', '!toppidor']:     # TODO: cmd parsing, smart-ass way to interpret them
                    self.top_pidor(int(update[3]-2e9))

    def top_pidor(self, chat_id):
        pidors = self._chat_databases[chat_id].get_pidors()
        print(pidors)

        response = 'Топ пидоров за все время:\n'
        count = 1
        total_pidor_count = 0
        for pidor in pidors:
            response += '{count}. [id{id}|{name}] - {pidor_count}\n'.format(count=count, id=pidor[0],
                                                                            name=pidor[1], pidor_count=pidor[2])
            count += 1
            total_pidor_count += pidor[2]

        response += '\nСредний показатель пидорства: ' + str(total_pidor_count / count - 1)
        self._vk.messages.send(peer_id=int(chat_id+2e9), message=response)


class Database:
    def __init__(self, chat_id):
        self._chat_id = chat_id
        self.db_file = DATABASE_FILE
        self.create_if_not_exists()

    def create_if_not_exists(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS chat_{} (user_id, user_name, user_pidor_count)""".
                       format(self._chat_id))
        conn.commit()
        conn.close()

    def get_pidors(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM chat_{}""".format(self._chat_id))
        pidors = cursor.fetchall()
        conn.close()
        return pidors
