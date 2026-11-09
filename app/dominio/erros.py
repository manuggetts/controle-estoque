class ErroDominio(Exception):
    """Base de todos os erros de regra de negócio."""

    codigo = "ERRO_DOMINIO"

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class DadoInvalido(ErroDominio):
    codigo = "VALIDACAO"


class EstoqueInsuficiente(ErroDominio):
    codigo = "ESTOQUE_INSUFICIENTE"


class JaLiberado(ErroDominio):
    codigo = "JA_LIBERADO"


class ProdutoJaExiste(ErroDominio):
    codigo = "PRODUTO_JA_EXISTE"


class ProdutoNaoEncontrado(ErroDominio):
    codigo = "PRODUTO_NAO_ENCONTRADO"


class ReservaNaoEncontrada(ErroDominio):
    codigo = "RESERVA_NAO_ENCONTRADA"


class BloqueioNaoEncontrado(ErroDominio):
    codigo = "BLOQUEIO_NAO_ENCONTRADO"