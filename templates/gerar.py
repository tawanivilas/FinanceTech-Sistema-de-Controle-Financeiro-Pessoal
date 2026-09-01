content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>FinanceTech - Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, sans-serif; margin: 0; background-color: #f4f6f9; }
        .header { display: flex; justify-content: space-between; align-items: center; background: #333; color: #fff; padding: 12px 20px; }
        .header a { color: #ff6b6b; text-decoration: none; font-weight: bold; }
        
        .main-layout { display: flex; min-height: calc(100vh - 60px); }
        
        /* Menu Lateral de Meses */
        .sidebar { width: 220px; background: #fff; border-right: 1px solid #ddd; padding: 15px; }
        .sidebar h4 { margin-top: 0; color: #555; }
        .sidebar ul { list-style: none; padding: 0; margin: 0; }
        .sidebar li { margin-bottom: 8px; }
        .sidebar a { display: block; padding: 8px 12px; border-radius: 4px; color: #333; text-decoration: none; background: #f8f9fa; }
        .sidebar a:hover, .sidebar a.active { background: #007bff; color: white; font-weight: bold; }

        .content { flex: 1; padding: 20px; }
        .card-form { background: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .form-row { display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; }
        label { margin-bottom: 5px; font-weight: bold; font-size: 13px; }
        input, select, button { padding: 8px; border-radius: 4px; border: 1px solid #ccc; }
        button { background-color: #28a745; color: white; border: none; cursor: pointer; font-weight: bold; height: 36px; padding: 0 18px; }
        
        table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #f2f2f2; }
        
        .status-pago { color: #28a745; font-weight: bold; background: #e6f4ea; padding: 3px 8px; border-radius: 12px; font-size: 12px; }
        .status-pendente { color: #dc3545; font-weight: bold; background: #fce8e6; padding: 3px 8px; border-radius: 12px; font-size: 12px; }
        .btn-edit { background: #ffc107; color: #333; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; font-weight: bold; margin-right: 5px; border: none; cursor: pointer; }
        .btn-delete { background: #dc3545; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; font-weight: bold; }
        
        /* Modal de Edição */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; }
        .modal-content { background: white; padding: 20px; border-radius: 5px; width: 400px; }
    </style>
</head>
<body>

    <div class="header">
        <h2>FinanceTech</h2>
        <div>
            <span>Olá, <strong>{{ usuario }}</strong>!</span> | 
            <a href="/logout">Sair</a>
        </div>
    </div>

    <div class="main-layout">
        <!-- Menu Lateral: 12 Meses -->
        <div class="sidebar">
            <h4>📅 Consultar Mês</h4>
            <ul>
                {% for m in meses %}
                <li>
                    <a href="/dashboard?mes={{ m.codigo }}" class="{% if m.codigo == mes_atual %}active{% endif %}">
                        {{ m.nome }}
                    </a>
                </li>
                {% endfor %}
            </ul>
        </div>

        <!-- Conteúdo Principal -->
        <div class="content">
            <div class="card-form">
                <h3>Nova Transação (Mês {{ mes_atual }})</h3>
                <form action="/transacao/nova" method="POST">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Descrição</label>
                            <input type="text" name="descricao" required placeholder="Ex: Conta de Luz">
                        </div>
                        
                        <div class="form-group">
                            <label>Valor (R$)</label>
                            <input type="number" step="0.01" name="valor" required placeholder="150.00">
                        </div>

                        <div class="form-group">
                            <label>Tipo</label>
                            <select name="tipo" id="tipo" onchange="toggleCamposDespesa()" required>
                                <option value="despesa">Despesa</option>
                                <option value="receita">Receita</option>
                            </select>
                        </div>

                        <div class="form-group" id="group-subtipo">
                            <label>Classificação</label>
                            <select name="subtipo_despesa" id="subtipo_despesa" onchange="toggleCamposTemporarios()">
                                <option value="fixa">Fixa</option>
                                <option value="variavel">Variável</option>
                                <option value="temporaria">Temporária (Com Prazo)</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Categoria</label>
                            <select name="categoria_id" required>
                                {% for cat in categorias %}
                                    <option value="{{ cat.id }}">{{ cat.nome }}</option>
                                {% endfor %}
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Data</label>
                            <input type="date" name="data_transacao" required>
                        </div>

                        <div class="form-group" style="flex-direction: row; align-items: center; gap: 5px; height: 36px;">
                            <input type="checkbox" id="pago" name="pago" value="1" style="margin: 0;">
                            <label for="pago" style="margin: 0; cursor: pointer;">Pago</label>
                        </div>
                    </div>

                    <div class="form-row" id="group-temporarios" style="display: none; margin-top: 15px; padding-top: 15px; border-top: 1px dashed #ccc;">
                        <div class="form-group">
                            <label>Parcela Atual</label>
                            <input type="number" name="parcela_atual" min="1" value="1">
                        </div>
                        <div class="form-group">
                            <label>Total de Parcelas</label>
                            <input type="number" name="total_parcelas" min="1" value="1">
                        </div>
                    </div>

                    <div style="margin-top: 15px;">
                        <button type="submit">Salvar Transação</button>
                    </div>
                </form>
            </div>

            <!-- Tabela com Botão Editar e Status Pago -->
            <h3>Lançamentos de {{ mes_atual }}</h3>
            <table>
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Descrição</th>
                        <th>Categoria</th>
                        <th>Valor</th>
                        <th>Status</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {% for t in transacoes %}
                    <tr>
                        <td>{{ t.data_transacao }}</td>
                        <td>
                            <strong>{{ t.descricao }}</strong>
                            {% if t.subtipo_despesa %}
                                <br><small style="color: #666;">({{ t.subtipo_despesa.upper() }})</small>
                            {% endif %}
                        </td>
                        <td>{{ t.categoria or 'Sem categoria' }}</td>
                        <td style="color: {% if t.tipo == 'receita' %}green{% else %}red{% endif %}; font-weight: bold;">
                            R$ {{ "%.2f"|format(t.valor) }}
                        </td>
                        <td>
                            {% if t.pago %}
                                <span class="status-pago">✔ Pago</span>
                            {% else %}
                                <span class="status-pendente">⏳ Pendente</span>
                            {% endif %}
                        </td>
                        <td>
                            <button class="btn-edit" onclick="abrirModalEdicao({{ t.id }}, '{{ t.descricao }}', {{ t.valor }}, '{{ t.tipo }}', '{{ t.data_transacao }}', {{ t.categoria_id or 0 }}, {{ 1 if t.pago else 0 }})">Editar</button>
                            <a href="/transacao/deletar/{{ t.id }}?mes={{ mes_atual }}" class="btn-delete" onclick="return confirm('Excluir este lançamento?')">Excluir</a>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" style="text-align: center;">Nenhum lançamento neste mês.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Modal de Edição -->
    <div id="modalEdicao" class="modal">
        <div class="modal-content">
            <h3>Editar Transação</h3>
            <form id="formEdicao" method="POST">
                <div class="form-group" style="margin-bottom: 10px;">
                    <label>Descrição</label>
                    <input type="text" id="edit-descricao" name="descricao" required>
                </div>
                <div class="form-group" style="margin-bottom: 10px;">
                    <label>Valor (R$)</label>
                    <input type="number" step="0.01" id="edit-valor" name="valor" required>
                </div>
                <div class="form-group" style="margin-bottom: 10px;">
                    <label>Tipo</label>
                    <select id="edit-tipo" name="tipo" required>
                        <option value="despesa">Despesa</option>
                        <option value="receita">Receita</option>
                    </select>
                </div>
                <div class="form-group" style="margin-bottom: 10px;">
                    <label>Categoria</label>
                    <select id="edit-categoria" name="categoria_id">
                        {% for cat in categorias %}
                            <option value="{{ cat.id }}">{{ cat.nome }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group" style="margin-bottom: 10px;">
                    <label>Data</label>
                    <input type="date" id="edit-data" name="data_transacao" required>
                </div>
                <div class="form-group" style="flex-direction: row; gap: 10px; margin-bottom: 15px;">
                    <input type="checkbox" id="edit-pago" name="pago" value="1">
                    <label for="edit-pago">Pago</label>
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button type="button" onclick="fecharModal()" style="background: #6c757d;">Cancelar</button>
                    <button type="submit">Salvar Alterações</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        function toggleCamposDespesa() {
            const tipo = document.getElementById('tipo').value;
            const groupSubtipo = document.getElementById('group-subtipo');
            const groupTemporarios = document.getElementById('group-temporarios');
            if (tipo === 'receita') {
                groupSubtipo.style.display = 'none';
                groupTemporarios.style.display = 'none';
            } else {
                groupSubtipo.style.display = 'flex';
                toggleCamposTemporarios();
            }
        }

        function toggleCamposTemporarios() {
            const subtipo = document.getElementById('subtipo_despesa').value;
            const groupTemporarios = document.getElementById('group-temporarios');
            groupTemporarios.style.display = (subtipo === 'temporaria') ? 'flex' : 'none';
        }

        function abrirModalEdicao(id, descricao, valor, tipo, data, categoriaId, pago) {
            document.getElementById('formEdicao').action = '/transacao/editar/' + id;
            document.getElementById('edit-descricao').value = descricao;
            document.getElementById('edit-valor').value = valor;
            document.getElementById('edit-tipo').value = tipo;
            document.getElementById('edit-data').value = data;
            document.getElementById('edit-categoria').value = categoriaId;
            document.getElementById('edit-pago').checked = (pago === 1);
            document.getElementById('modalEdicao').style.display = 'flex';
        }

        function fecharModal() {
            document.getElementById('modalEdicao').style.display = 'none';
        }
    </script>
</body>
</html>"""

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Sucesso!")