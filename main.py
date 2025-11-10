from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.exceptions import HTTPException as StarletteHTTPException
from database import engine
from response import response_err
from auth import router as auth_router
from trafo import router as trafo_router
from group_trafo import router as group_trafo_router
from hasil_kalkulasi import router as hasil_kalkulasi_router

import models
models.Base.metadata.create_all(bind=engine,checkfirst=True)

app = FastAPI(title="SMGD App - Documentation", version="1.0.0")
app.include_router(auth_router)
app.include_router(trafo_router)
app.include_router(group_trafo_router)
app.include_router(hasil_kalkulasi_router)

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
