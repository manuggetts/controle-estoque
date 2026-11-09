import sqlite3

from app.dominio.erros import ProdutoJaExiste
from app.dominio.modelos import Bloqueio, Produto, Reserva, Status


class RepositorioEstoque:
    """Converte objetos de domínio em SQL e vice-versa. Não contém regras de negócio."""

    def __init__(self, conexao: sqlite3.Connection):
        self.conexao = conexao

    # ---------- produtos ----------

    def inserir_produto(self, produto: Produto) -> None:
        try:
            self.conexao.execute(
                "INSERT INTO produtos (id, nome, total, reservado, bloqueado) "
                "VALUES (?, ?, ?, ?, ?)",
                (produto.id, produto.nome, produto.total, produto.reservado, produto.bloqueado),
            )
        except sqlite3.IntegrityError:
            raise ProdutoJaExiste(f"O produto '{produto.id}' já existe.") from None

    def buscar_produto(self, produto_id: str) -> Produto | None:
        linha = self.conexao.execute(
            "SELECT id, nome, total, reservado, bloqueado FROM produtos WHERE id = ?",
            (produto_id,),
        ).fetchone()
        return None if linha is None else Produto(**dict(linha))

    def atualizar_produto(self, produto: Produto) -> None:
        self.conexao.execute(
            "UPDATE produtos SET total = ?, reservado = ?, bloqueado = ? WHERE id = ?",
            (produto.total, produto.reservado, produto.bloqueado, produto.id),
        )

    # ---------- reservas ----------

    def inserir_reserva(self, reserva: Reserva) -> None:
        self.conexao.execute(
            "INSERT INTO reservas (id, produto_id, quantidade, referencia, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (reserva.id, reserva.produto_id, reserva.quantidade,
             reserva.referencia, reserva.status.value),
        )

    def buscar_reserva(self, reserva_id: str) -> Reserva | None:
        linha = self.conexao.execute(
            "SELECT id, produto_id, quantidade, referencia, status FROM reservas WHERE id = ?",
            (reserva_id,),
        ).fetchone()
        if linha is None:
            return None
        return Reserva(
            id=linha["id"],
            produto_id=linha["produto_id"],
            quantidade=linha["quantidade"],
            referencia=linha["referencia"],
            status=Status(linha["status"]),
        )

    def atualizar_status_reserva(self, reserva: Reserva) -> None:
        self.conexao.execute(
            "UPDATE reservas SET status = ? WHERE id = ?",
            (reserva.status.value, reserva.id),
        )

    # ---------- bloqueios ----------

    def inserir_bloqueio(self, bloqueio: Bloqueio) -> None:
        self.conexao.execute(
            "INSERT INTO bloqueios (id, produto_id, quantidade, motivo, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (bloqueio.id, bloqueio.produto_id, bloqueio.quantidade,
             bloqueio.motivo, bloqueio.status.value),
        )

    def buscar_bloqueio(self, bloqueio_id: str) -> Bloqueio | None:
        linha = self.conexao.execute(
            "SELECT id, produto_id, quantidade, motivo, status FROM bloqueios WHERE id = ?",
            (bloqueio_id,),
        ).fetchone()
        if linha is None:
            return None
        return Bloqueio(
            id=linha["id"],
            produto_id=linha["produto_id"],
            quantidade=linha["quantidade"],
            motivo=linha["motivo"],
            status=Status(linha["status"]),
        )

    def atualizar_status_bloqueio(self, bloqueio: Bloqueio) -> None:
        self.conexao.execute(
            "UPDATE bloqueios SET status = ? WHERE id = ?",
            (bloqueio.status.value, bloqueio.id),
        )