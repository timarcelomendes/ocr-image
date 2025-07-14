# data_extractor.py

import re
from typing import Optional, List, Any
from google.cloud.vision_v1.types.text_annotation import TextAnnotation

# --- Funções Auxiliares para Análise Espacial ---

def find_text_near_label(annotation: TextAnnotation, label_keywords: List[str], max_distance_x: int = 300, max_offset_y: int = 20) -> Optional[str]:
    """
    Encontra o texto mais próximo à direita de um rótulo, com tolerâncias ajustáveis.
    
    Args:
        annotation: O objeto full_text_annotation da Vision API.
        label_keywords: Lista de possíveis textos para o rótulo.
        max_distance_x: A distância MÁXIMA horizontal (em pixels) para procurar o valor.
        max_offset_y: A tolerância MÁXIMA vertical para considerar que as palavras estão na mesma linha.

    Returns:
        O texto do valor encontrado ou None.
    """
    all_words = [word for page in annotation.pages for block in page.blocks for paragraph in block.paragraphs for word in paragraph.words]
    
    label_word = None
    # Encontra a primeira ocorrência do rótulo
    for word in all_words:
        # Constrói a palavra a partir dos símbolos e normaliza (remove ":", deixa minúsculo)
        word_text = "".join([symbol.text for symbol in word.symbols]).lower().strip().replace(':', '')
        # Compara com a lista de keywords normalizadas
        normalized_keywords = [k.lower().strip().replace(':', '') for k in label_keywords]
        if word_text in normalized_keywords:
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
        # Ignora a própria palavra do rótulo
        if word == label_word:
            continue
            
        word_y_center = (word.bounding_box.vertices[0].y + word.bounding_box.vertices[3].y) / 2
        word_x_start = word.bounding_box.vertices[0].x
        
        # Verifica se está na mesma "linha" (tolerância vertical) e à direita do rótulo
        if abs(word_y_center - label_y_center) < max_offset_y and word_x_start > label_x_end and (word_x_start - label_x_end) < max_distance_x:
            candidate_words.append((word_x_start, word))
    
    if not candidate_words:
        return None
        
    # Ordena as palavras candidatas pela posição x para formar a frase
    candidate_words.sort()
    
    full_text = " ".join(["".join([s.text for s in w.symbols]) for _, w in candidate_words])
    
    # Remove o caractere ':' se ele for pego junto e espaços extras
    return full_text.strip().lstrip(':').strip()


# --- Funções de Extração Específicas ---

def find_name(annotation: TextAnnotation) -> Optional[str]:
    """Extrai o nome do paciente/cliente."""
    # AUMENTE A LISTA com todas as variações que encontrar nos seus formulários
    keywords = ["Nome", "Nome:", "Paciente", "Paciente:", "Cliente", "Cliente:", "Nome Completo", "Nome do Paciente"]
    # Aumentamos a distância para nomes compridos
    return find_text_near_label(annotation, keywords, max_distance_x=500)

def find_phone(full_text: str) -> Optional[str]:
    """Extrai um número de telefone usando regex no texto completo."""
    # Regex melhorado para formatos comuns no Brasil, com ou sem 9, com ou sem DDD.
    match = re.search(r'(\(?\d{2}\)?\s?9?\s?\d{4,5}[-\s]?\d{4})', full_text)
    if match:
        # Limpa e padroniza o número
        return re.sub(r'[\s()-]', '', match.group(1))
    return None

def find_birth_date(annotation: TextAnnotation) -> Optional[str]:
    """Extrai a data de nascimento associada ao seu rótulo."""
    keywords = ["Nascimento", "Nasc:", "Data de Nasc", "Data Nasc", "DN"]
    date_text = find_text_near_label(annotation, keywords)
    if date_text:
        # Regex mais flexível para datas (dd/mm/yyyy ou dd/mm/yy)
        date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{2,4})', date_text)
        if date_match:
            return date_match.group(1)
    return None

def find_completion_date(annotation: TextAnnotation, birth_date_val: Optional[str]) -> Optional[str]:
    """Extrai a data de tratamento/conclusão, evitando a data de nascimento."""
    keywords = ["Data", "Data:", "Tratamento", "Consulta", "Procedimento", "Data do Atendimento"]
    date_text = find_text_near_label(annotation, keywords)
    if date_text:
        date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{2,4})', date_text)
        if date_match and date_match.group(1) != birth_date_val:
            return date_match.group(1)
            
    # Plano B: se não achou com rótulo, pega a data mais recente no texto que não seja a de nascimento
    all_dates = re.findall(r'(\d{2}[-/]\d{2}[-/]\d{2,4})', annotation.text)
    
    # Remove a data de nascimento da lista de candidatas
    if birth_date_val and birth_date_val in all_dates:
        all_dates.remove(birth_date_val)
    
    return all_dates[-1] if all_dates else None

def extract_all_info(annotation: TextAnnotation) -> dict:
    """
    Orquestra a extração de todas as informações de uma anotação da Vision API.
    """
    full_text = annotation.text
    
    birth_date = find_birth_date(annotation)
    
    data = {
        "Nome": find_name(annotation),
        "Telefone": find_phone(full_text),
        "Data de Nascimento": birth_date,
        "Data do Tratamento": find_completion_date(annotation, birth_date) # Passa a data de nasc. para evitar repetição
    }
    
    # Converte None para "N/A" para exibição
    return {k: v if v is not None else "N/A" for k, v in data.items()}