import asyncio
import os.path
import sqlite3
import sys

from discord.ext import commands

bot = commands.Bot('\\')

taboo_data = {}


@bot.command(pass_context=True)
async def hi(context: commands.Context, *args):
    """Says hi to the user"""
    if args:
        if args[0] == 'rose':
            rose = None
            for member in context.message.server.members:
                if member.id == '347681561946357761':
                    rose = member
            await bot.say('hi ' + rose.mention + ' you are :lit: AF')
    else:
        await bot.say('hi ' + context.message.author.mention)


@bot.command(pass_context=True)
async def count(context: commands.Context, seconds: str):
    """counts down"""
    bot.loop.create_task(count_down(int(seconds), context.message.channel))


async def count_down(seconds: int, channel):
    await bot.wait_until_ready()
    await asyncio.sleep(seconds)
    await bot.send_message(channel, 'Tines out!')


@bot.event
async def on_message(message):
    if message.content == 'matrix':
        await bot.send_message(message.channel, 'winner')
    else:
        await bot.process_commands(message)


# =====.===== TABOO =====.=====


@bot.group(aliases=['t'], pass_context=True)
async def taboo(ctx):
    """Taboo game."""
    if ctx.invoked_subcommand is None:
        await bot.say('No arguments')


@taboo.command(name='new', aliases=['n'], pass_context=True)
async def taboo_new(context: commands.Context):
    """Creates a new taboo game"""
    server_id = context.message.server.id

    connection = sqlite3.connect('db/server-settings.db')
    cursor = connection.cursor()

    cursor.execute("create table if not exists taboo (server text, rounds int, seconds int)")

    settings = {}

    for row in cursor.execute("select server, rounds, seconds from taboo"):
        server, rounds, seconds = row
        if server == server_id:
            settings = {'server': server, 'rounds': rounds, 'seconds': seconds, 'teams': []}
            break

    if not settings:
        cursor.execute("insert into taboo ('{}', {}, {})".format(server_id, 10, 120))
        settings = {'server': server_id, 'rounds': 10, 'seconds': 120, 'teams': []}

    cursor.close()
    connection.commit()
    connection.close()

    taboo_data[server_id] = settings

    await bot.say('''
    New game created.
    
    \tTo add a new team - \\taboo addteam @member1 @member 2
    \tTo start the game - \\taboo start
    ''')


@taboo.command(name='addteam', aliases=['at'], pass_context=True)
async def taboo_add_team(context, member1, member2):
    """
    Adds a new team to the current game.
    """
    if not member1 or not member2:
        await  bot.say('Not enough arguments.')

    member1 = member1[2:-1] if '!' not in member1 else member1[3:-1]
    member2 = member2[2:-1] if '!' not in member2 else member2[3:-1]

    p1 = None
    p2 = None

    server = context.message.server
    for member in server.members:
        if member.id == member1:
            p1 = member
        if member.id == member2:
            p2 = member
        if p1 and p2:
            break

    if not p1 or not p2:
        await bot.say('You need to tag a person dummy.')
    elif p1 == p2:
        await bot.say(p1.mention + ' you need another person to play with you, dummy.')
    elif p1.bot:
        await bot.say(p1.mention + ' can\'t play, you dummy.')
    elif p2.bot:
        await bot.say(p1.mention + ' can\'t play, you dummy.')
    else:
        if server.id not in taboo_data:
            server_id = server.id

            connection = sqlite3.connect('db/server-settings.db')
            cursor = connection.cursor()

            cursor.execute(
                "create table if not exists taboo (server text, rounds int, seconds int)")

            settings = {}

            for row in cursor.execute("select server, rounds, seconds from taboo"):
                serv, rounds, seconds = row
                if serv == server_id:
                    settings = {'server': serv, 'rounds': rounds, 'seconds': seconds, 'teams': []}
                    break

            if not settings:
                cursor.execute("insert into taboo values(?, ?, ?)", (server_id, 10, 120))
                settings = {'server': server_id, 'rounds': 10, 'seconds': 120, 'teams': []}

            cursor.close()
            connection.commit()
            connection.close()

            taboo_data[server_id] = settings

        teams = taboo_data[server.id]['teams']

        found = False

        for team in teams:
            if p1 == team[0]:
                await bot.say('{} is already in a team with {}.'.format(p1.mention,
                                                                        team[1].mention))
                found = True
            elif p1 == team[1]:
                await bot.say('{} is already in a team with {}.'.format(p1.metion, team[0].mention))
                found = True

            if p2 == team[0]:
                await bot.say('{} is already in a team with {}.'.format(p2.mention,
                                                                        team[1].mention))
                found = True
            elif p2 == team[1]:
                await bot.say('{} is already in a team with {}.'.format(p2.metion, team[0].mention))
                found = True

        if not found:
            teams.append((p1, p2))
            await bot.say('{} and {} where added to the game.'.format(p1.mention, p2.mention))


@taboo.command(name='leaderboard', aliases=['l'], pass_context=True)
async def taboo_leaderboard(context: commands.Context):
    """
    Shows the server's leaderboard
    """
    server = context.message.server
    if server:
        await bot.say("{}'s leaderboard.".format(server.name))


@taboo.command(name='remteam', aliases=['rt'], pass_context=True)
async def taboo_remove_team(context):
    """
    Removes you from the game. It will also remove your partner.
    """
    server_id = context.message.server.id

    if server_id not in taboo_data:
        await bot.say('There\'s not game currently')
        return

    author = context.message.author

    teams = taboo_data[server_id]['teams']
    for i, team in enumerate(teams):
        if author in team:
            await bot.say('{} and {} where removed from the game.'.format(team[0].mention,
                                                                          team[1].mention))
        teams.pop(i)


async def taboo_loop(server_id: str, channel_id: str, seconds: int, rounds: int):
    playing = True
    round_counter = 0
    while playing and round_counter < rounds:
        await asyncio.sleep(seconds)


@taboo.command(name='start', aliases=['s'])
async def taboo_start():
    """Starts the game"""
    bot.loop.create_task(taboo_loop())


@taboo.command(name='stop', pass_context=True)
async def taboo_stop(context):
    """Stops the current game"""
    taboo_data[context.message.server.id]['playing'] = False


@taboo.command(name='time', aliases=['t'])
async def taboo_time(seconds):
    """
    Sets the maximum length per turn in seconds (default is 120)
    """
    pass


@taboo.command(name='wpg')
async def taboo_fist_of(wins_per_game: int):
    """
    Sets the number of maximum wins per game (default is 5).
    The game will end when a team reaches that many wins.
    """
    pass


def main():
    if len(sys.argv) < 2:
        print('ERROR: Token needed.')
    bot.run(sys.argv[1])


if __name__ == '__main__':
    main()
