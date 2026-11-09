import pytest

from app.dominio.erros import DadoInvalido, EstoqueInsuficiente, JaLiberado
from app.dominio.modelos import Produto, Status


@pytest.fixture
def produto():
    p = Produto(id="CAMISA-P")
    p.entrada(10)
    return p


def estado(p):
    return (p.total, p.reservado, p.bloqueado)


def invariante_ok(p):
    return (
        p.total == p.disponivel + p.reservado + p.bloqueado
        and p.disponivel >= 0
        and p.reservado >= 0
        and p.bloqueado >= 0
    )


# ---------- Entrada ----------

def test_entrada_soma_ao_total_e_ao_disponivel(produto):
    produto.entrada(5)
    assert (produto.total, produto.disponivel) == (15, 15)


@pytest.mark.parametrize("invalida", [0, -1, 1.5, "3", True, None])
def test_quantidade_invalida_e_rejeitada_sem_alterar_estado(produto, invalida):
    antes = estado(produto)
    with pytest.raises(DadoInvalido):
        produto.entrada(invalida)
    with pytest.raises(DadoInvalido):
        produto.saida(invalida)
    with pytest.raises(DadoInvalido):
        produto.reservar(invalida, "PED-1")
    with pytest.raises(DadoInvalido):
        produto.bloquear(invalida)
    assert estado(produto) == antes


# ---------- Saída ----------

def test_saida_reduz_o_total(produto):
    produto.saida(4)
    assert (produto.total, produto.disponivel) == (6, 6)


def test_saida_da_quantidade_exata_disponivel_funciona(produto):
    produto.saida(10)
    assert produto.total == 0


def test_saida_acima_do_disponivel_falha_sem_alterar_estado(produto):
    antes = estado(produto)
    with pytest.raises(EstoqueInsuficiente):
        produto.saida(11)
    assert estado(produto) == antes


def test_saida_nao_pode_usar_unidades_reservadas_nem_bloqueadas(produto):
    produto.reservar(5, "PED-1")
    produto.bloquear(3)
    antes = estado(produto)
    with pytest.raises(EstoqueInsuficiente):
        produto.saida(3)  # só 2 disponíveis
    assert estado(produto) == antes


# ---------- Reservar ----------

def test_reservar_move_do_disponivel_para_o_reservado(produto):
    reserva = produto.reservar(3, "PED-1")
    assert (produto.reservado, produto.disponivel, produto.total) == (3, 7, 10)
    assert reserva.status == Status.ATIVO
    assert reserva.id and reserva.referencia == "PED-1"


def test_reservar_acima_do_disponivel_falha_sem_alterar_estado(produto):
    antes = estado(produto)
    with pytest.raises(EstoqueInsuficiente):
        produto.reservar(11, "PED-1")
    assert estado(produto) == antes


def test_reservar_exige_referencia(produto):
    antes = estado(produto)
    with pytest.raises(DadoInvalido):
        produto.reservar(1, "   ")
    assert estado(produto) == antes


def test_varias_reservas_de_pedidos_diferentes_no_mesmo_produto(produto):
    r1 = produto.reservar(3, "PED-1")
    r2 = produto.reservar(2, "PED-2")
    r3 = produto.reservar(1, "PED-1")  # mesmo pedido pode reservar de novo
    assert len({r1.id, r2.id, r3.id}) == 3
    assert (produto.reservado, produto.disponivel) == (6, 4)


# ---------- Bloquear ----------

def test_bloquear_move_do_disponivel_para_o_bloqueado(produto):
    bloqueio = produto.bloquear(4, "avaria")
    assert (produto.bloqueado, produto.disponivel, produto.total) == (4, 6, 10)
    assert bloqueio.status == Status.ATIVO
    assert bloqueio.id


def test_bloquear_acima_do_disponivel_falha_sem_alterar_estado(produto):
    produto.reservar(8, "PED-1")
    antes = estado(produto)
    with pytest.raises(EstoqueInsuficiente):
        produto.bloquear(3)  # só 2 disponíveis
    assert estado(produto) == antes


# ---------- Liberar ----------

def test_liberar_reserva_devolve_ao_disponivel(produto):
    reserva = produto.reservar(3, "PED-1")
    produto.liberar_reserva(reserva)
    assert (produto.reservado, produto.disponivel) == (0, 10)
    assert reserva.status == Status.LIBERADO


def test_liberar_bloqueio_devolve_ao_disponivel(produto):
    bloqueio = produto.bloquear(4)
    produto.liberar_bloqueio(bloqueio)
    assert (produto.bloqueado, produto.disponivel) == (0, 10)
    assert bloqueio.status == Status.LIBERADO


def test_liberar_reserva_duas_vezes_falha_sem_alterar_estado(produto):
    reserva = produto.reservar(3, "PED-1")
    produto.liberar_reserva(reserva)
    antes = estado(produto)
    with pytest.raises(JaLiberado):
        produto.liberar_reserva(reserva)
    assert estado(produto) == antes


def test_liberar_bloqueio_duas_vezes_falha_sem_alterar_estado(produto):
    bloqueio = produto.bloquear(4)
    produto.liberar_bloqueio(bloqueio)
    antes = estado(produto)
    with pytest.raises(JaLiberado):
        produto.liberar_bloqueio(bloqueio)
    assert estado(produto) == antes


def test_liberar_registro_de_outro_produto_falha(produto):
    outro = Produto(id="CAMISA-M")
    outro.entrada(5)
    reserva_do_outro = outro.reservar(2, "PED-9")
    antes = estado(produto)
    with pytest.raises(DadoInvalido):
        produto.liberar_reserva(reserva_do_outro)
    assert estado(produto) == antes


def test_liberar_uma_reserva_nao_afeta_as_outras(produto):
    r1 = produto.reservar(3, "PED-1")
    r2 = produto.reservar(2, "PED-2")
    produto.liberar_reserva(r1)
    assert produto.reservado == 2
    assert r2.status == Status.ATIVO


# ---------- Invariante ----------

def test_invariante_vale_apos_sequencia_de_operacoes(produto):
    assert invariante_ok(produto)
    r1 = produto.reservar(3, "PED-1")
    assert invariante_ok(produto)
    b1 = produto.bloquear(2)
    assert invariante_ok(produto)
    produto.saida(4)
    assert invariante_ok(produto)
    produto.liberar_reserva(r1)
    assert invariante_ok(produto)
    produto.liberar_bloqueio(b1)
    assert invariante_ok(produto)
    produto.entrada(7)
    assert invariante_ok(produto)