import os

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "statementaiSecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRES = 525600
TOKEN_MODEL = "gpt-5"