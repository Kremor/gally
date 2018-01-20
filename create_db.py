from sqlite3 import Connection


class DB_Creator:

    def __init__(self, connection: Connection):
        cursor = connection.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS Cards (Id INT, Card TEXT, Banned Text)")

        cards = (
            (1, 'bitter', 'sour#beer#lemon#feeling#orange'),
            (2, 'bread', 'sandwich#bakery#flour#cheese'),
            (3, 'chemical', 'biological weapon#kill#anthrax#gas#terror'),
            (4, 'coat', 'outside#weather#raincold#anorak')
        )

        cursor.executemany("INSERT INTO Cards VALUES(?, ?, ?)", cards)

        connection.commit()
