from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
import models, schemas
from database import engine, SessionLocal
from auth import router as auth_router, get_current_user
from response import  response_err

models.Base.metadata.create_all(bind=engine,checkfirst=True)
app = FastAPI(title="FastAPI CRUD with JWT + Filters")
app.include_router(auth_router)

# Daftar origin yang diizinkan
origins = [
    "http://localhost:3000",   # Vite dev server
    "http://127.0.0.1:3000",   # alternatif
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # asal yang diizinkan
    allow_credentials=True,
    allow_methods=["*"],          # izinkan semua method (GET, POST, dll)
    allow_headers=["*"],          # izinkan semua header
)

# Tangani HTTPException (seperti 401, 404, dll)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return response_err(message=str(exc.detail), status_code=exc.status_code)

# Tangani error validasi (body request salah format, dsb)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return response_err(message="Validation error", data=exc.errors(), status_code=422)

# Tangani error tak terduga
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return response_err(message="Internal server error", status_code=500)

# Dependency DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create table 'trafo' when not exist
models.Base.metadata.create_all(bind=engine, tables=[models.Trafo.__table__])

# CREATE
@app.post("/items/", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    new_item = models.Item(**item.dict(), owner_id=current_user.id)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

# READ (with search + pagination)
@app.get("/items/", response_model=list[schemas.Item])
def read_items(
    q: str | None = Query(None, description="Cari berdasarkan nama"),
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(models.Item).filter(models.Item.owner_id == current_user.id)
    if q:
        query = query.filter(models.Item.name.contains(q))
    return query.offset(skip).limit(limit).all()

# READ by ID
@app.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    item = db.query(models.Item).filter(models.Item.id == item_id, models.Item.owner_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# UPDATE
@app.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id, models.Item.owner_id == current_user.id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

# DELETE
@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id, models.Item.owner_id == current_user.id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"message": f"Item {item_id} deleted"}

# CREATE
@app.post("/trafo/", response_model=schemas.Trafo)
def create_trafo(trafo: schemas.TrafoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    new_trafo = models.Trafo(**trafo.dict(), owner_id=current_user.id)
    db.add(new_trafo)
    db.commit()
    db.refresh(new_trafo)
    return new_trafo

# READ ALL
@app.get("/trafo/", response_model=list[schemas.Trafo])
def read_all_trafo(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(models.Trafo).filter(models.Trafo.owner_id == current_user.id).all()

# READ BY ID
@app.get("/trafo/{trafo_id}", response_model=schemas.Trafo)
def read_trafo(trafo_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    trafo = db.query(models.Trafo).filter(models.Trafo.id == trafo_id, models.Trafo.owner_id == current_user.id).first()
    if not trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    return trafo

# UPDATE BY ID
@app.put("/trafo/{trafo_id}", response_model=schemas.Trafo)
def update_trafo(trafo_id: int, trafo: schemas.TrafoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_trafo = db.query(models.Trafo).filter(models.Trafo.id == trafo_id, models.Trafo.owner_id == current_user.id).first()
    if not db_trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    for key, value in trafo.dict().items():
        setattr(db_trafo, key, value)
    db.commit()
    db.refresh(db_trafo)
    return db_trafo

# DELETE BY ID
@app.delete("/trafo/{trafo_id}")
def delete_trafo_by_id(trafo_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_trafo = db.query(models.Trafo).filter(models.Trafo.id == trafo_id, models.Trafo.owner_id == current_user.id).first()
    if not db_trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    db.delete(db_trafo)
    db.commit()
    return {"message": f"Trafo {trafo_id} deleted"}
