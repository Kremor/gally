import argparse
import os
import pip
import sqlite3

from discord import ClientException
from discord.ext import commands

import gally.utils as utils


bot = commands.Bot('\\')


def init_bot():
    pass


@bot.event
async def on_ready():
    from discord import Game

    bot_dir = utils.get_dir()

    for server in bot.servers:
        server_db = bot_dir + 'db/{}.db'.format(server.id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS ADMINS(ID TEXT)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS IDX_ADMIN_ID ON ADMINS(ID)")

        cursor.execute("CREATE TABLE IF NOT EXISTS SETTINGS(NAME TEXT, VALUE TEXT)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS IDX_SETTING_NAME ON SETTINGS(NAME)")

        cursor.close()
        connection.commit()
        connection.close()

        print('Connected to server {}'.format(server.id))

    bot_db = utils.get_dir() + 'bot.db'

    connection = sqlite3.connect(bot_db)
    cursor = connection.cursor()

    cursor.execute("SELECT NAME FROM EXTENSIONS")
    extensions_ = [ext[0] for ext in cursor.fetchall()]

    for ext in extensions_:
        try:
            bot.load_extension(ext)
            print("Extension '{}' loaded".format(ext))
        except ClientException:
            cursor.execute("DELETE FROM EXTENSIONS WHERE NAME LIKE '{}'".format(ext))
            print("Extension '{}' could not be loaded".format(ext))

    cursor.close()
    connection.close()

    await bot.change_presence(game=Game(name='\\help'))


@bot.command(pass_context=True, name='addadmin', aliases=['aa'])
@utils.is_admin()
async def add_admin(context):
    """
    Add a bot administrator. Admins only.

    Usage:

        \addadmin <@user>
    """
    mentions = context.message.mentions
    server_id = context.message.server.id

    if not len(mentions):
        await bot.say('No arguments passed after the command')
        return

    admins = utils.get_admins(server_id)

    server_db = utils.get_dir() + 'db/{}.db'.format(server_id)

    connection = sqlite3.connect(server_db)
    cursor = connection.cursor()

    for mention in mentions:
        if mention.id in admins:
            bot.say("{} is already an admin.".format(mention.mention))
        else:
            cursor.execute("REPLACE INTO ADMINS(ID) VALUES('{}')".format(
                mention.id
            ))
            await bot.say("{} was added to the admin list".format(mention.mention))

    cursor.close()
    connection.commit()
    connection.close()


@bot.command(pass_context=True, name='list_admins')
@utils.is_admin()
async def list_admins(context):
    """
    List all the bot's administrators. Admins only.

    Usage:

        \listadmins
    """
    admins = utils.get_admins(context.message.server.id)

    message = ''
    for i, admin in enumerate(admins):
        message += "{}. <@{}>\n".format(i+1, admin)

    await bot.say(embed=utils.get_embed(message, 'Admins'))


@bot.command(pass_context=True, name='list_conf')
@utils.is_admin()
async def list_conf(context):
    """
    List the bot settings. Admins only.

    Usage:

        \listconf
    """
    server_db = utils.get_dir() + 'db/{}.db'.format(context.message.server.id)

    connection = sqlite3.connect(server_db)
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM SETTINGS")
    settings = cursor.fetchall()

    message = '```'
    for setting, value in settings:
        message += '\n{:<20} - {:<20}'.format(setting, value)
    message += '\n```'

    await bot.say(embed=utils.get_embed(
        message, 'Configuration'
    ))

    cursor.close()
    connection.close()


@bot.command(name='list_all')
@utils.is_owner()
async def list_available_extension():
    """
    List all the available extensions. Bot owner only.
    """
    extensions = ''
    i = 1
    for path in os.listdir('gally/extensions'):
        if os.path.isdir('gally/extensions/' + path):
            if os.path.exists('gally/extensions/' + path + '/setup.py'):
                extensions += '\n{}. {}'.format(i, path)
                i += 1
    await bot.say(embed=utils.get_embed(extensions, 'Available extensions'))


@bot.command(name='extensions')
@utils.is_owner()
async def list_loaded_extensions():
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


@bot.command(name='load_ext')
@utils.is_owner()
async def load_extension(ext_name: str):
    """
    Loads an extension. Bot owner only.
    """
    if not os.path.exists('gally/extensions/{}/setup.py'.format(ext_name)):
        await bot.say(embed=utils.get_embed(
            "The extension '{}' could not be loaded `setup.py` does not exists.".format(ext_name)
        ))
        return

    if os.path.exists('gally/extensions/{}/requirements.txt'.format(ext_name)):
        pip.main(['install', '-r', 'gally/extensions/{}/requirements.txt'.format(ext_name)])

    ext_name = 'gally.extensions.{}.setup'.format(ext_name)

    bot_db = utils.get_dir() + 'bot.db'

    connection = sqlite3.connect(bot_db)
    connection.execute("REPLACE INTO EXTENSIONS(NAME) VALUES('{}')".format(
        ext_name
    ))
    connection.commit()
    connection.close()

    bot.load_extension(ext_name)
    await bot.say(embed=utils.get_embed("Extension `{}` loaded".format(ext_name)))


@bot.command(name='rload_ext')
@utils.is_owner()
async def reload_extension(ext_name):
    """
    Realoads an extension. Bot owner only.
    """
    if not os.path.exists('gally/extensions/{}/setup.py'.format(ext_name)):
        await bot.say(embed=utils.get_embed(
            "The extension '{}' could not be loaded `setup.py` does not exists.".format(ext_name)
        ))
        return

    if os.path.exists('gally/extensions/{}/requirements.txt'.format(ext_name)):
        pip.main(['install', '-r', 'gally/extensions/{}/requirements.txt'.format(ext_name)])

    ext_name = 'gally.extensions.{}.setup'.format(ext_name)

    bot_db = utils.get_dir() + 'bot.db'

    connection = sqlite3.connect(bot_db)
    connection.execute("REPLACE INTO EXTENSIONS(NAME) VALUES('{}')".format(
        ext_name
    ))
    connection.commit()
    connection.close()

    bot.unload_extension(ext_name)
    bot.load_extension(ext_name)
    await bot.say(embed=utils.get_embed("Extension `{}` reloaded".format(ext_name)))


@commands.command(pass_context=True, name='del_admin')
@utils.is_admin()
async def remove_admin(context):
    """
    Remove a bot administrator. Admins only.

    Usage:

        \removeadmin <@user>
    """
    mentions = context.message.mentions
    server_id = context.message.server.id

    if not len(mentions):
        await bot.say('No arguments passed after the command')
        return

    admins = utils.get_admins(server_id)

    server_db = utils.get_dir() + 'db/{}.db'.format(server_id)

    connection = sqlite3.connect(server_db)
    cursor = connection.cursor()

    for mention in mentions:
        if mention.id not in admins:
            bot.say(embed=utils.get_embed(
                "{} was not an admin.".format(mention.mention)
            ))
        else:
            cursor.execute("DELETE FROM ADMINS WHERE ID LIKE '{}'".format(
                mention.id
            ))
            await bot.say(embed=utils.get_embed(
                "{} was removed from the admin list".format(mention.mention)
            ))

    cursor.close()
    connection.commit()
    connection.close()


@bot.command(name='repo')
async def repo():
    """
    Links the bot's git repository.
    """
    await bot.say(embed=utils.get_embed(
        "https://github.com/Kremor/gally", 'Repo'
    ))


@bot.command()
@utils.is_owner()
async def reset():
    """
    Resets all the bot settings and databases. Bot owner only.
    """
    pass


@bot.command()
@utils.is_owner()
async def reset_server(server_id):
    """
    Resets the server database. Bot owner only.
    """
    pass


@bot.command(name='uload_ext', aliases=['ule'])
@utils.is_owner()
async def unload_extension(ext_name):
    """
    Unloads and extension. Bot owner only.
    """
    if not os.path.exists('gally/extensions/{}/setup.py'.format(ext_name)):
        await bot.say(embed=utils.get_embed(
            "The extension '{}' could not be loaded `setup.py` does not exists.".format(ext_name)
        ))
        return

    if os.path.exists('gally/extensions/{}/requirements.txt'.format(ext_name)):
        pip.main(['install', '-r', 'gally/extensions/{}/requirements.txt'.format(ext_name)])

    ext_name = 'gally.extensions.{}.setup'.format(ext_name)

    bot_db = utils.get_dir() + 'bot.db'

    connection = sqlite3.connect(bot_db)
    connection.execute("DELETE FROM EXTENSIONS(NAME) VALUES('{}')".format(
        ext_name
    ))
    connection.commit()
    connection.close()

    bot.unload_extension(ext_name)
    await bot.say(embed=utils.get_embed("Extension `{}` unloaded".format(ext_name)))


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

    bot_db = utils.get_dir() + 'bot.db'

    connection = sqlite3.connect(bot_db)
    cursor = connection.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS SETTINGS(NAME TEXT, VALUE TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS EXTENSIONS(NAME TEXT)")

    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS IDX_SETTING ON SETTINGS(NAME)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS IDX_EXT ON EXTENSIONS(NAME)")

    cursor.execute("REPLACE INTO SETTINGS VALUES(?, ?)", ('OWNER', owner_id))

    cursor.close()
    connection.commit()
    connection.close()

    bot.run(token)
