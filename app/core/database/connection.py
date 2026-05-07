import mysql.connector
from mysql.connector import Error

from app.core.config.settings import DB_CONFIG


class DatabaseConnection:

    @staticmethod
    def get_connection():
        try:
            connection = mysql.connector.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"]
            )

            if connection.is_connected():
                print("Connected to MySQL")

            return connection

        except Error as e:
            print(f"Database connection error: {e}")
            raise