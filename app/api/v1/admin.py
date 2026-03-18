from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.core.deps import get_current_user, require_admin
from sqlalchemy import func
from app.models import Usuario, Secretaria, Meta, PeriodoSeguimiento, EstadoPeriodo
from app.core.security import get_password_hash

router = APIRouter(prefix="/admin", tags=["admin"])


class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    email: str
    cargo: Optional[str]
    rol: str
    secretaria_id: Optional[int]
    secretaria_nombre: Optional[str]
    activo: bool

    class Config:
        from_attributes = True


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    cargo: Optional[str] = None
    secretaria_id: Optional[int] = None
    rol: str = "secretaria"


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    cargo: Optional[str] = None
    secretaria_id: Optional[int] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None


@router.get("/usuarios", response_model=List[UsuarioResponse])
def list_usuarios(db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    users = db.query(Usuario).all()
    return [
        UsuarioResponse(
            id=u.id,
            nombre=u.nombre,
            email=u.email,
            cargo=u.cargo,
            rol=u.rol.value,
            secretaria_id=u.secretaria_id,
            secretaria_nombre=u.secretaria.nombre if u.secretaria else None,
            activo=u.activo,
        )
        for u in users
    ]


@router.get("/usuarios/{user_id}", response_model=UsuarioResponse)
def get_usuario(user_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    u = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UsuarioResponse(id=u.id, nombre=u.nombre, email=u.email, cargo=u.cargo, rol=u.rol.value, secretaria_id=u.secretaria_id, secretaria_nombre=u.secretaria.nombre if u.secretaria else None, activo=u.activo)


@router.post("/usuarios", response_model=UsuarioResponse)
def create_usuario(body: UsuarioCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    u = Usuario(
        nombre=body.nombre,
        email=body.email,
        password_hash=get_password_hash(body.password),
        cargo=body.cargo,
        secretaria_id=body.secretaria_id,
        rol=body.rol,
        activo=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return UsuarioResponse(id=u.id, nombre=u.nombre, email=u.email, cargo=u.cargo, rol=u.rol.value, secretaria_id=u.secretaria_id, secretaria_nombre=u.secretaria.nombre if u.secretaria else None, activo=u.activo)


@router.put("/usuarios/{user_id}", response_model=UsuarioResponse)
def update_usuario(user_id: int, body: UsuarioUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    u = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if body.nombre is not None:
        u.nombre = body.nombre
    if body.email is not None:
        u.email = body.email
    if body.cargo is not None:
        u.cargo = body.cargo
    if body.secretaria_id is not None:
        u.secretaria_id = body.secretaria_id
    if body.rol is not None:
        u.rol = body.rol
    if body.activo is not None:
        u.activo = body.activo
    if body.password is not None and body.password.strip():
        u.password_hash = get_password_hash(body.password)
    db.commit()
    db.refresh(u)
    return UsuarioResponse(id=u.id, nombre=u.nombre, email=u.email, cargo=u.cargo, rol=u.rol.value, secretaria_id=u.secretaria_id, secretaria_nombre=u.secretaria.nombre if u.secretaria else None, activo=u.activo)


@router.delete("/usuarios/{user_id}")
def delete_usuario(user_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    u = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.activo = False
    db.commit()
    return {"message": "Usuario desactivado"}


@router.get("/secretarias")
def list_secretarias(db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    counts = dict(db.query(Meta.secretaria_id, func.count(Meta.id)).filter(Meta.activo == True).group_by(Meta.secretaria_id).all())
    return [
        {"id": s.id, "nombre": s.nombre, "tipo": s.tipo.value, "total_metas": counts.get(s.id, 0)}
        for s in db.query(Secretaria).order_by(Secretaria.nombre).all()
    ]


@router.get("/trimestres")
def list_trimestres(db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    return [
        {"id": p.id, "anio": p.anio, "trimestre": p.trimestre, "estado": p.estado.value, "fecha_limite": str(p.fecha_limite) if p.fecha_limite else None}
        for p in db.query(PeriodoSeguimiento).order_by(PeriodoSeguimiento.anio, PeriodoSeguimiento.trimestre).all()
    ]


class TrimestreUpdate(BaseModel):
    estado: str


@router.put("/trimestres/{periodo_id}")
def update_trimestre(periodo_id: int, body: TrimestreUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)):
    p = db.query(PeriodoSeguimiento).filter(PeriodoSeguimiento.id == periodo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    if body.estado in ("abierto", "cerrado", "proximo"):
        p.estado = EstadoPeriodo(body.estado)
    db.commit()
    return {"message": "Período actualizado"}
