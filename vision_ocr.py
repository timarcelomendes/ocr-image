# vision_ocr.py

import streamlit as st
from google.cloud import vision
from google.oauth2 import service_account

@st.cache_resource
def get_vision_client():
    """
    Cria e armazena em cache o cliente da Google Vision API usando as credenciais do Streamlit Secrets.
    """
    try:
        # Carrega as credenciais a partir do st.secrets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        return client
    except Exception as e:
        st.error(f"Falha ao inicializar o cliente da Google Vision API: {e}")
        st.error("Verifique se o seu arquivo 'secrets.toml' está configurado corretamente em .streamlit/secrets.toml")
        return None

def detect_document_text(image_bytes: bytes, client: vision.ImageAnnotatorClient):
    """
    Detecta e extrai texto de uma imagem usando o document_text_detection da Vision API.

    Args:
        image_bytes: A imagem em formato de bytes.
        client: O cliente inicializado da Vision API.

    Returns:
        O objeto full_text_annotation contendo todo o texto e seus detalhes estruturais.
    """
    if not client:
        raise ConnectionError("O cliente da Vision API não está disponível.")

    image = vision.Image(content=image_bytes)
    
    # Feature para habilitar o reconhecimento de texto manuscrito
    image_context = vision.ImageContext(language_hints=['pt-BR'])

    # document_text_detection é otimizado para texto denso e documentos
    response = client.document_text_detection(image=image, image_context=image_context)
    
    if response.error.message:
        raise Exception(f"Erro da API do Google Vision: {response.error.message}")

    return response.full_text_annotation