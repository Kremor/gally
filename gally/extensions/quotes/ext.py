import random
import re
import sqlite3
import time

from discord import Color
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot

import gally.utils as utils


add_re = re.compile(r'\\q(uote)?\s+add\s+')
look_re = re.compile(r'\\q(uote)?\s+look\s+')


class Quotes:

    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_user_name(self, server_id, user_id: str) -> str:
        user = self.bot.get_server(server_id).get_member(user_id)

        if user is not None:
            return user.nick

        user = await self.bot.get_user_info(user_id)

        return user.name

    async def format_quote(self, rowid: int, quote: str, author_id: str, added: int) -> Embed:
        t = int(time.time()) - added

        author = await self.bot.get_user_info(author_id)

        years = t // (60*60*24*365)
        t -= years * (60*60*24*365)
        days = t // (60*60*24)
        t -= days * (60*60*24)
        hours = t // (60*60)
        t -= hours * (60*60)
        minutes = t // 60

        time_string = ""
        if years:
            time_string += "{} years, ".format(years)
        if days:
            time_string += "{} days, ".format(days)
        if hours:
            time_string += "{} hours, ".format(hours)
        if minutes:
            if time_string:
                time_string += "and {} minutes ago.".format(minutes)
            else:
                time_string += "{} minutes ago.".format(minutes)

        if not time_string:
            time_string = '1 minute ago.'

        embed = Embed(
            description="```\n{}```".format(quote),
            title='Quote {}'.format(rowid),
            color=Color.blue()
        )
        embed.set_footer(text='By {}\nAdded {}'.format(
            author.name,
            time_string
        ))

        return embed

    @commands.group(aliases=['q'])
    async def quote(self):
        """
        Quotes
        """
        pass

    @quote.command(pass_context=True)
    async def add(self, context):
        """
        Adds a quote to the database.

        Usage:

            \\q[uote] add <quote>
        """
        match = re.match(add_re, context.message.content)
        if match:
            text = match.string[match.end(0):]
            if text:
                author_id = context.message.author.id
                date = int(time.time())

                server_db = utils.get_db(context.message.server.id)

                connection = sqlite3.connect(server_db)
                connection.execute("INSERT INTO QUOTES VALUES(?, ?, ?)", (text, author_id, date))
                connection.commit()
                connection.close()

                embed = Embed(
                    title="Quote Added",
                    description="```\n{}\n```".format(text),
                    color=Color.blue()
                )
                embed.set_footer(text="By {}".format(
                    context.message.author.name
                ))

                await self.bot.say(embed=embed)
            else:
                await self.bot.say("No quote passed as argument.")

    @quote.command(pass_cotext=True)
    async def delete(self, context, number):
        """
        Deletes a quote from the database. Admins only

        Usage:

            \\q[uote] del <quote number>
        """
        if not utils.is_number(number):
            await self.bot.say("No number passed as argument")
            return

        number = int(number)

        server_db = utils.get_db(context.message.server.id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM QUOTES WHERE ROWID={}".format(number))
        quote = cursor.fetchone()

        if quote:
            cursor.execute("DELETE FROM QUOTES WHERE ROWID={}".format(number))
            await self.bot.say(embed=utils.get_embed('Quote deleted'))
        else:
            await self.bot.say("There is no quote with the number {}".format(number))

        cursor.close()
        connection.commit()
        connection.close()

    @quote.command(pass_context=True)
    async def look(self, context):
        """
        Shows all the quotes that contain the text passed as argument.

        Usage:

            \\q[uote] look <text>
        """
        match = re.match(look_re, context.message.content)
        if match:
            text = match.string[match.end(0)]

            server_db = utils.get_db(context.message.server.id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("SELECT ROWID, * FROM QUOTES WHERE QUOTE LIKE '%{}%' COLLATE NOCASE".
                           format(text))
            quotes = cursor.fetchall()

            cursor.close()
            connection.close()

            if quotes:
                embed = Embed(title='Quotes')
                for rowid, quote, author_id, date in quotes:
                    author_name = await self.get_user_name(
                        context.message.server.id,
                        author_id
                    )
                    embed.add_field(
                        name=str(rowid),
                        value="```\n{}\n```\nby {}".format(quote, author_name),
                        inline=False
                    )
                await self.bot.say(embed=embed)
            else:
                await self.bot.say('No quotes available.')

    @quote.command(pass_context=True)
    async def rand(self, context):
        """
        Shows a random quote.
        If a user is passed as argument, shows a quote from that user.

        Usage:

            \\q[uote] rand <optional user>
        """
        server_db = utils.get_db(context.message.server.id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        if len(context.message.mentions) > 0:
            user_id = context.message.mentions[0].id
            cursor.execute("SELECT ROWID, * FROM QUOTES WHERE AUTHOR LIKE '{}'".format(user_id))
        else:
            cursor.execute("SELECT ROWID, * FROM QUOTES")

        quotes = cursor.fetchall()

        cursor.close()
        connection.close()

        if quotes:
            quote = random.choice(quotes)
            embed = await self.format_quote(*quote)
            await self.bot.say(embed=embed)
        else:
            await self.bot.say("No quotes available.")

    @quote.command(pass_context=True)
    async def show(self, context, number):
        """
        Shows the quote that corresponds to the number passed as argument.

        Usage:

            \\q[uote] show <number>
        """
        if not utils.is_number(number):
            await self.bot.say("No number passed as argument.")
            return

        number = int(number)

        server_db = utils.get_db(context.message.server.id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        cursor.execute(
            "SELECT ROWID, * FROM QUOTES WHERE ROWID={}".format(number)
        )
        quote = cursor.fetchone()

        cursor.close()
        connection.close()

        if quote:
            embed = await self.format_quote(*quote)
            await self.bot.say(embed=embed)
        else:
            await self.bot.say("No quotes available.")


def setup(bot: Bot):
    for server in bot.servers:
        server_db = utils.get_dir() + 'db/{}.db'.format(server.id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS QUOTES(QUOTE TEXT, AUTHOR TEXT, TIME INT)")

        cursor.close()
        connection.commit()
        connection.close()

    bot.add_cog(Quotes(bot))
