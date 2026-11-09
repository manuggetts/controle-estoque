from concurrent.futures import ThreadPoolExecutor

import pytest

from app.dominio.erros import EstoqueInsuficiente
from app.infra.banco import Banco
from app.servicos.estoque import ServicoEstoque


@pytest.fixture
def servico(tmp_path):
    banco = Banco(str(tmp_path / "concorrencia.db"))
    banco.inicializar()
    return ServicoEstoque(banco)


def test_reservas_simultaneas_nunca_ultrapassam_o_disponivel(servico):
    servico.cadastrar_produto("CAMISA-P")
    servico.entrada("CAMISA-P", 5)

    def tentar_reservar(numero: int) -> str:
        try:
            servico.reservar("CAMISA-P", 1, f"PED-{numero}")
            return "ok"
        except EstoqueInsuficiente:
            return "recusada"

    with ThreadPoolExecutor(max_workers=20) as pool:
        resultados = list(pool.map(tentar_reservar, range(20)))

    assert resultados.count("ok") == 5
    assert resultados.count("recusada") == 15

    produto = servico.consultar_produto("CAMISA-P")
    assert (produto.total, produto.reservado, produto.disponivel) == (5, 5, 0)