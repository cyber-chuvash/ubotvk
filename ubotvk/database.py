import sqlite3
import json

from ubotvk.config import Config


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
            features_dict[item[0]] = list(Config.DEFAULT_FEATURES) + json.loads(item[1])

        feature_chats_dict = {}
        for feature in installed_features:
            feature_chats_dict[feature] = [chat for chat in features_dict.keys()
                                           if feature in features_dict[chat]]

        return feature_chats_dict

    def get_chats(self) -> list:
        conn = sqlite3.connect(self._db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT chat_id FROM features""")
        chats = cursor.fetchall()
        return list(set([item[0] for item in chats]))

    def add_chat(self, chat_id: int):
        assert isinstance(chat_id, int)

        conn = sqlite3.connect(self._db_file)
        cursor = conn.cursor()
        cursor.execute("""SELECT chat_id FROM features WHERE chat_id=?""", (chat_id,))
        sel = cursor.fetchone()
        if sel is None:
            cursor.execute("""INSERT INTO features (chat_id, enabled_features) VALUES (?, ?)""",
                           (chat_id, json.dumps([])))
            conn.commit()
            conn.close()
        else:
            raise ValueError('Chat "{}" is already in the database'.format(chat_id))

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
                raise ValueError('Feature "{}" is already in the database'.format(feature))
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
            raise ValueError('Feature "{}" is not in the database'.format(feature))

        cursor.execute("""UPDATE features SET enabled_features=? WHERE chat_id=?""",
                       (json.dumps(enabled_features), chat_id))
        conn.commit()
        conn.close()
