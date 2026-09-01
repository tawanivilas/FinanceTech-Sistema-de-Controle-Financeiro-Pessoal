from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# 1. A VARIÁVEL APP DEVE SER DEFINIDA AQUI NO INÍCIO:
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configurações de Cookie para evitar Erro 401 no GitHub Codespaces
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True


def conectar_banco():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="financetech",
        password="financetech123",
        database="financetech"
    )

def cadastrar_categorias_padrao(cursor, usuario_id):
    categorias = [
        ('Salário', 'receita', None),
        ('Investimento', 'receita', None),
        ('Outras Receitas', 'receita', None),
        ('Moradia (Água/Luz/Gás/Aluguel)', 'despesa', 'fixa'),
        ('Educação (Faculdade/Cursos)', 'despesa', 'fixa'),
        ('Saúde (Plano/Remédios)', 'despesa', 'fixa'),
        ('Transporte (Combustível/App)', 'despesa', 'variavel'),
        ('Lazer (Streaming/Passeios)', 'despesa', 'variavel'),
        ('Cartão de Crédito', 'despesa', 'variavel'),
        ('Financiamentos', 'despesa', 'temporaria'),
        ('Compras Parceladas', 'despesa', 'temporaria'),
        ('Empréstimos', 'despesa', 'temporaria')
    ]
    sql = "INSERT INTO categorias (nome, tipo, subtipo_despesa, usuario_id) VALUES (%s, %s, %s, %s)"
    cursor.executemany(sql, [(c[0], c[1], c[2], usuario_id) for c in categorias])

def obter_meses():
    return [
        {'codigo': '2026-01', 'nome': 'Janeiro / 2026'},
        {'codigo': '2026-02', 'nome': 'Fevereiro / 2026'},
        {'codigo': '2026-03', 'nome': 'Março / 2026'},
        {'codigo': '2026-04', 'nome': 'Abril / 2026'},
        {'codigo': '2026-05', 'nome': 'Maio / 2026'},
        {'codigo': '2026-06', 'nome': 'Junho / 2026'},
        {'codigo': '2026-07', 'nome': 'Julho / 2026'},
        {'codigo': '2026-08', 'nome': 'Agosto / 2026'},
        {'codigo': '2026-09', 'nome': 'Setembro / 2026'},
        {'codigo': '2026-10', 'nome': 'Outubro / 2026'},
        {'codigo': '2026-11', 'nome': 'Novembro / 2026'},
        {'codigo': '2026-12', 'nome': 'Dezembro / 2026'}
    ]

@app.route('/', strict_slashes=False)
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'], strict_slashes=False)
def login():
    if 'usuario_id' in session and request.method == 'GET':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        try:
            conexao = conectar_banco()
            cursor = conexao.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            usuario = cursor.fetchone()
            cursor.close()
            conexao.close()

            if usuario and check_password_hash(usuario['senha'], senha):
                session['usuario_id'] = usuario['id']
                session['usuario_nome'] = usuario['nome']
                return redirect(url_for('dashboard'))
            return "E-mail ou senha incorretos!"
        except mysql.connector.Error as erro:
            return f"Erro ao realizar login: {erro}"

    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'], strict_slashes=False)
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')

        if senha != confirmar_senha:
            return "As senhas não são iguais!"

        try:
            conexao = conectar_banco()
            cursor = conexao.cursor()
            senha_hash = generate_password_hash(senha)
            cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)", (nome, email, senha_hash))
            usuario_id = cursor.lastrowid
            cadastrar_categorias_padrao(cursor, usuario_id)
            conexao.commit()
            cursor.close()
            conexao.close()
            return redirect(url_for('login'))
        except mysql.connector.Error as erro:
            return f"Erro ao cadastrar: {erro}"

    return render_template('cadastro.html')

@app.route('/logout', strict_slashes=False)
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard', strict_slashes=False)
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    mes_selecionado = request.args.get('mes', datetime.now().strftime('%Y-%m'))

    try:
        ano, mes = map(int, mes_selecionado.split('-'))
    except ValueError:
        mes_selecionado = datetime.now().strftime('%Y-%m')
        ano, mes = map(int, mes_selecionado.split('-'))

    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = primeiro_dia + relativedelta(months=1) - relativedelta(days=1)

    conexao = conectar_banco()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM categorias WHERE usuario_id = %s ORDER BY tipo DESC, nome", (usuario_id,))
    categorias = cursor.fetchall()

    if not categorias:
        cursor_insert = conexao.cursor()
        cadastrar_categorias_padrao(cursor_insert, usuario_id)
        conexao.commit()
        cursor_insert.close()
        cursor.execute("SELECT * FROM categorias WHERE usuario_id = %s ORDER BY tipo DESC, nome", (usuario_id,))
        categorias = cursor.fetchall()

    sql = """
        SELECT t.*, c.nome AS categoria
        FROM transacoes t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id = %s
          AND (
            DATE_FORMAT(t.data_transacao, '%Y-%m') = %s
            OR (
                t.subtipo_despesa = 'temporaria'
                AND t.data_termino IS NOT NULL
                AND t.data_transacao <= %s
                AND t.data_termino >= %s
            )
          )
        ORDER BY t.data_transacao DESC, t.id DESC
    """
    cursor.execute(sql, (usuario_id, mes_selecionado, ultimo_dia, primeiro_dia))
    transacoes = cursor.fetchall()

    total_receitas = 0.0
    total_despesas = 0.0
    despesas_categoria_mes = {}

    for t in transacoes:
        valor = float(t['valor'])
        if t['tipo'] == 'receita':
            total_receitas += valor
        elif t['tipo'] == 'despesa':
            total_despesas += valor
            nome_cat = t['categoria'] or 'Outros'
            despesas_categoria_mes[nome_cat] = despesas_categoria_mes.get(nome_cat, 0.0) + valor

        if isinstance(t['data_transacao'], (datetime, date)):
            data_original = t['data_transacao']
            t['data_transacao'] = data_original.strftime('%Y-%m-%d')
        else:
            data_original = datetime.strptime(str(t['data_transacao'])[:10], '%Y-%m-%d').date()
            t['data_transacao'] = str(data_original)

        if t.get('categoria_id') is None:
            t['categoria_id'] = ""

        t['classificacao'] = t.get('subtipo_despesa') or ''

        if t['tipo'] == 'despesa' and t['subtipo_despesa'] == 'temporaria' and t['total_parcelas']:
            parcela_inicial = t['parcela_atual'] or 1
            total_parcelas = int(t['total_parcelas'])

            diferenca_meses = (ano - data_original.year) * 12 + (mes - data_original.month)
            parcela_exibida = parcela_inicial + diferenca_meses

            if parcela_exibida < 1:
                parcela_exibida = 1
            if parcela_exibida > total_parcelas:
                parcela_exibida = total_parcelas

            t['parcela_atual'] = parcela_exibida
            t['total_parcelas'] = total_parcelas
            t['parcelas_restantes'] = max(total_parcelas - parcela_exibida, 0)
        else:
            t['parcelas_restantes'] = None

    saldo_mes = total_receitas - total_despesas

    sql_ano = """
        SELECT t.valor, c.nome AS categoria
        FROM transacoes t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id = %s AND t.tipo = 'despesa'
          AND YEAR(t.data_transacao) = %s
    """
    cursor.execute(sql_ano, (usuario_id, ano))
    despesas_ano_raw = cursor.fetchall()

    despesas_categoria_ano = {}
    for d in despesas_ano_raw:
        cat_nome = d['categoria'] or 'Outros'
        despesas_categoria_ano[cat_nome] = despesas_categoria_ano.get(cat_nome, 0.0) + float(d['valor'])

    cursor.close()
    conexao.close()

    return render_template(
        'dashboard.html',
        usuario=session['usuario_nome'],
        transacoes=transacoes,
        categorias=categorias,
        meses=obter_meses(),
        mes_atual=mes_selecionado,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        saldo_mes=saldo_mes,
        despesas_cat_mes=despesas_categoria_mes,
        despesas_cat_ano=despesas_categoria_ano
    )

@app.route('/transacao/nova', methods=['POST'], strict_slashes=False)
def nova_transacao():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    descricao = request.form.get('descricao', '').strip()
    valor = float(request.form.get('valor', 0))
    tipo = request.form.get('tipo', 'despesa')
    categoria_id = request.form.get('categoria_id')
    data_transacao_str = request.form.get('data_transacao')

    if not data_transacao_str:
        return "Data da transação é obrigatória."

    data_transacao = datetime.strptime(data_transacao_str, '%Y-%m-%d').date()
    pago = 1 if 'pago' in request.form else 0
    classificacao = request.form.get('classificacao', 'fixa')

    if tipo != 'despesa':
        classificacao = None

    parcela_atual = None
    total_parcelas = None
    data_termino = None

    if tipo == 'despesa' and classificacao == 'temporaria':
        try:
            parcela_atual = int(request.form.get('parcela_atual', 1))
            total_parcelas = int(request.form.get('total_parcelas', 1))
        except ValueError:
            return "Número de parcelas inválido."

        if parcela_atual < 1:
            parcela_atual = 1
        if total_parcelas < 1:
            total_parcelas = 1
        if parcela_atual > total_parcelas:
            return "A parcela atual não pode ser maior que o total de parcelas."

        data_termino_str = request.form.get('data_termino')
        if data_termino_str:
            try:
                data_termino = datetime.strptime(data_termino_str, '%Y-%m-%d').date()
            except ValueError:
                return "Data de término inválida."
        else:
            parcelas_restantes = total_parcelas - parcela_atual
            data_termino = data_transacao + relativedelta(months=parcelas_restantes)

    usuario_id = session['usuario_id']

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        sql = """
            INSERT INTO transacoes
            (descricao, valor, tipo, subtipo_despesa, parcela_atual, total_parcelas, data_transacao, data_termino, pago, categoria_id, usuario_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            descricao, valor, tipo, classificacao,
            parcela_atual, total_parcelas, data_transacao, data_termino,
            pago, categoria_id if categoria_id else None, usuario_id
        ))
        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect(url_for('dashboard', mes=data_transacao.strftime('%Y-%m')))
    except mysql.connector.Error as erro:
        return f"Erro ao salvar transação: {erro}"

@app.route('/transacao/deletar/<int:id>', strict_slashes=False)
def deletar_transacao(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM transacoes WHERE id = %s AND usuario_id = %s", (id, session['usuario_id']))
        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect(url_for('dashboard', mes=mes))
    except mysql.connector.Error as erro:
        return f"Erro ao excluir transação: {erro}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)