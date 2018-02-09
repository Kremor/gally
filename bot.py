import argparse
import asyncio
from os import path
import re
import shutil
import sqlite3

from discord.ext import commands

from taboo import Taboo

bot = commands.Bot('\\')

games = {}
queues = {}
settings = {}

__owner_id = ''


@bot.event
async def on_message(message):
    await bot.wait_until_ready()

    if str(settings[message.server.id]['CHANNEL']) == str(message.channel.id):
        if str(message.server.id) in games:
            if games[str(message.server.id)].playing:
                await queues[str(message.server.id)].put(message.content)

    await bot.process_commands(message)


@bot.event
async def on_ready():
    for server in bot.servers:
        if not path.exists('db/{}.db'.format(server.id)):
            shutil.copy2('database.db', 'db/{}.db'.format(server.id))

        connection = sqlite3.connect('db/{}.db'.format(server.id))
        cursor = connection.cursor()

        cursor.execute("select * from settings")
        settings_ = cursor.fetchall()

        cursor.close()
        connection.close()

        settings[server.id] = {}
        for setting, value in settings_:
            if __is_number(value) and len(setting) < 3:
                settings[server.id][setting] = int(value)
            else:
                settings[server.id][setting] = value
        print(settings)


""" ---... Cards management ...--- """


@bot.command(name='addcard', aliases=['ac'], pass_context=True)
async def add_card(context, *args):
    """
    Add a new card to the database.

    Usage:

        \addcard <card_name> <taboo1> <taboo2> <taboo3> <taboo4> ...
    """
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


@bot.command(name='card', aliases=['c'], pass_context=True)
async def show_card(context, *args):
    """
    Shows a card from the database

    Usage:

        \card <card_name>
    """
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


@bot.command(name='delcard', aliases=['dc'], pass_context=True)
async def del_card(context, *args):
    """
    Removes a card from the database.

    Usage:

        \delcard <card_name>
    """
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
    """
    Replace all the taboo words of a card.
    If the card does not exists it is added to the database instead.

    Usage:

        \replcard <card_name> <taboo1> <taboo2> <taboo3> <taboo4>
    """
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


""" ---... Taboo Game ...--- """


@bot.command(name='buzz', pass_context=True)
async def buzz(context, *args):
    """
    Use it when the clue giver commits a fault.
    Only the card watcher can use this command during the game.
    When used the current card is skipped and the card watcher's team receives a point.

    Usage:

        \buzz <taboo_word>
    """
    author_id = context.message.author.id
    server_id = context.message.server.id
    channel_id = context.message.channel.id

    if server_id in games:
        if channel_id == settings[server_id]['CHANNEL']:
            if args:
                taboo_game = games[server_id]
                if author_id == taboo_game.watcher:
                    taboo_word = args[0].upper().strip()
                    if taboo_word in taboo_game.current_card[1].split('|'):
                        taboo_game.skip()


@bot.command(name='join', aliases=['j'], pass_context=True)
async def join(context):
    """
    Adds you to the game.

    Usage:

        \join
    """
    server_id = context.message.server.id
    channel_id = context.message.channel.id
    author = context.message.author

    if channel_id != __get_setting(server_id, 'CHANNEL'):
        return

    if server_id not in games:
        await bot.say("There's not game currently taking place")
        return

    taboo_game = games[server_id]

    if taboo_game.playing:
        await bot.say("Can't add a player when a game is taking place.")
        return

    if author.id in taboo_game.players:
        await bot.say("{} you're already in the game dummy.".format(
            context.message.author.mention
        ))
        return

    taboo_game.add_player(author.id)
    await bot.say("{} was added to the game.\nThere are currently {} players in the game".format(
        author.mention, len(taboo_game.players)))


@bot.command(name='leave', aliases=['l'], pass_context=True)
async def leave(context):
    """
    Removes you from the game.

    Usage:

        \leave
    """
    server_id = context.message.server.id
    channel_id = context.message.channel.id
    author = context.message.author

    if channel_id != __get_setting(server_id, 'CHANNEL'):
        return

    if server_id not in games:
        await bot.say("There's not game currently taking place.")
        return

    taboo_game = games[server_id]

    if taboo_game.playing:
        await bot.say("Can't remove a player when a game is taking place.")
        return

    if author.id not in taboo_game.players:
        await bot.say("{} left the game :cry:".format(
            context.message.author.mention
        ))
        return

    taboo_game.remove_player(author.id)
    await bot.say("{} was removed to the game.\nThere are currently {} players in the game".format(
        author.mention, len(taboo_game.players)))


@bot.command(name='skip', aliases=['s'], pass_context=True)
async def skip(context):
    """
    Skips the current card.
    Only the clue giver can use this command.
    When used the opposite team receives a point.

    Usage:

        \skip
    """
    server_id = context.message.server.id
    channel_id = context.message.channel.id

    if channel_id != settings[server_id]['CHANNEL']:
        return

    if server_id not in games:
        await bot.say("There's not game currently taking place.")
        return

    games[server_id].skip()


@bot.command(name='start', pass_context=True)
async def start(context):
    """
    Forces a game to start.

    Usage:

        \start
    """
    server_id = context.message.server.id
    channel_id = context.message.channel.id

    if channel_id != __get_setting(server_id, 'CHANNEL'):
        return

    if server_id not in games:
        await bot.say("There's not game currently taking place.")
        return

    taboo_game = games[server_id]

    if taboo_game.playing:
        await bot.say("The game has already started.")
        return

    if len(taboo_game.players) < 4:
        await bot.say("You need at least 4 players to start a new game.")
        return

    taboo_game.playing = True


@bot.command(name='stop', pass_context=True)
async def stop(context):
    """
    Forces a game to stop.

    Usage:

        \stop
    """
    server_id = context.message.server.id
    channel_id = context.message.channel.id

    if channel_id != settings[server_id]['CHANNEL']:
        return

    if server_id not in games:
        await bot.say("There's not game currently taking place.")
        return

    games[server_id].break_ = True


@bot.command(name='taboo', aliases=['t'], pass_context=True)
async def taboo(context):
    """
    Starts a new game.
    When used will wait 5 minutes for other people to join.

    Usage:

        \taboo
    """
    server_id = context.message.server.id
    channel = context.message.channel

    if channel.id != settings[server_id]['CHANNEL']:
        return

    taboo_game = None if server_id not in games else games[server_id]

    if taboo_game is None:
        connection = sqlite3.connect('db/{}.db'.format(server_id))
        cursor = connection.cursor()

        cursor.execute("select * from cards")
        cards = cursor.fetchall()

        cursor.close()
        connection.close()

        if channel.id == 'NONE':
            await bot.say("Can't start a new game. A channel hasn't been set.")
            return

        taboo_game = Taboo(cards)
        taboo_game.add_player(context.message.author.id)
        games[server_id] = taboo_game
        queues[server_id] = asyncio.Queue()

        bot.loop.create_task(game_loop(server_id, channel, settings[server_id]['SECONDS']))

    elif taboo_game.playing:
        await bot.say("Can't start a new game when there's one taking place.")
    else:
        await bot.say("A game was already created and will start soon.")


""" ---... Miscellaneous ...--- """


@bot.command(name='addadmin', aliases=['aa'], pass_context=True)
async def add_admin(context):
    """
    Add a bot administrator. Admins only.

    Usage:

        \addadmin <@user>
    """
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
    """
    List all the bot's administrators. Admins only.

    Usage:

        \listadmins
    """
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
    """
    List the bot settings. Admins only.

    Usage:

        \listconf
    """
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
    """
    Remove a bot administrator. Admins only.

    Usage:

        \removeadmin <@user>
    """
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
    """
    Links the bot's git repository.
    """
    await bot.say('https://github.com/Kremor/gally')


@bot.command(name='setchannel', aliases=['sc'], pass_context=True)
async def set_channel(context):
    """
    Sets the channel to be used for the game.

    Usage:

        \setchannel <#channel>
    """
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
    """
    Sets the number of rounds per game. Admins only.

    Usage:

        \setrounds <rounds>
    """
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


@bot.command(name='settime', aliases=['st'], pass_context=True)
async def set_timer(context, *args):
    """
    Sets the durations per turn in seconds. Admins only.

    Usage:

        \settime <seconds>
    """
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


def __card_formatter(card: tuple) -> str:
    return "```diff\n+ {}\n{}\n -{}\n```".format(
        card[0], '-'*20, '\n- '.join(card[1].split('|'))
    )


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


""" ---... GAME LOOP ...--- """


async def game_loop(server_id: str, channel: str, time_per_turn: int):

    taboo_game = games[server_id]

    await bot.send_message(channel,
            """
            Game created. The game will start in 5 minutes.\nType `\\join` to enter the game.
            """)

    # Waits 5 minutes
    time = 0.0
    minute = 5

    while True:
        await asyncio.sleep(0.1)
        time += 0.1
        if time > 60:
            time = 0
            minute -= 1
            await bot.send_message(
                channel,
                "{} minutes before the game starts.\nType `\\join`to enter the game".format(minute)
            )
        if not minute or taboo_game.break_:
            break

    if taboo_game.break_:
        await bot.send_message(channel, "Game cancelled.")
        del games[server_id]
        return

    if len(taboo_game.players) < 4:
        await bot.send_message(
            channel,
            "Game cancelled, you need at least 4 players to start a new game."
        )
        del games[server_id]
        return

    await bot.say("Game has started.")

    # Game loop
    time = 0.0
    turn_time = time_per_turn
    taboo_game.start()
    current_card = __card_formatter(taboo_game.current_card)
    current_player = bot.get_server(server_id).get_member(taboo_game.current_player)
    watcher = bot.get_server(server_id).get_member(taboo_game.watcher)
    await bot.send_message(current_player, current_card)
    await bot.send_message(watcher, current_card)
    while taboo_game.playing and not taboo_game.break_:

        if turn_time < 0:
            taboo_game.next_turn()
            if not taboo_game.playing:
                continue

            turn_time = time_per_turn

            current_card = __card_formatter(taboo_game.current_card)
            current_player = bot.get_server(server_id).get_member(taboo_game.current_player)
            watcher = bot.get_server(server_id).get_member(taboo_game.watcher)
            queues[server_id] = asyncio.Queue()

            await bot.send_message(
                channel,
                "Time's over! It's next team turn"
            )

            await bot.send_message(current_player, current_card)
            await bot.send_message(watcher, current_card)

        elif not queues[server_id].empty():
            guess = await  queues[server_id].get().upper().strip()
            if taboo_game.guess(guess):
                await bot.send_message(
                    channel,
                    "Correct! The word was {}".format(taboo_game.current_card[0])
                )
                taboo_game.next_card()

                current_card = __card_formatter(taboo_game.current_card)
                current_player = bot.get_server(server_id).get_member(taboo_game.current_player)
                watcher = bot.get_server(server_id).get_member(taboo_game.watcher)

                await bot.send_message(current_player, current_card)
                await bot.send_message(watcher, current_card)

                queues[server_id] = asyncio.Queue()

            time = 0

        await asyncio.sleep(0.01)
        time += 0.01
        turn_time -= 0.01
        if time > 60:
            await bot.send_message(
                channel,
                "Game cancelled due to lack of activity."
            )
            break

    await bot.say("Game Over")
    del games[server_id]


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
