# -*- coding: utf-8 -*-
"""
Punto de entrada raíz para el servidor ASGI de Fiscalis.
Permite ejecutar indistintamente:
  uvicorn main:app --reload
  uvicorn app.main:app --reload
  python main.py
"""
from app.main import app
from app.core.config import settings

if __name__ == "__main__":
    import uvicorn
    # Modo de arranque directo
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 2
    )
