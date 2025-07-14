# app.py

import streamlit as st
import pandas as pd
import io
import cv2
import numpy as np

# Importação do nosso módulo do Document AI
from document_ai_parser import process_form_with_docai

# --- FUNÇÃO DE PRÉ-PROCESSAMENTO DE IMAGEM ---
def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Converte a imagem para preto e branco usando limiar adaptativo.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    processed_img = cv2.adaptiveThreshold(
        gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    _, buffer = cv2.imencode('.png', processed_img)
    return buffer.tobytes()


# --- Configuração da Página e CSS (sem alterações) ---
st.set_page_config(
    page_title="Processador Inteligente de Fichas",
    page_icon="🤖",
    layout="wide"
)
st.markdown("""
<style>
    /* ... (seu CSS customizado continua aqui) ... */
</style>
""", unsafe_allow_html=True)


# --- Estado da Sessão (Gerenciamento Centralizado) ---
if 'results' not in st.session_state:
    st.session_state.results = []
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0
# *** NOVA CHAVE PARA CONTROLAR O TOAST ***
if 'show_success_toast' not in st.session_state:
    st.session_state.show_success_toast = False


# --- LÓGICA PARA EXIBIR O TOAST NO INÍCIO DO SCRIPT ---
if st.session_state.get('show_success_toast'):
    st.toast("✅ Análise concluída com sucesso!", icon="🎉")
    # Reseta a chave para não mostrar o toast novamente em interações futuras
    st.session_state.show_success_toast = False


# --- BARRA LATERAL (SIDEBAR) (sem alterações) ---
with st.sidebar:
    st.image("https://i.imgur.com/v8D4ocJ.png", width=80)
    st.title("Processador AI")
    st.markdown("---")
    st.header("Como Usar")
    st.markdown(
        """
        1.  **📂 Carregue as imagens:** Na área principal, clique para selecionar as fichas.
        2.  **🤖 Analise os documentos:** Clique no botão "Analisar Imagens".
        3.  **✏️ Valide e corrija:** A tabela de resultados é editável.
        4.  **📊 Exporte para Excel:** Baixe seu arquivo `.xlsx` com os dados validados.
        """
    )
    st.markdown("---")
    st.info("Aplicação desenvolvida por Gemini.")


# --- TELA PRINCIPAL ---
st.header("Processador Inteligente de Fichas")
st.markdown("Uma ferramenta de alta precisão para extrair dados de formulários. Siga os passos na barra lateral para começar.")
st.divider()


# --- Container de Upload e Controles ---
with st.container():
    st.markdown("### 📂 1. Carregar Fichas")
    col1, col2 = st.columns([1, 2])

    with col1:
        preprocess_toggle = st.checkbox(
            "Otimizar imagens (remover sombras)",
            value=False,
            help="Use esta opção somente se a imagem tiver muitas sombras ou iluminação ruim."
        )

        uploaded_files = st.file_uploader(
            "Selecione uma ou mais imagens:",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}"
        )

        process_button = st.button(
            "🔍 Analisar Imagens",
            type="primary",
            use_container_width=True,
            disabled=not uploaded_files
        )

        if uploaded_files or st.session_state.processed:
            if st.button("🗑️ Limpar e Reiniciar", use_container_width=True):
                st.session_state.results = []
                st.session_state.processed = False
                st.session_state.uploader_key += 1
                st.session_state.show_success_toast = False # Garante que o toast não apareça ao limpar
                st.rerun()

    with col2:
        if uploaded_files:
            st.write(f"**Imagens prontas para análise:**")
            thumb_cols = st.columns(6)
            for idx, file in enumerate(uploaded_files):
                with thumb_cols[idx % 6]:
                    st.image(file, use_container_width=True)
                    st.caption(file.name)
        else:
            st.info("Aguardando o upload para ativar a análise.")


# --- Lógica de Processamento ---
if process_button:
    st.session_state.results = []
    progress_bar = st.progress(0, text="Iniciando análise...")

    for i, uploaded_file in enumerate(uploaded_files):
        progress_text = f"Analisando: {uploaded_file.name}"
        progress_bar.progress((i + 1) / len(uploaded_files), text=progress_text)
        try:
            image_bytes = uploaded_file.getvalue()
            final_image_bytes = image_bytes
            mime_type = uploaded_file.type

            if preprocess_toggle:
                final_image_bytes = preprocess_image(image_bytes)
                mime_type = 'image/png'

            extracted_data = process_form_with_docai(
                image_bytes=final_image_bytes,
                mime_type=mime_type
            )
            st.session_state.results.append({
                "Arquivo": uploaded_file.name,
                **extracted_data
            })
        except Exception as e:
            st.error(f"Erro ao processar '{uploaded_file.name}': {e}")

    progress_bar.empty()
    st.session_state.processed = True
    
    # *** MUDANÇA PRINCIPAL AQUI ***
    # Apenas ativa a "bandeira" para mostrar o toast na próxima execução
    st.session_state.show_success_toast = True
    st.rerun() # O rerun agora ocorre depois de ativar a bandeira


# --- Container de Resultados (sem alterações) ---
if st.session_state.processed and st.session_state.results:
    st.divider()
    with st.container():
        st.markdown("### ✏️ 2. Validar e Exportar Resultados")
        st.markdown("Os dados extraídos estão abaixo. **Clique duas vezes em qualquer célula para corrigir um valor** antes de exportar.")

        edited_df = st.data_editor(
            pd.DataFrame(st.session_state.results),
            num_rows="dynamic",
            use_container_width=True,
            column_config={ "Arquivo": st.column_config.TextColumn(disabled=True) }
        )

        st.session_state.results = edited_df.to_dict('records')

        excel_buffer = io.BytesIO()
        pd.DataFrame(st.session_state.results).to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        st.download_button(
            label="📊 Baixar Dados Corrigidos em Excel",
            data=excel_buffer,
            file_name="dados_extraidos_document_ai.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )