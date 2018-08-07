import unittest

from ubotvk import utils


class TestUtils(unittest.TestCase):
    def test_command_in_string(self):
        """
        command_in_string function takes a string, removes VK's mentions ("[id12345|Something]") and returns lowercase
        list of words (string.split()) if command was found, else - None
        """
        string = '[id13515|Test] cmd test'
        commands = ['cmd', 'cmd2']
        self.assertListEqual(utils.command_in_string(string, commands), ['cmd', 'test'])

        string = '      [id13515|Test]      cmd    test    '
        commands = ['cmd', 'cmd2']
        self.assertListEqual(utils.command_in_string(string, commands), ['cmd', 'test'])

        string = '[id13515|Test test test and test_=#@$(%&!)#@%$)+;".,v] cmd test'
        commands = ['cmd', 'cmd2']
        self.assertListEqual(utils.command_in_string(string, commands), ['cmd', 'test'])

        string = '[id13515|Test] cmd2 test'
        commands = ['cmd', 'cmd2']
        self.assertListEqual(utils.command_in_string(string, commands), ['cmd2', 'test'])

        string = '[id13515|Test] cMd2 TeST'
        commands = ['cmd', 'cmd2']
        self.assertListEqual(utils.command_in_string(string, commands), ['cmd2', 'test'])

        string = '[id13515|Test] cmd cmd2'
        commands = ['cmd', 'cmd2']
        self.assertListEqual(utils.command_in_string(string, commands), ['cmd', 'cmd2'])


if __name__ == '__main__':
    unittest.main()

