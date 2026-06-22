from passlib.context import CryptContext

def generate_hashes():
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    print("ADMIN_HASH:" + pwd.hash("adminpass"))
    print("ENGINEER_HASH:" + pwd.hash("engineerpass"))

if __name__ == '__main__':
    generate_hashes()
