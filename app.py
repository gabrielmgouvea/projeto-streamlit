import streamlit as st
import pandas as pd
import plotly.express as px

# Configs iniciais da página
st.set_page_config(
    page_title="Dashboard de Cartórios",
    layout="wide"
)

# Função pra carregar os dados de cadastro
@st.cache_data
def carregar_cadastro():
    """Carrega a lista completa de cartórios."""
    df = pd.read_csv("cadastro_cartorios.csv")
    return df

@st.cache_data
def carregar_e_limpar_financeiro():
    df = pd.read_csv("dados_financeiros.csv")

    # Limpeza dos dados
    coluna_valores = df['Valor arrecadação'].astype(str).str.strip()
    coluna_valores = coluna_valores.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['Valor arrecadação'] = pd.to_numeric(coluna_valores, errors='coerce')
    df['Dat. início do período'] = pd.to_datetime(df['Dat. início do período'], format='%d/%m/%Y', errors='coerce')
    
    # Remove qualquer linha que tenha falhado na conversão
    df.dropna(subset=['Valor arrecadação', 'Dat. início do período'], inplace=True)
    
    df = df[df['Valor arrecadação'] > 0]
    
    return df

# Carregamento inicial dos dados
try:
    df_cartorios = carregar_cadastro()
    df_financeiro_completo = carregar_e_limpar_financeiro()
except Exception as e:
    st.error(f"Erro ao carregar ou processar os arquivos: {e}")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.header("Configurações de Análise")

# 1. Seleção de Estado (Sempre obrigatória para filtrar o financeiro corretamente)
ufs_disponiveis = sorted(df_cartorios["UF"].unique())
estado_selecionado = st.sidebar.selectbox("1. Selecione o Estado:", ufs_disponiveis)

# 2. Pergunta se você quer ver um específico ou o geral
modo_analise = st.sidebar.radio(
    "Nível de Detalhe:",
    ("Visão Geral do Estado", "Cartório Específico")
)

cartorio_selecionado_nome = None
cns_para_analise = []

if modo_analise == "Cartório Específico":
    # Lógica antiga de selecionar cidade e nome
    cidades_no_estado = sorted(df_cartorios[df_cartorios["UF"] == estado_selecionado]["Cidade"].unique())
    cidade_selecionada = st.sidebar.selectbox("2. Selecione a Cidade:", cidades_no_estado)
    
    cartorios_na_cidade = df_cartorios[df_cartorios["Cidade"] == cidade_selecionada]
    cartorio_selecionado_nome = st.sidebar.selectbox("3. Selecione o Cartório:", cartorios_na_cidade["Denominação"].unique())
    
    if cartorio_selecionado_nome:
        info_cartorio = df_cartorios[df_cartorios["Denominação"] == cartorio_selecionado_nome].iloc[0]
        cns_para_analise = [info_cartorio['CNS']]
else:
    cns_para_analise = df_cartorios[df_cartorios["UF"] == estado_selecionado]['CNS'].unique().tolist()
    st.sidebar.info(f"Analisando dados agregados de {len(cns_para_analise)} cartórios em {estado_selecionado}.")


st.title(f"📊 Painel de Análise - {estado_selecionado}")

# Lógica de Exibição
if modo_analise == "Cartório Específico" and not cartorio_selecionado_nome:
    st.warning("Por favor, selecione um cartório na barra lateral.")
    st.stop()

# Se for cartório específico, mostra os cards de detalhes
if modo_analise == "Cartório Específico" and cartorio_selecionado_nome:
    st.header(f"Detalhes: {info_cartorio['Denominação']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Cidade", info_cartorio['Cidade'])
    col2.metric("Status", info_cartorio['Status'])
    col3.metric("Tipo", info_cartorio['Tipo'])
    st.markdown("---")

# 1. Filtra o financeiro baseando-se na lista de CNS (seja 1 ou seja 1000)
df_financeiro_filtrado = df_financeiro_completo[df_financeiro_completo['CNS'].isin(cns_para_analise)]

# 2. Agrega os dados por mês
if not df_financeiro_filtrado.empty:
    df_filtrado_agregado = df_financeiro_filtrado.groupby('Dat. início do período')['Valor arrecadação'].sum().reset_index()
    df_filtrado_agregado.rename(columns={'Dat. início do período': 'Mês'}, inplace=True)
else:
    df_filtrado_agregado = pd.DataFrame()

titulo_secao = "Análise Financeira Global" if modo_analise == "Visão Geral do Estado" else "Análise Financeira Individual"
st.header(titulo_secao)

if not df_filtrado_agregado.empty and len(df_filtrado_agregado) >= 1:
    
    # Cálculo de Variação (Último mês vs Penúltimo)
    ultimo_valor = df_filtrado_agregado['Valor arrecadação'].iloc[-1]
    
    if len(df_filtrado_agregado) >= 2:
        penultimo_valor = df_filtrado_agregado['Valor arrecadação'].iloc[-2]
        variacao = ultimo_valor - penultimo_valor
        delta_val = f"R$ {variacao:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        delta_val = None

    # Formatação BR para exibir
    valor_formatado = f"R$ {ultimo_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    col_metrica, col_vazia = st.columns([1, 2])
    col_metrica.metric(
        label=f"Arrecadação Total em {df_filtrado_agregado['Mês'].iloc[-1].strftime('%m/%Y')}",
        value=valor_formatado,
        delta=delta_val,
        help="Comparação com o mês anterior"
    )

    st.subheader("Evolução da Arrecadação Mensal")
    st.subheader("Evolução da Arrecadação Mensal")
    
    fig = px.line(
        df_filtrado_agregado, 
        x='Mês', 
        y='Valor arrecadação',
        title='Histórico de Arrecadação',
        markers=True # Adiciona bolinhas nos meses
    )
    # Formata o eixo Y para mostrar "R$"
    fig.update_layout(yaxis_tickprefix = 'R$ ')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Se quiser ver os dados brutos
    with st.expander("Ver dados detalhados em tabela"):
        if modo_analise == "Visão Geral do Estado":
             st.dataframe(df_filtrado_agregado) # Mostra o resumão por mês
        else:
             st.dataframe(df_financeiro_filtrado) # Mostra linha a linha do cartório

else:
    st.warning("Não foram encontrados dados financeiros suficientes para os filtros selecionados.")