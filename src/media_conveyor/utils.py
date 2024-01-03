import os
import secrets
import string

from .logging import setup_logger

logger = setup_logger()


def generate_password(length: int = 16):
    if length < 16 or length > 128:
        print("Password length should be between 16 and 128")
        return

    characters = string.ascii_letters + string.digits + "!&#$^<>-"
    while True:
        password = "".join(secrets.choice(characters) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!&#$^<>-" for c in password)
        ):
            break

    return password


def set_file_permissions(file_path):
    try:
        # Set the permissions of the file to chmod 400
        os.chmod(file_path, 0o400)
    except OSError as e:
        logger.error(f"Error setting permissions on file: {e}")
        return False
    return True
