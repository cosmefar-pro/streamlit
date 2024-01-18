from datetime import datetime as datetime
from pandas import DataFrame
import pandas as pd
import requests
from json import loads
import streamlit as st
import requests
import pendulum as pdl
from json import loads
import json
import warnings

# Suppress all warnings
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide") # Layout wide

# Token
exact_api_token = st.secrets["auth_token"]
exact_endpoint = "https://api.exactspotter.com/v3/Leads"

@st.cache_data
def api_call(endpoint: str, api_token: str, skip_value: int = 0):

    query_params = {
        '$skip': skip_value,
        '$filter': "registerDate ge 2023-01-01T00:00:00.0000000Z and registerDate le 2024-01-17T23:59:59.9999999Z",
        '$orderby': "registerDate desc"
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "token_exact": api_token,
    }

    response = requests.get(endpoint, headers=headers, params=query_params)

    json_file = loads(response.content.decode('latin-1'))['value']
    
    return json_file

def convert_and_parse(json_file, existing_dataframe=None) -> DataFrame:
    df = pd.DataFrame(json_file)

    df.dropna(subset=['registerDate', 'lead'], inplace=True)
    
    df['registerDate'] = df['registerDate'].apply(
        lambda x: datetime.strptime(x.split('T')[0], '%Y-%m-%d')
    )

    df['sdr_name'] = df.apply(extract_sdr_info, axis=1)
    df['salesrep_name'] = df.apply(extract_salesrep_info, axis=1)
    df['source'] = df.apply(extract_source_info, axis=1)

    dataframe = df[['id', 'lead', 'phone1',
                            'website', 'leadProduct', 'stage', 'source', 'cnpj',
                            'state', 'publicLink', 'country', 'sdr_name', 'salesrep_name', 'registerDate', 'updateDate']]

    if existing_dataframe is not None:
        existing_dataframe = pd.concat([existing_dataframe, dataframe], ignore_index=True)
        return existing_dataframe
    else:
        return dataframe

def extract_sdr_info(lead):
    sdr_info = lead.get("sdr", {})
    sdr_name = sdr_info.get("name", "")
    sdr_lastName = sdr_info.get("lastName", "")
    return f"{sdr_name} {sdr_lastName}"

def extract_salesrep_info(lead):
    salesrep_info = lead.get("salesRep", {})
    salesrep_name = salesrep_info.get("name", "")
    salesrep_lastName = salesrep_info.get("lastName", "")
    return f"{salesrep_name} {salesrep_lastName}"

def extract_source_info(lead):
    source_info = lead.get("source", {})
    source = source_info.get("value", "")
    return source

if __name__ == "__main__":
    skip_value = 0
    total_records = 0
    all_data = None

    while True:
        json_data = api_call(exact_endpoint, exact_api_token, skip_value)

        # Break out of the loop if no more records
        if not json_data:
            break

        all_data = convert_and_parse(json_data, all_data)

        # Update skip_value for the next iteration
        skip_value += 500
        total_records += len(json_data)

    # Save the entire DataFrame to a CSV file
    # all_data.to_csv("dados_test_all.csv", index=False)

    # print(f"Total records processed: {total_records}")
    df = pd.DataFrame(data=all_data)

    def convert_datetime(df, column):
        df[column] = pd.to_datetime(df[column])
        df[column] = df[column].dt.tz_localize(None)  # Remove the timezone
        df[column] = df[column].dt.strftime("%Y-%m-%d %I:%M:%S %p")
        df[column] = pd.to_datetime(df[column])

    convert_datetime(df, "updateDate")
    convert_datetime(df, "registerDate")

    # Get the current date and time with timezone information
    
    current_date = datetime.now() # Horário de Brasília

    # Convert the "updateDate" column to a tz-aware datetime, assuming it's in UTC
    df["updateDate"] = pd.to_datetime(df["updateDate"])
    df["registerDate"] = pd.to_datetime(df["registerDate"])

    # Calculate the difference in days
    df["Diff"] = (current_date - df["updateDate"]).dt.days

    # Extract the month from the "updateDate" column
    df["Mes"] = df["updateDate"].dt.month_name()
    df["Ano"] = df["updateDate"].dt.year

    dict_rename = {
    "registerDate": "Registrado",
    "updateDate": "Atualizado",
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
    "publicLink": "Link",
    "sdr_name": 'SDR',
    "salesrep_name": 'Sales'
    }

    # Rename the columns
    df = df.rename(columns=dict_rename)

    order = ['Origem', 'Lead', 'Telefone', 'Produto', 'ID',
         'Etapa', 'CNPJ', 'Estado', 'Pais', 'Site', 'Link', 'SDR', 'Sales', 'Diff', 'Mes', 'Ano', 'Registrado', 'Atualizado']

    df = df[order]

    # Streamlit ----------------------------------------------------------------------------------------- > Construction

    st.header('🔁 COSMEFAR CRM - Exact Spotted', divider='gray')
    st.subheader('Leads')

    # function to cleanup the fields of the multiselect widget
    def clear_multi():
        st.session_state.stage = []
        st.session_state.month = []
        st.session_state.year = []
        st.session_state.sdr = []
        return

    month_order = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    with st.sidebar:
        st.title('Filtros')
    

        # Adicione um novo filtro para pré-vendedora
        selected_sdr = st.selectbox('Selecione o pré-vendedor', df['SDR'].unique(), placeholder="Selecione", key="selected_sdr", index=None)

        # Use a pré-vendedora selecionada para filtrar as opções nos outros filtros
        filtered_stage_options = df[df['SDR'] == selected_sdr]['Etapa'].unique()
        filtered_month_options = df[df['SDR'] == selected_sdr]['Mes'].unique()
        filtered_year_options = df[df['SDR'] == selected_sdr]['Ano'].unique()

        stage = st.multiselect('Selecione a etapa', filtered_stage_options, placeholder="Escolha uma opção", key="stage")
        month = st.multiselect('Selecione o mês', filtered_month_options, placeholder="Escolha uma opção", key="month")
        year = st.multiselect('Selecione o ano', filtered_year_options, placeholder="Escolha uma opção", key="year")

        filters = st.button('Filtrar')  # botão para filtrar
        clear_filters = st.button('Limpar Filtros')  # botão para limpar filtros

    # Restante do código permanece inalterado

    filtered_df = df  # DataFrame para manipulação

    # Aplique os filtros
    if stage and month and year and selected_sdr:
        filtered_df = df[(df['Etapa'].isin(stage)) & (df['Mes'].isin(month)) & (df['Ano'].isin(year)) & (df['SDR'] == selected_sdr)]
    elif stage and month:
        filtered_df = df[(df['Etapa'].isin(stage)) & (df['Mes'].isin(month))]
    elif stage and year:
        filtered_df = df[(df['Etapa'].isin(stage)) & (df['Ano'].isin(year))]
    elif stage and selected_sdr:
        filtered_df = df[(df['Etapa'].isin(stage)) & (df['SDR'] == selected_sdr)]
    elif month and selected_sdr:
        filtered_df = df[(df['Mes'].isin(month)) & (df['SDR'] == selected_sdr)]
    elif month and year:
        filtered_df = df[(df['Mes'].isin(month)) & (df['Ano'].isin(year))]
    elif stage:
        filtered_df = df[df['Etapa'].isin(stage)]
    elif month:
        filtered_df = df[df['Mes'].isin(month)]
    elif year:
        filtered_df = df[df['Ano'].isin(year)]
    elif selected_sdr:
        filtered_df = df[df['SDR'] == selected_sdr]
    else:
        filtered_df = df.copy()

    # Reset the filters
    if clear_filters:
        stage = []
        month = []
        year = []
        sdr = []
        filtered_df = df

    # Rule: Function to color the rows
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
    st.dataframe(filtered_df.style.map(color_rows, subset=['Diff']))