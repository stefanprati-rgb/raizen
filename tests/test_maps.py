"""
Testes automatizados para validação de mapas de extração.

Este módulo verifica se os mapas funcionam corretamente contra seus PDFs de referência.
Detecta regressões quando mapas são atualizados.

Uso:
    pytest tests/test_maps.py -v
    pytest tests/test_maps.py::test_map_has_valid_regex -v
"""
import json
import re
import pytest
from pathlib import Path
from typing import Dict, List, Optional

import fitz

# Caminhos
MAPS_DIR = Path("maps")
PDFS_DIR = Path("data/raw")


def get_all_maps() -> List[Path]:
    """Retorna todos os mapas JSON."""
    return list(MAPS_DIR.glob("*.json"))


def load_map(map_path: Path) -> Dict:
    """Carrega um mapa JSON."""
    with open(map_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_reference_pdf(mapa: Dict) -> Optional[Path]:
    """Encontra o PDF de referência do mapa."""
    meta = mapa.get('meta', {})
    ref_pdf_name = meta.get('reference_pdf')
    
    if ref_pdf_name:
        # Buscar pelo nome exato
        for pdf in PDFS_DIR.rglob('*.pdf'):
            if pdf.name == ref_pdf_name:
                return pdf
    
    return None


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 10) -> str:
    """Extrai texto de um PDF."""
    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for i in range(min(len(doc), max_pages)):
            text += doc[i].get_text() + "\n"
        doc.close()
        return text
    except Exception:
        return ""


# =============================================================================
# TESTES DE ESTRUTURA DOS MAPAS
# =============================================================================

@pytest.mark.parametrize("map_path", get_all_maps())
def test_map_has_valid_structure(map_path: Path):
    """Verifica se o mapa tem estrutura válida."""
    mapa = load_map(map_path)
    
    # Deve ter 'campos' ou 'fields'
    assert 'campos' in mapa or 'fields' in mapa, \
        f"Mapa {map_path.name} não tem 'campos'"
    
    # Deve ter 'meta' ou 'modelo_identificado'
    assert 'meta' in mapa or 'modelo_identificado' in mapa, \
        f"Mapa {map_path.name} não tem metadados"


@pytest.mark.parametrize("map_path", get_all_maps())
def test_map_has_valid_regex(map_path: Path):
    """Verifica se todos os campos têm regex compilável."""
    mapa = load_map(map_path)
    campos = mapa.get('campos', mapa.get('fields', {}))
    
    for campo_nome, campo_data in campos.items():
        regex = campo_data.get('regex')
        if regex:
            try:
                re.compile(regex)
            except re.error as e:
                pytest.fail(f"Regex inválida em {map_path.name}/{campo_nome}: {e}")


@pytest.mark.parametrize("map_path", get_all_maps())
def test_map_regex_has_capture_group(map_path: Path):
    """Verifica se as regex têm grupos de captura."""
    mapa = load_map(map_path)
    campos = mapa.get('campos', mapa.get('fields', {}))
    
    for campo_nome, campo_data in campos.items():
        regex = campo_data.get('regex')
        if regex:
            # Deve ter pelo menos um grupo de captura ()
            if '(' not in regex or ')' not in regex:
                pytest.fail(
                    f"Regex sem grupo de captura em {map_path.name}/{campo_nome}: {regex}"
                )


@pytest.mark.parametrize("map_path", get_all_maps())
def test_map_has_layout_hash(map_path: Path):
    """Verifica se o mapa tem layout_hash (versionamento)."""
    mapa = load_map(map_path)
    meta = mapa.get('meta', {})
    
    # Aviso se não tiver layout_hash
    if 'layout_hash' not in meta:
        pytest.skip(f"Mapa {map_path.name} não tem layout_hash (sem PDF de referência)")


# =============================================================================
# TESTES DE EXTRAÇÃO (requerem PDF de referência)
# =============================================================================

def get_maps_with_reference_pdf() -> List[Path]:
    """Retorna mapas que têm PDF de referência."""
    maps_with_pdf = []
    for map_path in get_all_maps():
        mapa = load_map(map_path)
        if find_reference_pdf(mapa):
            maps_with_pdf.append(map_path)
    return maps_with_pdf


@pytest.mark.parametrize("map_path", get_maps_with_reference_pdf())
def test_map_extracts_from_reference_pdf(map_path: Path):
    """
    Teste de integração: verifica se o mapa extrai dados do PDF de referência.
    """
    mapa = load_map(map_path)
    pdf_path = find_reference_pdf(mapa)
    
    if not pdf_path:
        pytest.skip(f"PDF de referência não encontrado para {map_path.name}")
    
    # Extrair texto
    text = extract_text_from_pdf(pdf_path)
    if not text:
        pytest.skip(f"PDF vazio ou não legível: {pdf_path.name}")
    
    # Testar cada campo
    campos = mapa.get('campos', mapa.get('fields', {}))
    extraidos = 0
    
    for campo_nome, campo_data in campos.items():
        regex = campo_data.get('regex')
        if not regex:
            continue
        
        try:
            match = re.search(regex, text, re.IGNORECASE | re.MULTILINE)
            if match:
                extraidos += 1
        except re.error:
            pass
    
    # Deve extrair pelo menos 1 campo
    assert extraidos > 0, \
        f"Mapa {map_path.name} não extraiu nenhum campo do PDF {pdf_path.name}"


# =============================================================================
# TESTES DE REGRESSÃO
# =============================================================================

@pytest.mark.parametrize("map_path", get_all_maps())
def test_map_example_values_match_regex(map_path: Path):
    """
    Verifica se os `exemplo_valor` definidos no mapa são capturados pela regex.
    Detecta regressões quando a regex é alterada.
    """
    mapa = load_map(map_path)
    campos = mapa.get('campos', mapa.get('fields', {}))
    
    for campo_nome, campo_data in campos.items():
        regex = campo_data.get('regex')
        exemplo = campo_data.get('exemplo_valor')
        trecho = campo_data.get('trecho_original')
        
        if not regex or not trecho:
            continue
        
        try:
            match = re.search(regex, trecho, re.IGNORECASE)
            if match:
                valor_capturado = match.group(1) if match.groups() else match.group(0)
                # Se tem exemplo, verificar se bate
                if exemplo:
                    assert exemplo in str(valor_capturado) or str(valor_capturado) in exemplo, \
                        f"Regex capturou '{valor_capturado}' mas esperava '{exemplo}' em {map_path.name}/{campo_nome}"
        except re.error:
            pass  # Regex inválida já testada em outro teste


# =============================================================================
# SUMÁRIO DE MAPAS
# =============================================================================

def test_maps_summary():
    """Gera sumário dos mapas para relatório."""
    maps = get_all_maps()
    
    with_hash = 0
    with_pdf = 0
    
    for map_path in maps:
        mapa = load_map(map_path)
        if mapa.get('meta', {}).get('layout_hash'):
            with_hash += 1
        if find_reference_pdf(mapa):
            with_pdf += 1
    
    print(f"\n{'='*50}")
    print(f"SUMÁRIO DE MAPAS")
    print(f"{'='*50}")
    print(f"Total de mapas: {len(maps)}")
    print(f"Com layout_hash: {with_hash}")
    print(f"Com PDF de referência: {with_pdf}")
    print(f"{'='*50}")
    
    # Sempre passa (é um relatório)
    assert True
