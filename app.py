# app.py

import streamlit as st
import pandas as pd
import io

# Importa as funções do nosso arquivo de lógica separada
from azure_form_recognizer import process_with_custom_model, preprocess_image

# ==============================================================================
#           INTERFACE DA APLICAÇÃO (Streamlit)
# ==============================================================================

# --- Configuração da Página e outros códigos iniciais (sem alterações) ---
st.set_page_config(page_title="Processador de Fichas", page_icon="🤖", layout="wide")
st.markdown("""
<style>
    /* Melhora a aparência dos containers principais */
    [data-testid="stVerticalBlock"] .st-emotion-cache-12fmjuu.e1f1d6gn2 {
        background-color: #f8f9fa; /* Fundo do container com um cinza bem claro */
        border-radius: 10px;        /* Bordas arredondadas */
        padding: 25px;              /* Espaçamento interno */
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1); /* Sombra suave para dar profundidade */
    }

    /* Estilo para a barra lateral */
    [data-testid="stSidebar"] {
        background-color: #e9ecef; /* Fundo da sidebar com um tom um pouco mais escuro */
    }

    /* Garante que a legenda da imagem (nome do arquivo) quebre a linha se for muito longa */
    [data-testid="stImage"] + [data-testid="stCaption"] {
        word-break: break-word;
    }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("images/logo.png", width=80) 
    st.title("Processador AI")
    st.markdown("---")

    # Seção de Processamento de Imagens
    with st.expander("⚙️ Processar Novas Imagens", expanded=True):
        model_id = st.text_input(
            "Azure Model ID:", 
            placeholder="Digite seu Azure Model ID"
            value="", # Coloque seu Model ID aqui como padrão
            help="Cole o ID do seu modelo treinado no Document Intelligence Studio."
        )
        st.info(f"Usando Modelo: **{model_id}**")

    # --- NOVO RECURSO: UNIFICADOR DE ARQUIVOS ---
    st.markdown("---")
    with st.expander("🔄 Unificar Arquivos Excel"):
        st.markdown("Faça o upload de múltiplos arquivos Excel para combiná-los em um único arquivo.")
        excel_files_to_unify = st.file_uploader(
            "Selecione os arquivos .xlsx",
            type="xlsx",
            accept_multiple_files=True,
            key="excel_unifier"
        )

        if excel_files_to_unify:
            try:
                # Lista para guardar os DataFrames de cada arquivo
                df_list = []
                for file in excel_files_to_unify:
                    df_list.append(pd.read_excel(file))
                
                # Concatena todos os DataFrames em um só
                unified_df = pd.concat(df_list, ignore_index=True)
                
                # Remove linhas duplicadas para garantir a limpeza
                unified_df.drop_duplicates(inplace=True)
                
                st.success(f"{len(excel_files_to_unify)} arquivos lidos. Total de {len(unified_df)} linhas únicas.")

                # Converte o DataFrame unificado para um arquivo Excel em memória
                unified_excel_buffer = io.BytesIO()
                unified_df.to_excel(unified_excel_buffer, index=False, engine='openpyxl')
                unified_excel_buffer.seek(0)

                st.download_button(
                    label="📥 Baixar Arquivo Unificado",
                    data=unified_excel_buffer,
                    file_name="dados_consolidados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Ocorreu um erro ao unificar os arquivos: {e}")


# --- TELA PRINCIPAL ---
st.header("Processador Inteligente de Fichas")
st.markdown(f"Utilizando o modelo treinado: **{model_id}**")
st.divider()

# --- Container de Upload e Controles ---
with st.container():
    st.markdown("### 📂 1. Carregar Fichas")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.warning("A otimização de imagem (P&B) é aplicada automaticamente para garantir a melhor precisão.")
        
        uploaded_files = st.file_uploader("Selecione uma ou mais imagens:", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key=f"uploader_{st.session_state.uploader_key}")
        
        process_button = st.button("🔍 Analisar com Modelo Treinado", type="primary", use_container_width=True, disabled=not uploaded_files)

        if uploaded_files or st.session_state.processed:
            if st.button("🗑️ Limpar e Reiniciar", use_container_width=True):
                st.session_state.results = []
                st.session_state.processed = False
                st.session_state.uploader_key += 1
                st.rerun()

    with col2:
        if uploaded_files:
            st.write(f"**Imagens prontas para análise:**")
            thumb_cols = st.columns(6)
            for idx, file in enumerate(uploaded_files):
                with thumb_cols[idx % 6]:
                    st.image(file, use_column_width=True)
                    st.caption(file.name)
        else:
            st.info("Aguardando o upload para ativar a análise.")

# --- LÓGICA DE PROCESSAMENTO ---
if process_button:
    if not model_id:
        st.error("Por favor, insira o Azure Model ID na barra lateral.")
    else:
        st.session_state.results = []
        progress_bar = st.progress(0, text="Iniciando análise...")
        for i, uploaded_file in enumerate(uploaded_files):
            progress_text = f"Analisando: {uploaded_file.name}"
            progress_bar.progress((i + 1) / len(uploaded_files), text=progress_text)
            try:
                image_bytes = uploaded_file.getvalue()
                final_image_bytes = preprocess_image(image_bytes)
                
                extracted_data = process_with_custom_model(final_image_bytes, model_id)
                
                if "Error" in extracted_data:
                    st.error(f"Falha ao processar '{uploaded_file.name}': {extracted_data['Error']}")
                    error_row = {"Arquivo": uploaded_file.name, "Status": extracted_data['Error']}
                    st.session_state.results.append(error_row)
                    continue
                
                st.session_state.results.append({"Arquivo": uploaded_file.name, **extracted_data})
            except Exception as e:
                st.error(f"Erro inesperado ao processar '{uploaded_file.name}': {e}")
        
        progress_bar.empty()
        st.session_state.processed = True
        st.session_state.show_success_toast = True
        st.rerun()

# --- CONTAINER DE RESULTADOS ---
if st.session_state.processed and st.session_state.results:
    st.divider()
    st.markdown("### ✏️ 2. Validar e Exportar Resultados")
    st.markdown("Os dados extraídos abaixo refletem os campos que você treinou no Azure.")

    df = pd.DataFrame(st.session_state.results).fillna("N/A")
    if "Arquivo" not in df.columns:
        df.insert(0, "Arquivo", [])

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={"Arquivo": st.column_config.TextColumn(disabled=True)}
    )
    
    st.session_state.results = edited_df.to_dict('records')

    excel_buffer = io.BytesIO()
    pd.DataFrame(st.session_state.results).to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    st.download_button(
        label="📊 Baixar Dados Corrigidos em Excel",
        data=excel_buffer,
        file_name="dados_extraidos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )