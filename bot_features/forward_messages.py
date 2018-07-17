
RECEIVER_ID = 212771532


def __init__(vk_api):
    return ForwardMessages(vk_api)


class ForwardMessages(object):
    def __init__(self, vk_api):
        self.vk = vk_api
        self.triggered_by = [4]  # More info: https://vk.com/dev/using_longpoll

    def __call__(self, update):
        if (update[2] & 2) == 0:    # Check if message is inbox
            self.vk.messages.send(peer_id=RECEIVER_ID, message=str(update))
