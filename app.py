# app.py

import streamlit as st
import pandas as pd
import io

# Importações dos nossos módulos
from vision_ocr import get_vision_client, detect_document_text
from data_extractor import extract_all_info, find_completion_date # Importando explicitamente

# --- Configuração da Página ---
st.set_page_config(
    page_title="Processador Inteligente de Fichas",
    page_icon="🤖",
    layout="wide"
)

# --- Título e Descrição ---
st.title("🤖 Processador Inteligente de Fichas")
st.markdown(
    """
    Faça o upload de uma ou mais imagens de fichas. A aplicação usará a IA do Google Cloud Vision
    para extrair as informações, que você poderá **corrigir diretamente na tabela** antes de exportar para Excel.
    """
)

# --- Inicialização do Cliente da API ---
client = get_vision_client()

# --- Estado da Sessão ---
if 'results' not in st.session_state:
    st.session_state.results = []
if 'processed' not in st.session_state:
    st.session_state.processed = False

# --- Lógica da Aplicação ---
if client:
    # Colunas para layout
    col1, col2 = st.columns([1, 2])

    with col1:
        uploaded_files = st.file_uploader(
            "Selecione as imagens das fichas:",
            type=['png', 'jpg', 'jpeg', 'bmp', 'tiff'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.write(f"{len(uploaded_files)} imagens carregadas.")
            # Mostra miniaturas
            for file in uploaded_files:
                st.image(file, width=150)
        
        process_button = st.button("Processar Imagens", type="primary", use_container_width=True, disabled=not uploaded_files)
        
        if st.session_state.processed:
            if st.button("Limpar Resultados", use_container_width=True):
                st.session_state.results = []
                st.session_state.processed = False
                st.rerun()

    if process_button:
        st.session_state.results = [] # Limpa resultados anteriores
        with st.spinner("Analisando imagens com a IA do Google..."):
            for uploaded_file in uploaded_files:
                try:
                    image_bytes = uploaded_file.getvalue()
                    annotation = detect_document_text(image_bytes, client)
                    
                    # Extrai informações usando a nova lógica
                    extracted_data = extract_all_info(annotation)
                    
                    st.session_state.results.append({
                        "Arquivo": uploaded_file.name,
                        **extracted_data
                    })
                except Exception as e:
                    st.error(f"Erro ao processar '{uploaded_file.name}': {e}")
        st.session_state.processed = True
        st.rerun() # Recarrega para exibir os resultados

    with col2:
        if st.session_state.processed and st.session_state.results:
            st.subheader("Resultados Extraídos (Você pode editar os campos abaixo)")
            
            # O st.data_editor é a chave para a interface interativa
            edited_df = st.data_editor(
                pd.DataFrame(st.session_state.results),
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Arquivo": st.column_config.TextColumn(
                        "Arquivo de Origem",
                        disabled=True,
                        help="Nome do arquivo de imagem processado"
                    )
                }
            )

            # Salva as edições de volta no estado da sessão
            st.session_state.results = edited_df.to_dict('records')

            st.subheader("Exportar para Excel")
            
            # Converte para Excel em memória
            excel_buffer = io.BytesIO()
            final_df = pd.DataFrame(st.session_state.results)
            final_df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            
            st.download_button(
                label="📥 Baixar Dados em Excel",
                data=excel_buffer,
                file_name="dados_extraidos_fichas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        elif st.session_state.processed and not st.session_state.results:
            st.warning("O processamento foi concluído, mas nenhuma informação pôde ser extraída.")
        else:
            st.info("Aguardando o upload e processamento das imagens.")

else:
    st.error("A aplicação não pode iniciar. Verifique a configuração das credenciais.")