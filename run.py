#!/usr/bin/env python

from ubotvk.bot import Bot


bot = Bot()

try:
    bot.start_loop()

except Exception as err:
    bot.logger.exception("""\n
    #############################
    !!!!!!!! BOT CRASHED !!!!!!!!
    #############################\n
    """, exc_info=True)
    bot.crash_handler(exc=err)
    raise
