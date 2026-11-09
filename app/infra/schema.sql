CREATE TABLE IF NOT EXISTS produtos (
    id         TEXT PRIMARY KEY,
    nome       TEXT,
    total      INTEGER NOT NULL DEFAULT 0 CHECK (total >= 0),
    reservado  INTEGER NOT NULL DEFAULT 0 CHECK (reservado >= 0),
    bloqueado  INTEGER NOT NULL DEFAULT 0 CHECK (bloqueado >= 0),
    CHECK (reservado + bloqueado <= total)
);

CREATE TABLE IF NOT EXISTS reservas (
    id          TEXT PRIMARY KEY,
    produto_id  TEXT NOT NULL REFERENCES produtos(id),
    quantidade  INTEGER NOT NULL CHECK (quantidade > 0),
    referencia  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('ATIVO', 'LIBERADO'))
);

CREATE TABLE IF NOT EXISTS bloqueios (
    id          TEXT PRIMARY KEY,
    produto_id  TEXT NOT NULL REFERENCES produtos(id),
    quantidade  INTEGER NOT NULL CHECK (quantidade > 0),
    motivo      TEXT,
    status      TEXT NOT NULL CHECK (status IN ('ATIVO', 'LIBERADO'))
);