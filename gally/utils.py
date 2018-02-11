import re
import sqlite3

from discord import Color
from discord import Embed
from discord.ext import commands


def get_admins(server_id) -> list:
    # Owner
    bot_db = get_dir() + '/bot.db'

    connection = sqlite3.connect(bot_db)
    cursor = connection.cursor()

    cursor.execute("select value from settings where setting like 'OWNER'")
    owner_id = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    # Admins
    server_db = get_dir() + '/db/{}.db'.format(server_id)

    connection = sqlite3.connect(server_db)
    cursor = connection.cursor()

    cursor.execute("select id from admins")
    admins = [admin[0] for admin in cursor.fetchall()]

    cursor.close()
    connection.close()

    return [owner_id] + admins


def get_setting(server_id: str, setting: str):
    server_db = get_dir() + '/db/{}.db'.format(server_id)

    connection = sqlite3.connect(server_db)
    cursor = connection.cursor()

    cursor.execute("select value from settings where setting like '{}'".format(setting))
    value = cursor.fetchone()

    cursor.close()
    connection.close()

    return value[0] if value else 'NONE'


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

    return home_dir + '/.local/gally_bot'


def get_embed(description: str, title: str=''):
    return Embed(title=title, description=description, color=Color.magenta())


def is_admin():

    def predicate(context):
        admins = get_admins(context.message.server.id)

        return context.message.author.id in admins

    return commands.check(predicate)


def is_number(n: str):
    if re.fullmatch(re_number, n):
        return True
    return False


def is_owner():

    def predicate(context):
        bot_db = get_dir() + '/bot.db'

        connection = sqlite3.connect(bot_db)
        cursor = connection.cursor()

        cursor.execute("select value from settings where setting like 'OWNER'")
        owner_id = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return context.message.author.id == owner_id

    return commands.check(predicate)


def is_user_id(id_: str):
    if re.fullmatch(re_user_id, id_):
        return True
    return False


re_user_id = re.compile(r'\d{17}')
re_number = re.compile(r'\d+')


def set_setting(server_id: str, setting: str, value: str):
    server_db = get_dir() + '/db/{}.db'.format(server_id)

    connection = sqlite3.connect(server_db)
    connection.execute("replace into settings(setting, value) values('{}', '{}')".format(
        setting, value
    ))
    connection.commit()
    connection.close()
