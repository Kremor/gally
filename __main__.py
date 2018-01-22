import asyncio
import os.path
import sqlite3
import sys

from discord.ext import commands

from taboo import Taboo

bot = commands.Bot('\\')

games = {}


""" ---... Cards management ...--- """


@bot.command(name='addcard', aliases=['ac'], pass_context=True)
async def add_card(context):
    pass


@bot.command(name='removecard', aliases=['rc'], pass_context=True)
async def remove_card(context):
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
    pass


@bot.command(name='listadmins', aliases=['la'], pass_context=True)
async def list_admins(context):
    pass


@bot.command(name='listcon', aliases=['lc'], pass_context=True)
async def list_conf(context):
    pass


@bot.command(name='removeadmin', aliases=['ra'], pass_context=True)
async def remove_admin(context):
    pass


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


""" ---... MAIN ...--- """


def main():
    if len(sys.argv) < 2:
        print('ERROR: Token needed.')
    bot.run(sys.argv[1])


if __name__ == '__main__':
    main()
