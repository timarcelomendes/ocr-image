# app.py

import streamlit as st
import pandas as pd
import io

# Importação do nosso módulo do Document AI (sem alterações aqui)
from document_ai_parser import process_form_with_docai

# --- Configuração da Página ---
st.set_page_config(
    page_title="Processador Inteligente de Fichas",
    page_icon="🤖",
    layout="wide"
)

# --- Título e Descrição ---
st.title("🚀 Processador de Fichas com Document AI")
st.markdown(
    """
    Uma ferramenta de alta precisão para extrair dados de formulários.
    Carregue as imagens, valide os resultados e exporte para Excel com facilidade.
    """
)

# --- Estado da Sessão (Gerenciamento Centralizado) ---
if 'results' not in st.session_state:
    st.session_state.results = []
if 'processed' not in st.session_state:
    st.session_state.processed = False
# Chave para forçar a recriação do widget de upload de arquivos
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

# --- Interface Principal com Containers ---

# Container para a seção de Upload e Controles
input_container = st.container()
with input_container:
    st.header("1. Carregar Imagens")
    # Layout em colunas para organizar os controles e a galeria de imagens
    col1, col2 = st.columns([1, 2])

    with col1:
        # Widget de upload de arquivos com uma chave dinâmica
        uploaded_files = st.file_uploader(
            "Selecione uma ou mais imagens:",
            type=['png', 'jpg', 'jpeg', 'bmp', 'tiff'],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}" # A chave força o reset
        )

        process_button = st.button(
            "Analisar com Document AI",
            type="primary",
            use_container_width=True,
            disabled=not uploaded_files
        )

        # O novo botão "Limpar e Reiniciar" fica visível se houver algo para limpar
        if uploaded_files or st.session_state.processed:
            if st.button("Limpar e Reiniciar", use_container_width=True):
                # Reseta o estado da aplicação
                st.session_state.results = []
                st.session_state.processed = False
                # Incrementa a chave do uploader para limpá-lo
                st.session_state.uploader_key += 1
                # Força a re-execução do script para aplicar as mudanças imediatamente
                st.rerun()

    with col2:
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} imagens prontas para análise:**")
            # Galeria de miniaturas organizada
            thumb_cols = st.columns(6) # Ajuste o número de colunas conforme sua preferência
            for idx, file in enumerate(uploaded_files):
                # Exibe a imagem na coluna correspondente, fazendo um ciclo
                thumb_cols[idx % 6].image(
                    file,
                    caption=f"_{file.name[:15]}..._", # Legenda curta
                    use_container_width=True
                )
        else:
            st.info("Aguardando o upload de uma ou mais imagens para começar.")


# --- Lógica de Processamento (ocorre quando o botão é clicado) ---
if process_button:
    st.session_state.results = []
    # Usamos uma barra de progresso para um feedback mais detalhado
    progress_bar = st.progress(0, text="Iniciando análise...")
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            # Atualiza o texto da barra de progresso
            progress_text = f"Analisando: {uploaded_file.name}"
            progress_bar.progress((i + 1) / len(uploaded_files), text=progress_text)
            
            image_bytes = uploaded_file.getvalue()
            extracted_data = process_form_with_docai(
                image_bytes=image_bytes,
                mime_type=uploaded_file.type
            )
            st.session_state.results.append({
                "Arquivo": uploaded_file.name,
                **extracted_data
            })
        except Exception as e:
            st.error(f"Erro ao processar '{uploaded_file.name}': {e}")
            
    progress_bar.empty() # Limpa a barra de progresso ao concluir
    st.session_state.processed = True
    st.rerun()


# --- Container para a exibição dos Resultados ---
results_container = st.container()
with results_container:
    if st.session_state.processed and st.session_state.results:
        st.header("2. Validar e Exportar Resultados")
        st.markdown("Os dados extraídos estão abaixo. **Você pode clicar em qualquer célula para corrigir um valor** antes de exportar.")
        
        # O editor de dados interativo
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

        # Converte para Excel em memória
        excel_buffer = io.BytesIO()
        final_df = pd.DataFrame(st.session_state.results)
        final_df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        st.download_button(
            label="📥 Baixar Dados Corrigidos em Excel",
            data=excel_buffer,
            file_name="dados_extraidos_document_ai.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )