import os
import re
import unicodedata

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
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


# =========================================================
# CONFIGURAÇÃO DA SESSÃO
# =========================================================

IS_PRODUCTION = (
    os.environ.get("FLASK_ENV", "").lower() == "production"
    or
    os.environ.get("SESSION_COOKIE_SECURE", "").lower() == "true"
)

if IS_PRODUCTION:
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True
else:
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False


# =========================================================
# CONEXÃO COM O BANCO
# =========================================================

def conectar_banco():

    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")

    if not db_user:
        raise RuntimeError(
            "DB_USER não está configurado."
        )

    if not db_password:
        raise RuntimeError(
            "DB_PASSWORD não está configurado."
        )

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
        user=db_user,
        password=db_password,
        database=os.environ.get(
            "DB_NAME",
            "financetech"
        ),
        ssl_disabled=False
    )


# =========================================================
# FECHAR BANCO
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
# SLUG PARA CATEGORIAS
# =========================================================

def slugify(text):

    if not text:
        return "outros"

    text = str(text)

    text = unicodedata.normalize(
        "NFKD",
        text
    ).encode(
        "ascii",
        "ignore"
    ).decode(
        "ascii"
    )

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "-",
        text
    )

    text = text.strip("-")

    return text or "outros"


# =========================================================
# CONVERTER VALOR BRASILEIRO
# =========================================================

def converter_valor(valor_str):

    if valor_str is None:
        return None

    valor_str = str(valor_str).strip()

    if not valor_str:
        return None

    try:

        valor_str = (
            valor_str
            .replace("R$", "")
            .replace(" ", "")
        )

        # 1.500,50 -> 1500.50
        if "," in valor_str:

            valor_str = (
                valor_str
                .replace(".", "")
                .replace(",", ".")
            )

        valor = float(valor_str)

        return valor

    except (ValueError, TypeError):

        return None


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/",
    methods=["GET", "POST"],
    strict_slashes=False
)
@app.route(
    "/login",
    methods=["GET", "POST"],
    strict_slashes=False
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        senha = request.form.get(
            "senha",
            ""
        )

        if not email or not senha:
            return "Informe e-mail e senha."

        conexao = None
        cursor = None

        try:

            conexao = conectar_banco()

            cursor = conexao.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    email,
                    senha
                FROM usuarios
                WHERE email = %s
                """,
                (email,)
            )

            usuario = cursor.fetchone()

            if not usuario:
                return "E-mail ou senha incorretos!"

            if not check_password_hash(
                usuario["senha"],
                senha
            ):
                return "E-mail ou senha incorretos!"

            session.clear()

            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]

            return redirect(
                url_for("dashboard")
            )

        except Error:

            app.logger.exception(
                "Erro no login"
            )

            return (
                "Erro ao realizar login. "
                "Verifique a conexão com o banco."
            ), 500

        except Exception:

            app.logger.exception(
                "Erro inesperado no login"
            )

            return (
                "Ocorreu um erro inesperado ao realizar login."
            ), 500

        finally:

            fechar_banco(
                cursor,
                conexao
            )

    return render_template(
        "login.html"
    )


# =========================================================
# CADASTRO
# =========================================================

@app.route(
    "/cadastro",
    methods=["GET", "POST"]
)
def cadastro():

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        senha = request.form.get(
            "senha",
            ""
        )

        confirmar_senha = request.form.get(
            "confirmar_senha",
            ""
        )

        if not nome or not email or not senha:
            return "Preencha todos os campos."

        if senha != confirmar_senha:
            return "As senhas não são iguais!"

        conexao = None
        cursor = None

        try:

            conexao = conectar_banco()

            cursor = conexao.cursor(
                dictionary=True
            )

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

            senha_hash = generate_password_hash(
                senha
            )

            cursor.execute(
                """
                INSERT INTO usuarios
                (
                    nome,
                    email,
                    senha
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    nome,
                    email,
                    senha_hash
                )
            )

            conexao.commit()

            return redirect(
                url_for("login")
            )

        except Error:

            if conexao:
                conexao.rollback()

            app.logger.exception(
                "Erro no cadastro"
            )

            return (
                "Erro ao realizar cadastro. "
                "Verifique a conexão com o banco."
            ), 500

        except Exception:

            if conexao:
                conexao.rollback()

            app.logger.exception(
                "Erro inesperado no cadastro"
            )

            return (
                "Ocorreu um erro inesperado no cadastro."
            ), 500

        finally:

            fechar_banco(
                cursor,
                conexao
            )

    return render_template(
        "cadastro.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session["usuario_id"]

    mes_atual = request.args.get(
        "mes"
    )

    if not mes_atual:

        mes_atual = date.today().strftime(
            "%Y-%m"
        )

    try:

        ano, mes = map(
            int,
            mes_atual.split("-")
        )

        primeiro_dia = date(
            ano,
            mes,
            1
        )

        ultimo_dia = (
            primeiro_dia
            + relativedelta(months=1)
            - timedelta(days=1)
        )

    except (ValueError, TypeError):

        primeiro_dia = date.today().replace(
            day=1
        )

        ultimo_dia = (
            primeiro_dia
            + relativedelta(months=1)
            - timedelta(days=1)
        )

        mes_atual = primeiro_dia.strftime(
            "%Y-%m"
        )

    meses = []

    nomes_meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro"
    ]

    ano_atual = date.today().year

    for numero_mes in range(1, 13):

        meses.append({
            "valor": f"{ano_atual}-{numero_mes:02d}",
            "nome": nomes_meses[numero_mes - 1]
        })

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                t.id,
                t.descricao,
                t.valor,
                t.tipo,
                t.data,
                t.pago,
                t.categoria_id,
                c.nome AS categoria_nome
            FROM transacoes t
            LEFT JOIN categorias c
                ON t.categoria_id = c.id
            WHERE t.usuario_id = %s
              AND t.data BETWEEN %s AND %s
            ORDER BY
                t.data DESC,
                t.id DESC
            """,
            (
                usuario_id,
                primeiro_dia,
                ultimo_dia
            )
        )

        transacoes = cursor.fetchall()

        total_receitas = 0
        total_despesas = 0

        despesas_cat_mes = {}

        for item in transacoes:

            item["categoria_nome"] = (
                item["categoria_nome"]
                or
                "Sem categoria"
            )

            item["categoria_slug"] = slugify(
                item["categoria_nome"]
            )

            item["status"] = (
                "Pago"
                if item["pago"]
                else
                "Pendente"
            )

            valor = float(
                item["valor"] or 0
            )

            if item["tipo"] == "receita":

                total_receitas += valor

            else:

                total_despesas += valor

                categoria = item[
                    "categoria_nome"
                ]

                despesas_cat_mes[
                    categoria
                ] = (
                    despesas_cat_mes.get(
                        categoria,
                        0
                    )
                    + valor
                )

        saldo_mes = (
            total_receitas
            -
            total_despesas
        )

        cursor.execute(
            """
            SELECT
                id,
                nome,
                tipo,
                subtipo_despesa
            FROM categorias
            WHERE usuario_id IS NULL
               OR usuario_id = %s
            ORDER BY nome
            """,
            (usuario_id,)
        )

        categorias = cursor.fetchall()

        return render_template(
            "dashboard.html",
            usuario=session.get(
                "usuario_nome"
            ),
            mes_atual=mes_atual,
            meses=meses,
            transacoes=transacoes,
            total_receitas=total_receitas,
            total_despesas=total_despesas,
            saldo_mes=saldo_mes,
            despesas_cat_mes=despesas_cat_mes,
            categorias=categorias
        )

    except Error:

        app.logger.exception(
            "Erro no dashboard"
        )

        return (
            "Erro ao carregar o dashboard. "
            "Verifique a conexão com o banco."
        ), 500

    except Exception:

        app.logger.exception(
            "Erro inesperado no dashboard"
        )

        return (
            "Ocorreu um erro inesperado ao carregar o dashboard."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# LANÇAMENTOS
# =========================================================

@app.route("/lancamentos")
def lancamentos():

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session["usuario_id"]

    periodo = request.args.get(
        "periodo",
        "este_mes"
    )

    tipo = request.args.get(
        "tipo",
        ""
    )

    categoria_id = request.args.get(
        "categoria_id",
        ""
    )

    status = request.args.get(
        "status",
        ""
    )

    hoje = date.today()

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor(
            dictionary=True
        )

        query = """
            SELECT
                t.id,
                t.descricao,
                t.valor,
                t.tipo,
                t.data,
                t.pago,
                t.categoria_id,
                c.nome AS categoria_nome
            FROM transacoes t
            LEFT JOIN categorias c
                ON t.categoria_id = c.id
            WHERE t.usuario_id = %s
        """

        parametros = [
            usuario_id
        ]

        # -------------------------------------------------
        # FILTRO DE PERÍODO
        # -------------------------------------------------

        if periodo == "hoje":

            query += """
                AND t.data = %s
            """

            parametros.append(
                hoje
            )

        elif periodo == "7_dias":

            data_inicio = (
                hoje
                -
                timedelta(days=6)
            )

            query += """
                AND t.data BETWEEN %s AND %s
            """

            parametros.extend([
                data_inicio,
                hoje
            ])

        elif periodo == "mes_passado":

            primeiro_mes = (
                hoje.replace(day=1)
                -
                relativedelta(months=1)
            )

            ultimo_mes = (
                hoje.replace(day=1)
                -
                timedelta(days=1)
            )

            query += """
                AND t.data BETWEEN %s AND %s
            """

            parametros.extend([
                primeiro_mes,
                ultimo_mes
            ])

        else:

            primeiro_mes = hoje.replace(
                day=1
            )

            ultimo_mes = (
                primeiro_mes
                +
                relativedelta(months=1)
                -
                timedelta(days=1)
            )

            query += """
                AND t.data BETWEEN %s AND %s
            """

            parametros.extend([
                primeiro_mes,
                ultimo_mes
            ])

        # -------------------------------------------------
        # FILTRO TIPO
        # -------------------------------------------------

        if tipo in (
            "receita",
            "despesa"
        ):

            query += """
                AND t.tipo = %s
            """

            parametros.append(
                tipo
            )

        # -------------------------------------------------
        # FILTRO CATEGORIA
        # -------------------------------------------------

        if categoria_id:

            try:

                categoria_id_int = int(
                    categoria_id
                )

                query += """
                    AND t.categoria_id = %s
                """

                parametros.append(
                    categoria_id_int
                )

            except ValueError:

                pass

        # -------------------------------------------------
        # FILTRO STATUS
        # -------------------------------------------------

        if status == "Pago":

            query += """
                AND t.pago = 1
            """

        elif status == "Pendente":

            query += """
                AND (
                    t.pago = 0
                    OR
                    t.pago IS NULL
                )
            """

        # -------------------------------------------------
        # ORDEM
        # -------------------------------------------------

        query += """
            ORDER BY
                t.data DESC,
                t.id DESC
        """

        cursor.execute(
            query,
            tuple(parametros)
        )

        lancamentos_lista = cursor.fetchall()

        # -------------------------------------------------
        # PREPARAR DADOS
        # -------------------------------------------------

        for item in lancamentos_lista:

            categoria_nome = (
                item["categoria_nome"]
                or
                "Sem Categoria"
            )

            item["categoria_nome"] = (
                categoria_nome
            )

            item["categoria_slug"] = slugify(
                categoria_nome
            )

            item["status"] = (
                "Pago"
                if item["pago"]
                else
                "Pendente"
            )

        # -------------------------------------------------
        # CATEGORIAS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                nome,
                tipo,
                subtipo_despesa
            FROM categorias
            WHERE usuario_id IS NULL
               OR usuario_id = %s
            ORDER BY nome
            """,
            (usuario_id,)
        )

        categorias = cursor.fetchall()

        return render_template(
            "lancamentos.html",
            lancamentos=lancamentos_lista,
            categorias=categorias
        )

    except Error:

        app.logger.exception(
            "Erro ao carregar lançamentos"
        )

        return (
            "Erro ao carregar lançamentos. "
            "Verifique a conexão com o banco."
        ), 500

    except Exception:

        app.logger.exception(
            "Erro inesperado ao carregar lançamentos"
        )

        return (
            "Ocorreu um erro inesperado ao carregar os lançamentos."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# NOVA TRANSAÇÃO
# =========================================================

@app.route(
    "/nova-transacao",
    methods=["POST"]
)
@app.route(
    "/novo-lancamento",
    methods=["POST"]
)
def nova_transacao():

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session["usuario_id"]

    tipo = request.form.get(
        "tipo",
        ""
    ).strip().lower()

    descricao = request.form.get(
        "descricao",
        ""
    ).strip()

    valor_str = request.form.get(
        "valor",
        ""
    ).strip()

    categoria_id_str = request.form.get(
        "categoria_id",
        ""
    ).strip()

    data_str = request.form.get(
        "data",
        ""
    ).strip()

    status_input = request.form.get(
        "status_pago",
        "Pendente"
    ).strip()

    # -----------------------------------------------------
    # VALIDAÇÕES
    # -----------------------------------------------------

    if tipo not in (
        "receita",
        "despesa"
    ):

        return "Tipo de lançamento inválido."

    if not descricao:

        return "Informe a descrição."

    valor = converter_valor(
        valor_str
    )

    if valor is None or valor <= 0:

        return "Informe um valor válido."

    try:

        if data_str:

            data_transacao = datetime.strptime(
                data_str,
                "%Y-%m-%d"
            ).date()

        else:

            data_transacao = date.today()

    except ValueError:

        return "Data inválida."

    categoria_id = None

    if categoria_id_str:

        try:

            categoria_id = int(
                categoria_id_str
            )

        except ValueError:

            return "Categoria inválida."

    pago_int = (
        1
        if status_input == "Pago"
        else
        0
    )

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor()

        # -------------------------------------------------
        # VALIDAR CATEGORIA
        # -------------------------------------------------

        if categoria_id is not None:

            cursor.execute(
                """
                SELECT id
                FROM categorias
                WHERE id = %s
                  AND (
                      usuario_id IS NULL
                      OR usuario_id = %s
                  )
                """,
                (
                    categoria_id,
                    usuario_id
                )
            )

            categoria = cursor.fetchone()

            if not categoria:

                return (
                    "A categoria selecionada "
                    "não é válida."
                )

        # -------------------------------------------------
        # INSERT
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO transacoes
            (
                usuario_id,
                categoria_id,
                valor,
                tipo,
                data,
                descricao,
                data_transacao,
                pago
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                usuario_id,
                categoria_id,
                valor,
                tipo,
                data_transacao,
                descricao,
                data_transacao,
                pago_int
            )
        )

        conexao.commit()

        return redirect(
            url_for("lancamentos")
        )

    except Error:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro ao criar lançamento"
        )

        return (
            "Erro ao criar lançamento. "
            "Verifique os dados informados."
        ), 500

    except Exception:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro inesperado ao criar lançamento"
        )

        return (
            "Ocorreu um erro inesperado ao criar o lançamento."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# EDITAR TRANSAÇÃO
# =========================================================

@app.route(
    "/editar-transacao/<int:id>",
    methods=["GET", "POST"]
)
@app.route(
    "/editar-lancamento/<int:id>",
    methods=["GET", "POST"]
)
def editar_transacao(id):

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session["usuario_id"]

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor(
            dictionary=True
        )

        # =================================================
        # GET - ABRIR TELA DE EDIÇÃO
        # =================================================

        if request.method == "GET":

            cursor.execute(
                """
                SELECT
                    t.id,
                    t.descricao,
                    t.valor,
                    t.tipo,
                    t.data,
                    t.pago,
                    t.categoria_id
                FROM transacoes t
                WHERE t.id = %s
                  AND t.usuario_id = %s
                """,
                (
                    id,
                    usuario_id
                )
            )

            transacao = cursor.fetchone()

            if not transacao:

                return (
                    "Lançamento não encontrado "
                    "ou sem permissão."
                ), 404

            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    tipo,
                    subtipo_despesa
                FROM categorias
                WHERE usuario_id IS NULL
                   OR usuario_id = %s
                ORDER BY nome
                """,
                (usuario_id,)
            )

            categorias = cursor.fetchall()

            return render_template(
                "editar_transacao.html",
                transacao=transacao,
                categorias=categorias
            )

        # =================================================
        # POST - SALVAR EDIÇÃO
        # =================================================

        descricao = request.form.get(
            "descricao",
            ""
        ).strip()

        valor_str = request.form.get(
            "valor",
            ""
        ).strip()

        tipo = request.form.get(
            "tipo",
            ""
        ).strip().lower()

        categoria_id_str = request.form.get(
            "categoria_id",
            ""
        ).strip()

        data_str = request.form.get(
            "data",
            ""
        ).strip()

        status_input = request.form.get(
            "status_pago",
            ""
        ).strip()

        # -------------------------------------------------
        # DESCRIÇÃO
        # -------------------------------------------------

        if not descricao:

            return "Informe a descrição."

        # -------------------------------------------------
        # TIPO
        # -------------------------------------------------

        if tipo not in (
            "receita",
            "despesa"
        ):

            return "Tipo de lançamento inválido."

        # -------------------------------------------------
        # VALOR
        # -------------------------------------------------

        valor = converter_valor(
            valor_str
        )

        if valor is None:

            return "Informe um valor válido."

        if valor <= 0:

            return "O valor deve ser maior que zero."

        # -------------------------------------------------
        # DATA
        # -------------------------------------------------

        try:

            if data_str:

                data_transacao = datetime.strptime(
                    data_str,
                    "%Y-%m-%d"
                ).date()

            else:

                data_transacao = date.today()

        except ValueError:

            return "Data inválida."

        # -------------------------------------------------
        # CATEGORIA
        # -------------------------------------------------

        categoria_id = None

        if categoria_id_str:

            try:

                categoria_id = int(
                    categoria_id_str
                )

            except ValueError:

                return "Categoria inválida."

        # -------------------------------------------------
        # VERIFICAR SE A TRANSAÇÃO EXISTE
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                descricao,
                valor,
                tipo,
                data,
                pago,
                categoria_id
            FROM transacoes
            WHERE id = %s
              AND usuario_id = %s
            """,
            (
                id,
                usuario_id
            )
        )

        transacao_existe = cursor.fetchone()

        if not transacao_existe:

            return (
                "Lançamento não encontrado "
                "ou sem permissão."
            ), 404

        # -------------------------------------------------
        # VERIFICAR CATEGORIA
        # -------------------------------------------------

        if categoria_id is not None:

            cursor.execute(
                """
                SELECT id
                FROM categorias
                WHERE id = %s
                  AND (
                      usuario_id IS NULL
                      OR usuario_id = %s
                  )
                """,
                (
                    categoria_id,
                    usuario_id
                )
            )

            categoria = cursor.fetchone()

            if not categoria:

                return (
                    "A categoria selecionada "
                    "não é válida."
                )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        pago_int = (
            1
            if status_input == "Pago"
            else
            0
        )

        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE transacoes
            SET
                descricao = %s,
                valor = %s,
                tipo = %s,
                data = %s,
                data_transacao = %s,
                categoria_id = %s,
                pago = %s
            WHERE id = %s
              AND usuario_id = %s
            """,
            (
                descricao,
                valor,
                tipo,
                data_transacao,
                data_transacao,
                categoria_id,
                pago_int,
                id,
                usuario_id
            )
        )

        # IMPORTANTE:
        # Não vamos mais considerar rowcount == 0 como erro.
        # Se o usuário salvar os mesmos dados antigos,
        # o MySQL pode retornar 0 linhas alteradas.
        # Mesmo assim, o UPDATE foi válido.

        conexao.commit()

        return redirect(
            url_for("lancamentos")
        )

    except Error:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro ao editar lançamento"
        )

        return (
            "Erro ao editar lançamento. "
            "Verifique os dados informados."
        ), 500

    except Exception:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro inesperado ao editar lançamento"
        )

        return (
            "Ocorreu um erro inesperado ao editar o lançamento."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# EXCLUIR TRANSAÇÃO
# =========================================================

@app.route(
    "/excluir-transacao/<int:id>",
    methods=["POST"]
)
@app.route(
    "/excluir-lancamento/<int:id>",
    methods=["POST"]
)
def excluir_transacao(id):

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session["usuario_id"]

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM transacoes
            WHERE id = %s
              AND usuario_id = %s
            """,
            (
                id,
                usuario_id
            )
        )

        if cursor.rowcount == 0:

            conexao.rollback()

            return (
                "Lançamento não encontrado "
                "ou sem permissão."
            ), 404

        conexao.commit()

        return redirect(
            url_for("lancamentos")
        )

    except Error:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro ao excluir lançamento"
        )

        return (
            "Erro ao excluir lançamento."
        ), 500

    except Exception:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro inesperado ao excluir lançamento"
        )

        return (
            "Ocorreu um erro inesperado ao excluir o lançamento."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# METAS
# =========================================================

@app.route("/metas")
def metas():

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session["usuario_id"]

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor(
            dictionary=True
        )

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
            ORDER BY data_limite ASC
            """,
            (usuario_id,)
        )

        metas_lista = cursor.fetchall()

        for meta in metas_lista:

            valor_meta = float(
                meta["valor_meta"] or 0
            )

            valor_atual = float(
                meta["valor_atual"] or 0
            )

            if valor_meta > 0:

                porcentagem = (
                    valor_atual
                    /
                    valor_meta
                ) * 100

            else:

                porcentagem = 0

            meta["porcentagem"] = max(
                0,
                min(
                    100,
                    porcentagem
                )
            )

        return render_template(
            "metas.html",
            metas=metas_lista
        )

    except Error:

        app.logger.exception(
            "Erro ao carregar metas"
        )

        return (
            "Erro ao carregar metas."
        ), 500

    except Exception:

        app.logger.exception(
            "Erro inesperado ao carregar metas"
        )

        return (
            "Ocorreu um erro inesperado ao carregar as metas."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# NOVA META
# =========================================================

@app.route(
    "/nova-meta",
    methods=["GET", "POST"]
)
def nova_meta():

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        usuario_id = session[
            "usuario_id"
        ]

        titulo = request.form.get(
            "titulo",
            ""
        ).strip()

        valor_meta_str = request.form.get(
            "valor_meta",
            ""
        ).strip()

        prazo = request.form.get(
            "prazo",
            ""
        ).strip()

        valor_meta = converter_valor(
            valor_meta_str
        )

        if not titulo:

            return "Informe o nome da meta."

        if valor_meta is None or valor_meta <= 0:

            return "Informe um valor válido."

        # Validar prazo, se informado
        prazo_data = None

        if prazo:

            try:

                prazo_data = datetime.strptime(
                    prazo,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                return "Prazo inválido."

        conexao = None
        cursor = None

        try:

            conexao = conectar_banco()

            cursor = conexao.cursor()

            cursor.execute(
                """
                INSERT INTO metas
                (
                    usuario_id,
                    titulo,
                    valor_alvo,
                    valor_atual,
                    data_limite
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    usuario_id,
                    titulo,
                    valor_meta,
                    0,
                    prazo_data
                )
            )

            conexao.commit()

            return redirect(
                url_for("metas")
            )

        except Error:

            if conexao:
                conexao.rollback()

            app.logger.exception(
                "Erro ao criar meta"
            )

            return (
                "Erro ao criar meta."
            ), 500

        except Exception:

            if conexao:
                conexao.rollback()

            app.logger.exception(
                "Erro inesperado ao criar meta"
            )

            return (
                "Ocorreu um erro inesperado ao criar a meta."
            ), 500

        finally:

            fechar_banco(
                cursor,
                conexao
            )

    return render_template(
        "nova_meta.html"
    )


# =========================================================
# DEPOSITAR NA META
# =========================================================

@app.route(
    "/depositar-meta/<int:id>",
    methods=["POST"]
)
def depositar_meta(id):

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session[
        "usuario_id"
    ]

    valor_str = request.form.get(
        "valor",
        request.form.get(
            "valor_adicional",
            ""
        )
    )

    valor = converter_valor(
        valor_str
    )

    if valor is None or valor <= 0:

        return "Informe um valor válido."

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor()

        # Primeiro verifica se a meta existe
        cursor.execute(
            """
            SELECT id
            FROM metas
            WHERE id = %s
              AND usuario_id = %s
            """,
            (
                id,
                usuario_id
            )
        )

        meta = cursor.fetchone()

        if not meta:

            return (
                "Meta não encontrada "
                "ou sem permissão."
            ), 404

        cursor.execute(
            """
            UPDATE metas
            SET valor_atual =
                COALESCE(valor_atual, 0) + %s
            WHERE id = %s
              AND usuario_id = %s
            """,
            (
                valor,
                id,
                usuario_id
            )
        )

        conexao.commit()

        return redirect(
            url_for("metas")
        )

    except Error:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro ao depositar na meta"
        )

        return (
            "Erro ao depositar na meta."
        ), 500

    except Exception:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro inesperado ao depositar na meta"
        )

        return (
            "Ocorreu um erro inesperado ao depositar na meta."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# EXCLUIR META
# =========================================================

@app.route(
    "/excluir-meta/<int:id>",
    methods=["GET", "POST"]
)
def excluir_meta(id):

    if "usuario_id" not in session:

        return redirect(
            url_for("login")
        )

    usuario_id = session[
        "usuario_id"
    ]

    conexao = None
    cursor = None

    try:

        conexao = conectar_banco()

        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM metas
            WHERE id = %s
              AND usuario_id = %s
            """,
            (
                id,
                usuario_id
            )
        )

        if cursor.rowcount == 0:

            conexao.rollback()

            return (
                "Meta não encontrada "
                "ou sem permissão."
            ), 404

        conexao.commit()

        return redirect(
            url_for("metas")
        )

    except Error:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro ao excluir meta"
        )

        return (
            "Erro ao excluir meta."
        ), 500

    except Exception:

        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro inesperado ao excluir meta"
        )

        return (
            "Ocorreu um erro inesperado ao excluir a meta."
        ), 500

    finally:

        fechar_banco(
            cursor,
            conexao
        )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )