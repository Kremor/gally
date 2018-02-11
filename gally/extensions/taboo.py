import asyncio
import random
import sqlite3

from discord.ext import commands
from discord.ext.commands import Bot

import gally.utils as utils


def is_taboo_channel():

    def predicate(context):
        channel_id = utils.get_setting(context.message.server.id, 'TABOO_CHANNEL')

        return channel_id == context.message.channel.id

    return commands.check(predicate)


class TabooGame:

    def __init__(self, cards: list, rounds=1):
        self.cards = cards
        self.current_card = ()
        self.current_player = ''
        self.watcher = ''
        self.players = []
        self.playing = False
        self.break_ = False
        self.rounds = rounds
        self.team_a = []
        self.team_b = []
        self.team_a_score = 0
        self.team_b_score = 0
        self.turns = []
        self.queue = asyncio.Queue()

    @staticmethod
    def format_card(card) -> str:
        return "```diff\n+ {}\n{}\n- {}\n```".format(
            card[0], '-' * 20, '\n- '.join(card[1].split('|'))
        )

    def add_player(self, player: str):
        if player not in self.players:
            self.players.append(player)

    def guess(self):
        if self.queue.empty():
            return

        word = self.queue.get_nowait().upper().strip()

        if word == self.current_card[0]:
            self.current_card = self.cards.pop()
            if self.current_player in self.team_a:
                self.team_a_score += 1
            else:
                self.team_b_score += 1
            return True
        return False

    def next_card(self):
        self.current_card = self.cards.pop()
        if self.current_player in self.team_a:
            self.team_a_score += 1
        else:
            self.team_b_score += 1

    def next_turn(self):
        if self.current_player in self.team_a:
            self.team_b_score += 1
        elif self.current_player in self.team_b:
            self.team_a_score += 1

        if not self.turns:
            self.rounds -= 1
            if not self.rounds:
                self.playing = False
            else:
                self.turns = self.players[:]

        if self.playing:
            self.current_card = self.cards.pop()
            self.current_player = self.turns.pop()
            self.watcher = self.players[
                self.players.index(self.current_player) + 3
                if self.players.index(self.current_player) + 3 < len(self.players)
                else self.players.index(self.current_player) + 3 - len(self.players)
            ]

    def remove_player(self, player: str):
        if player in self.players:
            self.players.remove(player)

    def skip_card(self):
        self.current_card = self.cards.pop()
        if self.current_player in self.team_a:
            self.team_b_score += 1
        else:
            self.team_a_score += 1

    def start(self):
        if not self.playing:
            self.playing = True
            random.shuffle(self.cards)
            random.shuffle(self.players)
            self.turns = self.players[:]
            for i, player in enumerate(self.players):
                if i % 2 == 0:
                    self.team_a.append(player)
                else:
                    self.team_b.append(player)
            self.next_turn()

    def stop(self):
        if self.playing:
            self.playing = False
            self.break_ = True


class TabooExt:

    def __init__(self, bot: Bot):
        self.bot = bot
        self.games = {}

    """ ---... CARDS ... --- """

    @commands.command(pass_context=True, name='addcard', aliases=['ac'])
    async def add_card(self, context, *args):
        """
        Add a new card to the database.

        Usage:

            \addcard <card_name> <taboo1> <taboo2> <taboo3> <taboo4> ...
        """
        if len(args) == 0:
            await self.bot.say("No arguments passed.")
        elif len(args) < 5:
            await self.bot.say("You need at least 4 taboo words to add a new card.")
        else:
            card = args[0].upper().strip()
            taboo_ = [str(word).upper().strip() for word in args[1:]]
            server_id = context.message.server.id
            server_db = utils.get_dir() + '/db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("select card from cards where card like '{}'".format(card))
            if cursor.fetchone() is not None:
                await self.bot.say("The card {} already exists in the database".format(card))
            else:
                cursor.execute(
                    "insert into cards values('{}', '{}')".format(card, '|'.join(taboo_)))
                await self.bot.say(embed=utils.get_embed(
                    TabooGame.format_card((card, '|'.join(taboo_))), "Card added."
                ))

            cursor.close()
            connection.commit()
            connection.close()

    @commands.command(pass_context=True, aliases=['c'])
    async def card(self, context, *args):
        """
        Shows a card from the database

        Usage:

            \card <card_name>
        """
        if len(args) < 1:
            await self.bot.say("No arguments passed.")
        else:
            card = args[0].upper().strip()
            server_id = context.message.server.id
            server_db = utils.get_dir() + '/db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("select taboo from cards where card like '{}'".format(card))
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

    @commands.command(pass_context=True, name='delcard', aliases=['dc'])
    async def delete_card(self, context, *args):
        """
        Removes a card from the database.

        Usage:

            \delcard <card_name>
        """
        if len(args) < 1:
            await self.bot.say("No arguments passed.")
        else:
            card = args[0].upper().strip()
            server_id = context.message.server.id
            server_db = utils.get_dir() + '/db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("select taboo from cards where card like '{}'".format(card))
            taboo_ = cursor.fetchone()
            taboo_ = taboo_[0] if taboo_ else None

            if taboo_ is not None:
                cursor.execute("delete from cards where card like '{}'".format(card))
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

    @commands.command(pass_context=True, name='replcard', aliases=['rc'])
    async def replace_card(self, context, *args):
        """
        Replace all the taboo words of a card.
        If the card does not exists it is added to the database instead.

        Usage:

            \replcard <card_name> <taboo1> <taboo2> <taboo3> <taboo4>
        """
        if len(args) == 0:
            await self.bot.say("No arguments passed.")
        elif len(args) < 5:
            await self.bot.say("You need at least 4 taboo words to add a new card.")
        else:
            card = args[0].upper().strip()
            taboo_ = [word.upper().strip() for word in args[1:]]
            server_id = context.message.server.id
            server_db = utils.get_dir() + '/db/{}.db'.format(server_id)

            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute(
                "replace into cards (card, taboo) values('{}', '{}')".format(card, '|'.join(
                    taboo_)))
            await self.bot.say(embed=utils.get_embed(
                TabooGame.format_card((card, '|'.join(taboo_))), 'Card replaced.'
            ))

            cursor.close()
            connection.commit()
            connection.close()

    """ ---... TABOO ...--- """

    @commands.command(pass_context=True)
    @is_taboo_channel()
    async def buzz(self, context, *args):
        """
        Use it when the clue giver commits a fault.
        Only the card watcher can use this command during the game.
        When used the current card is skipped and the card watcher's team receives a point.

        Usage:

            \buzz <taboo_word>
        """
        author_id = context.message.author.id
        server_id = context.message.server.id

        if server_id in self.games:
            if args:
                taboo_game = self.games[server_id]
                if author_id == taboo_game.watcher:
                    taboo_word = args[0].upper().strip()
                    if taboo_word in taboo_game.current_card[1].split('|'):
                        taboo_game.skip()

    @commands.command(pass_context=True, aliases=['j'])
    @is_taboo_channel()
    async def join(self, context):
        """
        Adds you to the game.

        Usage:

            \join
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
        await self.bot.say(
            "{} was added to the game.\nThere are currently {} players in the game".format(
                author.mention, len(taboo_game.players)))

    @commands.command(pass_context=True, aliases=['l'])
    @is_taboo_channel()
    async def leave(self, context):
        """
        Removes you from the game.

        Usage:

            \leave
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
            await self.bot.say("{} left the game :cry:".format(
                context.message.author.mention
            ))
            return

        taboo_game.remove_player(author.id)
        await self.bot.say(
            "{} was removed to the game.\nThere are currently {} players in the game".format(
                author.mention, len(taboo_game.players)))

    @commands.command(pass_context=True, aliases=['s'])
    @is_taboo_channel()
    async def skip(self, context):
        """
        Skips the current card.
        Only the clue giver can use this command.
        When used the opposite team receives a point.

        Usage:

            \skip
        """
        server_id = context.message.server.id

        if server_id not in self.games:
            return

        taboo_game = self.games[server_id]

        if context.message.author.id != taboo_game.current_player:
            return

        taboo_game.skip()

    @commands.command(pass_context=True)
    @is_taboo_channel()
    async def start(self, context):
        """
        Forces a game to start.

        Usage:

            \start
        """
        server_id = context.message.server.id
        channel_id = context.message.channel.id

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

        taboo_game.playing = True

    @commands.command(pass_context=True)
    @is_taboo_channel()
    async def stop(self, context):
        """
        Forces a game to stop.

        Usage:

            \stop
        """
        server_id = context.message.server.id

        if server_id not in self.games:
            await self.bot.say("There's not game currently taking place.")
            return

        self.games[server_id].break_ = True

    @commands.command(pass_context=True, aliases=['t'])
    @is_taboo_channel()
    async def taboo(self, context):
        """
        Starts a new game.
        When used will wait 5 minutes for other people to join.

        Usage:

            \taboo
        """
        server_id = context.message.server.id
        channel = context.message.channel

        taboo_game = None if server_id not in self.games else self.games[server_id]

        if taboo_game is None:
            server_db = utils.get_dir() + '/db/{}.db'.format(server_id)
            connection = sqlite3.connect(server_db)
            cursor = connection.cursor()

            cursor.execute("select * from cards")
            cards = cursor.fetchall()

            cursor.execute("select value from settings where setting like 'TABOO_SECONDS'")
            seconds = cursor.fetchone()

            cursor.close()
            connection.close()

            seconds = seconds[0] if seconds else 120

            taboo_game = TabooGame(cards)
            taboo_game.add_player(context.message.author.id)
            self.games[server_id] = taboo_game

            self.bot.loop.create_task(
                self.game_loop(server_id, channel, seconds)
            )

        elif taboo_game.playing:
            await self.bot.say("Can't start a new game when there's one taking place.")
        else:
            await self.bot.say("A game was already created and will start soon.")

    """ ---... CONFIG ...--- """

    @commands.command(name='setchannel', aliases=['sc'], pass_context=True)
    @utils.is_admin()
    async def set_channel(self, context):
        """
        Sets the channel to be used for the game.

        Usage:

            \setchannel <#channel>
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

    @commands.command(name='setrounds', aliases=['sr'], pass_context=True)
    @utils.is_admin()
    async def set_rounds(self, context, *args):
        """
        Sets the number of rounds per game. Admins only.

        Usage:

            \setrounds <rounds>
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

    @commands.command(name='settime', aliases=['st'], pass_context=True)
    @utils.is_admin()
    async def set_timer(self, context, *args):
        """
        Sets the durations per turn in seconds. Admins only.

        Usage:

            \settime <seconds>
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

    """ ---... GAME LOOP ...--- """

    async def game_loop(self, server_id: str, channel: str, time_per_turn: int):

        taboo_game = self.games[server_id]

        await self.bot.send_message(
            channel,
            "Game created. The game will start in 5 minutes.\nType `\\join` to enter the game."
        )

        # Waits 5 minutes
        time = 0.0
        minute = 5

        while True:
            await asyncio.sleep(0.1)
            time += 0.1
            if time > 60:
                time = 0
                minute -= 1
                await self.bot.send_message(
                    channel,
                    "{} minutes before the game starts.\nType `\\join`to enter the game".format(
                        minute)
                )
            if not minute or taboo_game.break_:
                break

        if taboo_game.break_:
            await self.bot.send_message(channel, "Game cancelled.")
            del self.games[server_id]
            return

        if len(taboo_game.players) < 4:
            await self.bot.send_message(
                channel,
                "Game cancelled, you need at least 4 players to start a new game."
            )
            del self.games[server_id]
            return

        await self.bot.say("Game has started.")

        # Game loop
        time = 0.0
        turn_time = time_per_turn
        taboo_game.start()
        current_card = TabooGame.format_card(taboo_game.current_card)
        current_player = self.bot.get_server(server_id).get_member(taboo_game.current_player)
        watcher = self.bot.get_server(server_id).get_member(taboo_game.watcher)
        await self.bot.send_message(current_player, current_card)
        await self.bot.send_message(watcher, current_card)
        while taboo_game.playing and not taboo_game.break_:

            if turn_time < 0:
                taboo_game.next_turn()
                if not taboo_game.playing:
                    continue

                turn_time = time_per_turn

                current_card = TabooGame.format_card(taboo_game.current_card)
                current_player = self.bot.get_server(server_id).get_member(
                    taboo_game.current_player)
                watcher = self.bot.get_server(server_id).get_member(taboo_game.watcher)
                taboo_game.queue = asyncio.Queue()

                await self.bot.send_message(
                    channel,
                    "Time's over! It's next team turn"
                )

                await self.bot.send_message(current_player, current_card)
                await self.bot.send_message(watcher, current_card)

            else:
                if taboo_game.guess():
                    await self.bot.send_message(
                        channel,
                        "Correct! The word was {}".format(taboo_game.current_card[0])
                    )
                    taboo_game.next_card()

                    current_card = TabooGame.format_card(taboo_game.current_card)
                    current_player = self.bot.get_server(server_id).get_member(
                        taboo_game.current_player)
                    watcher = self.bot.get_server(server_id).get_member(taboo_game.watcher)

                    await self.bot.send_message(current_player, current_card)
                    await self.bot.send_message(watcher, current_card)

                    taboo_game.queue = asyncio.Queue()

                time = 0

            await asyncio.sleep(0.01)
            time += 0.01
            turn_time -= 0.01
            if time > 60:
                await self.bot.send_message(
                    channel,
                    "Game cancelled due to lack of activity."
                )
                break

        await self.bot.say("Game Over")
        del self.games[server_id]


def setup(bot):
    bot.add_cog(TabooExt(bot))
