import argparse
from os import path
import queue
import re
import shutil
import sqlite3

from discord.ext import commands

from taboo import Taboo

bot = commands.Bot('\\')

games = {}
queues = {}

__owner_id = ''


@bot.event
async def on_ready():
    for server in bot.servers:
        if not path.exists('db/{}.db'.format(server.id)):
            shutil.copy2('database.db', 'db/{}.db'.format(server.id))


""" ---... Cards management ...--- """


@bot.command(name='addcard', aliases=['ac'], pass_context=True)
async def add_card(context, *args):
    if len(args) == 0:
        await bot.say("No arguments passed.")
    elif len(args) < 5:
        await bot.say("You need at least 4 taboo words to add a new card.")
    else:
        card = args[0].upper().strip()
        taboo_ = [str(word).upper().strip() for word in args[1:]]
        server_id = context.message.server.id

        connection = sqlite3.connect('db/{}.db'.format(server_id))
        cursor = connection.cursor()

        cursor.execute("select card from cards where card like '{}'".format(card))
        if cursor.fetchone() is not None:
            await bot.say("The card {} already exists in the database".format(card))
        else:
            cursor.execute("insert into cards values('{}', '{}')".format(card, '|'.join(taboo_)))
            await bot.say("""
            Card added:\n```diff\n+ {}\n{}\n- {}\n```
            """.format(card, '-'*20, '\n- '.join(taboo_))
            )

        cursor.close()
        connection.commit()
        connection.close()


@bot.command(name='delcard', aliases=['dc'], pass_context=True)
async def del_card(context, *args):
    if len(args) < 1:
        await bot.say("No arguments passed.")
    else:
        card = args[0].upper().strip()
        server_id = context.message.server.id

        connection = sqlite3.connect('db/{}.db'.format(server_id))
        cursor = connection.cursor()

        cursor.execute("select taboo from cards where card like '{}'".format(card))
        taboo_ = cursor.fetchone()
        taboo_ = taboo_[0] if taboo_ else None

        if taboo_:
            cursor.execute("delete from cards where card like '{}'".format(card))
            await bot.say("The card:\n```diff\n+ {}\n{}\n- {}\n```\nwas removed from the "
                          "database.".format(card, '-' * 20, '\n- '.join(taboo_.split('|'))))
        else:
            await bot.say("The card {} does not exists in the database.".format(card))

        cursor.close()
        connection.commit()
        connection.close()


@bot.command(name='replcard', aliases=['rc'], pass_context=True)
async def replace_card(context, *args):
    if len(args) == 0:
        await bot.say("No arguments passed.")
    elif len(args) < 5:
        await bot.say("You need at least 4 taboo words to add a new card.")
    else:
        card = args[0].upper().strip()
        taboo_ = [word.upper().strip() for word in args[1:]]
        server_id = context.message.server.id

        connection = sqlite3.connect('db/{}.db'.format(server_id))
        cursor = connection.cursor()

        cursor.execute("replace into cards (card, taboo) values('{}', '{}')".format(card, '|'.join(
            taboo_)))
        await bot.say("""
        Card added:\n```diff\n+ {}\n{}\n- {}\n```
        """.format(card, '-'*20, '\n- '.join(taboo_))
        )

        cursor.close()
        connection.commit()
        connection.close()


@bot.command(name='showcard', aliases=['c'], pass_context=True)
async def show_card(context, *args):
    if len(args) < 1:
        await bot.say("No arguments passed.")
    else:
        card = args[0].upper().strip()
        server_id = context.message.server.id

        connection = sqlite3.connect('db/{}.db'.format(server_id))
        cursor = connection.cursor()

        cursor.execute("select taboo from cards where card like '{}'".format(card))
        taboo_ = cursor.fetchone()
        taboo_ = taboo_[0] if taboo_ else None

        if taboo_:
            await bot.say("```diff\n+ {}\n{}\n- {}```".format(
                card, '-'*20, '\n- '.join(taboo_.split('|'))
            ))
        else:
            await bot.say("The card {} does not exists in the database.".format(card))


""" ---... Taboo Game ...--- """


@bot.command(name='buzz', pass_context=True)
async def buzz(context):
    pass


@bot.command(name='join', aliases=['j'], pass_context=True)
async def join(context):
    server_id = context.message.server.id
    author = context.message.author
    pass


@bot.command(name='leave', aliases=['l'], pass_context=True)
async def leave(context):
    pass


@bot.command(name='skip', aliases=['s'], pass_context=True)
async def skip(context):
    pass


@bot.command(name='start', pass_context=True)
async def start(context):
    pass


@bot.command(name='stop', pass_context=True)
async def stop(context):
    pass


@bot.command(name='taboo', aliases=['t'], pass_context=True)
async def taboo(context):
    server_id = context.message.server.id

    taboo_game = None if server_id not in games else games[server_id]

    if not taboo_game:
        games[server_id] = Taboo()
        queues[server_id] = queue.Queue()

        await bot.say("""
        Game created. The game will start in 5 minutes.
            Type `\\join` to join the game.
        """)
    elif taboo_game.playing:
        await bot.say("Can't start a new game when there's one taking place.")
    else:
        await bot.say("A game was already created and will start soon.")


""" ---... Miscellaneous ...--- """


@bot.command(name='addadmin', aliases=['aa'], pass_context=True)
async def add_admin(context):
    author = context.message.author.id
    mentions = context.message.mentions
    server_id = context.message.server.id

    if not len(mentions):
        await bot.say('No arguments passed after the command')
        return

    admins = __get_admins(server_id)

    if author in admins:
        if mentions[0].id not in admins:
            __add_admin(server_id, mentions[0].id)
            await bot.say("{} is now an admin.".format(mentions[0].mention))
        else:
            await bot.say("{} was already an admin.".format(mentions[0].mention))


@bot.command(name='listadmins', aliases=['la'], pass_context=True)
async def list_admins(context):
    author = context.message.author.id
    server_id = context.message.server.id

    admins = __get_admins(server_id)

    if author in admins:
        text = ""
        for i, admin in enumerate(admins):
            text += " {}. <@{}>\n".format(i+1, admin)
        await bot.say("Admins:\n" + text)


@bot.command(name='listconf', aliases=['lc'], pass_context=True)
async def list_conf(context):
    server_id = context.message.server.id
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("select * from settings")
    settings = cursor.fetchall()
    string = "```"

    for setting, value in settings:
        string += '\n{}\t-\t{}'.format(setting, value)
    string += '\n```'

    await bot.say(string)


@bot.command(name='removeadmin', aliases=['ra'], pass_context=True)
async def remove_admin(context):
    author = context.message.author.id
    mentions = context.message.mentions
    server_id = context.message.server.id

    if not len(mentions):
        await bot.say('No arguments passed after the command')
        return

    admins = __get_admins(server_id)

    if author in admins:
        if mentions[0].id not in admins:
            await bot.say("{} is not an admin.".format(mentions[0].mention))
        else:
            __remove_admin(server_id, mentions[0].id)
            await bot.say("{} was removed from the admin list.".format(mentions[0].mention))


@bot.command(name='repo')
async def repo():
    await bot.say('https://github.com/Kremor/gally')


@bot.command(name='setchannel', aliases=['sc'], pass_context=True)
async def set_channel(context):
    author_id = context.message.author.id
    server_id = context.message.server.id

    admins = __get_admins(server_id)

    if author_id not in admins:
        return

    channel_mentions = context.message.channel_mentions
    if not len(channel_mentions):
        await bot.say("No channel passed as argument.")
        return

    __set_setting(server_id, 'CHANNEL', channel_mentions[0].id)
    await bot.say("The bot will listen to the channel {} when playing taboo.".format(
        channel_mentions[0].mention
    ))


@bot.command(name='setrounds', aliases=['sr'], pass_context=True)
async def set_rounds(context, *args):
    author_id = context.message.author.id
    server_id = context.message.server.id

    admins = __get_admins(server_id)

    if author_id not in admins:
        return

    if not len(args):
        await bot.say("No arguments were passed to the command.")
        return

    if not __is_number(args[0]):
        await bot.say("Argument must be a number.")
        return

    if int(args[0]) < 1:
        await bot.say("You need at lest 1 round to play the game.")
        return

    __set_setting(server_id, 'ROUNDS', args[0])
    await bot.say("Setting updated. A game will finish after {} rounds.".format(args[0]))


@bot.command(name='settimer', aliases=['st'], pass_context=True)
async def set_timer(context, *args):
    author_id = context.message.author.id
    server_id = context.message.server.id

    admins = __get_admins(server_id)

    if author_id not in admins:
        return

    if not len(args):
        await bot.say("No arguments were passed to the command.")
        return

    if not __is_number(args[0]):
        await bot.say("Argument must be a number.")
        return

    if int(args[0]) < 60:
        await bot.say("Turns must be at least 60 seconds long.")
        return

    __set_setting(server_id, 'SECONDS', args[0])
    await bot.say("Setting updated. A turn will finish after {} seconds.".format(args[0]))


""" ---... UTILITY ...--- """


def __add_admin(server_id: str, admin_id: str):
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("insert into admins values({})".format(admin_id))

    cursor.close()
    connection.commit()
    connection.close()


def __get_admins(server_id: str) -> list:
    global __owner_id

    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("select * from admins".format(server_id))

    admins = [__owner_id] + [admin[0] for admin in cursor.fetchall()]

    cursor.close()
    connection.close()

    return admins


def __remove_admin(server_id: str, admin_id: str):
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("delete from admins where id like '{}'".format(admin_id))

    cursor.close()
    connection.commit()
    connection.close()


def __add_card(server_id: str, card: str, taboos: str):
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("insert into cards values({}, {})".format(card, taboos))

    cursor.close()
    connection.commit()
    connection.close()


def __get_cards(server_id: str) -> list:
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("select * from cards".format(server_id))

    cards = list(cursor.fetchall())

    cursor.close()
    connection.close()

    return cards


def __remove_card(server_id: str, card: str):
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("delete from cards where card like '{}'".format(card))

    cursor.close()
    connection.commit()
    connection.close()


def __get_setting(server_id: str, setting: str) -> str:
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("select value from settings where setting like '{}'".format(setting))

    value = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return value


def __set_setting(server_id: str, setting: str, value: str):
    connection = sqlite3.connect('db/{}.db'.format(server_id))
    cursor = connection.cursor()

    cursor.execute("replace into settings (setting, value) values('{}', '{}')".format(
        setting, value
    ))

    cursor.close()
    connection.commit()
    connection.close()


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


if __name__ == '__main__':
    main()
