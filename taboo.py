import random


class Taboo:

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

    def add_player(self, player: str):
        if player not in self.players:
            self.players.append(player)

    def guess(self, word: str):
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
