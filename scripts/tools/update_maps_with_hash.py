"""
Script para adicionar layout_hash aos mapas existentes.

Lê cada mapa, tenta encontrar um PDF de referência correspondente,
calcula o layout_hash e atualiza o mapa.
"""
import json
from pathlib import Path
from datetime import datetime

# Importar o fingerprinter
from raizen_power.utils.pdf_fingerprint import PDFModelIdentifier

def find_reference_pdf(map_name: str, pdf_dirs: list) -> str:
    """
    Tenta encontrar um PDF de referência para o mapa.
    
    Estratégia:
    1. Buscar por nome similar
    2. Buscar por tipo e número de páginas
    """
    # Extrair info do nome do mapa
    # Ex: 01_TERMO_ADESAO_09p_aviso_fidel.json
    parts = map_name.replace('.json', '').split('_')
    
    tipo = None
    paginas = None
    
    for part in parts:
        if part.endswith('p') and part[:-1].isdigit():
            paginas = int(part[:-1])
        if part in ['TERMO', 'SOLAR', 'ADITIVO', 'DISTRATO', 'REEMISSAO']:
            tipo = part
    
    # Buscar PDFs correspondentes
    for pdf_dir in pdf_dirs:
        for pdf_path in Path(pdf_dir).rglob('*.pdf'):
            pdf_name = pdf_path.name.upper()
            
            # Match por tipo
            if tipo and tipo in pdf_name:
                # Verificar páginas se disponível
                # Por enquanto, retorna o primeiro match
                return str(pdf_path)
    
    return None


def update_map_with_hash(map_path: Path, identifier: PDFModelIdentifier, pdf_dirs: list) -> dict:
    """Atualiza um mapa com layout_hash."""
    
    with open(map_path, 'r', encoding='utf-8') as f:
        mapa = json.load(f)
    
    # Verificar se já tem layout_hash
    if 'meta' in mapa and 'layout_hash' in mapa.get('meta', {}):
        return {"status": "skip", "reason": "já possui layout_hash"}
    
    # Encontrar PDF de referência
    ref_pdf = find_reference_pdf(map_path.name, pdf_dirs)
    
    if not ref_pdf:
        return {"status": "no_pdf", "reason": "PDF de referência não encontrado"}
    
    # Calcular fingerprint
    try:
        result = identifier.classify_pdf(ref_pdf, "CPFL")
        fingerprint = result.get("fingerprint", {})
        
        # Adicionar campos ao meta
        if 'meta' not in mapa:
            mapa['meta'] = {}
        
        mapa['meta']['layout_hash'] = fingerprint.get('visual_hash', '')
        mapa['meta']['structure_hash'] = fingerprint.get('structure_hash', '')
        mapa['meta']['composite_id'] = fingerprint.get('composite_id', '')
        mapa['meta']['updated_at'] = datetime.now().isoformat()
        mapa['meta']['reference_pdf'] = Path(ref_pdf).name
        
        # Salvar mapa atualizado
        with open(map_path, 'w', encoding='utf-8') as f:
            json.dump(mapa, f, indent=4, ensure_ascii=False)
        
        return {"status": "updated", "pdf": ref_pdf, "hash": fingerprint.get('visual_hash', '')}
        
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def main():
    maps_dir = Path("maps")
    pdf_dirs = [
        "data/raw",
        "data/processed",
    ]
    
    identifier = PDFModelIdentifier()
    
    maps = list(maps_dir.glob("*.json"))
    print(f"Encontrados {len(maps)} mapas")
    print("-" * 60)
    
    stats = {"updated": 0, "skip": 0, "no_pdf": 0, "error": 0}
    
    for map_path in maps:
        result = update_map_with_hash(map_path, identifier, pdf_dirs)
        status = result["status"]
        stats[status] = stats.get(status, 0) + 1
        
        if status == "updated":
            print(f"[OK] {map_path.name} -> {result.get('hash', '')[:8]}")
        elif status == "skip":
            print(f"[SKIP] {map_path.name} (ja atualizado)")
        elif status == "no_pdf":
            print(f"[NOPDF] {map_path.name}")
        else:
            print(f"[ERR] {map_path.name}: {result.get('reason', '')}")
    
    print("-" * 60)
    print(f"Atualizados: {stats['updated']}")
    print(f"Ignorados: {stats['skip']}")
    print(f"Sem PDF: {stats['no_pdf']}")
    print(f"Erros: {stats['error']}")
    
    # Salvar cache do identifier
    identifier._save_cache()


if __name__ == "__main__":
    main()
