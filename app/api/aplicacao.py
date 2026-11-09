from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import (
    BloqueioOut,
    CadastroProduto,
    NovaReserva,
    NovoBloqueio,
    ProdutoOut,
    Quantidade,
    ReservaOut,
)
from app.dominio.erros import ErroDominio
from app.dominio.modelos import Bloqueio, Produto, Reserva
from app.infra.banco import Banco
from app.servicos.estoque import ServicoEstoque

# Tradução do código de erro do domínio para o status HTTP.
STATUS_POR_CODIGO = {
    "VALIDACAO": 422,
    "PRODUTO_NAO_ENCONTRADO": 404,
    "RESERVA_NAO_ENCONTRADA": 404,
    "BLOQUEIO_NAO_ENCONTRADO": 404,
    "ESTOQUE_INSUFICIENTE": 409,
    "JA_LIBERADO": 409,
    "PRODUTO_JA_EXISTE": 409,
}


def _erro(status: int, codigo: str, mensagem: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"erro": {"codigo": codigo, "mensagem": mensagem}},
    )


def _produto_out(p: Produto) -> ProdutoOut:
    return ProdutoOut(
        id=p.id, nome=p.nome, total=p.total, disponivel=p.disponivel,
        reservado=p.reservado, bloqueado=p.bloqueado,
    )


def _reserva_out(r: Reserva) -> ReservaOut:
    return ReservaOut(
        id=r.id, produto_id=r.produto_id, quantidade=r.quantidade,
        referencia=r.referencia, status=r.status.value,
    )


def _bloqueio_out(b: Bloqueio) -> BloqueioOut:
    return BloqueioOut(
        id=b.id, produto_id=b.produto_id, quantidade=b.quantidade,
        motivo=b.motivo, status=b.status.value,
    )


def criar_app(caminho_banco: str) -> FastAPI:
    banco = Banco(caminho_banco)
    banco.inicializar()
    servico = ServicoEstoque(banco)

    app = FastAPI(title="Controle de Estoque", version="1.0.0")

    # ---------- tratamento de erros ----------

    @app.exception_handler(ErroDominio)
    async def tratar_erro_dominio(_request, erro: ErroDominio):
        return _erro(STATUS_POR_CODIGO.get(erro.codigo, 400), erro.codigo, erro.mensagem)

    @app.exception_handler(RequestValidationError)
    async def tratar_validacao(_request, erro: RequestValidationError):
        detalhes = [
            f"{'.'.join(str(parte) for parte in e['loc'] if parte != 'body')}: {e['msg']}"
            for e in erro.errors()
        ]
        return _erro(422, "VALIDACAO", "; ".join(detalhes))

    # ---------- produtos ----------

    @app.post("/produtos", status_code=201, response_model=ProdutoOut)
    def cadastrar_produto(dados: CadastroProduto):
        return _produto_out(servico.cadastrar_produto(dados.id, dados.nome))

    @app.get("/produtos/{produto_id}", response_model=ProdutoOut)
    def consultar_produto(produto_id: str):
        return _produto_out(servico.consultar_produto(produto_id))

    @app.post("/produtos/{produto_id}/entrada", response_model=ProdutoOut)
    def entrada(produto_id: str, dados: Quantidade):
        return _produto_out(servico.entrada(produto_id, dados.quantidade))

    @app.post("/produtos/{produto_id}/saida", response_model=ProdutoOut)
    def saida(produto_id: str, dados: Quantidade):
        return _produto_out(servico.saida(produto_id, dados.quantidade))

    # ---------- reservas ----------

    @app.post("/produtos/{produto_id}/reservas", status_code=201, response_model=ReservaOut)
    def reservar(produto_id: str, dados: NovaReserva):
        return _reserva_out(servico.reservar(produto_id, dados.quantidade, dados.referencia))

    @app.get("/reservas/{reserva_id}", response_model=ReservaOut)
    def consultar_reserva(reserva_id: str):
        return _reserva_out(servico.consultar_reserva(reserva_id))

    @app.post("/reservas/{reserva_id}/liberar", response_model=ReservaOut)
    def liberar_reserva(reserva_id: str):
        return _reserva_out(servico.liberar_reserva(reserva_id))

    # ---------- bloqueios ----------

    @app.post("/produtos/{produto_id}/bloqueios", status_code=201, response_model=BloqueioOut)
    def bloquear(produto_id: str, dados: NovoBloqueio):
        return _bloqueio_out(servico.bloquear(produto_id, dados.quantidade, dados.motivo))

    @app.get("/bloqueios/{bloqueio_id}", response_model=BloqueioOut)
    def consultar_bloqueio(bloqueio_id: str):
        return _bloqueio_out(servico.consultar_bloqueio(bloqueio_id))

    @app.post("/bloqueios/{bloqueio_id}/liberar", response_model=BloqueioOut)
    def liberar_bloqueio(bloqueio_id: str):
        return _bloqueio_out(servico.liberar_bloqueio(bloqueio_id))

    return app