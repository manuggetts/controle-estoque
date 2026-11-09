from pydantic import BaseModel, Field, StrictInt


# ---------- entrada ----------

class CadastroProduto(BaseModel):
    id: str = Field(min_length=1)
    nome: str | None = None


class Quantidade(BaseModel):
    quantidade: StrictInt = Field(gt=0)


class NovaReserva(BaseModel):
    quantidade: StrictInt = Field(gt=0)
    referencia: str = Field(min_length=1)


class NovoBloqueio(BaseModel):
    quantidade: StrictInt = Field(gt=0)
    motivo: str | None = None


# ---------- saída ----------

class ProdutoOut(BaseModel):
    id: str
    nome: str | None
    total: int
    disponivel: int
    reservado: int
    bloqueado: int


class ReservaOut(BaseModel):
    id: str
    produto_id: str
    quantidade: int
    referencia: str
    status: str


class BloqueioOut(BaseModel):
    id: str
    produto_id: str
    quantidade: int
    motivo: str | None
    status: str