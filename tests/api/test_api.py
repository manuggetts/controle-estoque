import pytest
from fastapi.testclient import TestClient

from app.api.aplicacao import criar_app


@pytest.fixture
def cliente(tmp_path):
    return TestClient(criar_app(str(tmp_path / "api.db")))


def criar_produto(cliente, produto_id="CAMISA-P", entrada=10):
    assert cliente.post("/produtos", json={"id": produto_id}).status_code == 201
    if entrada:
        resposta = cliente.post(f"/produtos/{produto_id}/entrada", json={"quantidade": entrada})
        assert resposta.status_code == 200


def situacao(cliente, produto_id="CAMISA-P"):
    """(total, disponivel, reservado, bloqueado)"""
    c = cliente.get(f"/produtos/{produto_id}").json()
    return (c["total"], c["disponivel"], c["reservado"], c["bloqueado"])


# ---------- produtos ----------

def test_cadastrar_produto_retorna_201_com_estoque_zerado(cliente):
    resposta = cliente.post("/produtos", json={"id": "CAMISA-P", "nome": "Camisa P"})
    assert resposta.status_code == 201
    assert resposta.json() == {
        "id": "CAMISA-P", "nome": "Camisa P",
        "total": 0, "disponivel": 0, "reservado": 0, "bloqueado": 0,
    }


def test_cadastrar_produto_duplicado_retorna_409(cliente):
    criar_produto(cliente, entrada=0)
    resposta = cliente.post("/produtos", json={"id": "CAMISA-P"})
    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "PRODUTO_JA_EXISTE"


@pytest.mark.parametrize("id_invalido", ["", "   "])
def test_cadastrar_produto_com_id_vazio_retorna_422(cliente, id_invalido):
    resposta = cliente.post("/produtos", json={"id": id_invalido})
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "VALIDACAO"


def test_consultar_produto_inexistente_retorna_404(cliente):
    resposta = cliente.get("/produtos/NAO-EXISTE")
    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "PRODUTO_NAO_ENCONTRADO"


# ---------- entrada e saída ----------

def test_entrada_aumenta_total_e_disponivel(cliente):
    criar_produto(cliente)
    resposta = cliente.post("/produtos/CAMISA-P/entrada", json={"quantidade": 5})
    assert resposta.status_code == 200
    assert situacao(cliente) == (15, 15, 0, 0)


def test_saida_reduz_o_total(cliente):
    criar_produto(cliente)
    resposta = cliente.post("/produtos/CAMISA-P/saida", json={"quantidade": 4})
    assert resposta.status_code == 200
    assert situacao(cliente) == (6, 6, 0, 0)


def test_saida_acima_do_disponivel_retorna_409_sem_alterar_estado(cliente):
    criar_produto(cliente)
    resposta = cliente.post("/produtos/CAMISA-P/saida", json={"quantidade": 11})
    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "ESTOQUE_INSUFICIENTE"
    assert situacao(cliente) == (10, 10, 0, 0)


@pytest.mark.parametrize(
    "caminho, corpo",
    [
        ("entrada", {"quantidade": 1}),
        ("saida", {"quantidade": 1}),
        ("reservas", {"quantidade": 1, "referencia": "PED-1"}),
        ("bloqueios", {"quantidade": 1}),
    ],
)
def test_operacoes_em_produto_inexistente_retornam_404(cliente, caminho, corpo):
    resposta = cliente.post(f"/produtos/NAO-EXISTE/{caminho}", json=corpo)
    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "PRODUTO_NAO_ENCONTRADO"


@pytest.mark.parametrize(
    "corpo",
    [{"quantidade": 0}, {"quantidade": -1}, {"quantidade": 1.5},
     {"quantidade": "3"}, {"quantidade": True}, {}],
)
def test_quantidade_invalida_retorna_422_sem_alterar_estado(cliente, corpo):
    criar_produto(cliente)
    for caminho in ("entrada", "saida", "reservas", "bloqueios"):
        enviado = {**corpo, "referencia": "PED-1"} if caminho == "reservas" else corpo
        resposta = cliente.post(f"/produtos/CAMISA-P/{caminho}", json=enviado)
        assert resposta.status_code == 422
        assert resposta.json()["erro"]["codigo"] == "VALIDACAO"
    assert situacao(cliente) == (10, 10, 0, 0)


# ---------- reservas ----------

def test_reservar_retorna_201_com_id_e_atualiza_o_estoque(cliente):
    criar_produto(cliente)
    resposta = cliente.post(
        "/produtos/CAMISA-P/reservas", json={"quantidade": 3, "referencia": "PED-1"}
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] and corpo["status"] == "ATIVO" and corpo["referencia"] == "PED-1"
    assert situacao(cliente) == (10, 7, 3, 0)


def test_reservar_acima_do_disponivel_retorna_409_sem_alterar_estado(cliente):
    criar_produto(cliente)
    resposta = cliente.post(
        "/produtos/CAMISA-P/reservas", json={"quantidade": 11, "referencia": "PED-1"}
    )
    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "ESTOQUE_INSUFICIENTE"
    assert situacao(cliente) == (10, 10, 0, 0)


def test_reservar_sem_referencia_retorna_422(cliente):
    criar_produto(cliente)
    resposta = cliente.post("/produtos/CAMISA-P/reservas", json={"quantidade": 1})
    assert resposta.status_code == 422
    assert situacao(cliente) == (10, 10, 0, 0)


# ---------- bloqueios ----------

def test_bloquear_retorna_201_e_atualiza_o_estoque(cliente):
    criar_produto(cliente)
    resposta = cliente.post(
        "/produtos/CAMISA-P/bloqueios", json={"quantidade": 4, "motivo": "avaria"}
    )
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "ATIVO"
    assert situacao(cliente) == (10, 6, 0, 4)


def test_bloquear_acima_do_disponivel_retorna_409_sem_alterar_estado(cliente):
    criar_produto(cliente)
    cliente.post("/produtos/CAMISA-P/reservas", json={"quantidade": 8, "referencia": "PED-1"})
    resposta = cliente.post("/produtos/CAMISA-P/bloqueios", json={"quantidade": 3})
    assert resposta.status_code == 409
    assert situacao(cliente) == (10, 2, 8, 0)


# ---------- consultas por ID ----------

def test_consultar_reserva_e_bloqueio_por_id(cliente):
    criar_produto(cliente)
    reserva = cliente.post(
        "/produtos/CAMISA-P/reservas", json={"quantidade": 3, "referencia": "PED-1"}
    ).json()
    bloqueio = cliente.post("/produtos/CAMISA-P/bloqueios", json={"quantidade": 2}).json()

    assert cliente.get(f"/reservas/{reserva['id']}").json() == reserva
    assert cliente.get(f"/bloqueios/{bloqueio['id']}").json() == bloqueio


@pytest.mark.parametrize(
    "caminho, codigo",
    [("reservas", "RESERVA_NAO_ENCONTRADA"), ("bloqueios", "BLOQUEIO_NAO_ENCONTRADO")],
)
def test_consultar_reserva_ou_bloqueio_inexistente_retorna_404(cliente, caminho, codigo):
    resposta = cliente.get(f"/{caminho}/NAO-EXISTE")
    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == codigo


# ---------- liberação ----------

def test_liberar_reserva_devolve_ao_disponivel_e_repetir_retorna_409(cliente):
    criar_produto(cliente)
    reserva = cliente.post(
        "/produtos/CAMISA-P/reservas", json={"quantidade": 3, "referencia": "PED-1"}
    ).json()

    resposta = cliente.post(f"/reservas/{reserva['id']}/liberar")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "LIBERADO"
    assert situacao(cliente) == (10, 10, 0, 0)

    repetida = cliente.post(f"/reservas/{reserva['id']}/liberar")
    assert repetida.status_code == 409
    assert repetida.json()["erro"]["codigo"] == "JA_LIBERADO"
    assert situacao(cliente) == (10, 10, 0, 0)


def test_liberar_bloqueio_devolve_ao_disponivel_e_repetir_retorna_409(cliente):
    criar_produto(cliente)
    bloqueio = cliente.post("/produtos/CAMISA-P/bloqueios", json={"quantidade": 4}).json()

    resposta = cliente.post(f"/bloqueios/{bloqueio['id']}/liberar")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "LIBERADO"
    assert situacao(cliente) == (10, 10, 0, 0)

    repetida = cliente.post(f"/bloqueios/{bloqueio['id']}/liberar")
    assert repetida.status_code == 409
    assert repetida.json()["erro"]["codigo"] == "JA_LIBERADO"
    assert situacao(cliente) == (10, 10, 0, 0)


@pytest.mark.parametrize("caminho", ["reservas", "bloqueios"])
def test_liberar_inexistente_retorna_404(cliente, caminho):
    resposta = cliente.post(f"/{caminho}/NAO-EXISTE/liberar")
    assert resposta.status_code == 404


# ---------- fluxo completo ----------

def test_fluxo_completo(cliente):
    criar_produto(cliente)  # total 10
    reserva = cliente.post(
        "/produtos/CAMISA-P/reservas", json={"quantidade": 3, "referencia": "PED-1"}
    ).json()
    bloqueio = cliente.post("/produtos/CAMISA-P/bloqueios", json={"quantidade": 2}).json()
    assert situacao(cliente) == (10, 5, 3, 2)

    # saída maior que o disponível é recusada; a do tamanho exato funciona
    assert cliente.post("/produtos/CAMISA-P/saida", json={"quantidade": 6}).status_code == 409
    assert cliente.post("/produtos/CAMISA-P/saida", json={"quantidade": 5}).status_code == 200
    assert situacao(cliente) == (5, 0, 3, 2)

    cliente.post(f"/reservas/{reserva['id']}/liberar")
    assert situacao(cliente) == (5, 3, 0, 2)
    cliente.post(f"/bloqueios/{bloqueio['id']}/liberar")
    assert situacao(cliente) == (5, 5, 0, 0)