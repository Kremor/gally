import asyncio
import enum
import random
import re
import sqlite3

from discord import Color
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot

import editdistance

import gally.utils as utils


buzz_re = re.compile(r'\\t(aboo)?\s+buzz\s+')
taboo_re = re.compile(r'\\t(aboo)?\s+')


def is_taboo_channel():

    def predicate(context):
        channel_id = utils.get_setting(context.message.server.id, 'TABOO_CHANNEL')

        return channel_id == context.message.channel.id

    return commands.check(predicate)


class TabooMsg:

    class Type(enum.Enum):
        none = 0
        start = 1
        stop = 2
        game_over = 3
        skip_card = 4
        guess = 5
        buzz = 6

    def __init__(self, type_: Type=Type.none, content='', author: str=''):
        self.type = type_
        self.content = content
        self.author = author


class TabooGame:

    def __init__(self, bot: Bot, server_id, channel, cards: list, callback, rounds: int=1,
                 seconds: int=120):
        self.bot = bot
        self.callback = callback
        self.channel = channel
        self.server_id = server_id

        self.cards = cards
        self.rounds = rounds
        self.seconds = seconds

        self.current_card = ()
        self.clue_giver = ''
        self.watcher = ''

        self.players = []
        self.playing = False

        self.team_a = []
        self.team_b = []
        self.team_a_score = 0
        self.team_b_score = 0

        self.turns = []
        self.queue = asyncio.Queue()

        self.bot.loop.create_task(self.game_loop())

    @staticmethod
    def format_card(card: tuple) -> str:
        return "```diff\n+ {}\n{}\n- {}\n```".format(
            card[0], '-' * 20, '\n- '.join(card[1].split('|'))
        )

    def add_player(self, player: str):
        if player not in self.players:
            self.players.append(player)
        print(self.players)

    async def buzz(self, word):
        word = word.uppeer().strip()
        for taboo in self.current_card[1].split('|'):
            if editdistance.eval(taboo, word) < 2:
                embed = Embed(description='<@{}> said **{}**.\nCard skipped.', title='Taboo')
                embed.add_field(name='Card', value=self.format_card(self.current_card))
                await self.bot.send_message(self.channel, embed=embed)
                self.current_card = self.cards.pop()
                self.score(True)
                await self.dm_current_card()
                break

    async def dm_current_card(self):
        if not self.current_card or not self.clue_giver or not self.watcher:
            return

        card = self.format_card(self.current_card)
        clue_giver = self.get_player(self.clue_giver)
        watcher = self.get_player(self.watcher)

        await self.bot.send_message(
            clue_giver,
            embed=utils.get_embed(card)
        )
        await self.bot.send_message(
            watcher,
            embed=utils.get_embed(card)
        )

    def get_player(self, user_id):
        return self.bot.get_server(self.server_id).get_member(user_id)

    def get_team(self, t: str):
        t = t.upper().strip()
        team = self.team_a if t == 'A' else self.team_b

        result = ''

        for i, member in enumerate(team):
            result += '\n{}. <@{}>'.format(i+1, member)

        return result

    def get_watcher_id(self) -> str:
        index = self.players.index(self.clue_giver) + 3
        if index >= len(self.players):
            index -= len(self.players)
        return self.players[index]

    async def guess(self, word):
        word = word.upper().strip()

        if editdistance.eval(word, self.current_card[0]) < 2:
            await self.bot.send_message(
                self.channel,
                embed=utils.get_embed(
                    'The word was **{}**'.format(self.current_card[0]), title='Correct'
                )
            )

            self.current_card = self.cards.pop()
            self.score()

            await self.dm_current_card()

    async def next_turn(self):
        if not self.turns:
            self.rounds -= 1
            if not self.rounds:
                self.queue.put_nowait(
                    TabooMsg(TabooMsg.Type.game_over)
                )
            else:
                self.turns = self.players[:]

        if self.rounds:
            self.current_card = self.cards.pop()
            self.clue_giver = self.turns.pop()
            self.watcher = self.get_watcher_id()

            description = 'Now is Team\'s {} turn.'.format(
                'A' if self.clue_giver in self.team_a else 'B'
            )

            # TODO - finish message
            await self.bot.send_message(
                self.channel,
                embed=utils.get_embed(
                    description, title='Time\'s over'
                )
            )

            await self.dm_current_card()

    def remove_player(self, player: str):
        if player in self.players:
            self.players.remove(player)

    def score(self, opposite: bool=False):
        if opposite:
            if self.clue_giver in self.team_a:
                self.team_b_score += 1
            else:
                self.team_a_score += 1
        else:
            if self.clue_giver in self.team_a:
                self.team_a_score += 1
            else:
                self.team_b_score += 1

    def send_message(self, type_: TabooMsg.Type, content='', author=''):
        self.queue.put_nowait(TabooMsg(type_, content, author))

    async def skip_card(self):
        await self.bot.send_message(
            self.channel, embed=utils.get_embed(self.format_card(self.current_card), 'Card skipped')
        )
        self.score(True)
        self.current_card = self.cards.pop()

    """ ---... GAME LOOP ...--- """

    async def game_loop(self):
        inactive_time = 0.0
        time = 0.0
        minutes = 5

        await self.bot.send_message(
            self.channel,
            embed=utils.get_embed("New game created.\nType `\\taboo join` to enter the game")
        )

        while True:
            await asyncio.sleep(0.01)
            time += 0.01

            message = self.queue.get_nowait() if not self.queue.empty() else TabooMsg()

            # Quit game
            if message.type == TabooMsg.Type.stop:
                await self.bot.send_message(
                    self.channel,
                    embed=utils.get_embed('Game cancelled.')
                )
                break

            # Start game
            if message.type == TabooMsg.Type.start:
                if len(self.players) < 4:
                    await self.bot.send_message(
                        self.channel,
                        embed=utils.get_embed('You need at least 4 players to start a new game.')
                    )
                    self.send_message(TabooMsg.Type.stop)
                    continue
                random.shuffle(self.cards)
                self.current_card = self.cards.pop()

                random.shuffle(self.players)
                for i, player in enumerate(self.players):
                    if i % 2 == 0:
                        self.team_a.append(player)
                    else:
                        self.team_b.append(player)
                self.turns = self.players[:]
                self.clue_giver = self.turns.pop()
                self.watcher = self.get_watcher_id()

                await  self.dm_current_card()

                embed = Embed(title='Game has started', color=Color.magenta())
                embed.add_field(name='Team A', value=self.get_team('a'))
                embed.add_field(name='Team B', value=self.get_team('b'))
                # TODO - finish message
                await self.bot.send_message(
                    self.channel,
                    embed=embed
                )
                self.playing = True
                continue

            if not self.playing:
                if time > 60:
                    time = 0
                    minutes -= 1
                    if minutes:
                        await self.bot.send_message(
                            self.channel,
                            embed=utils.get_embed(
                                "{} minutes before the game starts.".format(minutes)
                            )
                        )
                    else:
                        self.queue.put_nowait(TabooMsg(TabooMsg.Type.start))
            else:

                # Inactive time
                if message.type == TabooMsg.Type.none:
                    inactive_time += 0.01
                    if inactive_time > 60:
                        await self.bot.send_message(
                            self.channel, embed=utils.get_embed("Game canceled due to inactivity.")
                        )
                        break
                else:
                    inactive_time = 0

                # Next turn
                if time > self.seconds:
                    await  self.next_turn()
                    time = 0

                # Guess card
                elif message.type == TabooMsg.Type.guess:
                    if (self.clue_giver in self.team_a and message.author in self.team_a) or\
                       (self.clue_giver in self.team_b and message.author in self.team_b):
                        await self.guess(message.content)

                # Skip card
                elif message.type == TabooMsg.Type.skip_card:
                    if self.clue_giver == message.author:
                        await self.skip_card()
                        await self.dm_current_card()

                # Buzz
                elif message.type == TabooMsg.Type.buzz:
                    if self.watcher == message.author:
                        await self.buzz(message.content)

                # Game Over
                elif message.type == TabooMsg.Type.game_over:
                    embed = Embed(title='Game Over!')
                    if self.team_a_score > self.team_b_score:
                        embed.description = "The winner is Team A :tada:"
                        for i, member in enumerate(self.team_a):
                            embed.description += '\n{}. <@{}>'.format(i+1, member)
                    elif self.team_b_score > self.team_a_score:
                        embed.description = "The winner is Team B :tada:"
                        for i, member in enumerate(self.team_b):
                            embed.description += '\n{}. <@{}>'.format(i + 1, member)
                    else:
                        embed.description = "Nobody won! Everyone's a looser :tada:"
                    await self.bot.send_message(self.channel, embed=embed)
                    break

        self.callback(self.server_id)


class Taboo:

    def __init__(self, bot: Bot):
        self.bot = bot
        self.games = {}

    @commands.group(pass_context=True, aliases=['t'])
    async def taboo(self, context):
        """
        Play Taboo.
        """
        if context.invoked_subcommand is None:
            match = re.match(taboo_re, context.message.content)
            guess = match.string[match.end(0):] if match else ''
            print(guess)
            server_id = context.message.server.id
            if server_id in self.games and guess:
                self.games[server_id].queue.put_nowait(
                    TabooMsg(
                        TabooMsg.Type.buzz,
                        guess,
                        context.message.author.id
                    )
                )

    """ ---... CARDS ... --- """

    @taboo.command(pass_context=True, name='addcard', aliases=['ac'])
    async def add_card(self, context, *args):
        """
        Add a new card to the database.

        Usage:

            \taboo addcard <card_name> <taboo1> <taboo2> <taboo3> <taboo4> ...
        """
        if len(args) == 0:
            await self.bot.say("No arguments passed.")
        elif len(args) < 5:
            await self.bot.say("You need at least 4 taboo words to add a new card.")
        else:
            card = args[0].upper().strip()
            taboo_ = [str(word).upper().strip() for word in args[1:]]
            server_id = context.message.server.id
            server_db = utils.get_dir() + 'db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("SELECT CARD FROM CARDS WHERE CARD LIKE '{}'".format(card))
            if cursor.fetchone() is not None:
                await self.bot.say("The card {} already exists in the database".format(card))
            else:
                cursor.execute(
                    "INSERT INTO CARDS VALUES(?, ?)", (card, '|'.join(taboo_)))
                await self.bot.say(embed=utils.get_embed(
                    TabooGame.format_card((card, '|'.join(taboo_))), "Card added."
                ))

            cursor.close()
            connection.commit()
            connection.close()

    @taboo.command(pass_context=True, aliases=['c'])
    async def card(self, context, *args):
        """
        Shows a card from the database

        Usage:

            \taboo card <card_name>
        """
        if len(args) < 1:
            await self.bot.say("No arguments passed.")
        else:
            card = args[0].upper().strip()
            server_id = context.message.server.id
            server_db = utils.get_dir() + 'db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("SELECT TABOO FROM CARDS WHERE CARD LIKE '{}'".format(card))
            taboo_ = cursor.fetchone()
            taboo_ = taboo_[0] if taboo_ else None

            cursor.close()
            connection.close()

            if taboo_ is not None:
                await self.bot.say(embed=utils.get_embed(
                    TabooGame.format_card((card, taboo_))
                ))
            else:
                await self.bot.say(embed=utils.get_embed(
                    "The card {} does not exists in the database.".format(card)
                ))

    @taboo.command(pass_context=True, name='delcard', aliases=['dc'])
    async def delete_card(self, context, *args):
        """
        Removes a card from the database.

        Usage:

            \taboo delcard <card_name>
        """
        if len(args) < 1:
            await self.bot.say("No arguments passed.")
        else:
            card = args[0].upper().strip()
            server_id = context.message.server.id
            server_db = utils.get_dir() + 'db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("SELECT TABOO FROM CARDS WHERE CARD LIKE '{}'".format(card))
            taboo_ = cursor.fetchone()
            taboo_ = taboo_[0] if taboo_ else None

            if taboo_ is not None:
                cursor.execute("DELETE FROM CARDS WHERE CARD LIKE '{}'".format(card))
                await self.bot.say(embed=utils.get_embed(
                   TabooGame.format_card((card, taboo_)), 'Card deleted.'
                ))
            else:
                await self.bot.say(embed=utils.get_embed(
                    "The card {} does not exists in the database.".format(card)
                ))

            cursor.close()
            connection.commit()
            connection.close()

    def del_game(self, server_id: str):
        if server_id in self.games:
            del self.games[server_id]

    @taboo.command(pass_context=True, name='replcard', aliases=['rc'])
    async def replace_card(self, context, *args):
        """
        Replace all the taboo words of a card.
        If the card does not exists it is added to the database instead.

        Usage:

            \taboo replcard <card_name> <taboo1> <taboo2> <taboo3> <taboo4>
        """
        if len(args) == 0:
            await self.bot.say("No arguments passed.")
        elif len(args) < 5:
            await self.bot.say("You need at least 4 taboo words to add a new card.")
        else:
            card = args[0].upper().strip()
            taboo_ = [word.upper().strip() for word in args[1:]]
            server_id = context.message.server.id
            server_db = utils.get_dir() + 'db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute(
                "REPLACE INTO CARDS(CARD, TABOO) values(?, ?)", (card, '|'.join(taboo_)))
            await self.bot.say(embed=utils.get_embed(
                TabooGame.format_card((card, '|'.join(taboo_))), 'Card replaced.'
            ))

            cursor.close()
            connection.commit()
            connection.close()

    """ ---... TABOO ...--- """

    @taboo.command(pass_context=True)
    @is_taboo_channel()
    async def buzz(self, context, *args):
        """
        Use it when the clue giver commits a fault.
        Only the card watcher can use this command during the game.
        When used the current card is skipped and the card watcher's team receives a point.

        Usage:

            \taboo buzz <taboo_word>
        """
        server_id = context.message.server.id

        match = re.match(buzz_re, context.message.content)
        buzz = match.string[match.end(0):] if match else ''

        if server_id in self.games and buzz:
            self.games[server_id].send_message(
                TabooMsg.Type.buzz,
                buzz,
                author=context.message.author.id
            )

    @taboo.command(pass_context=True, aliases=['j'])
    @is_taboo_channel()
    async def join(self, context):
        """
        Adds you to the game.

        Usage:

            \taboo join
        """
        server_id = context.message.server.id
        author = context.message.author

        if server_id not in self.games:
            await self.bot.say("There's not game currently taking place")
            return

        taboo_game = self.games[server_id]

        if taboo_game.playing:
            await self.bot.say("Can't add a player when a game is taking place.")
            return

        if author.id in taboo_game.players:
            await self.bot.say("{} you're already in the game dummy.".format(
                context.message.author.mention
            ))
            return

        taboo_game.add_player(author.id)
        await self.bot.say(embed=utils.get_embed(
            "{} was added to the game.\nThere are currently {} players in the game".format(
                author.mention, len(taboo_game.players)
            )
        ))

    @taboo.command(pass_context=True, aliases=['l'])
    @is_taboo_channel()
    async def leave(self, context):
        """
        Removes you from the game.

        Usage:

            \taboo leave
        """
        server_id = context.message.server.id
        author = context.message.author

        if server_id not in self.games:
            await self.bot.say("There's not game currently taking place.")
            return

        taboo_game = self.games[server_id]

        if taboo_game.playing:
            await self.bot.say("Can't remove a player when a game is taking place.")
            return

        if author.id not in taboo_game.players:
            await self.bot.say("You're not in the game dummy.".format(
                context.message.author.mention
            ))
            return

        taboo_game.remove_player(author.id)
        await self.bot.say(embed=utils.get_embed(
            "{} left the game :cry:\nThere are currently {} players in the game".format(
                author.mention, len(taboo_game.players)
            )
        ))

    @taboo.command(pass_context=True, aliases=['n'])
    @is_taboo_channel()
    async def new(self, context):
        """
        Starts a new game.
        When used will wait 5 minutes for other people to join.

        Usage:

            \taboo new
        """
        server_id = context.message.server.id
        channel = context.message.channel

        taboo_game = None if server_id not in self.games else self.games[server_id]

        if taboo_game is None:
            server_db = utils.get_dir() + 'db/{}.db'.format(server_id)
            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM CARDS")
            cards = cursor.fetchall()

            cursor.execute("SELECT VALUE FROM SETTINGS WHERE NAME LIKE 'TABOO_SECONDS'")
            seconds = cursor.fetchone()

            cursor.execute("SELECT VALUE FROM SETTINGS WHERE NAME LIKE 'TABOO_ROUNDS'")
            rounds = cursor.fetchone()

            cursor.close()
            connection.close()

            seconds = int(seconds[0]) if seconds else 120
            rounds = int(rounds[0]) if rounds else 1

            taboo_game = TabooGame(
                self.bot, server_id, channel, cards, self.del_game, rounds, seconds
            )
            taboo_game.add_player(context.message.author.id)
            self.games[server_id] = taboo_game
        elif taboo_game.playing:
            await self.bot.say("Can't start a new game when there's one taking place.")
        else:
            await self.bot.say("A game was already created and will start soon.")

    @taboo.command(pass_context=True, aliases=['s'])
    @is_taboo_channel()
    async def skip(self, context):
        """
        Skips the current card.
        Only the clue giver can use this command.
        When used the opposite team receives a point.

        Usage:

            \taboo skip
        """
        server_id = context.message.server.id

        if server_id not in self.games:
            self.games[server_id].send_message(
                TabooMsg.Type.skip_card,
                author=context.message.author.id
            )

    @taboo.command(pass_context=True)
    @is_taboo_channel()
    async def start(self, context):
        """
        Forces a game to start.

        Usage:

            \taboo start
        """
        server_id = context.message.server.id

        if server_id not in self.games:
            await self.bot.say("There's not game currently taking place.")
            return

        taboo_game = self.games[server_id]

        if taboo_game.playing:
            await self.bot.say("The game has already started.")
            return

        if len(taboo_game.players) < 4:
            await self.bot.say("You need at least 4 players to start a new game.")
            return

        self.games[server_id].send_message(TabooMsg.Type.start)

    @taboo.command(pass_context=True)
    @is_taboo_channel()
    async def stop(self, context):
        """
        Forces a game to stop.

        Usage:

            \taboo stop
        """
        server_id = context.message.server.id

        if server_id not in self.games:
            await self.bot.say("There's not game currently taking place.")
            return

        self.games[server_id].send_message(TabooMsg.Type.stop)

    """ ---... CONFIG ...--- """

    @taboo.command(name='setchannel', aliases=['sc'], pass_context=True)
    @utils.is_admin()
    async def set_channel(self, context):
        """
        Sets the channel to be used for the game. Admins only.

        Usage:

            \taboo setchannel <#channel>
        """
        server_id = context.message.server.id

        channel_mentions = context.message.channel_mentions
        if not len(channel_mentions):
            await self.bot.say("No channel passed as argument.")
            return

        utils.set_setting(server_id, 'TABOO_CHANNEL', channel_mentions[0].id)
        await self.bot.say(embed=utils.get_embed(
            "The bot will listen to the channel {} when playing taboo.".format(
                channel_mentions[0].mention
            )
        ))

    @taboo.command(name='setrounds', aliases=['sr'], pass_context=True)
    @utils.is_admin()
    async def set_rounds(self, context, *args):
        """
        Sets the number of rounds per game. Admins only.

        Usage:

            \taboo setrounds <rounds>
        """
        server_id = context.message.server.id

        if not len(args):
            await self.bot.say("No arguments were passed to the command.")
            return

        if not utils.is_number(args[0]):
            await self.bot.say("Argument must be a number.")
            return

        if len(args[0]) > 3:
            await self.bot.say("Number must be lower than 999.")

        if int(args[0]) < 1:
            await self.bot.say("You need at lest 1 round to play the game.")
            return

        utils.set_setting(server_id, 'TABOO_ROUNDS', args[0])
        await self.bot.say(embed=utils.get_embed(
            "Setting updated. A game will finish after {} rounds.".format(args[0])
        ))

    @taboo.command(name='settime', aliases=['st'], pass_context=True)
    @utils.is_admin()
    async def set_timer(self, context, *args):
        """
        Sets the durations per turn in seconds. Admins only.

        Usage:

            \taboo settime <seconds>
        """
        server_id = context.message.server.id

        if not len(args):
            await self.bot.say("No arguments were passed to the command.")
            return

        if not utils.is_number(args[0]):
            await self.bot.say("Argument must be a number.")
            return

        if int(args[0]) < 60:
            await self.bot.say("Turns must be at least 60 seconds long.")
            return

        utils.set_setting(server_id, 'TABOO_SECONDS', args[0])
        await self.bot.say(embed=utils.get_embed(
            "Setting updated. A turn will finish after {} seconds.".format(args[0])
        ))
