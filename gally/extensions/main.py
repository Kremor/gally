import sqlite3

from discord import Color
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot

import gally.utils as utils


class Main:

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(pass_context=True, name='addadmin', aliases=['aa'])
    @utils.is_admin()
    async def add_admin(self, context):
        """
        Add a bot administrator. Admins only.

        Usage:

            \addadmin <@user>
        """
        mentions = context.message.mentions
        server_id = context.message.server.id

        if not len(mentions):
            await self.bot.say('No arguments passed after the command')
            return

        admins = utils.get_admins(server_id)

        server_db = utils.get_dir() + '/db/{}.db'.format(server_id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        for mention in mentions:
            if mention.id in admins:
                self.bot.say("{} is already an admin.".format(mention.mention))
            else:
                cursor.execute("replace into admins(id) values('{}')".format(
                    mention.id
                ))
                await self.bot.say("{} was added to the admin list".format(mention.mention))

        cursor.close()
        connection.commit()
        connection.close()

    @commands.command(pass_context=True, name='listadmins', aliases=['la'])
    @utils.is_admin()
    async def list_admins(self, context):
        """
        List all the bot's administrators. Admins only.

        Usage:

            \listadmins
        """
        admins = utils.get_admins(context.message.server.id)

        message = ''
        for i, admin in enumerate(admins):
            message += "{}. <@{}>\n".format(i+1, admin)

        await self.bot.say(embed=Embed(
            title='Admins', color=Color.magenta(), description=message
        ))

    @commands.command(pass_context=True, name='listconf', aliases=['lc'])
    @utils.is_admin()
    async def list_conf(self, context):
        """
        List the bot settings. Admins only.

        Usage:

            \listconf
        """
        server_db = utils.get_dir() + '/db/{}.db'.format(context.message.server.id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        cursor.execute("select * from settings")
        settings = cursor.fetchall()

        message = ''
        for setting, value in settings:
            message += '{:<20} - {:<20}\n'.format(setting, value)

        await self.bot.say(embed=utils.get_embed(
            message, 'Configuration'
        ))

    @commands.command(pass_context=True, name='removeadmin', aliases=['ra'])
    @utils.is_admin()
    async def remove_admin(self, context):
        """
        Remove a bot administrator. Admins only.

        Usage:

            \removeadmin <@user>
        """
        mentions = context.message.mentions
        server_id = context.message.server.id

        if not len(mentions):
            await self.bot.say('No arguments passed after the command')
            return

        admins = utils.get_admins(server_id)

        server_db = utils.get_dir() + '/db/{}.db'.format(server_id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        for mention in mentions:
            if mention.id not in admins:
                self.bot.say(embed=utils.get_embed(
                    "{} was not an admin.".format(mention.mention)
                ))
            else:
                cursor.execute("delete from admins where id like '{}'".format(
                    mention.id
                ))
                await self.bot.say(embed=utils.get_embed(
                    "{} was removed from the admin list".format(mention.mention)
                ))

        cursor.close()
        connection.commit()
        connection.close()

    @commands.command(name='repo')
    async def repo(self):
        """
        Links the bot's git repository.
        """
        await self.bot.say(embed=utils.get_embed(
            "https://github.com/Kremor/gally", 'Repo'
        ))


def setup(bot: Bot):
    bot.add_cog(Main(bot))
