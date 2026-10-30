import sqlite3
from getpass import getpass

from database import initialize_database, create_user
from security import hash_password


def main():
    initialize_database()

    print("Create Manager Account")
    print("----------------------")

    username = input("Enter manager username: ").strip().lower()
    password = getpass("Enter manager password: ")
    confirm_password = getpass("Confirm manager password: ")

    if len(username) < 3:
        print("Username must contain at least 3 characters.")
        return

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    try:
        password_hash = hash_password(password)

        user_id = create_user(
            username=username,
            password_hash=password_hash,
            role="manager"
        )

        print("\nManager account created successfully!")
        print(f"User ID: {user_id}")
        print(f"Username: {username}")
        print("Role: manager")

    except sqlite3.IntegrityError:
        print("This username already exists.")


if __name__ == "__main__":
    main()