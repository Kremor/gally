from sqlite3 import Connection


class DB_Creator:

    def __init__(self, connection: Connection):
        cursor = connection.cursor()

        cursor.execute("CREATE TABLE IF NOT EXISTS Cards (Card TEXT, Banned Text)")

        cards = (
            ('bitter', 'sour#beer#lemon#feeling#orange'),
            ('bread', 'sandwich#bakery#flour#cheese'),
            ('chemical', 'biological weapon#kill#anthrax#gas#terror'),
            ('coat', 'outside#weather#raincold#anorak')
        )

        cursor.executemany("INSERT INTO Cards VALUES(?, ?, ?)", cards)

        connection.commit()
