from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from app.db.session import SessionLocal
from app.models import Usuario, RolUsuario
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
) -> Optional[Usuario]:
    if not credentials:
        return None
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None
    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.activo == True).first()
    return user


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
) -> Usuario:
    user = get_current_user_optional(db=db, credentials=credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado. Inicie sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not current_user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo.")
    return current_user


def require_admin(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    if current_user.rol != RolUsuario.admin:
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador.")
    return current_user


def require_secretaria(current_user: Usuario = Depends(get_current_active_user)) -> Usuario:
    if current_user.rol != RolUsuario.secretaria:
        raise HTTPException(status_code=403, detail="Acceso restringido a secretaría.")
    return current_user
