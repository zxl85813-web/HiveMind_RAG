import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False

if __name__ == "__main__":
    p = "admin123"
    h = hash_password(p)
    print(f"Password: {p}")
    print(f"Hash: {h}")
    result = verify_password(p, h)
    print(f"Verify Correct: {result}")
    
    result_wrong = verify_password("wrong", h)
    print(f"Verify Wrong: {result_wrong}")
    
    # Check compatibility with a standard $2b$ hash
    h2 = "$2b$12$KPhN9Yp5L.V79m1m5W/oX.5E.5m3T8r21z9X.Y5e5z9X.Y5e5z9X." # Dummy format
    # Actually let's use a real one from my previous run
    h3 = "$2b$12$baobRcyGTvg59Zwx9PvT3eKDBYGTUlVuemmG4Q5NP4t8AEAk8YB5O"
    print(f"Checking real hash: {h3}")
    result3 = verify_password("admin123", h3)
    print(f"Verify Real: {result3}")
