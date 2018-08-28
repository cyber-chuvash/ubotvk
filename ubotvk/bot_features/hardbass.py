import random
import time


RESPONSES = ['Хуйня', 'Говно', 'Че за срань']
AUDIO_LIST = ['436295874_456239021', '436295874_456239022', '436295874_456239023', '436295874_456239024',
              '436295874_456239025', '436295874_456239026', '436295874_456239027', '436295874_456239028',
              '436295874_456239029', '436295874_456239030']


def __init__(vk_api):
    return HardBass(vk_api)


class HardBass(object):
    def __init__(self, vk_api):
        self.vk = vk_api

        # Long Poll codes that should trigger this feature. More info: https://vk.com/dev/using_longpoll
        self.triggered_by = [4]

    def __call__(self, update):
        if (update[2] & 2) == 0:    # Check if message is inbox
            if update[7] and 'attach1_type' in update[7] and update[7]['attach1_type'] == 'audio':
                self.vk.messages.send(peer_id=update[3], message=random.choice(RESPONSES),
                                      forward_messages=update[1])
                time.sleep(0.5)
                self.vk.messages.send(peer_id=update[3], message='Вот это нормальная музыка',
                                      attachment='audio{}'.format(random.choice(AUDIO_LIST)))

