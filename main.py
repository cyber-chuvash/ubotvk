import requests

from chuvash import ubotvk
import config


def long_poll(server, key, ts, wait=25, mode=2, version=3):
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
    return request.json()


bot = ubotvk.Bot(login=config.LOGIN, password=config.PASSWORD, app_id=config.APP_ID, api_version='5.80')

lps = bot.vk_api.messages.getLongPollServer(need_pts=1, lp_version=3)
key, server, ts = lps['key'], lps['server'], lps['ts']

while True:
    response = long_poll(server, key, ts)
    ts = response['ts']

    for update in response['updates']:
        print(update)
