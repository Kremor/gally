import sys

from discord.ext import commands
import taboo


bot = commands.Bot('\\')


@bot.command()
async def hi(*args):
    """Says hi"""
    await bot.say('hi' + args)


@bot.group(pass_context=True)
async def taboo(ctx):
    """Creates a new taboo game."""
    if ctx.invoked_subcommand is None:
        await bot.say('No arguments')


# =====.===== TABOO =====.=====


@taboo.command(name='new')
async def taboo_new():
    """Creates a new taboo game"""
    await bot.say('New game created')


@taboo.command(name='at')
async def taboo_add_team(member1, member2):
    """
    Adds a new team to the current game.
    """
    await bot.say('{} and {} where added to the game'.format(member1, member2))


@taboo.command(name='rt')
async def taboo_remove_team(member):
    """
    Removes a team from the game.
    Where <member> can be any of the members of the team.
    """
    pass


@taboo.command(name='start')
async def taboo_start():
    """Starts the game"""
    pass


@taboo.command(name='stop')
async def taboo_stop():
    """Stops the current game"""
    pass


@taboo.command(name='time')
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
