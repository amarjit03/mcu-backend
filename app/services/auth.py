from sqlalchemy.orm import Session

from app.core import security
from app.models.user import User
from app.schemas.auth import Token


class AuthService:
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not security.verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def create_user_tokens(user_id: int, role: str) -> Token:
        access_token = security.create_access_token(subject=user_id, role=role)
        refresh_token = security.create_refresh_token(subject=user_id, role=role)
        return Token(access_token=access_token, refresh_token=refresh_token)
