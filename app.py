import os
import re
import unicodedata

from dotenv import load_dotenv
load_dotenv()

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

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


# =========================================================
# CONFIGURAÇÃO DO FLASK
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "finance-tech-chave-secreta"
)


IS_PRODUCTION = (
    os.environ.get("FLASK_ENV", "").lower() == "production"
    or os.environ.get("SESSION_COOKIE_SECURE", "").lower() == "true"
)


if IS_PRODUCTION:
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True
else:
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False


# =========================================================
# NOMES DOS MESES EM PORTUGUÊS
# =========================================================

MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}


# =========================================================
# CONEXÃO COM O BANCO DE DADOS
# =========================================================

def conectar_banco():

    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")

    if not db_user:
        raise RuntimeError("DB_USER não está configurado.")

    if not db_password:
        raise RuntimeError("DB_PASSWORD não está configurado.")

    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "gateway01.sa-east-1.prod.aws.tidbcloud.com"),
        port=int(os.environ.get("DB_PORT", "4000")),
        user=db_user,
        password=db_password,
        database=os.environ.get("DB_NAME", "financetech"),
        ssl_disabled=False
    )


# =========================================================
# FECHAR CONEXÃO
# =========================================================

def fechar_banco(cursor=None, conexao=None):

    try:
        if cursor:
            cursor.close()
    except Exception:
        pass

    try:
        if conexao and conexao.is_connected():
            conexao.close()
    except Exception:
        pass


# =========================================================
# SLUGIFY
# =========================================================

def slugify(text):

    if not text:
        return "outros"

    text = str(text)

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")

    return text or "outros"


# =========================================================
# CONVERTER VALOR
# =========================================================

def converter_valor(valor_str):

    if valor_str is None:
        return None

    valor_str = str(valor_str).strip()

    if not valor_str:
        return None

    try:
        valor_str = valor_str.replace("R$", "").replace(" ", "")

        if "," in valor_str:
            valor_str = valor_str.replace(".", "").replace(",", ".")

        valor = float(valor_str)
        return valor

    except (ValueError, TypeError):
        return None


# =========================================================
# LOGIN
# =========================================================

@app.route("/")
@app.route("/login")
def login():

    if "usuario_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def realizar_login():

    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")

    if not email or not senha:
        flash("Preencha e-mail e senha.", "warning")
        return redirect(url_for("login"))

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, nome, email, senha
            FROM usuarios
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
            """,
            (email,)
        )

        usuario = cursor.fetchone()

        if not usuario:
            flash("E-mail ou senha incorretos!", "danger")
            return redirect(url_for("login"))

        senha_banco = usuario["senha"]
        senha_valida = False

        try:
            senha_valida = check_password_hash(senha_banco, senha)
        except Exception:
            senha_valida = (senha_banco == senha)

        if not senha_valida:
            flash("E-mail ou senha incorretos!", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["usuario_id"] = usuario["id"]
        session["usuario_nome"] = usuario["nome"]

        return redirect(url_for("dashboard"))

    except Error:
        app.logger.exception("Erro ao realizar login")
        flash("Erro ao conectar ao banco de dados.", "danger")
        return redirect(url_for("login"))

    except Exception:
        app.logger.exception("Erro inesperado no login")
        flash("Ocorreu um erro inesperado.", "danger")
        return redirect(url_for("login"))

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# CADASTRO
# =========================================================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "GET":
        return render_template("cadastro.html")

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    confirmar_senha = request.form.get("confirmar_senha", "")

    if not nome:
        flash("Informe seu nome.", "warning")
        return redirect(url_for("cadastro"))

    if not email:
        flash("Informe seu e-mail.", "warning")
        return redirect(url_for("cadastro"))

    if not senha:
        flash("Informe uma senha.", "warning")
        return redirect(url_for("cadastro"))

    if senha != confirmar_senha:
        flash("As senhas não são iguais!", "warning")
        return redirect(url_for("cadastro"))

    senha_hash = generate_password_hash(senha)

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id FROM usuarios
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
            """,
            (email,)
        )

        usuario_existente = cursor.fetchone()

        if usuario_existente:
            flash("Este e-mail já está cadastrado.", "warning")
            return redirect(url_for("cadastro"))

        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha)
            VALUES (%s, %s, %s)
            """,
            (nome, email, senha_hash)
        )

        conexao.commit()
        flash("Cadastro realizado com sucesso! Faça login.", "success")
        return redirect(url_for("login"))

    except Error:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro ao cadastrar usuário")
        flash("Erro ao realizar cadastro.", "danger")
        return redirect(url_for("cadastro"))

    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro inesperado no cadastro")
        flash("Ocorreu um erro inesperado.", "danger")
        return redirect(url_for("cadastro"))

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]
    hoje = date.today()
    mes_param = request.args.get("mes")

    if mes_param:
        try:
            ano_sel, mes_sel = mes_param.split("-")
            primeiro_dia = date(int(ano_sel), int(mes_sel), 1)
        except (ValueError, TypeError):
            primeiro_dia = hoje.replace(day=1)
    else:
        primeiro_dia = hoje.replace(day=1)

    ultimo_dia = primeiro_dia + relativedelta(months=1)
    mes_atual = primeiro_dia.strftime("%Y-%m")

    meses = []
    for i in range(12):
        data_ref = hoje.replace(day=1) - relativedelta(months=i)
        meses.append({
            "valor": data_ref.strftime("%Y-%m"),
            "nome": f"{MESES_PT[data_ref.month]} de {data_ref.year}"
        })

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                t.id, t.descricao, t.tipo, t.valor, t.data, t.status,
                c.nome AS categoria
            FROM transacoes t
            LEFT JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s
              AND t.data >= %s
              AND t.data < %s
            ORDER BY t.data DESC, t.id DESC
            """,
            (usuario_id, primeiro_dia, ultimo_dia)
        )

        transacoes = cursor.fetchall()

        total_receitas = 0
        total_despesas = 0

        for transacao in transacoes:
            valor = float(transacao["valor"] or 0)
            tipo = str(transacao["tipo"] or "").lower()

            if tipo in ["receita", "entrada", "income"]:
                total_receitas += valor
            else:
                total_despesas += valor

        saldo_mes = total_receitas - total_despesas

        cursor.execute(
            """
            SELECT
                c.nome AS categoria,
                SUM(t.valor) AS total
            FROM transacoes t
            LEFT JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s
              AND t.tipo IN ('despesa', 'saida')
              AND t.data >= %s
              AND t.data < %s
            GROUP BY c.nome
            ORDER BY total DESC
            """,
            (usuario_id, primeiro_dia, ultimo_dia)
        )

        despesas_categoria = cursor.fetchall()
        despesas_cat_mes = {
            (linha["categoria"] or "Sem categoria"): float(linha["total"] or 0)
            for linha in despesas_categoria
        }

        return render_template(
            "dashboard.html",
            transacoes=transacoes,
            total_receitas=total_receitas,
            total_despesas=total_despesas,
            saldo_mes=saldo_mes,
            despesas_cat_mes=despesas_cat_mes,
            meses=meses,
            mes_atual=mes_atual
        )

    except Error:
        app.logger.exception("Erro ao carregar dashboard")
        flash("Erro ao carregar o dashboard.", "danger")
        return render_template(
            "dashboard.html",
            transacoes=[],
            total_receitas=0,
            total_despesas=0,
            saldo_mes=0,
            despesas_cat_mes={},
            meses=meses,
            mes_atual=mes_atual
        )

    except Exception:
        app.logger.exception("Erro inesperado no dashboard")
        flash("Erro ao carregar o dashboard.", "danger")
        return render_template(
            "dashboard.html",
            transacoes=[],
            total_receitas=0,
            total_despesas=0,
            saldo_mes=0,
            despesas_cat_mes={},
            meses=meses,
            mes_atual=mes_atual
        )

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# LANÇAMENTOS
# =========================================================

@app.route("/lancamentos")
def lancamentos():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    periodo = request.args.get("periodo", "todos")
    tipo_filtro = request.args.get("tipo", "")
    categoria_filtro = request.args.get("categoria", "")
    status_filtro = request.args.get("status", "")

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        sql = """
            SELECT
                t.id, t.descricao, t.tipo, t.valor, t.data, t.status, t.categoria_id,
                c.nome AS categoria
            FROM transacoes t
            LEFT JOIN categorias c ON t.categoria_id = c.id
            WHERE t.usuario_id = %s
        """

        parametros = [usuario_id]
        hoje = date.today()

        if periodo in ["mes", "este_mes"]:
            primeiro_dia = hoje.replace(day=1)
            proximo_mes = primeiro_dia + relativedelta(months=1)
            sql += " AND t.data >= %s AND t.data < %s"
            parametros.extend([primeiro_dia, proximo_mes])

        elif periodo in ["7dias", "7_dias"]:
            data_inicio = hoje - timedelta(days=7)
            sql += " AND t.data >= %s"
            parametros.append(data_inicio)

        elif periodo in ["30dias", "30_dias"]:
            data_inicio = hoje - timedelta(days=30)
            sql += " AND t.data >= %s"
            parametros.append(data_inicio)

        elif periodo == "mes_passado":
            primeiro_dia_mes_atual = hoje.replace(day=1)
            primeiro_dia_mes_passado = primeiro_dia_mes_atual - relativedelta(months=1)
            sql += " AND t.data >= %s AND t.data < %s"
            parametros.extend([primeiro_dia_mes_passado, primeiro_dia_mes_atual])

        if tipo_filtro:
            sql += " AND t.tipo = %s"
            parametros.append(tipo_filtro)

        if categoria_filtro:
            sql += " AND t.categoria_id = %s"
            parametros.append(categoria_filtro)

        if status_filtro:
            sql += " AND t.status = %s"
            parametros.append(status_filtro)

        sql += " ORDER BY t.data DESC, t.id DESC"

        cursor.execute(sql, tuple(parametros))
        transacoes = cursor.fetchall()

        cursor.execute(
            """
            SELECT id, nome
            FROM categorias
            WHERE usuario_id IS NULL OR usuario_id = %s
            ORDER BY nome
            """,
            (usuario_id,)
        )

        categorias = cursor.fetchall()

        return render_template(
            "lancamentos.html",
            transacoes=transacoes,
            categorias=categorias,
            periodo=periodo,
            tipo_filtro=tipo_filtro,
            categoria_filtro=categoria_filtro,
            status_filtro=status_filtro
        )

    except Error:
        app.logger.exception("Erro ao carregar lançamentos")
        flash("Erro ao carregar os lançamentos.", "danger")
        return render_template(
            "lancamentos.html",
            transacoes=[],
            categorias=[],
            periodo=periodo,
            tipo_filtro=tipo_filtro,
            categoria_filtro=categoria_filtro,
            status_filtro=status_filtro
        )

    except Exception:
        app.logger.exception("Erro inesperado nos lançamentos")
        flash("Erro ao carregar os lançamentos.", "danger")
        return render_template(
            "lancamentos.html",
            transacoes=[],
            categorias=[],
            periodo=periodo,
            tipo_filtro=tipo_filtro,
            categoria_filtro=categoria_filtro,
            status_filtro=status_filtro
        )

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# NOVA TRANSAÇÃO / NOVO LANÇAMENTO
# =========================================================

@app.route("/nova-transacao", methods=["GET", "POST"])
@app.route("/novo-lancamento", methods=["GET", "POST"])
def nova_transacao():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    if request.method == "GET":
        return redirect(url_for("lancamentos"))

    descricao = request.form.get("descricao", "").strip()
    tipo = request.form.get("tipo", "").strip().lower()
    valor_str = request.form.get("valor", "").strip()
    data_str = request.form.get("data", "").strip()
    categoria_id_str = request.form.get("categoria_id", "").strip()

    status = (
        request.form.get("status")
        or request.form.get("status_pago")
        or "Pago"
    ).strip()

    if not descricao:
        flash("Informe a descrição.", "warning")
        return redirect(url_for("lancamentos"))

    if tipo not in ["receita", "despesa"]:
        flash("Tipo de lançamento inválido.", "warning")
        return redirect(url_for("lancamentos"))

    valor = converter_valor(valor_str)

    if valor is None or valor <= 0:
        flash("Informe um valor válido.", "warning")
        return redirect(url_for("lancamentos"))

    if data_str:
        try:
            data_transacao = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Data inválida.", "warning")
            return redirect(url_for("lancamentos"))
    else:
        data_transacao = date.today()

    categoria_id = None
    if categoria_id_str:
        try:
            categoria_id = int(categoria_id_str)
        except ValueError:
            categoria_id = None

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO transacoes
            (usuario_id, descricao, tipo, valor, data, categoria_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (usuario_id, descricao, tipo, valor, data_transacao, categoria_id, status)
        )

        conexao.commit()
        flash("Lançamento criado com sucesso!", "success")
        return redirect(url_for("lancamentos"))

    except Error:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro ao criar transação")
        flash("Erro ao criar lançamento.", "danger")
        return redirect(url_for("lancamentos"))

    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro inesperado ao criar transação")
        flash("Ocorreu um erro inesperado.", "danger")
        return redirect(url_for("lancamentos"))

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# EDITAR TRANSAÇÃO
# =========================================================

@app.route("/editar-transacao/<int:transacao_id>", methods=["GET", "POST"])
@app.route("/editar-lancamento/<int:transacao_id>", methods=["GET", "POST"])
def editar_transacao(transacao_id):

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
            SELECT * FROM transacoes
            WHERE id = %s AND usuario_id = %s
            LIMIT 1
            """,
            (transacao_id, usuario_id)
        )

        transacao = cursor.fetchone()

        if not transacao:
            flash("Lançamento não encontrado.", "warning")
            return redirect(url_for("lancamentos"))

        cursor.execute(
            """
            SELECT id, nome FROM categorias
            WHERE usuario_id IS NULL OR usuario_id = %s
            ORDER BY nome
            """,
            (usuario_id,)
        )

        categorias = cursor.fetchall()

        if request.method == "GET":
            return render_template(
                "editar_transacao.html",
                transacao=transacao,
                categorias=categorias
            )

        descricao = request.form.get("descricao", "").strip()
        tipo = request.form.get("tipo", "").strip().lower()
        valor = converter_valor(request.form.get("valor", ""))
        data_str = request.form.get("data", "").strip()
        categoria_id_str = request.form.get("categoria_id", "").strip()

        status = (
            request.form.get("status")
            or request.form.get("status_pago")
            or transacao.get("status", "Pago")
        ).strip()

        if not descricao:
            flash("Informe a descrição.", "warning")
            return redirect(url_for("editar_transacao", transacao_id=transacao_id))

        if tipo not in ["receita", "despesa"]:
            flash("Tipo inválido.", "warning")
            return redirect(url_for("editar_transacao", transacao_id=transacao_id))

        if valor is None or valor <= 0:
            flash("Informe um valor válido.", "warning")
            return redirect(url_for("editar_transacao", transacao_id=transacao_id))

        if data_str:
            try:
                data_transacao = datetime.strptime(data_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Data inválida.", "warning")
                return redirect(url_for("editar_transacao", transacao_id=transacao_id))
        else:
            data_transacao = date.today()

        categoria_id = None
        if categoria_id_str:
            try:
                categoria_id = int(categoria_id_str)
            except ValueError:
                categoria_id = None

        cursor.close()
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE transacoes
            SET
                descricao = %s,
                tipo = %s,
                valor = %s,
                data = %s,
                categoria_id = %s,
                status = %s
            WHERE id = %s AND usuario_id = %s
            """,
            (descricao, tipo, valor, data_transacao, categoria_id, status, transacao_id, usuario_id)
        )

        conexao.commit()
        flash("Lançamento atualizado com sucesso!", "success")
        return redirect(url_for("lancamentos"))

    except Error:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro ao editar transação")
        flash("Erro ao editar lançamento.", "danger")
        return redirect(url_for("lancamentos"))

    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro inesperado ao editar transação")
        flash("Ocorreu um erro inesperado.", "danger")
        return redirect(url_for("lancamentos"))

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# EXCLUIR TRANSAÇÃO
# =========================================================

@app.route("/excluir-transacao/<int:transacao_id>", methods=["GET", "POST"])
@app.route("/excluir-lancamento/<int:transacao_id>", methods=["GET", "POST"])
def excluir_transacao(transacao_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM transacoes
            WHERE id = %s AND usuario_id = %s
            """,
            (transacao_id, usuario_id)
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            flash("Lançamento não encontrado.", "warning")
            return redirect(url_for("lancamentos"))

        conexao.commit()
        flash("Lançamento excluído com sucesso!", "success")
        return redirect(url_for("lancamentos"))

    except Error:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro ao excluir transação")
        flash("Erro ao excluir lançamento.", "danger")
        return redirect(url_for("lancamentos"))

    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro inesperado ao excluir transação")
        flash("Ocorreu um erro inesperado.", "danger")
        return redirect(url_for("lancamentos"))

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# METAS
# =========================================================

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
                m.id,
                m.titulo AS nome,
                m.valor_alvo AS valor_meta,
                m.valor_atual,
                m.data_limite AS prazo,
                c.nome AS categoria
            FROM metas m
            LEFT JOIN categorias c
                ON m.categoria_id = c.id
            WHERE m.usuario_id = %s
            ORDER BY
                m.data_limite ASC,
                m.id DESC
            """,
            (usuario_id,)
        )

        metas_lista = cursor.fetchall()

        for meta in metas_lista:

            valor_meta = float(meta["valor_meta"] or 0)
            valor_atual = float(meta["valor_atual"] or 0)

            if valor_meta > 0:
                porcentagem = (valor_atual / valor_meta) * 100
            else:
                porcentagem = 0

            meta["porcentagem"] = round(max(0, min(100, porcentagem)), 1)

            if meta["prazo"]:
                if isinstance(meta["prazo"], (date, datetime)):
                    meta["prazo"] = meta["prazo"].strftime("%d/%m/%Y")

        return render_template("metas.html", metas=metas_lista)

    except Error:
        app.logger.exception("Erro ao carregar metas")
        flash("Erro ao carregar metas.", "danger")
        return render_template("metas.html", metas=[])

    except Exception:
        app.logger.exception("Erro inesperado ao carregar metas")
        flash("Ocorreu um erro inesperado ao carregar as metas.", "danger")
        return render_template("metas.html", metas=[])

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# NOVA META
# =========================================================

@app.route("/nova-meta", methods=["POST"])
@app.route("/cadastrar-meta", methods=["POST"])
@app.route("/nova_meta", methods=["POST"])
def nova_meta():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    nome = request.form.get("nome", "").strip()
    categoria_nome = request.form.get("categoria", "").strip()
    valor_meta_str = request.form.get("valor_meta", "").strip()
    prazo = request.form.get("prazo", "").strip()

    if not nome:
        flash("Informe o nome da meta.", "warning")
        return redirect(url_for("metas"))

    valor_meta = converter_valor(valor_meta_str)

    if valor_meta is None or valor_meta <= 0:
        flash("Informe um valor válido para a meta.", "warning")
        return redirect(url_for("metas"))

    data_limite = None

    if prazo:
        try:
            data_limite = datetime.strptime(prazo, "%Y-%m-%d").date()
        except ValueError:
            flash("Data limite inválida.", "warning")
            return redirect(url_for("metas"))

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()

        categoria_id = None

        if categoria_nome:
            cursor = conexao.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id
                FROM categorias
                WHERE LOWER(nome) = LOWER(%s)
                  AND (usuario_id IS NULL OR usuario_id = %s)
                LIMIT 1
                """,
                (categoria_nome, usuario_id)
            )

            categoria = cursor.fetchone()
            cursor.close()
            cursor = None

            if categoria:
                categoria_id = categoria["id"]

        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO metas
            (usuario_id, titulo, categoria_id, valor_alvo, valor_atual, data_limite)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (usuario_id, nome, categoria_id, valor_meta, 0, data_limite)
        )

        conexao.commit()
        flash("Meta criada com sucesso!", "success")
        return redirect(url_for("metas"))

    except Error:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro ao cadastrar meta")
        flash("Erro ao cadastrar meta. Verifique os dados informados.", "danger")
        return redirect(url_for("metas"))

    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro inesperado ao cadastrar meta")
        flash("Ocorreu um erro inesperado ao salvar a meta.", "danger")
        return redirect(url_for("metas"))

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# DEPOSITAR NA META
# =========================================================

@app.route("/depositar-meta/<int:id>", methods=["POST"])
def depositar_meta(id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    valor_str = request.form.get("valor", "").strip()
    valor = converter_valor(valor_str)

    if valor is None or valor <= 0:
        flash("Informe um valor válido.", "warning")
        return redirect(url_for("metas"))

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT id
            FROM metas
            WHERE id = %s AND usuario_id = %s
            """,
            (id, usuario_id)
        )

        meta = cursor.fetchone()

        if not meta:
            flash("Meta não encontrada.", "warning")
            return redirect(url_for("metas"))

        cursor.execute(
            """
            UPDATE metas
            SET valor_atual = COALESCE(valor_atual, 0) + %s
            WHERE id = %s AND usuario_id = %s
            """,
            (valor, id, usuario_id)
        )

        conexao.commit()
        flash("Aporte realizado com sucesso!", "success")
        return redirect(url_for("metas"))

    except Error:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro ao depositar na meta")
        flash("Erro ao realizar o aporte.", "danger")
        return redirect(url_for("metas"))

    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro inesperado ao depositar na meta")
        flash("Erro inesperado ao realizar o aporte.", "danger")
        return redirect(url_for("metas"))

    finally:
        fechar_banco(cursor, conexao)


# =========================================================
# EXCLUIR META
# =========================================================

@app.route("/excluir-meta/<int:id>", methods=["GET", "POST"])
def excluir_meta(id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM metas
            WHERE id = %s AND usuario_id = %s
            """,
            (id, usuario_id)
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            flash("Meta não encontrada.", "warning")
            return redirect(url_for("metas"))

        conexao.commit()
        flash("Meta excluída!", "info")
        return redirect(url_for("metas"))

    except Error:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro ao excluir meta")
        flash("Erro ao excluir meta.", "danger")
        return redirect(url_for("metas"))

    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception("Erro inesperado ao excluir meta")
        flash("Erro inesperado ao excluir a meta.", "danger")
        return redirect(url_for("metas"))

    finally:
        fechar_banco(cursor, conexao)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=not IS_PRODUCTION)