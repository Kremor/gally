import argparse
import re
import shutil
import sqlite3

from discord.ext import commands

bot = commands.Bot('\\')

settings = {}

__owner_id = ''


def get_dir() -> str:
    import os
    from pathlib import Path

    home_dir = str(Path.home())

    if not os.path.exists(home_dir + '/.local'):
        os.mkdir(home_dir + '/.local')

    if not os.path.exists(home_dir + '/.local/gally_bot'):
        os.mkdir(home_dir + '/.local/gally_bot')

    if not os.path.exists(home_dir + '/.local/gally_bot/db'):
        os.mkdir(home_dir + '/.local/gally_bot/db')

    return home_dir + '/.local/gally_bot/'



def is_channel(context):
    return settings[context.message.server.id]['CHANNEL'] == context.message.channel.id


def is_owner():
    global __owner_id

    def predicate(context):
        return context.message.author.id == __owner_id

    return commands.check(predicate)


@bot.event
async def on_ready():
    # from os import path
    #
    # bot_dir = get_dir()
    #
    # for server in bot.servers:
    #     if not path.exists(bot_dir + 'db/{}.db'.format(server.id)):
    #         shutil.copy2('database.db', bot_dir + 'db/{}.db'.format(server.id))
    #
    #     connection = sqlite3.connect(bot_dir + 'db/{}.db'.format(server.id))
    #     cursor = connection.cursor()
    #
    #     cursor.execute("select * from settings")
    #     settings_ = cursor.fetchall()
    #
    #     cursor.close()
    #     connection.close()
    #
    #     settings[server.id] = {}
    #     for setting, value in settings_:
    #         if __is_number(value) and len(setting) < 3:
    #             settings[server.id][setting] = int(value)
    #         else:
    #             settings[server.id][setting] = value
    #
    # await bot.change_presence(game=Game(name='\\help'))

    bot.load_extension('gally.taboo')


@bot.command(name='le')
@is_owner()
async def load_extension(ext_name):
    """
    Loads an extension. Bot owner only.
    """
    await bot.load_extension(ext_name)


@bot.command(name='ule')
@is_owner()
async def unload_extension(ext_name):
    """
    Unloads and extension. Bot owner only.
    """
    bot.unload_extension(ext_name)


""" ---... Miscellaneous ...--- """


# @bot.command(name='addadmin', aliases=['aa'], pass_context=True)
# async def add_admin(context):
#     """
#     Add a bot administrator. Admins only.
#
#     Usage:
#
#         \addadmin <@user>
#     """
#     author = context.message.author.id
#     mentions = context.message.mentions
#     server_id = context.message.server.id
#
#     if not len(mentions):
#         await bot.say('No arguments passed after the command')
#         return
#
#     admins = __get_admins(server_id)
#
#     if author in admins:
#         if mentions[0].id not in admins:
#             __add_admin(server_id, mentions[0].id)
#             await bot.say("{} is now an admin.".format(mentions[0].mention))
#         else:
#             await bot.say("{} was already an admin.".format(mentions[0].mention))
#
#
# @bot.command(name='listadmins', aliases=['la'], pass_context=True)
# async def list_admins(context):
#     """
#     List all the bot's administrators. Admins only.
#
#     Usage:
#
#         \listadmins
#     """
#     author = context.message.author.id
#     server_id = context.message.server.id
#
#     admins = __get_admins(server_id)
#
#     if author in admins:
#         text = ""
#         for i, admin in enumerate(admins):
#             text += " {}. <@{}>\n".format(i+1, admin)
#         await bot.say("Admins:\n" + text)
#
#
# @bot.command(name='listconf', aliases=['lc'], pass_context=True)
# async def list_conf(context):
#     """
#     List the bot settings. Admins only.
#
#     Usage:
#
#         \listconf
#     """
#     server_id = context.message.server.id
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("select * from settings")
#     settings = cursor.fetchall()
#     string = "```"
#
#     for setting, value in settings:
#         string += '\n{}\t-\t{}'.format(setting, value)
#     string += '\n```'
#
#     await bot.say(string)
#
#
# @bot.command(name='removeadmin', aliases=['ra'], pass_context=True)
# async def remove_admin(context):
#     """
#     Remove a bot administrator. Admins only.
#
#     Usage:
#
#         \removeadmin <@user>
#     """
#     author = context.message.author.id
#     mentions = context.message.mentions
#     server_id = context.message.server.id
#
#     if not len(mentions):
#         await bot.say('No arguments passed after the command')
#         return
#
#     admins = __get_admins(server_id)
#
#     if author in admins:
#         if mentions[0].id not in admins:
#             await bot.say("{} is not an admin.".format(mentions[0].mention))
#         else:
#             __remove_admin(server_id, mentions[0].id)
#             await bot.say("{} was removed from the admin list.".format(mentions[0].mention))
#
#
# @bot.command(name='repo')
# async def repo():
#     """
#     Links the bot's git repository.
#     """
#     await bot.say('https://github.com/Kremor/gally')
#
#
# """ ---... UTILITY ...--- """


# def is_admin(context):
#     global __owner_id
#
#     admins = __get_admins(context.message.server.id)
#
#     return is_owner(context) or context.message.author.id in admins
#
#
# def __add_admin(server_id: str, admin_id: str):
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("insert into admins values({})".format(admin_id))
#
#     cursor.close()
#     connection.commit()
#     connection.close()


# def __get_admins(server_id: str) -> list:
#     global __owner_id
#
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("select * from admins".format(server_id))
#
#     admins = [__owner_id] + [admin[0] for admin in cursor.fetchall()]
#
#     cursor.close()
#     connection.close()
#
#     return admins
#
#
# def __remove_admin(server_id: str, admin_id: str):
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("delete from admins where id like '{}'".format(admin_id))
#
#     cursor.close()
#     connection.commit()
#     connection.close()
#
#
# def __add_card(server_id: str, card: str, taboos: str):
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("insert into cards values({}, {})".format(card, taboos))
#
#     cursor.close()
#     connection.commit()
#     connection.close()
#
#
# def __get_cards(server_id: str) -> list:
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("select * from cards".format(server_id))
#
#     cards = list(cursor.fetchall())
#
#     cursor.close()
#     connection.close()
#
#     return cards
#
#
# def __remove_card(server_id: str, card: str):
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("delete from cards where card like '{}'".format(card))
#
#     cursor.close()
#     connection.commit()
#     connection.close()
#
#
# def __get_setting(server_id: str, setting: str) -> str:
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("select value from settings where setting like '{}'".format(setting))
#
#     value = cursor.fetchone()[0]
#
#     cursor.close()
#     connection.close()
#
#     return value
#
#
# def __set_setting(server_id: str, setting: str, value: str):
#     connection = sqlite3.connect('db/{}.db'.format(server_id))
#     cursor = connection.cursor()
#
#     cursor.execute("replace into settings (setting, value) values('{}', '{}')".format(
#         setting, value
#     ))
#
#     cursor.close()
#     connection.commit()
#     connection.close()


__user_id = re.compile(r'\d{17}')
__c_s_id = re.compile(r'\d{18}')
__number = re.compile(r'\d+')
__token = re.compile(r'[0-9a-zA-Z._-]{57}')


def __is_user_id(id: str):
    if re.fullmatch(__user_id, id):
        return True
    return False


def __is_c_s_id(id: str):
    if re.fullmatch(__c_s_id, id):
        return True
    return False


def __is_number(n: str):
    if re.fullmatch(__number, n):
        return True
    return False


def __is_token(token: str):
    if re.fullmatch(__token, token):
        return True
    else:
        return False


""" ---... MAIN ...--- """


def main():
    parser = argparse.ArgumentParser(description='A simple discord bot for playing taboo.')
    parser.add_argument('-o', '--owner', help="The bot's owner's id", required=True)
    parser.add_argument('-t', '--token', help="The bot's token", required=True)

    args = parser.parse_args()

    print(args)

    global __owner_id
    __owner_id = args.owner
    token = args.token

    if not __is_user_id(__owner_id):
        print('Argument passed to OWNER is not a valid user id.')
        return

    bot.run(token)


main()
