import streamlit as st
import pandas as pd

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
    
    return df

# Carregamento inicial dos dados
try:
    df_cartorios = carregar_cadastro()
    df_financeiro_completo = carregar_e_limpar_financeiro()
except Exception as e:
    st.error(f"Erro ao carregar ou processar os arquivos: {e}")
    st.stop()

# Barra lateral onde seleciona os Estados
st.sidebar.header("Encontre um Cartório")
estado_selecionado = st.sidebar.selectbox("1. Selecione o Estado:", sorted(df_cartorios["UF"].unique()))
cidades_no_estado = sorted(df_cartorios[df_cartorios["UF"] == estado_selecionado]["Cidade"].unique())
cidade_selecionada = st.sidebar.selectbox("2. Selecione a Cidade:", cidades_no_estado)
cartorios_na_cidade = df_cartorios[df_cartorios["Cidade"] == cidade_selecionada]
cartorio_selecionado_nome = st.sidebar.selectbox("3. Selecione o Cartório:", cartorios_na_cidade["Denominação"].unique())

st.title("🔎 Painel de Análise de Serventias Extrajudiciais")
st.markdown("Use os filtros para selecionar um cartório e visualizar sua análise financeira individual.")

# Se nenhum cartório for selecionado, mostra um aviso
if not cartorio_selecionado_nome:
    st.warning("Por favor, selecione um cartório na barra lateral para começar a análise.")
else:
    # Mostra as informações do cartório selecionado
    info_cartorio = df_cartorios[df_cartorios["Denominação"] == cartorio_selecionado_nome].iloc[0]
    st.header(f"Informações de: {info_cartorio['Denominação']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Cidade", info_cartorio['Cidade'])
    col2.metric("Status", info_cartorio['Status'])
    col3.metric("Tipo", info_cartorio['Tipo'])

    st.markdown("---")
    st.header("Análise Financeira do Cartório Selecionado")

    # 1. Encontra o CNS do cartório selecionado
    cns_selecionado = info_cartorio['CNS']
    
    # 2. Filtra o DataFrame financeiro para conter apenas os dados daquele CNS
    df_financeiro_filtrado = df_financeiro_completo[df_financeiro_completo['CNS'] == cns_selecionado]
    
    # 3. Agrega os dados filtrados por mês
    if not df_financeiro_filtrado.empty:
        df_filtrado_agregado = df_financeiro_filtrado.set_index('Dat. início do período')['Valor arrecadação'].resample('M').sum().reset_index()
        df_filtrado_agregado.rename(columns={'Dat. início do período': 'Mês'}, inplace=True)
    else:
        df_filtrado_agregado = pd.DataFrame()
    
    if not df_filtrado_agregado.empty and len(df_filtrado_agregado) >= 2:
        ultimo_valor = df_filtrado_agregado['Valor arrecadação'].iloc[-1]
        penultimo_valor = df_filtrado_agregado['Valor arrecadação'].iloc[-2]
        variacao = ultimo_valor - penultimo_valor
        
        st.metric(
            label=f"Arrecadação em {df_filtrado_agregado['Mês'].iloc[-1].strftime('%m/%Y')}",
            value=f"R$ {ultimo_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            delta=f"R$ {variacao:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            help="Variação em relação ao mês anterior."
        )
    else:
        st.warning("Não há dados financeiros suficientes para este cartório para calcular a variação.")

    st.subheader("Evolução da Arrecadação Mensal")
    if not df_filtrado_agregado.empty:
        st.line_chart(df_filtrado_agregado.set_index('Mês')['Valor arrecadação'])
    else:
        st.warning("Não foram encontrados dados de arrecadação para o cartório selecionado.")
        
    st.subheader("Dados Detalhados (do Cartório Selecionado)")
    st.dataframe(df_financeiro_filtrado)