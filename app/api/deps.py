from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import TokenPayload

# Swagger login configuration using OAuth2 token flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        is_refresh = payload.get("refresh", False)
        if user_id is None or is_refresh:
            raise credentials_exception
        token_payload = TokenPayload(sub=user_id, role=payload.get("role"))
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(token_payload.sub)).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        # SUPERADMIN inherits all roles
        if current_user.role == UserRole.SUPERADMIN:
            return current_user
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The user does not have enough privileges. Required role(s): {', '.join(self.allowed_roles)}"
            )
        return current_user

# Dependencies to require specific roles
RequireStudent = RoleChecker([UserRole.STUDENT])
RequireStaff = RoleChecker([UserRole.STAFF])
RequireHead = RoleChecker([UserRole.HEAD])
RequireAdmin = RoleChecker([UserRole.ADMIN])
RequireSuperAdmin = RoleChecker([UserRole.SUPERADMIN])

# Union roles
RequireAnyStaff = RoleChecker([UserRole.STAFF, UserRole.HEAD, UserRole.ADMIN])
RequireManagement = RoleChecker([UserRole.HEAD, UserRole.ADMIN])
