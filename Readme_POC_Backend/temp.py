# import secrets
# print(secrets.token_urlsafe(32))

import secrets

secret_key = secrets.token_hex(32)
print(secret_key)
