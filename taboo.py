import random


class Taboo:

    def __init__(self, server_id: str):
        self.players = []
        self.team_a = 0
        self.team_b = 0
        self.playing = False
        self.turns = []

    def add_player(self, player: str):
        if self.playing:
            return TabooResult(False, "Can't add players while a game is taking place.")
        elif player in self.players:
            return TabooResult(False, "Player is already in the game.")
        else:
            self.players.append(player)
            return TabooResult(True, "<@{}> was added to the game.".format(player))

    def next_turn(self):
        pass

    def remove_player(self, player: str):
        if self.playing:
            return TabooResult(False, "Can't remove players when a game is taking place.")
        elif player not in self.players:
            return TabooResult(False, "<@{}> is not in the game.".format(player))
        else:
            self.players.remove(player)
            return TabooResult(True, "Player removed.")

    def skip_card(self):
        pass

    def skip_player(self):
        pass

    def start(self):
        if self.playing:
            return TabooResult(False, "The game already started.")
        elif len(self.players) < 4:
            return TabooResult(False, "Need at least 4 players to start the game.")
        else:
            random.shuffle(self.players)
            team_a = "+ Team A\n" + '-' * 20
            team_b = "+ Team B\n" + '-' * 20

            for i, player in self.players:
                if (i+1) % 2 == 1:
                    team_a += '\n' + '- ' + '<@{}>'.format(player)
                else:
                    team_b += '\n' + '- ' + '<@{}>'.format(player)

            self.playing = True

            return "=== GAME STARTED ===\n" + team_a + '\n' + team_b

    def stop(self):
        if self.playing:
            self.playing = False


class TabooResult:
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message
