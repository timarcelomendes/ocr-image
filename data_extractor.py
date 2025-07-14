# data_extractor.py

import re
from typing import Optional, List

# --- Funções Auxiliares para Análise Espacial ---

def find_text_near_label(annotation, label_keywords: List[str], max_distance: int = 200) -> Optional[str]:
    """
    Encontra o texto mais próximo à direita de um rótulo encontrado na anotação da Vision API.
    
    Args:
        annotation: O objeto full_text_annotation da Vision API.
        label_keywords: Lista de possíveis textos para o rótulo (ex: ["Nome", "Paciente"]).
        max_distance: A distância máxima (em pixels) para procurar o valor.

    Returns:
        O texto do valor encontrado ou None.
    """
    all_words = [word for page in annotation.pages for block in page.blocks for paragraph in block.paragraphs for word in paragraph.words]
    
    label_word = None
    # Encontra a primeira ocorrência do rótulo
    for word in all_words:
        word_text = "".join([symbol.text for symbol in word.symbols]).lower()
        if any(keyword.lower() in word_text for keyword in label_keywords):
            label_word = word
            break
            
    if not label_word:
        return None

    # Vértice de referência do rótulo (centro da borda direita)
    label_y_center = (label_word.bounding_box.vertices[0].y + label_word.bounding_box.vertices[3].y) / 2
    label_x_end = label_word.bounding_box.vertices[1].x

    candidate_words = []
    # Procura por palavras candidatas na mesma linha e próximas
    for word in all_words:
        word_y_center = (word.bounding_box.vertices[0].y + word.bounding_box.vertices[3].y) / 2
        word_x_start = word.bounding_box.vertices[0].x
        
        # Verifica se está na mesma "linha" vertical e à direita do rótulo
        if abs(word_y_center - label_y_center) < 20 and word_x_start > label_x_end and (word_x_start - label_x_end) < max_distance:
            candidate_words.append((word_x_start, word))
    
    if not candidate_words:
        return None
        
    # Ordena as palavras candidatas pela posição x para formar a frase
    candidate_words.sort()
    
    full_text = " ".join(["".join([s.text for s in w.symbols]) for _, w in candidate_words])
    
    # Remove o caractere ':' se ele for pego junto
    return full_text.strip().lstrip(':').strip()


# --- Funções de Extração Específicas ---

def find_name(annotation) -> Optional[str]:
    """Extrai o nome do paciente/cliente."""
    keywords = ["Nome:", "Nome", "Paciente:", "Cliente:"]
    return find_text_near_label(annotation, keywords, max_distance=400)

def find_phone(full_text: str) -> Optional[str]:
    """Extrai um número de telefone usando regex no texto completo."""
    # Regex melhorado para formatos comuns no Brasil
    match = re.search(r'(\(?\d{2}\)?\s?9?\d{4,5}-?\d{4})', full_text)
    if match:
        # Limpa e padroniza o número
        return re.sub(r'[\s()-]', '', match.group(1))
    return None

def find_birth_date(annotation) -> Optional[str]:
    """Extrai a data de nascimento associada ao seu rótulo."""
    keywords = ["Nascimento", "Nasc:"]
    date_text = find_text_near_label(annotation, keywords, max_distance=300)
    if date_text:
        # Confirma que o texto encontrado é de fato uma data
        date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4})', date_text)
        if date_match:
            return date_match.group(1)
    return None

def find_completion_date(annotation) -> Optional[str]:
    """Extrai a data de tratamento/conclusão associada ao seu rótulo."""
    keywords = ["Tratamento", "Data", "Consulta"]
    date_text = find_text_near_label(annotation, keywords, max_distance=300)
    if date_text:
        date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4})', date_text)
        if date_match:
            return date_match.group(1)
            
    # Plano B: se não achou com rótulo, pega a última data no texto que não seja a de nascimento
    all_dates = re.findall(r'(\d{2}[-/]\d{2}[-/]\d{4})', annotation.text)
    birth_date = find_birth_date(annotation)
    if birth_date and birth_date in all_dates:
        all_dates.remove(birth_date)
    
    return all_dates[-1] if all_dates else None

def extract_all_info(annotation) -> dict:
    """
    Orquestra a extração de todas as informações de uma anotação da Vision API.
    """
    full_text = annotation.text
    
    data = {
        "Nome": find_name(annotation),
        "Telefone": find_phone(full_text),
        "Data de Nascimento": find_birth_date(annotation),
        "Data do Tratamento": find_completion_date(annotation)
    }
    
    # Converte None para "N/A" para exibição, se preferir.
    for key, value in data.items():
        if value is None:
            data[key] = "N/A"
            
    return data