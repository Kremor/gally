import sqlite3
import time

from create_db import DB_Creator

class Taboo:

    __data = {}

    def __init__(self):

        connection = sqlite3.connect('cards.db')

        DB_Creator(connection)

        connection.commit()
        connection.close()

    def add_card(self, card: str, banned: str):
        pass

    def add_team(self, server_id, team_name: str, players):
        if server_id not in self.__data:
            self.new_game(server_id)
        game = self.__data[server_id]
        if team_name not in game:
            game[team_name] = 0

    def update_score(self, server_id, team_name):
        pass

    def new_game(self, server_id):
        self.__data[server_id] = {}

    def remove_card_by_id(self, id: int):
        pass

    def remove_card_by_name(self, card: str):
        pass

    def start(self):
        pass

    def stop(self, server_id):
        if server_id in self.__data:
            del self.__data[server_id]
