from app.core.database.connection import DatabaseConnection


class BaseRepository:

    def __init__(self):
        self.connection = DatabaseConnection.get_connection()
        self.cursor = self.connection.cursor(dictionary=True)

    def close(self):
        self.cursor.close()
        self.connection.close()