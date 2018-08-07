import json
import os


class Config:
    _conf = json.loads(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.json'), 'r').read())

    LOGIN = str(_conf['login'])
    PASSWORD = str(_conf['password'])
    APP_ID = int(_conf['app_id'])
    INSTALLED_FEATURES = tuple(_conf['installed_features'])
    DEFAULT_FEATURES = tuple(_conf['on_by_default'])

