import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


class Banco:
    """Cria conexões e garante que cada operação rode em uma transação."""

    def __init__(self, caminho: str):
        self.caminho = caminho

    def _conectar(self) -> sqlite3.Connection:
        # isolation_level=None: nós mesmos controlamos BEGIN/COMMIT/ROLLBACK.
        # timeout=10: se outra transação estiver escrevendo, espera até 10 s.
        conexao = sqlite3.connect(self.caminho, timeout=10, isolation_level=None)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        return conexao

    def inicializar(self) -> None:
        conexao = self._conectar()
        try:
            conexao.executescript(SCHEMA.read_text(encoding="utf-8"))
        finally:
            conexao.close()

    @contextmanager
    def transacao(self):
        """Tudo dentro do bloco `with` é gravado junto, ou desfeito junto."""
        conexao = self._conectar()
        try:
            conexao.execute("BEGIN IMMEDIATE")
            try:
                yield conexao
            except BaseException:
                conexao.execute("ROLLBACK")
                raise
            conexao.execute("COMMIT")
        finally:
            conexao.close()