from app.core.database.connection import DatabaseConnection


def main():
    connection = DatabaseConnection.get_connection()

    if connection.is_connected():
        print("Application started successfully")

    connection.close()


if __name__ == "__main__":
    main()