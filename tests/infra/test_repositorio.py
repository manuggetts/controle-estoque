import sqlite3

import pytest

from app.dominio.erros import ProdutoJaExiste
from app.dominio.modelos import Bloqueio, Produto, Reserva, Status
from app.infra.banco import Banco
from app.infra.repositorio import RepositorioEstoque


@pytest.fixture
def banco(tmp_path):
    b = Banco(str(tmp_path / "teste.db"))
    b.inicializar()
    return b


def test_produto_e_salvo_e_recuperado_em_outra_conexao(banco):
    with banco.transacao() as conexao:
        RepositorioEstoque(conexao).inserir_produto(Produto(id="A", nome="Camisa", total=10))

    with banco.transacao() as conexao:
        lido = RepositorioEstoque(conexao).buscar_produto("A")

    assert lido == Produto(id="A", nome="Camisa", total=10, reservado=0, bloqueado=0)


def test_produto_inexistente_retorna_none(banco):
    with banco.transacao() as conexao:
        assert RepositorioEstoque(conexao).buscar_produto("NAO-EXISTE") is None


def test_produto_duplicado_levanta_produto_ja_existe(banco):
    with banco.transacao() as conexao:
        RepositorioEstoque(conexao).inserir_produto(Produto(id="A"))

    with pytest.raises(ProdutoJaExiste):
        with banco.transacao() as conexao:
            RepositorioEstoque(conexao).inserir_produto(Produto(id="A"))


def test_rollback_desfaz_tudo_quando_ocorre_erro(banco):
    with pytest.raises(RuntimeError):
        with banco.transacao() as conexao:
            RepositorioEstoque(conexao).inserir_produto(Produto(id="A"))
            raise RuntimeError("falha no meio da operação")

    with banco.transacao() as conexao:
        assert RepositorioEstoque(conexao).buscar_produto("A") is None


def test_banco_impede_estado_inconsistente(banco):
    with banco.transacao() as conexao:
        RepositorioEstoque(conexao).inserir_produto(Produto(id="A", total=10))

    with pytest.raises(sqlite3.IntegrityError):
        with banco.transacao() as conexao:
            conexao.execute("UPDATE produtos SET reservado = 99 WHERE id = 'A'")

    with banco.transacao() as conexao:
        assert RepositorioEstoque(conexao).buscar_produto("A").reservado == 0


def test_reserva_de_produto_inexistente_e_barrada_pelo_banco(banco):
    with pytest.raises(sqlite3.IntegrityError):
        with banco.transacao() as conexao:
            RepositorioEstoque(conexao).inserir_reserva(Reserva("NAO-EXISTE", 1, "PED-1"))


def test_reserva_e_salva_recuperada_e_liberada(banco):
    with banco.transacao() as conexao:
        repo = RepositorioEstoque(conexao)
        produto = Produto(id="A")
        repo.inserir_produto(produto)
        produto.entrada(10)
        reserva = produto.reservar(3, "PED-1")
        repo.atualizar_produto(produto)
        repo.inserir_reserva(reserva)

    with banco.transacao() as conexao:
        repo = RepositorioEstoque(conexao)
        lida = repo.buscar_reserva(reserva.id)
        assert lida == reserva
        produto = repo.buscar_produto("A")
        produto.liberar_reserva(lida)
        repo.atualizar_produto(produto)
        repo.atualizar_status_reserva(lida)

    with banco.transacao() as conexao:
        repo = RepositorioEstoque(conexao)
        assert repo.buscar_reserva(reserva.id).status == Status.LIBERADO
        assert repo.buscar_produto("A").reservado == 0


def test_bloqueio_e_salvo_recuperado_e_liberado(banco):
    with banco.transacao() as conexao:
        repo = RepositorioEstoque(conexao)
        produto = Produto(id="A")
        repo.inserir_produto(produto)
        produto.entrada(10)
        bloqueio = produto.bloquear(4, "avaria")
        repo.atualizar_produto(produto)
        repo.inserir_bloqueio(bloqueio)

    with banco.transacao() as conexao:
        repo = RepositorioEstoque(conexao)
        lido = repo.buscar_bloqueio(bloqueio.id)
        assert lido == bloqueio
        produto = repo.buscar_produto("A")
        produto.liberar_bloqueio(lido)
        repo.atualizar_produto(produto)
        repo.atualizar_status_bloqueio(lido)

    with banco.transacao() as conexao:
        repo = RepositorioEstoque(conexao)
        assert repo.buscar_bloqueio(bloqueio.id).status == Status.LIBERADO
        assert repo.buscar_produto("A").bloqueado == 0