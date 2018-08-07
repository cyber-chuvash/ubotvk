import re


def command_in_string(text: str, commands: list):
    """
    Searches for commands in a string
    :param text: a string, which contains a mention of the bot ('[id12345|Bot Name]' in text)
    :param commands: commands to find
    :return: normalized list of words if command was found, else None
    """
    assert isinstance(text, str)
    assert not isinstance(commands, str)

    text = re.sub('\[id\d+\|.*\]', '', text)
    lst = text.lower().split()

    if lst and len(lst[0]) > 1:
        if lst[0][0] in ['/', '!']:     # Check if first symbol is useless
            lst[0] = lst[0][1:]

        if lst[0] in commands:
            return lst

    return None


