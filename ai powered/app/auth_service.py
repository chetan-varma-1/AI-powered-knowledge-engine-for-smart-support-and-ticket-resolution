import bcrypt # For password hashing 
import database
import logging

def hash_password(password):
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed_password):
    """Verifies a password against the stored hash."""
    return bcrypt.checkpw(password.encode('utf-8'),hash.encode('utf-8'))

def register_user(username, password, role = "user"):
    """Registers a new user."""
    hashed = hash_password(password)
    if database.create_user(username, hashed, role):
        logging.info(f"User {username} created sucessfully.")
        return True
    else:
        logging.warning(f"User {username} created failed (already exists?).")
        return False

def login_user(username, password):
    """Authenticates a user.
       Returns the user dict if successful, None otherwise."""
    user = database.get_user(username)
    if user and verify_password(password, user['password_hash']):
        return user
    return None

def create_default_user():
    """Created a defualth admin and user if they don't exist."""
    #Check if admin exists
    if not database.get_user("admin"):
        register_user("admin", "admin123", "admin")
        logging.info("Default admin user created.")
    #Check if user exists
    if not database.get_user("user"):
        register_user("user", "user123", "user")
        logging.info("Default user created.")