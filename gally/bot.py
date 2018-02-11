import argparse
from os import path
import sqlite3

from discord.ext import commands

import gally.utils as utils


bot = commands.Bot('\\')


@bot.event
async def on_ready():
    from shutil import copy2
    from discord import Game

    bot_dir = utils.get_dir()

    for server in bot.servers:
        server_db_path = bot_dir + '/db/{}.db'.format(server.id)
        if not path.exists(server_db_path):
            copy2('database.db', server_db_path)

        print('Connected to server {} as {}'.format(server.name, server.me.name))

    bot_db = utils.get_dir() + '/bot.db'

    connection = sqlite3.connect(bot_db)
    cursor = connection.cursor()

    cursor.execute("select name from extensions")
    extensions_ = [ext[0] for ext in cursor.fetchall()]

    for ext in extensions_:
        if not ext.startswith('gally.', 0, len('gally.')):
            ext = 'gally.' + ext
        print("Extension '{}' loaded".format(ext))
        bot.load_extension(ext)

    cursor.close()
    connection.close()

    await bot.change_presence(game=Game(name='\\help'))


@bot.command(name='e')
@utils.is_owner()
async def extensions():
    """
    Lists all the loaded extensions. Bot owner only
    """
    extensions_ = bot.extensions

    if not extensions_:
        await bot.say(embed=utils.get_embed('There are not extensions loaded'))
        return

    message = ''
    for i, extension in enumerate(extensions_):
        message += '{}. {}\n'.format(i+1, extension)

    await bot.say(embed=utils.get_embed(message, title='Extensions'))


@bot.command(name='le')
@utils.is_owner()
async def load_extension(ext_name: str):
    """
    Loads an extension. Bot owner only.
    """
    if not path.exists('gally/extensions/{}.py'.format(ext_name)):
        await bot.say(embed=utils.get_embed(
            "The extension '{}' does not exists.".format(ext_name)
        ))
        return

    ext_name = 'gally.extensions.{}'.format(ext_name)

    bot_db = utils.get_dir() + '/bot.db'

    connection = sqlite3.connect(bot_db)
    connection.execute("replace into extensions(name) values('{}')".format(
        ext_name
    ))
    connection.commit()
    connection.close()

    bot.load_extension(ext_name)
    await bot.say(embed=utils.get_embed("Extension '{}' loaded".format(ext_name)))


@bot.command(name='re')
@utils.is_owner()
async def reload_extension(ext_name):
    """
    Realoads an extension. Bot owner only.
    """
    if not path.exists('gally/extensions/{}.py'.format(ext_name)):
        await bot.say(embed=utils.get_embed(
            "The extension '{}' does not exists.".format(ext_name)
        ))
        return

    ext_name = 'gally.extensions.{}'.format(ext_name)

    bot_db = utils.get_dir() + '/bot.db'

    connection = sqlite3.connect(bot_db)
    connection.execute("replace into extensions(name) values('{}')".format(
        ext_name
    ))
    connection.commit()
    connection.close()

    bot.unload_extension(ext_name)
    bot.load_extension(ext_name)
    await bot.say(embed=utils.get_embed("Extension '{}' reloaded".format(ext_name)))


@bot.command(name='ule')
@utils.is_owner()
async def unload_extension(ext_name):
    """
    Unloads and extension. Bot owner only.
    """
    if not path.exists('gally/extensions/{}.py'.format(ext_name)):
        await bot.say(embed=utils.get_embed(
            "The extension '{}' does not exists.".format(ext_name)
        ))
        return

    ext_name = 'gally.extensions.{}'.format(ext_name)

    bot_db = utils.get_dir() + '/bot.db'

    connection = sqlite3.connect(bot_db)
    connection.execute("delete from extensions where name like '{}'".format(
        ext_name
    ))
    connection.commit()
    connection.close()

    bot.unload_extension(ext_name)
    await bot.say(embed=utils.get_embed("Extension '{}' unloaded".format(ext_name)))


""" ---... MAIN ...--- """


def main():
    parser = argparse.ArgumentParser(description='A simple discord bot for playing taboo.')
    parser.add_argument('-o', '--owner', help="The bot's owner's id", required=True)
    parser.add_argument('-t', '--token', help="The bot's token", required=True)

    args = parser.parse_args()

    owner_id = args.owner
    token = args.token

    if not utils.is_user_id(owner_id):
        print('Argument passed to OWNER is not a valid user id.')
        return

    bot_db = utils.get_dir() + '/bot.db'

    connection = sqlite3.connect(bot_db)
    cursor = connection.cursor()

    cursor.execute("create table if not exists settings(setting text, value text)")
    cursor.execute("create table if not exists extensions(name text)")

    cursor.execute("create unique index if not exists idx_setting on settings(setting)")
    cursor.execute("create unique index if not exists idx_ext_name on extensions(name)")

    cursor.execute("replace into settings(setting, value) values('OWNER', '{}')".format(
        owner_id
    ))

    cursor.close()
    connection.commit()
    connection.close()

    bot.run(token)


main()
