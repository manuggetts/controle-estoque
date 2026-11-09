from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from app.dominio.erros import DadoInvalido, EstoqueInsuficiente, JaLiberado


class Status(str, Enum):
    ATIVO = "ATIVO"
    LIBERADO = "LIBERADO"


def _novo_id() -> str:
    return str(uuid4())


QUANTIDADE_MAXIMA = 1_000_000_000  # por operação; evita estouro do INTEGER de 64 bits do SQLite


def validar_quantidade(quantidade) -> None:
    """Quantidade precisa ser um inteiro entre 1 e QUANTIDADE_MAXIMA (bool não vale)."""
    if (
        isinstance(quantidade, bool)
        or not isinstance(quantidade, int)
        or quantidade <= 0
        or quantidade > QUANTIDADE_MAXIMA
    ):
        raise DadoInvalido(
            f"A quantidade deve ser um inteiro entre 1 e {QUANTIDADE_MAXIMA}."
        )


@dataclass
class Reserva:
    produto_id: str
    quantidade: int
    referencia: str  # identificação do pedido/solicitação
    id: str = field(default_factory=_novo_id)
    status: Status = Status.ATIVO


@dataclass
class Bloqueio:
    produto_id: str
    quantidade: int
    motivo: str | None = None
    id: str = field(default_factory=_novo_id)
    status: Status = Status.ATIVO


@dataclass
class Produto:
    id: str
    nome: str | None = None
    total: int = 0
    reservado: int = 0
    bloqueado: int = 0

    @property
    def disponivel(self) -> int:
        return self.total - self.reservado - self.bloqueado

    def entrada(self, quantidade: int) -> None:
        validar_quantidade(quantidade)
        self.total += quantidade

    def saida(self, quantidade: int) -> None:
        validar_quantidade(quantidade)
        self._exigir_disponivel(quantidade)
        self.total -= quantidade

    def reservar(self, quantidade: int, referencia: str) -> Reserva:
        validar_quantidade(quantidade)
        if not isinstance(referencia, str) or not referencia.strip():
            raise DadoInvalido("A referência do pedido é obrigatória.")
        self._exigir_disponivel(quantidade)
        self.reservado += quantidade
        return Reserva(self.id, quantidade, referencia.strip())

    def bloquear(self, quantidade: int, motivo: str | None = None) -> Bloqueio:
        validar_quantidade(quantidade)
        self._exigir_disponivel(quantidade)
        self.bloqueado += quantidade
        return Bloqueio(self.id, quantidade, motivo)

    def liberar_reserva(self, reserva: Reserva) -> None:
        self._exigir_ativo_e_do_produto(reserva)
        self.reservado -= reserva.quantidade
        reserva.status = Status.LIBERADO

    def liberar_bloqueio(self, bloqueio: Bloqueio) -> None:
        self._exigir_ativo_e_do_produto(bloqueio)
        self.bloqueado -= bloqueio.quantidade
        bloqueio.status = Status.LIBERADO

    def _exigir_disponivel(self, quantidade: int) -> None:
        if quantidade > self.disponivel:
            raise EstoqueInsuficiente(
                f"Quantidade disponível: {self.disponivel}; solicitado: {quantidade}."
            )

    def _exigir_ativo_e_do_produto(self, registro) -> None:
        if registro.produto_id != self.id:
            raise DadoInvalido("O registro não pertence a este produto.")
        if registro.status == Status.LIBERADO:
            raise JaLiberado("Este registro já foi liberado.")