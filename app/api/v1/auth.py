from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Usuario
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.deps import get_current_user
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserResponse,
    TokenResponse,
    RefreshRequest,
    RefreshResponse,
    ChangePasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_to_response(user: Usuario) -> UserResponse:
    return UserResponse(
        id=user.id,
        nombre=user.nombre,
        email=user.email,
        cargo=user.cargo,
        rol=user.rol.value,
        secretaria_id=user.secretaria_id,
        secretaria_nombre=user.secretaria.nombre if user.secretaria else None,
        requiere_cambio_password=user.requiere_cambio_password or False,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.query(Usuario).filter(Usuario.email == body.email, Usuario.activo == True).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/",
    )
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_response(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token de actualización inválido.")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido.")
    user = db.query(Usuario).filter(Usuario.id == int(user_id), Usuario.activo == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")
    access_token = create_access_token(data={"sub": str(user.id)})
    return RefreshResponse(access_token=access_token)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Sesión cerrada."}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta.")
    current_user.password_hash = get_password_hash(body.new_password)
    current_user.requiere_cambio_password = False
    db.commit()
    return {"message": "Contraseña actualizada."}


@router.get("/me", response_model=UserResponse)
def me(current_user: Usuario = Depends(get_current_user)):
    return _user_to_response(current_user)
