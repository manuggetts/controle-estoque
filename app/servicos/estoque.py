from app.dominio.erros import (
    BloqueioNaoEncontrado,
    DadoInvalido,
    ProdutoNaoEncontrado,
    ReservaNaoEncontrada,
)
from app.dominio.modelos import Bloqueio, Produto, Reserva
from app.infra.banco import Banco
from app.infra.repositorio import RepositorioEstoque


class ServicoEstoque:
    """Cada método é um caso de uso e roda dentro de UMA transação:
    carrega, aplica a regra do domínio e salva. Se algo falhar, nada é gravado."""

    def __init__(self, banco: Banco):
        self.banco = banco

    def cadastrar_produto(self, produto_id: str, nome: str | None = None) -> Produto:
        if not isinstance(produto_id, str) or not produto_id.strip():
            raise DadoInvalido("O id do produto é obrigatório.")
        produto = Produto(id=produto_id.strip(), nome=nome)
        with self.banco.transacao() as conexao:
            RepositorioEstoque(conexao).inserir_produto(produto)
        return produto

    def consultar_produto(self, produto_id: str) -> Produto:
        with self.banco.transacao() as conexao:
            return self._produto(RepositorioEstoque(conexao), produto_id)

    def entrada(self, produto_id: str, quantidade: int) -> Produto:
        with self.banco.transacao() as conexao:
            repo = RepositorioEstoque(conexao)
            produto = self._produto(repo, produto_id)
            produto.entrada(quantidade)
            repo.atualizar_produto(produto)
            return produto

    def saida(self, produto_id: str, quantidade: int) -> Produto:
        with self.banco.transacao() as conexao:
            repo = RepositorioEstoque(conexao)
            produto = self._produto(repo, produto_id)
            produto.saida(quantidade)
            repo.atualizar_produto(produto)
            return produto

    def reservar(self, produto_id: str, quantidade: int, referencia: str) -> Reserva:
        with self.banco.transacao() as conexao:
            repo = RepositorioEstoque(conexao)
            produto = self._produto(repo, produto_id)
            reserva = produto.reservar(quantidade, referencia)
            repo.atualizar_produto(produto)
            repo.inserir_reserva(reserva)
            return reserva

    def bloquear(self, produto_id: str, quantidade: int, motivo: str | None = None) -> Bloqueio:
        with self.banco.transacao() as conexao:
            repo = RepositorioEstoque(conexao)
            produto = self._produto(repo, produto_id)
            bloqueio = produto.bloquear(quantidade, motivo)
            repo.atualizar_produto(produto)
            repo.inserir_bloqueio(bloqueio)
            return bloqueio

    def consultar_reserva(self, reserva_id: str) -> Reserva:
        with self.banco.transacao() as conexao:
            return self._reserva(RepositorioEstoque(conexao), reserva_id)

    def consultar_bloqueio(self, bloqueio_id: str) -> Bloqueio:
        with self.banco.transacao() as conexao:
            return self._bloqueio(RepositorioEstoque(conexao), bloqueio_id)

    def liberar_reserva(self, reserva_id: str) -> Reserva:
        with self.banco.transacao() as conexao:
            repo = RepositorioEstoque(conexao)
            reserva = self._reserva(repo, reserva_id)
            produto = self._produto(repo, reserva.produto_id)
            produto.liberar_reserva(reserva)
            repo.atualizar_produto(produto)
            repo.atualizar_status_reserva(reserva)
            return reserva

    def liberar_bloqueio(self, bloqueio_id: str) -> Bloqueio:
        with self.banco.transacao() as conexao:
            repo = RepositorioEstoque(conexao)
            bloqueio = self._bloqueio(repo, bloqueio_id)
            produto = self._produto(repo, bloqueio.produto_id)
            produto.liberar_bloqueio(bloqueio)
            repo.atualizar_produto(produto)
            repo.atualizar_status_bloqueio(bloqueio)
            return bloqueio

    # ---------- auxiliares ----------

    @staticmethod
    def _produto(repo: RepositorioEstoque, produto_id: str) -> Produto:
        produto = repo.buscar_produto(produto_id)
        if produto is None:
            raise ProdutoNaoEncontrado(f"Produto '{produto_id}' não encontrado.")
        return produto

    @staticmethod
    def _reserva(repo: RepositorioEstoque, reserva_id: str) -> Reserva:
        reserva = repo.buscar_reserva(reserva_id)
        if reserva is None:
            raise ReservaNaoEncontrada(f"Reserva '{reserva_id}' não encontrada.")
        return reserva

    @staticmethod
    def _bloqueio(repo: RepositorioEstoque, bloqueio_id: str) -> Bloqueio:
        bloqueio = repo.buscar_bloqueio(bloqueio_id)
        if bloqueio is None:
            raise BloqueioNaoEncontrado(f"Bloqueio '{bloqueio_id}' não encontrado.")
        return bloqueio