# azure_form_recognizer.py

import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.ai.formrecognizer import DocumentAnalysisClient
from typing import Dict

# --- FUNÇÃO DE FORMATAÇÃO DE TELEFONE (LÓGICA ATUALIZADA) ---
def format_phone_number(phone_str: str) -> str:
    """
    Limpa e formata um número de telefone para o padrão brasileiro,
    ignorando caracteres extras no final.
    """
    if not phone_str or not isinstance(phone_str, str):
        return "N/A"

    # 1. Limpa o número, deixando apenas os dígitos
    digits = "".join(filter(str.isdigit, phone_str))

    # 2. Verifica o tamanho do número e aplica a máscara correta,
    #    priorizando os formatos mais longos e usando '>=' para ser mais flexível.
    if len(digits) >= 11: # Celular com DDD (e possivelmente mais dígitos)
        # Pega apenas os 11 primeiros dígitos para formatar
        clean_number = digits[:11]
        return f"({clean_number[:2]}) {clean_number[2:7]}-{clean_number[7:]}"
    
    elif len(digits) >= 10: # Fixo com DDD (e possivelmente mais dígitos)
        # Pega apenas os 10 primeiros dígitos para formatar
        clean_number = digits[:10]
        return f"({clean_number[:2]}) {clean_number[2:6]}-{clean_number[6:]}"
    
    elif len(digits) == 9: # Celular sem DDD
        return f"{digits[:5]}-{digits[5:]}"
    
    elif len(digits) == 8: # Fixo sem DDD
        return f"{digits[:4]}-{digits[4:]}"
    
    else:
        # Se não se encaixar em nenhum padrão, retorna o número limpo que encontrou
        return digits if digits else "N/A"

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
    """
    client = get_azure_client()
    if not client:
        raise ConnectionError("Cliente do Azure não está disponível.")

    try:
        poller = client.begin_analyze_document(model_id=model_id, document=image_bytes)
        result = poller.result()

    except ResourceNotFoundError:
        return {"Error": f"O Model ID '{model_id}' não foi encontrado. Verifique o ID no Azure Studio."}
    except Exception as e:
        return {"Error": f"Ocorreu um erro ao analisar o documento: {e}"}

    raw_extracted_data = {}
    if result.documents:
        for doc in result.documents:
            for field_name, field in doc.fields.items():
                if field and field.content:
                    raw_extracted_data[field_name.lower()] = field.content
    
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
                value = raw_extracted_data[label]
                
                if column_name in ["Fone", "Cel"]:
                    final_data[column_name] = format_phone_number(value)
                else:
                    final_data[column_name] = value
                break
                
    return final_data