import app

conn = app.conectar_banco()
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE transacoes ADD COLUMN status VARCHAR(20) DEFAULT 'Pago'")
    conn.commit()
    print("Coluna 'status' adicionada com sucesso!")
except Exception as e:
    print("Erro ou coluna ja existe:", e)

cur.close()
conn.close()
