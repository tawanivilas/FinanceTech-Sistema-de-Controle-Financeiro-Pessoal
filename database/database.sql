SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS transacoes;
DROP TABLE IF EXISTS metas;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    senha VARCHAR(255) NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    nome VARCHAR(50) NOT NULL,
    tipo ENUM('receita', 'despesa') NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE transacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria_id INT NULL,
    descricao VARCHAR(255),
    valor DECIMAL(10, 2) NOT NULL,
    tipo ENUM('receita', 'despesa') NOT NULL,
    subtipo_despesa VARCHAR(50) NULL,
    parcela_atual INT NULL,
    total_parcelas INT NULL,
    data DATE NULL,
    data_transacao DATE NOT NULL,
    data_termino DATE NULL,
    pago TINYINT(1) DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE metas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nome VARCHAR(100) NOT NULL,
    valor_meta DECIMAL(10, 2) NOT NULL,
    valor_atual DECIMAL(10, 2) DEFAULT 0.00,
    prazo DATE NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO categorias (nome, tipo, usuario_id) VALUES
('Alimentação', 'despesa', NULL),
('Transporte', 'despesa', NULL),
('Moradia', 'despesa', NULL),
('Lazer', 'despesa', NULL),
('Saúde', 'despesa', NULL),
('Salário', 'receita', NULL),
('Investimentos', 'receita', NULL),
('Outros', 'receita', NULL);

SET FOREIGN_KEY_CHECKS = 1;