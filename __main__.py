import argparse
import re
import sqlite3

from discord.ext import commands

from taboo import Taboo

bot = commands.Bot('\\')

games = {}

__owner_id = ''


@bot.event()
async def on_ready():
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    for server in bot.servers:
        cursor.execute("create table if not exists admins_{} (id text)".format(
            server.id
        ))
        cursor.execute(
            "create unique index idx_admins_{0}_id on admins_{0}(id)".format(server.id)
        )

        cursor.execute("create table if not exists cards_{} (card text, taboo text)".format(
            server.id
        ))
        cursor.execute("create unique index idx_cards_{0}_card on cards_{0}(card)".format(
            server.id
        ))

        cursor.execute("create table if not exists settings_{} (setting text, value text)".format(
            server.id
        ))
        cursor.execute("create unique index idx_settings_{0}_setting on settings_{0}("
                       "setting)".format(server.id))

        cursor.execute("insert into settings_{0}(name, value) select '{1}', '{2}' where not "
                       "exists (select 1 from settings_{0} where name='{1}')".format(
                        server, 'rounds', '1'))
        cursor.execute("insert into settings_{0}(name, value) select '{1}', '{2}' where not "
                       "exists (select 1 from settings_{0} where name='{1}')".format(
                        server, 'seconds', '120'))


    cursor.close()
    connection.commit()
    connection.close()


""" ---... Cards management ...--- """


@bot.command(name='addcard', aliases=['ac'], pass_context=True)
async def add_card(context, *args):
    if len(args) == 0:
        await bot.say("No arguments passed.")
    elif len(args) < 5:
        await bot.say("You need at least 4 taboo words to add a new card.")
    else:
        await bot.say("""
        Card added:\n```diff\n+ {}\n--------------------\n{}\n```
        """.format(args[0].upper(), '- ' + '\n- '.join(args[1:]).upper())
        )


@bot.command(name='removecard', aliases=['rc'], pass_context=True)
async def remove_card(context, *args):
    pass


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
        taboo_game = Taboo()
        await bot.say("""
        Game created. The game will start in 5 minutes.
            Type `\\join` to join the game.
        """)
    elif taboo_game.playing:
        await bot.say("Can't start a new game when there's one taking place.")
    else:
        await bot.say("A game was already created and will start soon.")

    games[server_id] = taboo_game


""" ---... Miscellaneous ...--- """


@bot.command(name='addadmin', aliases=['aa'], pass_context=True)
async def add_admin(context):
    author = context.message.author.id
    mentions = context.message.mentions
    server_id = context.message.server.id
    is_admin = False

    if not len(mentions):
        await bot.say('No arguments passed after the command')
        return

    admins = __get_admins(server_id)

    for admin in admins:
        if author == admin:
            is_admin = True
            break

    if is_admin:
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


@bot.command(name='listcon', aliases=['lc'], pass_context=True)
async def list_conf(context):
    pass


@bot.command(name='removeadmin', aliases=['ra'], pass_context=True)
async def remove_admin(context):
    author = context.message.author.id
    mentions = context.message.mentions
    server_id = context.message.server.id
    is_admin = False

    if not len(mentions):
        await bot.say('No arguments passed after the command')
        return

    admins = __get_admins(server_id)

    for admin in admins:
        if author == admin:
            is_admin = True
            break

    if is_admin:
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
    pass


@bot.command(name='setrounds', aliases=['sr'], pass_context=True)
async def set_rounds(context, *args):
    pass


@bot.command(name='settimer', aliases=['st'], pass_context=True)
async def set_timer(context, *args):
    pass


""" ---... UTILITY ...--- """


def __add_admin(server_id: str, admin_id: str):
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("insert into admins_{} values({})".format(
        server_id, admin_id
    ))

    cursor.close()
    connection.commit()
    connection.close()


def __get_admins(server_id: str) -> list:
    global __owner_id

    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("select * from admins_{}".format(server_id))

    admins = [__owner_id] + [admin[0] for admin in cursor.fetchall()]

    cursor.close()
    connection.close()

    return admins


def __remove_admin(server_id: str, admin_id: str):
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("remove from admins_{} where id like'{}'".format(
        server_id, admin_id
    ))

    cursor.close()
    connection.commit()
    connection.close()


def __add_card(server_id: str, card: str, taboos: str):
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("insert into cards_{} values({}, {})".format(
        server_id, card, taboos
    ))

    cursor.close()
    connection.commit()
    connection.close()


def __get_cards(server_id: str) -> list:
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("select * from cards_{}".format(server_id))

    cards = list(cursor.fetchall())

    cursor.close()
    connection.close()

    return cards


def __remove_card(server_id: str, card: str):
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("remove from cards_{} where card like'{}'".format(
        server_id, card
    ))

    cursor.close()
    connection.commit()
    connection.close()


def __get_setting(server_id: str, setting: str) -> str:
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("select value from settings_{} where setting like '{}'".format(
        server_id, setting
    ))

    value = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return value


def __set_setting(server_id: str, setting: str, value: str):
    connection = sqlite3.connect('db/database.db')
    cursor = connection.cursor()

    cursor.execute("select value from settings_{} where setting like '{}'".format(
        server_id, setting
    ))

    cursor.close()
    connection.commit()
    connection.close()


__user_id = re.compile(r'\d{17}')
__c_s_id = re.compile(r'\d{18}')
__token = re.compile(r'[0-9a-zA-Z._-]{57}')


def __is_user_id(id: str):
    if re.fullmatch(__user_id, id):
        return True
    return False


def __is_c_s_id(id: str):
    if re.fullmatch(__c_s_id, id):
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
