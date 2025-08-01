from passlib.context import CryptContext

pw_content = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash(password):
    return pw_content.hash(password)

def verify(plain_pw, hashed_pw):
    return pw_content.verify(plain_pw, hashed_pw)