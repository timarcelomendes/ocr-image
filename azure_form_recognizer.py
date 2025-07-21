# azure_form_recognizer.py

import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError # Importa a exceção específica
from azure.ai.formrecognizer import DocumentAnalysisClient
from typing import Dict

@st.cache_resource
def get_azure_client():
    """Cria e armazena em cache o cliente do Azure Form Recognizer."""
    try:
        endpoint = st.secrets.azure.form_recognizer_endpoint
        key = st.secrets.azure.form_recognizer_key
        return DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    except Exception as e:
        st.error(f"Falha ao inicializar o cliente do Azure: {e}")
        return None

def preprocess_image(image_bytes: bytes) -> bytes:
    """Converte a imagem para preto e branco para otimizar o OCR."""
    import cv2
    import numpy as np
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    processed_img = cv2.adaptiveThreshold(gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    _, buffer = cv2.imencode('.png', processed_img)
    return buffer.tobytes()

def process_with_custom_model(image_bytes: bytes, model_id: str) -> Dict[str, str]:
    """
    Usa o seu modelo customizado e mapeia os resultados para uma estrutura de colunas fixa.
    Agora inclui tratamento de erro para Model ID inválido.
    """
    client = get_azure_client()
    if not client:
        raise ConnectionError("Cliente do Azure não está disponível.")

    try:
        # Tenta analisar o documento com o Model ID fornecido
        poller = client.begin_analyze_document(model_id=model_id, document=image_bytes)
        result = poller.result()

    except ResourceNotFoundError:
        # Captura o erro se o modelo não for encontrado e retorna uma mensagem clara
        return {"Error": f"O Model ID '{model_id}' não foi encontrado ou não está pronto. Verifique o ID no Azure Studio."}
    except Exception as e:
        # Captura outros erros inesperados durante a análise
        return {"Error": f"Ocorreu um erro ao analisar o documento: {e}"}

    # Extrai todos os campos brutos que o seu modelo treinado retornou
    raw_extracted_data = {}
    if result.documents:
        for doc in result.documents:
            for field_name, field in doc.fields.items():
                if field and field.content:
                    raw_extracted_data[field_name.lower()] = field.content
    
    # Mapeia os resultados para as colunas desejadas
    COLUMN_MAPPING = {
        "Nome":    ["nome", "name", "nome_paciente"],
        "Data":    ["data", "date", "data de nascimento"],
        "Fone":    ["fone", "telefone", "telefone fixo"],
        "Cel":     ["cel", "celular", "mobile"],
        "Address": ["address", "endereço", "endereco"],
    }

    final_data = {}
    for column_name, possible_labels in COLUMN_MAPPING.items():
        final_data[column_name] = "N/A"
        for label in possible_labels:
            if label in raw_extracted_data:
                final_data[column_name] = raw_extracted_data[label]
                break
                
    return final_data