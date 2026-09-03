import os

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import mysql.connector
from mysql.connector import Error

from datetime import datetime, date
from dateutil.relativedelta import relativedelta


# ============================================================
# CONFIGURAÇÃO DO FLASK
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "chave-secreta-financetech"
)

app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True


# ============================================================
# CONEXÃO COM O TIDB CLOUD
# ============================================================

def conectar_banco():
    return mysql.connector.connect(
        host=os.environ.get(
            "DB_HOST",
            "gateway01.sa-east-1.prod.aws.tidbcloud.com"
        ),
        port=int(
            os.environ.get(
                "DB_PORT",
                "4000"
            )
        ),
        user=os.environ.get(
            "DB_USER"
        ),
        password=os.environ.get(
            "DB_PASSWORD"
        ),
        database=os.environ.get(
            "DB_NAME",
            "financetech"
        ),
        ssl_disabled=False
    )


# ============================================================
# FECHAR CONEXÃO
# ============================================================

def fechar_banco(cursor=None, conexao=None):
    try:
        if cursor:
            cursor.close()
    except Exception:
        pass

    try:
        if conexao:
            conexao.close()
    except Exception:
        pass


# ============================================================
# VERIFICAR USUÁRIO LOGADO
# ============================================================

def usuario_logado():
    return "usuario_id" in session


# ============================================================
# LOGIN
# ============================================================

@app.route("/", methods=["GET", "POST"], strict_slashes=False)
@app.route("/login", methods=["GET", "POST"], strict_slashes=False)
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        if not email or not senha:
            return "Preencha o e-mail e a senha."

        conexao = None
        cursor = None

        try:
            conexao = conectar_banco()
            cursor = conexao.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT *
                FROM usuarios
                WHERE email = %s
                """,
                (email,)
            )

            usuario = cursor.fetchone()

            if usuario:
                senha_banco = usuario.get("senha")

                if senha_banco:
                    try:
                        senha_correta = check_password_hash(
                            senha_banco,
                            senha
                        )
                    except Exception:
                        senha_correta = False

                    if senha_correta:
                        session.clear()
                        session["usuario_id"] = usuario["id"]
                        session["usuario_nome"] = usuario["nome"]

                        return redirect(url_for("dashboard"))

            return "E-mail ou senha incorretos!"

        except Error as e:
            return f"Erro ao realizar login: {e}"

        finally:
            fechar_banco(cursor, conexao)

    return render_template("login.html")


# ============================================================
# CADASTRO
# ============================================================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nome or not email or not senha:
            return "Preencha todos os campos."

        if senha != confirmar_senha:
            return "As senhas não são iguais!"

        conexao = None
        cursor = None

        try:
            conexao = conectar_banco()
            cursor = conexao.cursor()

            cursor.execute(
                """
                SELECT id
                FROM usuarios
                WHERE email = %s
                """,
                (email,)
            )

            usuario_existente = cursor.fetchone()

            if usuario_existente:
                return "Este e-mail já está cadastrado."

            senha_hash = generate_password_hash(senha)

            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha)
                VALUES (%s, %s, %s)
                """,
                (nome, email, senha_hash)
            )

            conexao.commit()
            return redirect(url_for("login"))

        except Error as e:
            if conexao:
                conexao.rollback()
            return f"Erro ao realizar cadastro: {e}"

        finally:
            fechar_banco(cursor, conexao)

    return render_template("cadastro.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]
    usuario_nome = session.get("usuario_nome", "")
    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        hoje = date.today()
        mes_atual = request.args.get("mes", hoje.strftime("%Y-%m"))

        nomes_meses = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        meses = [
            {"codigo": f"{hoje.year}-{str(i).zfill(2)}", "nome": nomes_meses[i - 1]}
            for i in range(1, 13)
        ]

        sql = """
            SELECT
                t.*,
                c.nome AS categoria
            FROM transacoes t
            LEFT JOIN categorias c
                ON t.categoria_id = c.id
            WHERE
                t.usuario_id = %s
                AND DATE_FORMAT(t.data, '%%Y-%%m') = %s
            ORDER BY
                t.data DESC,
                t.id DESC
        """

        cursor.execute(sql, (usuario_id, mes_atual))
        transacoes = cursor.fetchall()

        for t in transacoes:
            data_original = t.get("data")

            if isinstance(data_original, (datetime, date)):
                t["data_transacao"] = data_original.strftime("%Y-%m-%d")
            elif data_original:
                try:
                    data_convertida = datetime.strptime(
                        str(data_original)[:10],
                        "%Y-%m-%d"
                    ).date()
                    t["data_transacao"] = str(data_convertida)
                except Exception:
                    t["data_transacao"] = str(data_original)
            else:
                t["data_transacao"] = ""

        receitas = sum(
            float(t["valor"])
            for t in transacoes
            if t.get("tipo") == "receita"
        )

        despesas = sum(
            float(t["valor"])
            for t in transacoes
            if t.get("tipo") == "despesa"
        )

        saldo = receitas - despesas

        despesas_categoria = {}
        for t in transacoes:
            if t.get("tipo") != "despesa":
                continue

            categoria = t.get("categoria") or "Sem categoria"
            valor = float(t.get("valor", 0) or 0)
            despesas_categoria[categoria] = despesas_categoria.get(categoria, 0) + valor

        sql_ano = """
            SELECT
                t.valor,
                c.nome AS categoria
            FROM transacoes t
            LEFT JOIN categorias c
                ON t.categoria_id = c.id
            WHERE
                t.usuario_id = %s
                AND t.tipo = 'despesa'
                AND YEAR(t.data) = %s
        """

        cursor.execute(sql_ano, (usuario_id, hoje.year))
        despesas_ano = cursor.fetchall()

        total_despesas_ano = sum(
            float(t["valor"])
            for t in despesas_ano
        )

        cursor.execute(
            """
            SELECT *
            FROM categorias
            ORDER BY nome
            """
        )
        categorias = cursor.fetchall()

        return render_template(
            "dashboard.html",
            usuario=usuario_nome,
            mes_atual=mes_atual,
            meses=meses,
            transacoes=transacoes,
            receitas=receitas,
            despesas=despesas,
            saldo=saldo,
            despesas_categoria=despesas_categoria,
            despesas_ano=despesas_ano,
            total_despesas_ano=total_despesas_ano,
            categorias=categorias
        )

    except Error as e:
        return f"Erro ao carregar dashboard: {e}"

    finally:
        fechar_banco(cursor, conexao)


# ============================================================
# NOVA TRANSAÇÃO
# ============================================================

@app.route("/nova-transacao", methods=["GET", "POST"])
def nova_transacao():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = None
    cursor = None

    if request.method == "POST":
        descricao = request.form.get("descricao", "").strip()
        valor_str = request.form.get("valor", "0").replace(",", ".")
        tipo = request.form.get("tipo", "")
        categoria_id = request.form.get("categoria_id")
        data_transacao_str = request.form.get("data_transacao")

        try:
            valor = float(valor_str)
            if valor <= 0:
                return "O valor deve ser maior que zero."

            data_transacao = None
            if data_transacao_str:
                data_transacao = datetime.strptime(
                    data_transacao_str,
                    "%Y-%m-%d"
                ).date()

            if not data_transacao:
                return "Informe a data da transação."

            conexao = conectar_banco()
            cursor = conexao.cursor()

            cursor.execute(
                """
                INSERT INTO transacoes
                (descricao, valor, tipo, data, data_transacao, categoria_id, usuario_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    descricao,
                    valor,
                    tipo,
                    data_transacao,
                    data_transacao,
                    categoria_id if categoria_id else None,
                    session["usuario_id"]
                )
            )

            conexao.commit()
            return redirect(url_for("dashboard"))

        except ValueError:
            return "Valor ou data inválida."

        except Error as e:
            if conexao:
                conexao.rollback()
            return f"Erro ao criar transação: {e}"

        finally:
            fechar_banco(cursor, conexao)

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM categorias
            ORDER BY nome
            """
        )

        categorias = cursor.fetchall()

        return render_template(
            "nova_transacao.html",
            categorias=categorias
        )

    except Error as e:
        return f"Erro ao carregar categorias: {e}"

    finally:
        fechar_banco(cursor, conexao)


# ============================================================
# EDITAR TRANSAÇÃO
# ============================================================

@app.route("/editar-transacao/<int:id>", methods=["GET", "POST"])
def editar_transacao(id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        if request.method == "POST":
            descricao = request.form.get("descricao", "").strip()
            valor_str = request.form.get("valor", "0").replace(",", ".")
            tipo = request.form.get("tipo", "")
            categoria_id = request.form.get("categoria_id")
            data_transacao_str = request.form.get("data_transacao")

            valor = float(valor_str)
            data_transacao = None

            if data_transacao_str:
                data_transacao = datetime.strptime(
                    data_transacao_str,
                    "%Y-%m-%d"
                ).date()

            if not data_transacao:
                return "Informe a data da transação."

            cursor.execute(
                """
                UPDATE transacoes
                SET
                    descricao = %s,
                    valor = %s,
                    tipo = %s,
                    categoria_id = %s,
                    data = %s,
                    data_transacao = %s
                WHERE
                    id = %s
                    AND usuario_id = %s
                """,
                (
                    descricao,
                    valor,
                    tipo,
                    categoria_id if categoria_id else None,
                    data_transacao,
                    data_transacao,
                    id,
                    session["usuario_id"]
                )
            )

            conexao.commit()
            return redirect(url_for("dashboard"))

        cursor.execute(
            """
            SELECT *
            FROM transacoes
            WHERE
                id = %s
                AND usuario_id = %s
            """,
            (id, session["usuario_id"])
        )

        transacao = cursor.fetchone()

        if not transacao:
            return "Transação não encontrada."

        cursor.execute(
            """
            SELECT *
            FROM categorias
            ORDER BY nome
            """
        )

        categorias = cursor.fetchall()

        return render_template(
            "editar_transacao.html",
            transacao=transacao,
            categorias=categorias
        )

    except ValueError:
        return "Valor ou data inválida."

    except Error as e:
        if conexao:
            conexao.rollback()
        return f"Erro ao editar transação: {e}"

    finally:
        fechar_banco(cursor, conexao)


# ============================================================
# EXCLUIR TRANSAÇÃO
# ============================================================

@app.route("/excluir-transacao/<int:id>", methods=["POST", "GET"])
def excluir_transacao(id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM transacoes
            WHERE
                id = %s
                AND usuario_id = %s
            """,
            (id, session["usuario_id"])
        )

        conexao.commit()
        return redirect(url_for("dashboard"))

    except Error as e:
        if conexao:
            conexao.rollback()
        return f"Erro ao excluir transação: {e}"

    finally:
        fechar_banco(cursor, conexao)


# ============================================================
# METAS
# ============================================================

@app.route("/metas")
def metas():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]
    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                titulo AS nome,
                valor_alvo AS valor_meta,
                valor_atual,
                data_limite AS prazo
            FROM metas
            WHERE usuario_id = %s
            ORDER BY id DESC
            """,
            (usuario_id,)
        )

        metas = cursor.fetchall()

        for meta in metas:
            valor_meta = float(meta.get("valor_meta", 0) or 0)
            valor_atual = float(meta.get("valor_atual", 0) or 0)

            if valor_meta > 0:
                porcentagem = (valor_atual / valor_meta) * 100
            else:
                porcentagem = 0

            porcentagem = min(max(porcentagem, 0), 100)
            meta["porcentagem"] = round(porcentagem, 2)

        return render_template("metas.html", metas=metas)

    except Error as e:
        return f"Erro ao carregar metas: {e}"

    finally:
        fechar_banco(cursor, conexao)


# ============================================================
# NOVA META
# ============================================================

@app.route("/nova-meta", methods=["GET", "POST"])
def nova_meta():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        valor_meta_str = request.form.get("valor_meta", "0").replace(",", ".")
        prazo_str = request.form.get("prazo")

        if not nome:
            return "Informe o nome da meta."

        conexao = None
        cursor = None

        try:
            valor_meta = float(valor_meta_str)
            if valor_meta <= 0:
                return "O valor da meta deve ser maior que zero."

            prazo = None
            if prazo_str:
                prazo = datetime.strptime(
                    prazo_str,
                    "%Y-%m-%d"
                ).date()

            conexao = conectar_banco()
            cursor = conexao.cursor()

            cursor.execute(
                """
                INSERT INTO metas
                (usuario_id, titulo, valor_alvo, valor_atual, data_limite)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    session["usuario_id"],
                    nome,
                    valor_meta,
                    0,
                    prazo
                )
            )

            conexao.commit()
            return redirect(url_for("metas"))

        except ValueError:
            return "Valor ou prazo inválido."

        except Error as e:
            if conexao:
                conexao.rollback()
            return f"Erro ao criar meta: {e}"

        finally:
            fechar_banco(cursor, conexao)

    return render_template("nova_meta.html")


# ============================================================
# DEPOSITAR VALOR NA META
# ============================================================

@app.route("/depositar-meta/<int:id>", methods=["POST"])
def depositar_meta(id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    valor_str = request.form.get("valor", "0").replace(",", ".")

    if valor_str == "0":
        valor_str = request.form.get("valor_adicional", "0").replace(",", ".")

    try:
        valor = float(valor_str)
        if valor <= 0:
            return "O valor deve ser maior que zero."
    except ValueError:
        return "Valor inválido."

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE metas
            SET valor_atual = valor_atual + %s
            WHERE
                id = %s
                AND usuario_id = %s
            """,
            (valor, id, session["usuario_id"])
        )

        conexao.commit()
        return redirect(url_for("metas"))

    except Error as e:
        if conexao:
            conexao.rollback()
        return f"Erro ao adicionar valor à meta: {e}"

    finally:
        fechar_banco(cursor, conexao)


# ============================================================
# EXCLUIR META
# ============================================================

@app.route("/excluir-meta/<int:id>", methods=["POST", "GET"])
def excluir_meta(id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM metas
            WHERE
                id = %s
                AND usuario_id = %s
            """,
            (id, session["usuario_id"])
        )

        conexao.commit()
        return redirect(url_for("metas"))

    except Error as e:
        if conexao:
            conexao.rollback()
        return f"Erro ao excluir meta: {e}"

    finally:
        fechar_banco(cursor, conexao)


# ============================================================
# EXECUTAR APLICAÇÃO
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        debug=True
    )