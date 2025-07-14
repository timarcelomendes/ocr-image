# document_ai_parser.py
import streamlit as st
from typing import Dict
from google.cloud import documentai
from google.oauth2 import service_account

@st.cache_resource
def get_document_ai_client():
    # ... (nenhuma mudança nesta função)
    try:
        creds_dict = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        opts = {"api_endpoint": f"{st.secrets.doc_ai.location}-documentai.googleapis.com"}
        client = documentai.DocumentProcessorServiceClient(client_options=opts, credentials=credentials)
        return client
    except Exception as e:
        st.error(f"Falha ao inicializar o cliente do Google Document AI: {e}")
        return None

def process_form_with_docai(
    image_bytes: bytes,
    mime_type: str,
) -> Dict[str, str]:
    # ... (nenhuma mudança na parte inicial da função)
    client = get_document_ai_client()
    if not client:
        raise ConnectionError("O cliente do Document AI não está disponível.")
    
    processor_name = client.processor_path(
        st.secrets.gcp_service_account.project_id,
        st.secrets.doc_ai.location,
        st.secrets.doc_ai.processor_id,
    )
    
    raw_document = documentai.RawDocument(content=image_bytes, mime_type=mime_type)
    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
    
    result = client.process_document(request=request)
    document = result.document

    # *** MUDANÇA IMPORTANTE AQUI ***
    # Defina os campos EXATAMENTE como você os rotulou no Document AI.
    # A chave do dicionário é o que aparecerá na coluna da sua tabela.
    # O valor é o rótulo que você criou no Document AI (ex: 'Cel').
    target_fields_map = {
        "Nome": "Nome",
        "Telefone": "Cel",  # A coluna se chamará "Telefone", mas buscará o rótulo "Cel"
        "Data": "Data"      # A coluna se chamará "Data" e buscará o rótulo "Data"
    }

    # Inicializa o dicionário de resultados com as chaves que queremos na tabela
    results = {col_name: "N/A" for col_name in target_fields_map.keys()}

    # Itera sobre as entidades (campos) encontradas pelo Document AI
    for entity in document.entities:
        # entity.type_ é o rótulo que você criou (ex: "Cel")
        label_from_doc_ai = entity.type_
        value = entity.mention_text.strip()

        # Verifica se o rótulo encontrado está no nosso mapeamento
        for col_name, doc_ai_label in target_fields_map.items():
            if label_from_doc_ai == doc_ai_label:
                results[col_name] = value
                break # Pula para a próxima entidade

    return results