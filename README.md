# 💰 FinanceTech – Sistema de Controle Financeiro Pessoal

##  Sobre o Projeto

O **FinanceTech – Sistema de Controle Financeiro Pessoal** é uma aplicação web desenvolvida para a disciplina de **Produto de Software**.

O sistema tem como objetivo auxiliar o usuário na **organização, acompanhamento e gestão de sua vida financeira**, permitindo registrar receitas e despesas, organizar lançamentos por categorias, acompanhar indicadores financeiros e definir metas pessoais.

A aplicação possui uma interface web responsiva, autenticação de usuários, gerenciamento de lançamentos financeiros, gráficos para análise dos gastos e acompanhamento do progresso de metas.

---

## 🎯 Objetivos do Sistema

O FinanceTech foi desenvolvido com os seguintes objetivos:

* Facilitar o controle das finanças pessoais;
* Centralizar receitas e despesas em um único sistema;
* Organizar despesas por categorias;
* Permitir o acompanhamento do saldo financeiro;
* Facilitar a consulta do histórico de movimentações;
* Apresentar informações financeiras por meio de gráficos;
* Permitir a criação e acompanhamento de metas financeiras;
* Registrar aportes realizados nas metas;
* Oferecer uma interface simples e intuitiva para o usuário.

---

# 🚀 Funcionalidades

O desenvolvimento do FinanceTech foi dividido em quatro entregas contínuas (**Avaliações Continuadas – ACs**).

## 🔹 AC1 – Autenticação e Entradas

* [x] **Criar Conta**

  * Cadastro de novos usuários;
  * Validação dos dados informados;
  * Armazenamento seguro das senhas.

* [x] **Fazer Login**

  * Autenticação de usuários cadastrados;
  * Controle de sessão;
  * Proteção das áreas internas do sistema.

* [x] **Registrar Receitas**

  * Cadastro de entradas financeiras;
  * Descrição da receita;
  * Valor;
  * Data do lançamento.

---

## 🔹 AC2 – Saídas e Categorização

* [x] **Registrar Despesas**

  * Cadastro de saídas financeiras;
  * Descrição;
  * Valor;
  * Data;
  * Categoria.

* [x] **Organizar Despesas por Categoria**

  * Associação de despesas às categorias;
  * Organização dos gastos;
  * Facilitação da análise financeira.

---

## 🔹 AC3 – Gerenciamento de Lançamentos

* [x] **Editar Lançamentos**

  * Alteração de receitas e despesas;
  * Atualização de valores;
  * Alteração de datas;
  * Alteração de descrições e categorias.

* [x] **Excluir Lançamentos**

  * Exclusão de registros financeiros;
  * Atualização automática dos indicadores financeiros.

---

## 🔹 AC4 – Painel de Controle, Gráficos e Metas

* [x] **Consultar Movimentações**

  * Visualização do histórico de lançamentos;
  * Consulta de receitas e despesas;
  * Filtros para facilitar a localização dos registros.

* [x] **Acompanhar Indicadores**

  * Total de receitas;
  * Total de despesas;
  * Saldo atual;
  * Atualização dos valores conforme os lançamentos.

* [x] **Análise Gráfica**

  * Visualização dos gastos por categoria;
  * Representação gráfica das movimentações;
  * Auxílio na identificação dos principais gastos.

* [x] **Filtros**

  * Filtro por período;
  * Filtro por categoria;
  * Filtro por tipo de lançamento.

* [x] **Metas Financeiras**

  * Cadastro de metas pessoais;
  * Definição de valor-alvo;
  * Acompanhamento do valor acumulado;
  * Cálculo do progresso em porcentagem.

* [x] **Aportes**

  * Registro de valores destinados às metas;
  * Atualização do progresso da meta;
  * Acompanhamento do valor acumulado.

---

# 🖥️ Principais Telas

O sistema possui as seguintes telas principais:

### 🔐 1. Login e Cadastro

Área responsável pela autenticação dos usuários.

O usuário pode criar sua conta e posteriormente acessar o sistema utilizando suas credenciais.

### 📊 2. Dashboard

Painel principal do Finance Tech.

Apresenta:

* Total de receitas;
* Total de despesas;
* Saldo atual;
* Gráficos;
* Informações sobre lançamentos recentes;
* Resumo da situação financeira.

### 💰 3. Lançamentos

Tela destinada ao gerenciamento das movimentações financeiras.

Permite:

* Cadastrar receitas
* Cadastrar despesas
* Editar lançamentos
* Excluir lançamentos
* Consultar histórico
* Aplicar filtros.

### 🎯 4. Metas Financeiras

Tela destinada ao acompanhamento dos objetivos financeiros.

Permite:

* Criar uma meta
* Definir valor-alvo
* Registrar aportes
* Visualizar valor acumulado
* Acompanhar o percentual de progresso.

---

# 🛠️ Tecnologias Utilizadas

## Backend

* **Python**
* **Flask**
* **Werkzeug**

## Frontend

* **HTML5**
* **CSS3**
* **JavaScript**
* **Bootstrap 5**
* **FontAwesome**
* **Jinja2**

## Banco de Dados

* **TiDB Cloud**
* Compatibilidade com **MySQL**
* **MySQL Connector/Python**

## Deploy

* **Render**

## Controle de Versão

* **Git**
* **GitHub**

---

# 🏗️ Arquitetura do Projeto

O FinanceTech utiliza uma arquitetura baseada na separação entre interface, aplicação e banco de dados.

```text
┌─────────────────────────────┐
│          FRONTEND           │
│                             │
│ HTML + CSS + JavaScript     │
│ Bootstrap + FontAwesome     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│           BACKEND           │
│                             │
│ Python + Flask              │
│ Rotas + Regras de negócio   │
│ Autenticação + Sessões      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        BANCO DE DADOS       │
│                             │
│ TiDB Cloud / MySQL          │
│ Usuários + Lançamentos      │
│ Categorias + Metas          │
└─────────────────────────────┘
```

---

# 📂 Estrutura do Projeto

A estrutura principal do projeto segue o padrão de uma aplicação Flask:

```text
FinanceTech-Sistema-de-Controle-Financeiro-Pessoal/
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── cadastro.html
│   ├── dashboard.html
│   ├── lancamentos.html
│   └── metas.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   ├── js/
│   │   └── script.js
│   │
│   └── img/
│
└── ...
```

---

# 🗄️ Banco de Dados

O sistema utiliza um banco de dados relacional compatível com MySQL.

Entre os principais dados armazenados estão:

### Usuários

Responsáveis pelo acesso ao sistema.

Principais informações:

* ID;
* Nome;
* E-mail;
* Senha;
* Data de cadastro.

### Categorias

Utilizadas para organizar os lançamentos financeiros.

### Transações

Armazenam as receitas e despesas registradas pelo usuário.

Entre as informações estão:

* Descrição;
* Valor;
* Tipo;
* Data;
* Categoria;
* Usuário responsável.

### Metas

Armazenam os objetivos financeiros cadastrados pelo usuário.

As metas possuem informações como:

* Nome da meta;
* Valor-alvo;
* Valor acumulado;
* Progresso;
* Aportes realizados.

---

# 🌐 Acesso ao Projeto

### 💻 GitHub

**Repositório:**

https://github.com/tawanivilas/FinanceTech-Sistema-de-Controle-Financeiro-Pessoal

### 🚀 Sistema Online

**Aplicação publicada:**

https://financetech-sistema-de-controle.onrender.com

#

---

# 📈 Evolução do Produto

O desenvolvimento foi realizado de forma incremental, permitindo que cada AC adicionasse novas funcionalidades ao sistema.

```text
AC1
│
├── Cadastro
├── Login
└── Receitas
      │
      ▼
AC2
│
├── Despesas
└── Categorias
      │
      ▼
AC3
│
├── Editar
└── Excluir
      │
      ▼
AC4
│
├── Dashboard
├── Indicadores
├── Gráficos
├── Filtros
├── Metas
└── Aportes
```

#

---

# 👨‍💻 Projeto

**FinanceTech – Sistema de Controle Financeiro Pessoal**

Desenvolvido para a disciplina de **Produto de Software**.

**Tecnologias principais:**

`Python` · `Flask` · `HTML` · `CSS` · `JavaScript` · `Bootstrap` · `MySQL/TiDB Cloud` · `Render` · `GitHub`

---

## 📌 Status do Projeto

**Projeto concluído**, contemplando as funcionalidades planejadas para as quatro avaliações continuadas:

* ✅ AC1 – Autenticação e Entradas
* ✅ AC2 – Saídas e Categorização
* ✅ AC3 – Gerenciamento de Lançamentos
* ✅ AC4 – Dashboard, Gráficos e Metas





