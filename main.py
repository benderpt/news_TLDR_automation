import pandas as pd
import xml.etree.ElementTree as ET
import requests
from supabase import create_client
import os
import logging

# Configuração do logger para salvar em arquivo
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Define o nível do logger

# Cria um file handler que escreve mensagens de nível INFO ou superior para o arquivo de log
log_filename = 'process_rss_log.txt'
file_handler = logging.FileHandler(log_filename, mode='a')
file_handler.setLevel(logging.INFO)

# Define o formato das mensagens de log
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Adiciona o file handler ao logger
logger.addHandler(file_handler)

def fetch_rss(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logger.info(f"RSS feed fetched successfully from {url}")
            return response.content
        else:
            logger.error(f"Failed to fetch RSS feed. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.exception(f"Exception occurred while fetching RSS feed: {e}")
        return None

def process_rss_content(rss_content):
    try:
        root = ET.fromstring(rss_content)
        dados = []

        for item in root.findall('.//item'):
            guid = item.findtext('guid')
            titulo = item.findtext('title')
            noticia = item.findtext('description')
            link = item.findtext('link') if item.find('link') is not None else 'No link available'
            data_publicacao = item.findtext('pubDate')
            fonte = item.findtext('source')  # Extrai o texto da fonte

            # Predefinições para categorias
            categories = {'id': None, 'publication-type': None, 'author': 'sem autor', 'aav': None}
            for category in item.findall('.//category'):
                domain = category.attrib.get('domain')
                if domain in categories:
                    categories[domain] = category.text if category.text is not None else categories[domain]

            valor_publicitario = convert_to_decimal_format(categories['aav'])
            
            dados.append({
                'guid': guid,
                'título': titulo,
                'notícia': noticia,
                'link': link,
                'data_de_publicação': data_publicacao,
                'id': categories['id'],
                'tipo_de_meio': categories['publication-type'],
                'autores': categories['author'],
                'valor_publicitário': valor_publicitario,
                'dossier': 'Dossier',  # Adicione a lógica para definir 'Dossier' se necessário
                'fonte': fonte  # Inclui a fonte
            })

            logger.info(f"Item processed: {item.findtext('title')}")

        return pd.DataFrame(dados)
    except ET.ParseError as e:
        raise Exception(f"Error parsing RSS content: {e}")

def convert_to_decimal_format(value):
    try:
        if isinstance(value, str):
            return float(value.replace(',', '.'))
        else:
            return value
    except ValueError:
        pass
    return None

def insert_data_to_supabase(df, supabase_client):
    for index, row in df.iterrows():
        try:
            existing_record = supabase_client.table('Notícias').select('id').eq('id', row['id']).execute()
            
            if existing_record.data and len(existing_record.data) > 0:
                logger.info(f"Record with ID {row['id']} already exists. Skipping.")
            else:
                insert_response = supabase_client.table('Notícias').insert(row.to_dict()).execute()
                
                if insert_response.data:
                    logger.info(f"Record with ID {row['id']} inserted successfully.")
                else:
                    logger.warning(f"Failed to insert record with ID {row['id']}. No data in response.")
        except Exception as e:
            logger.exception(f"Exception occurred while inserting data for ID {row['id']}: {e}")

# URL do feed RSS
rss_url = "https://pt.cision.com/cisionpoint/xmlcp/default.aspx?userid=a7c2fabd-55f7-4d1f-b232-dc47aa1601eb"

# Detalhes da conexão Supabase
url = "https://rhzbwahkrnsrmpgozhyq.supabase.co"
key = os.environ.get('SUPABASE_API_KEY')
supabase = create_client(url, key)

try:
    logger.info("Script started")
    rss_content = fetch_rss(rss_url)
    all_data = process_rss_content(rss_content)
        
    if all_data is not None and not all_data.empty:
        # Aplica a conversão no campo 'valor_publicitário'
        all_data['valor_publicitário'] = all_data['valor_publicitário'].apply(convert_to_decimal_format)
        insert_data_to_supabase(all_data, supabase)
    else:
        logger.info("No data found in the RSS feed.")
        logger.info("Script finished successfully")

except Exception as e:
    logger.exception("An unexpected error occurred")