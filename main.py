import requests

from chuvash import ubotvk
from vk_requests.exceptions import VkAPIError

import config


def new_message(update):
    pass


def handle_update(update):
    print(update)
    if update[0] == 4:
        new_message(update)


class Main:
    """
    Creates ubotvk.Bot instance with credentials from config.py,
    Gets Long Poll server,
    Continuously gets updates from VK.
    """

    def __init__(self):
        self.bot = ubotvk.Bot(login=config.LOGIN, password=config.PASSWORD, app_id=config.APP_ID, api_version='5.80')

        self.key, self.server, self.ts = self.get_long_poll_server()

        while True:
            try:
                response = self.long_poll(self.server, self.key, self.ts)
                self.ts = response['ts']

                for update in response['updates']:
                    handle_update(update)

            except VkAPIError as api_err:
                print(api_err)
                # if api_err.code ==

    def get_long_poll_server(self):
        lps = self.bot.vk_api.messages.getLongPollServer(need_pts=0, lp_version=3)
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

        if 'failed' not in res.keys():
            return res

        elif res['failed'] == 1:
            self.ts = res['ts']
        elif res['failed'] in [2, 3]:
            self.key, self.server, self.ts = self.get_long_poll_server()
        elif res['failed'] == 4:
            raise ValueError('Wrong Long Poll version')
        else:
            raise Exception


if __name__ == '__main__':
    main = Main()
