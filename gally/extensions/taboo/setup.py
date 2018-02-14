import json
import sqlite3

from discord.ext.commands import Bot

import gally.utils as utils
from gally.extensions.taboo import Taboo


def setup(bot: Bot):
    for server in bot.servers:
        server_db = utils.get_dir() + 'db/{}.db'.format(server.id)

        connection = sqlite3.connect(server_db)
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO SETTINGS(NAME, VALUE)"
            "SELECT 'TABOO_CHANNEL', 'NONE'"
            "WHERE NOT EXISTS(SELECT NAME FROM SETTINGS WHERE NAME LIKE 'TABOO_CHANNEL')"
        )

        cursor.execute(
            "INSERT INTO SETTINGS(NAME, VALUE)"
            "SELECT 'TABOO_ROUNDS', '1'"
            "WHERE NOT EXISTS(SELECT NAME FROM SETTINGS WHERE NAME LIKE 'TABOO_ROUNDS')"
        )

        cursor.execute(
            "INSERT INTO SETTINGS(NAME, VALUE)"
            "SELECT 'TABOO_SECONDS', '120'"
            "WHERE NOT EXISTS(SELECT NAME FROM SETTINGS WHERE NAME LIKE 'TABOO_SECONDS')"
        )

        cursor.execute("CREATE TABLE IF NOT EXISTS CARDS(CARD TEXT, TABOO TEXT)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS IDX_TABOO_CARD ON CARDS(CARD)")

        cursor.execute("SELECT * FROM CARDS")

        if not cursor.fetchall():
            with open('gally/extensions/taboo/taboo_cards.json', 'r') as file_:
                cards = json.load(file_)
                for card in cards:
                    cursor.execute("INSERT INTO CARDS VALUES(?, ?)", (card, cards[card]))

        cursor.close()
        connection.commit()
        connection.close()

    bot.add_cog(Taboo(bot))
