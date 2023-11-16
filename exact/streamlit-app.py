# Back-end:
from datetime import datetime as dt
from io import StringIO
from json import loads
# import pendulum as pdl
import pandas as pd
import requests
import warnings
import warnings
import json

# Suppress all warnings
warnings.filterwarnings('ignore')

# Dataviz
import streamlit as st
import plotly.express as px
from plotly import graph_objects as go
import matplotlib.pyplot as plt


# Token
base_url = "https://api.exactspotter.com/v3/Leads"


headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "token_exact":  st.secrets["token"], # Secrets using streamlit
}

params = {"$orderby": "registerDate desc"}

response = requests.get(base_url, headers=headers, params=params)

def process_response(response):
    if response.status_code == 200:
        # data = loads(response.content.decode("utf-8"))["value"]
        # # st.dataframe(data)  # Exibir o DataFrame no Streamlit
        # return data  # Return data if the status code is 200
        json_data = json.loads(response.content.decode("utf-8"))
        value = json_data.get('value')  # Access the 'value' key from the decoded JSON
        return value
    else:
        st.error(f"Erro na solicitação: {response.status_code}")

data = process_response(response)

df = pd.DataFrame(data)

columns = [
    "registerDate",
    "updateDate",
    "lead",
    "phone1",
    "leadProduct",
    "id",
    "stage",
    "cnpj",
    "state",
    "country",
    "website",
    "source",
    "publicLink"
]

# Rename the columns
df = df[columns]

def convert_datetime(df, column):
    df[column] = pd.to_datetime(df[column])
    df[column] = df[column].dt.tz_localize(None)  # Remove the timezone
    df[column] = df[column].dt.strftime("%Y-%m-%d %I:%M:%S %p")
    df[column] = pd.to_datetime(df[column])

convert_datetime(df, "updateDate")
convert_datetime(df, "registerDate")

# date_format = '%Y-%m-%d'
# df['updateDate'] = df['updateDate'].apply(lambda x: dt.strptime(x.split('T')[0],date_format))
# df['registerDate'] = df['registerDate'].apply(lambda x: dt.strptime(x.split('T')[0],date_format))

# Get the current date and time
current_date = pdl.now('America/Sao_Paulo')

# Calculate the difference in days
df["Dias"] = (current_date - df["updateDate"]).dt.days

# Extract the month from the "updateDate" column
df["Mes"] = df["updateDate"].dt.month_name()

dict_rename = {
    "registerDate": "DataRegistro",
    "updateDate": "DataAtualizacao",
    "lead": "Lead",
    "phone1": "Telefone",
    "leadProduct": "Produto",
    "id": "ID",
    "stage": "Etapa",
    "cnpj": "CNPJ",
    "state": "Estado",
    "country": "Pais",
    "website": "Site",
    "source": "Origem",
    "publicLink": "LinkPublico",
}

# Rename the columns
df = df.rename(columns=dict_rename)

# Reorder the columns
order = ['Dias', 'Mes', 'Origem', 'Lead', 'Telefone', 'Produto', 'ID',
         'Etapa', 'CNPJ', 'Estado', 'Pais', 'Site', 'LinkPublico', 'DataRegistro', 'DataAtualizacao']

df = df[order]

df.dropna(subset = ['DataRegistro', 'Lead'], inplace = True)

# Handling the missing values and converting the data types
def fillna(df, column):
    df[column] = df[column].str.replace(' ', '')
    df[column] = df[column].str.replace(' ', '')
    df[column] = df[column].fillna("VAZIO").astype(str)

fillna(df, "Telefone")
fillna(df, "Estado")
fillna(df, "Produto")
fillna(df, "Pais")
fillna(df, "Site")
fillna(df, "CNPJ")

# Convert the columns to string
df["ID"] = df["ID"].astype(str)
df['Lead'] = df['Lead'].str.upper().astype(str)
df['Origem'] = df['Origem'].str['value'].astype(str)

# Streamlit ----------------------------------------------------------------------------------------- > Construction

st. set_page_config(layout="wide") # Layout wide

st.header('🔁 COSMEFAR CRM - Exact Spotted', divider='gray')
st.subheader('Leads')

# function to cleanup the fields of the multiselect widget
def clear_multi():
    st.session_state.stage = []
    st.session_state.month = []
    st.session_state.sources = []
    return

with st.sidebar:
    st.title('Filtros')
    stage = st.sidebar.multiselect('Selecione a etapa', df['Etapa'].unique(), placeholder="Escolha uma opção", key="stage") # filter by etapa
    month = st.sidebar.multiselect('Selecione o mês', df['Mes'].unique(), placeholder="Escolha uma opção", key="month") # filter by mes
    source = st.sidebar.multiselect('Selecione a origem', df['Origem'].unique(), placeholder="Escolha uma opção", key="source") # filter by origem
    filters = st.sidebar.button('Filtrar')  # button to filter
    clear_filters = st.sidebar.button('Limpar Filtros', on_click=clear_multi)  # button to clean filters
    # st.session_state # verificando o estado da session
    st.link_button("Ir para a Exact", "https://www.exactsales.com.br/prelogin.html")

filtered_df = df # Dataframe for manipulation

if stage and month and source:
    filtered_df = df[df['Etapa'].isin(stage) & df['Mes'].isin(month) & df['Origem'].isin(source)]
elif stage and month:
    filtered_df = df[df['Etapa'].isin(stage) & df['Mes'].isin(month)]
elif stage and source:
    filtered_df = df[df['Etapa'].isin(stage) & df['Origem'].isin(source)]
elif month and source:
    filtered_df = df[df['Mes'].isin(month) & df['Origem'].isin(source)]
elif stage:
    filtered_df = df[df['Etapa'].isin(stage)]
elif month:
    filtered_df = df[df['Mes'].isin(month)]
elif source:
    filtered_df = df[df['Origem'].isin(source)]
else:
    filtered_df = df.copy()

# Reset the filters
if clear_filters:
    stage = []
    month = []
    source = []
    filtered_df = df

# Function to color the rows
def color_rows(val):
    if val <= 3:
        return 'background-color: green'
    elif val > 3 and val < 7:
        return 'background-color: yellow'
    elif val >= 7:
        return 'background-color: red'
    else:
        return ""

# Ploting the DataFrame

st.dataframe(filtered_df.style.map(color_rows, subset=['Dias']))


stage_order = [
    'Entrada',
    'Em contato',
    'Aprovado F2',
    'Reunião SDR',
    'Qualificados',
    'Reunião Vendas',
    'Negociação',
    'Descartado'
]

# Convert the 'Mes' column to a categorical data type with the custom sort order
filtered_df['Etapa'] = pd.Categorical(filtered_df['Etapa'], categories=stage_order, ordered=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader('Média de dias por etapa')
    etapa_media = filtered_df[['Dias', 'Etapa']].groupby(
        'Etapa').mean().sort_values('Dias', ascending=False).round(0)
    st.bar_chart(etapa_media)

with col4:
    st.subheader('Quantidade de leads por etapa')
    etapa_count = filtered_df[['ID', 'Etapa']].groupby(
        'Etapa').nunique().sort_values('ID', ascending=False).round(0)
    st.bar_chart(etapa_count)

month_order = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

# Convert the 'Mes' column to a categorical data type with the custom sort order
filtered_df['Mes'] = pd.Categorical(filtered_df['Mes'], categories=month_order, ordered=True)

col1, col2 = st.columns(2)

with col2:
    st.subheader('Quantidade de Leads por mês')
    mes_count = filtered_df[['Etapa', 'Mes']].groupby(
        'Mes').count().sort_values('Mes', ascending=False).round(0)
    st.bar_chart(mes_count)

with col1:
    st.subheader('Quantidade de Leads por origem')
    origem_count = filtered_df[['ID', 'Origem']].groupby(
        'Origem').count().sort_values('ID', ascending=False).round(0)
    st.bar_chart(origem_count)
