# app.py

import streamlit as st
import pandas as pd
import io

# Importação do nosso módulo do Document AI
from document_ai_parser import process_form_with_docai

# --- Configuração da Página ---
st.set_page_config(
    page_title="Processador Inteligente de Fichas",
    page_icon="🤖",
    layout="wide"
)

# --- CSS Customizado para um Visual Mais Amigável ---
st.markdown("""
<style>
    /* Melhora a aparência dos containers */
    [data-testid="stVerticalBlock"] .st-emotion-cache-12fmjuu.e1f1d6gn2 {
        background-color: #f8f9fa; /* Fundo do container principal */
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
    }
    /* Estilo para a barra lateral */
    [data-testid="stSidebar"] {
        background-color: #e9ecef; /* Fundo da sidebar */
    }
</style>
""", unsafe_allow_html=True)


# --- Estado da Sessão (Gerenciamento Centralizado) ---
if 'results' not in st.session_state:
    st.session_state.results = []
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0
if 'show_balloons' not in st.session_state:
    st.session_state.show_balloons = False


# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("images/logo.png", width=80) # Use um logo de sua preferência
    st.title("Processador AI")
    st.markdown("---")
    st.header("Como Usar")
    st.markdown(
        """
        1.  **📂 Carregue as imagens:** Na área principal, clique para selecionar as fichas que deseja processar.
        2.  **🤖 Analise os documentos:** Clique no botão "Analisar Imagens" para que a IA extraia os dados.
        3.  **✏️ Valide e corrija:** A tabela de resultados é editável. Clique duas vezes em qualquer campo para fazer correções.
        4.  **📊 Exporte para Excel:** Com os dados validados, clique no botão de download para gerar seu arquivo `.xlsx`.
        """
    )
    st.markdown("---")
    st.info("RAKITI Soluções em Analytics")


# --- TELA PRINCIPAL ---
st.header("Processador Inteligente de Fichas")
st.markdown("Uma ferramenta de alta precisão para extrair dados de formulários. Siga os passos na barra lateral para começar.")
st.divider()


# --- Container de Upload e Controles ---
with st.container():
    st.markdown("### 📂 1. Carregar Fichas")
    col1, col2 = st.columns([1, 2])

    with col1:
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
                st.session_state.show_balloons = False
                st.rerun()

    with col2:
        if uploaded_files:
            st.write(f"**Imagens prontas para análise:**")
            thumb_cols = st.columns(6)
            for idx, file in enumerate(uploaded_files):
                thumb_cols[idx % 6].image(
                    file,
                    caption=f"_{file.name[:15]}..._",
                    use_container_width=True
                )
        else:
            st.info("Aguardando o upload para ativar a análise. Veja as instruções na barra lateral.")


# --- Lógica de Processamento ---
if process_button:
    st.session_state.results = []
    progress_bar = st.progress(0, text="Iniciando análise...")

    for i, uploaded_file in enumerate(uploaded_files):
        progress_text = f"Analisando: {uploaded_file.name}"
        progress_bar.progress((i + 1) / len(uploaded_files), text=progress_text)
        try:
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

    progress_bar.empty()
    st.session_state.processed = True
    st.session_state.show_balloons = True  # Ativa os balões para a próxima renderização
    st.toast("✅ Análise concluída com sucesso!", icon="🎉")
    st.rerun()


# --- Container de Resultados ---
if st.session_state.processed and st.session_state.results:
    st.divider()
    with st.container():
        st.markdown("### ✏️ 2. Validar e Exportar Resultados")
        st.markdown("Os dados extraídos estão abaixo. **Clique duas vezes em qualquer célula para corrigir um valor** antes de exportar.")
        
        # Comemoração com balões (só na primeira vez)
        if st.session_state.show_balloons:
            st.balloons()
            st.session_state.show_balloons = False

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