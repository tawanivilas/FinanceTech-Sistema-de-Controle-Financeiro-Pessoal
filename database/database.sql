CREATE TABLE IF NOT EXISTS metas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    valor_alvo DECIMAL(10,2) NOT NULL,
    valor_atual DECIMAL(10,2) DEFAULT 0.00,
    data_inicio DATE NULL,
    data_limite DATE NULL,
    categoria_id INT NULL,
    usuario_id INT NOT NULL,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);