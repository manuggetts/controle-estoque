import os

from app.api.aplicacao import criar_app

app = criar_app(os.getenv("ESTOQUE_DB", "estoque.db"))