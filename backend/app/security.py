from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

HASHER = PasswordHasher()


def password_matches(encoded, password):
    try:
        return HASHER.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def issue_token(user_id, settings):
    now = datetime.now(timezone.utc)
    return jwt.encode({
        'sub': user_id, 'iat': now, 'nbf': now,
        'exp': now + timedelta(minutes=settings.token_minutes),
        'iss': settings.jwt_issuer, 'aud': settings.jwt_audience, 'jti': str(uuid4()),
    }, settings.jwt_secret.get_secret_value(), algorithm='HS256')


def verify_token(token, settings):
    return jwt.decode(
        token, settings.jwt_secret.get_secret_value(), algorithms=['HS256'],
        issuer=settings.jwt_issuer, audience=settings.jwt_audience,
        options={'require': ['sub', 'exp', 'iat', 'nbf', 'iss', 'aud', 'jti']},
    )['sub']
