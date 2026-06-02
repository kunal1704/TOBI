import base64
import hashlib
import json
import os
import secrets
from datetime import datetime


DATA_DIR = ".tobi_data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SESSION_FILE = os.path.join(DATA_DIR, "remembered_session.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path, default):
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _save_json(path, payload):
    _ensure_data_dir()

    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def _hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120000,
    )

    return {
        "salt": base64.b64encode(salt).decode("utf-8"),
        "hash": base64.b64encode(password_hash).decode("utf-8"),
    }


def load_users():
    return _load_json(USERS_FILE, {})


def save_users(users):
    _save_json(USERS_FILE, users)


def create_user(email, password, full_name=""):
    email = email.strip().lower()
    users = load_users()

    if not email:
        raise ValueError("Email is required.")

    if email in users:
        raise ValueError("An account already exists for this email.")

    password_data = _hash_password(password)
    users[email] = {
        "email": email,
        "full_name": full_name.strip(),
        "password": password_data,
        "profile": {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    save_users(users)

    return users[email]


def verify_user(email, password):
    email = email.strip().lower()
    user = load_users().get(email)

    if not user:
        return None

    salt = base64.b64decode(user["password"]["salt"])
    candidate = _hash_password(password, salt=salt)["hash"]

    if secrets.compare_digest(candidate, user["password"]["hash"]):
        return user

    return None


def get_user(email):
    return load_users().get(email.strip().lower())


def save_user_profile(email, profile):
    email = email.strip().lower()
    users = load_users()

    if email not in users:
        raise ValueError("User not found.")

    users[email]["profile"] = profile
    users[email]["updated_at"] = datetime.now().isoformat()
    save_users(users)

    return users[email]


def remember_user(email):
    _save_json(SESSION_FILE, {"email": email.strip().lower()})


def get_remembered_user():
    session = _load_json(SESSION_FILE, {})
    email = session.get("email")

    if not email:
        return None

    return get_user(email)


def clear_remembered_user():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
