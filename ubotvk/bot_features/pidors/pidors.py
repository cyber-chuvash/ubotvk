import sqlite3
import os


DATABASE_FILE = os.path.join(os.path.dirname(__file__), 'pidors.sqlite3')


class Pidors(object):
    def __init__(self, vk_api, list_of_chats):
        self._vk = vk_api

        self._chats_database = Database()
        self.enabled_in_chats = list_of_chats

        # Long Poll codes that should trigger this feature. More info: https://vk.com/dev/using_longpoll
        self.triggered_by = [4]

    def __call__(self, update):
        if (update[2] & 2) == 0:  # Check if message is inbox
            if int(update[3] - 2e9) in self.enabled_in_chats:
                if update[5] in ['/toppidor', '!toppidor']:     # TODO: cmd parsing, smart-ass way to interpret them
                    self.top_pidor(int(update[3]-2e9))

    def top_pidor(self, chat_id):
        pidors = self._chats_database.get_pidors(chat_id)
        print(pidors)

        response = 'Топ пидоров за все время:\n'
        count = 1
        total_pidor_count = 0
        for pidor in pidors:
            response += '{count}. [id{id}|{name}] - {pidor_count}\n'.format(count=count, id=pidor[1],
                                                                            name=pidor[2], pidor_count=pidor[3])
            count += 1
            total_pidor_count += pidor[3]

        response += '\nСредний показатель пидорства: ' + str(total_pidor_count / (count - 1))
        self._vk.messages.send(peer_id=int(chat_id+2e9), message=response)

    def new_chat(self, chat_id):
        self.enabled_in_chats.append(chat_id)
        members = self._vk.messages.getConversationMembers(peer_id=int(chat_id + 2e9))['profiles']
        for member in members:
            self._chats_database.add_member(chat_id, member)


class Database:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.create_if_not_exists()

    def create_if_not_exists(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS Chats (chat_id, user_id, user_name, user_pidor_count)""")
        conn.commit()
        conn.close()

    def add_member(self, chat_id, member):
        _id = member['id']
        _full_name = member['first_name'] + ' ' + member['last_name']

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO Chats (chat_id, user_id, user_name, user_pidor_count) VALUES (?, ?, ?, ?)""",
                       (chat_id, _id, _full_name, 0))
        conn.commit()
        conn.close()

    def get_pidors(self, chat_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM Chats WHERE Chats.chat_id=?""", (chat_id,))
        pidors = cursor.fetchall()
        conn.close()
        return pidors
