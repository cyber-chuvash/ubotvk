import unittest

import os
import sqlite3
import json

from ubotvk.bot import Database


class TestDatabase(unittest.TestCase):
    db_file = 'test_db.sqlite'
    test_id = 123
    test_feature = 'test_feature'

    def setUp(self):
        try:
            os.remove(self.db_file)
        except OSError:
            pass

        self.db = Database(self.db_file)
        self.db.add_chat(self.test_id)

    def tearDown(self):
        os.remove(self.db_file)

    def test_created_table_on_init(self):
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("""SELECT name FROM sqlite_master WHERE type='table'""")
        select = [name[0] for name in cur.fetchall()]
        self.assertTrue('features' in select)

    def test_add_chat(self):
        # Test normal conditions: chat_id:int
        self.db.add_chat(self.test_id + 1)
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("""SELECT chat_id FROM features""")
        select = [chat_ids[0] for chat_ids in cur.fetchall()]
        self.assertTrue(self.test_id + 1 in select)

        # Test abnormal conditions: chat_id:str
        with self.assertRaises(AssertionError):
            self.db.add_chat('test')

    def test_add_feature(self):
        # Test normal conditions: chat_id: int, feature: str
        self.db.add_feature(self.test_id, self.test_feature)
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        select = json.loads(cur.fetchone()[0])
        self.assertTrue(self.test_feature in select)

        # Test same feature being added second time (it shouldn't be)
        self.db.add_feature(self.test_id, self.test_feature)
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        select = json.loads(cur.fetchone()[0])
        self.assertTrue(select.count(self.test_feature) == 1)

        # Test abnormal conditions: i.e. chat_id:str, feature: int
        with self.assertRaises(AssertionError):
            self.db.add_feature('test', 123)

        with self.assertRaises(AssertionError):
            self.db.add_feature('test', self.test_feature)

        with self.assertRaises(AssertionError):
            self.db.add_feature(self.test_id, 123)

    def test_remove_feature(self):
        # Test normal conditions: chat_id: int, feature: str
        self.db.add_feature(self.test_id, self.test_feature)

        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        before = json.loads(cur.fetchone()[0])

        self.db.remove_feature(self.test_id, self.test_feature)

        cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        after = json.loads(cur.fetchone()[0])
        conn.close()

        self.assertTrue(next(iter(set(before) - set(after))) == self.test_feature)

        # Removing what is already not in database raises AttributeError

        with self.assertRaises(AttributeError):
            self.db.remove_feature(self.test_id, self.test_feature)

        with self.assertRaises(AttributeError):
            self.db.add_feature(self.test_id, self.test_feature + '123')
            self.db.remove_feature(self.test_id, self.test_feature)

        # # Test removing what is already removed (blank list)
        #
        # conn = sqlite3.connect(self.db_file)
        # cur = conn.cursor()
        # cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        # before = json.loads(cur.fetchone()[0])
        #
        # self.db.remove_feature(self.test_id, self.test_feature)
        #
        # cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        # after = json.loads(cur.fetchone()[0])
        # conn.close()
        #
        # self.assertTrue((set(before) - set(after)).__len__() == 0)
        #
        # # Test removing what is already removed (not blank list)
        #
        # self.db.add_feature(self.test_id, self.test_feature)
        # self.db.add_feature(self.test_id, self.test_feature + '123')
        # self.db.remove_feature(self.test_id, self.test_feature)
        #
        # conn = sqlite3.connect(self.db_file)
        # cur = conn.cursor()
        # cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        # before = json.loads(cur.fetchone()[0])
        #
        # self.db.remove_feature(self.test_id, self.test_feature)
        #
        # cur.execute("""SELECT enabled_features FROM features WHERE chat_id=?""", (self.test_id,))
        # after = json.loads(cur.fetchone()[0])
        # conn.close()
        #
        # self.assertTrue((set(before) - set(after)).__len__() == 0)

    def test_get_feature_chats_dict(self):
        self.db.add_chat(self.test_id+1)
        self.db.add_chat(self.test_id+2)

        installed_features = [self.test_feature, self.test_feature+'1', self.test_feature+'2', 'some_other']

        self.db.add_feature(self.test_id, self.test_feature)
        self.db.add_feature(self.test_id, self.test_feature+'1')
        self.db.add_feature(self.test_id, self.test_feature+'2')
        self.db.add_feature(self.test_id+1, self.test_feature)
        self.db.add_feature(self.test_id+1, self.test_feature+'2')
        self.db.add_feature(self.test_id+2, self.test_feature)
        self.db.add_feature(self.test_id+2, self.test_feature+'1')

        d = self.db.get_feature_chats_dict(installed_features=installed_features)
        print(d)
        self.assertTrue(d ==
                        {self.test_feature: [self.test_id, self.test_id+1, self.test_id+2],
                         self.test_feature+'1': [self.test_id, self.test_id+2],
                         self.test_feature+'2': [self.test_id, self.test_id+1],
                         'some_other': []})


if __name__ == '__main__':
    unittest.main()
