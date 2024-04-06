from supabase import create_client, Client
import pandas as pd
from openai import OpenAI
import os

# Supabase connection details
url = "https://rhzbwahkrnsrmpgozhyq.supabase.co"
supabase_key = os.environ.get('SUPABASE_API_KEY')
supabase = create_client(url, supabase_key)

# Define a OpenAI API key
openai_api_key = os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# Carrega dados da tabela Supabase (assegure-se de que este passo está correto)
response = supabase.table('promptgpt').select('*').execute()
df = pd.DataFrame(response.data)

# Define as tarefas de análise (mantido conforme seu código)
analysis_tasks = """
1. Extração de menções do PlanAPP: Extrair e mostrar todas as frases em que o PlanAPP é mencionado.
2. Extração de menções do trabalho ou atividade do PlanAPP: Extrair e mostrar todas as frases em que o trabalho do PlanAPP é mencionado.
3. Extração de pessoas que trabalhem no PlanAPP: Extrair e apenas as pessoas que trabalham no PlanAPP.
4. O que aconteceu ao PlanAPP? É uma atualização institucional ou é relacionado com um projeto do PlanAPP?

Formato da resposta
Frases relacionadas com o PlanAPP:  Relativo ao ponto 1 e 2
Pessoas identificadas: Relativo ao ponto 3 
Projetos ou atividades identificadas: Relativo ao ponto 4 
Centralidade: Identificar se o tema central da notícia é o planAPP, se é secundário ou é apenas uma referêncais
TLDR: Elabora um TLDR. Diz-se apenas PlanAPP, e não se inclui O Centro de Competências de Planeamento, de Políticas e de Prospetiva da Administração Pública
"""

# Geração de TLDR com a API da OpenAI
tldrs = []
for index, row in df.iterrows():
    news_content = row['concatenated_column']  # Certifique-se de que esta coluna existe
    prompt = f"Por favor, analise a seguinte notícia e responda às perguntas:\n\n{news_content}\n\nTarefas de Análise:\n{analysis_tasks}\n\nResposta:"
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        assistant_reply = response.choices[0].message.content if response.choices else "Resposta não disponível"
        tldrs.append(assistant_reply)
    except Exception as e:
        print(f"Ocorreu um erro na linha {index}: {e}")
        tldrs.append("Erro ao gerar TLDR")

# Adiciona os TLDRs ao DataFrame
df['TLDR'] = tldrs

# Atualiza a tabela 'Notícias' no Supabase com os novos TLDRs
for index, row in df.iterrows():
    try:
        update_response = supabase.table('Notícias').update({'TLDR': row['TLDR']}).eq('id', row['id']).execute()

        # Tente inspecionar a estrutura de update_response para entender como acessar os erros
        print(update_response)  # Isso ajudará a entender a estrutura do objeto

        # Verificação genérica de sucesso baseada na presença de dados
        if update_response.data:
            print(f"TLDR atualizado com sucesso para a notícia com id {row['id']}")
        else:
            # Sem uma forma clara de acessar o erro, essa mensagem é genérica
            print(f"Erro ou resposta inesperada ao atualizar TLDR para a notícia com id {row['id']}")
    except Exception as e:
        print(f"Ocorreu um erro ao atualizar TLDR para a notícia com id {row['id']}: {e}")