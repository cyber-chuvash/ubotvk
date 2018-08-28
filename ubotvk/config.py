import json
import os


class Config:
    try:
        _conf = json.loads(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.json'), 'r').read())

        LOGIN = str(_conf['login'])
        PASSWORD = str(_conf['password'])
        APP_ID = int(_conf.get('app_id', 6666569))

        INSTALLED_FEATURES = tuple(_conf['installed_features']) if _conf.get('installed_features', None) else None
        DEFAULT_FEATURES = tuple(_conf['on_by_default']) if _conf.get('on_by_default', None) else []

        LOG_DIR = _conf.get('log_dir', None)
        LOG_LEVEL = _conf.get('log_level', 'WARNING')
        MAINTAINER_VK_ID = int(_conf['maintainer_vk_id'])

    except FileNotFoundError:
        LOGIN = str(os.environ['VK_LOGIN'])
        PASSWORD = str(os.environ['VK_PASS'])
        APP_ID = int(os.environ.get('VK_APP_ID', 6666569))

        INSTALLED_FEATURES = \
            tuple(os.environ['UBOTVK_INST_FEAT'].split(',')) if os.environ.get('UBOTVK_INST_FEAT', None) else None
        DEFAULT_FEATURES = \
            tuple(os.environ['UBOTVK_DEF_FEAT'].split(',')) if os.environ.get('UBOTVK_DEF_FEAT', None) else []

        LOG_DIR = os.environ.get('UBOTVK_LOG_DIR', None)
        LOG_LEVEL = os.environ.get('UBOTVK_LOG_LEVEL', 'WARNING')
        MAINTAINER_VK_ID = int(os.environ.get('UBOTVK_MAINTAINER_ID', 212771532))


