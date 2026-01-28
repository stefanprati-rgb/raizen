"""
Gera prompts para criação de mapas usando análise estatística.
- Analisa variação dentro de cada grupo
- Determina quantidade ideal de amostras
- Gera prompt detalhado para Gemini
"""
import json
import re
import math
from pathlib import Path
from collections import Counter
from datetime import datetime

SOURCE_DIR = Path("contratos_organizados")
OUTPUT_DIR = Path("output/mapping_prompts")


def calculate_sample_size(population: int, confidence: float = 0.90, margin: float = 0.10) -> int:
    """
    Calcula tamanho da amostra usando fórmula estatística.
    
    Fórmula: n = (Z^2 * p * (1-p)) / E^2
    Ajustada para população finita: n_adj = n / (1 + (n-1)/N)
    
    Args:
        population: Tamanho da população
        confidence: Nível de confiança (0.90 = 90%)
        margin: Margem de erro (0.10 = 10%)
    """
    # Z-scores para níveis de confiança
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.645)
    
    # Proporção estimada (0.5 = máxima variabilidade)
    p = 0.5
    
    # Tamanho da amostra inicial
    n = (z ** 2 * p * (1 - p)) / (margin ** 2)
    
    # Ajuste para população finita
    n_adj = n / (1 + (n - 1) / population)
    
    # Mínimo 2, máximo 10
    return max(2, min(10, math.ceil(n_adj)))


def analyze_group_variation(folder: Path) -> dict:
    """Analisa variação dentro de um grupo de PDFs."""
    pdfs = list(folder.glob("*.pdf"))
    
    if not pdfs:
        return None
    
    # Padrões de nome para identificar variações
    patterns = {
        "SOLAR": 0,
        "TERMO_ADESAO": 0,
        "ADESAO": 0,
        "ADITIVO": 0,
        "DISTRATO": 0,
        "CONDICOES": 0,
        "REEM": 0,  # Reemissão
        "ADT": 0,   # Aditivo
        "Clicksign": 0,
        "Qualisign": 0,
        "DocuSign": 0,
    }
    
    for pdf in pdfs:
        name = pdf.name.upper()
        for pattern in patterns:
            if pattern.upper() in name:
                patterns[pattern] += 1
    
    # Identificar tipos predominantes
    total = len(pdfs)
    variation_score = sum(1 for v in patterns.values() if v > 0) / len(patterns)
    
    # Selecionar amostras representativas
    sample_size = calculate_sample_size(total)
    
    # Selecionar PDFs variados
    samples = []
    used_patterns = set()
    
    for pdf in pdfs:
        name = pdf.name.upper()
        # Priorizar PDFs com padrões diferentes
        for pattern in patterns:
            if pattern.upper() in name and pattern not in used_patterns:
                samples.append(pdf)
                used_patterns.add(pattern)
                break
        
        if len(samples) >= sample_size:
            break
    
    # Completar com amostras aleatórias se necessário
    if len(samples) < sample_size:
        remaining = [p for p in pdfs if p not in samples]
        samples.extend(remaining[:sample_size - len(samples)])
    
    return {
        "total": total,
        "sample_size": len(samples),
        "samples": samples,
        "patterns": {k: v for k, v in patterns.items() if v > 0},
        "variation_score": round(variation_score, 2)
    }


def generate_prompt(combo: str, pages: int, distributor: str, analysis: dict) -> str:
    """Gera prompt detalhado para o Gemini."""
    
    # Listar padrões encontrados
    patterns_text = ""
    if analysis["patterns"]:
        patterns_text = "\n".join([f"   - {k}: {v} arquivos" for k, v in analysis["patterns"].items()])
    else:
        patterns_text = "   - Padrão único"
    
    # Listar arquivos de amostra
    samples_text = "\n".join([f"   {i+1}. {s.name}" for i, s in enumerate(analysis["samples"])])
    
    prompt = f"""# CRIAR MAPA DE EXTRAÇÃO: {combo}

## Contexto
- **Distribuidora**: {distributor}
- **Páginas**: {pages}
- **Total de arquivos**: {analysis["total"]}
- **Variação detectada**: {analysis["variation_score"]:.0%}

## Padrões de nome encontrados:
{patterns_text}

## Arquivos de amostra ({len(analysis["samples"])}):
{samples_text}

## Instruções

Analise os PDFs anexados e crie um mapa JSON para extração com os seguintes campos:

### Campos OBRIGATÓRIOS:
1. `razao_social` - Nome da empresa/cliente
2. `cnpj` - CNPJ do cliente (formato: XX.XXX.XXX/XXXX-XX)
3. `num_instalacao` - Número da instalação/UC
4. `num_cliente` - Número do cliente na distribuidora
5. `distribuidora` - Nome da distribuidora (CEMIG, CPFL, etc.)
6. `duracao_meses` - Duração do contrato em meses
7. `email` - Email de contato
8. `representante_nome` - Nome do representante legal

### Campos OPCIONAIS (se disponíveis):
- `endereco` - Endereço completo
- `telefone` - Telefone de contato
- `desconto_percentual` - Percentual de desconto
- `data_assinatura` - Data de assinatura do contrato

## Formato de Saída

```json
{{
  "modelo_identificado": "Termo de Adesão {distributor} {pages}p",
  "distribuidora_principal": "{distributor}",
  "paginas_analisadas": {pages},
  "campos": {{
    "razao_social": {{
      "regex": "PADRÃO_REGEX_AQUI",
      "grupo": 1,
      "descricao": "Descrição do campo"
    }},
    ...
  }}
}}
```

## Dicas para Regex:
- Use `[\\s\\n,]*` para lidar com quebras de linha
- Use `(?:texto)?` para partes opcionais
- Teste cada regex no texto extraído do PDF
- Considere variações de formatação (espaços, tabulações)

Por favor, analise os {len(analysis["samples"])} PDFs anexados e gere o mapa JSON completo.
"""
    return prompt


def main():
    print("=" * 70)
    print("GERADOR DE PROMPTS PARA MAPEAMENTO")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Criar pasta de saída
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Listar combos sem mapa
    print("\n📊 Analisando grupos...")
    
    # Carregar mapas existentes
    maps_dir = Path("maps")
    existing_maps = set()
    for f in maps_dir.glob("*.json"):
        existing_maps.add(f.stem.upper())
    
    # Analisar cada combo
    combos_analysis = []
    
    for pages_folder in SOURCE_DIR.iterdir():
        if not pages_folder.is_dir():
            continue
        
        match = re.match(r'(\d+)_paginas', pages_folder.name)
        if not match:
            continue
        pages = int(match.group(1))
        
        for dist_folder in pages_folder.iterdir():
            if not dist_folder.is_dir():
                continue
            
            distributor = dist_folder.name
            combo = f"{distributor}_{pages:02d}p"
            
            # Verificar se já tem mapa
            has_map = any(combo.upper().replace('-', '_') in m.replace('-', '_') for m in existing_maps)
            if has_map:
                continue
            
            # Analisar grupo
            analysis = analyze_group_variation(dist_folder)
            if analysis:
                combos_analysis.append({
                    "combo": combo,
                    "pages": pages,
                    "distributor": distributor,
                    "folder": dist_folder,
                    "analysis": analysis
                })
    
    # Ordenar por quantidade
    combos_analysis.sort(key=lambda x: x["analysis"]["total"], reverse=True)
    
    print(f"   {len(combos_analysis)} combos precisam de mapas")
    
    # Gerar prompts para top 20
    print(f"\n📝 Gerando prompts para os 20 maiores grupos...")
    
    prompts_summary = []
    
    for i, item in enumerate(combos_analysis[:20], 1):
        combo = item["combo"]
        analysis = item["analysis"]
        
        print(f"\n[{i}/20] {combo} ({analysis['total']} arquivos)")
        print(f"   Amostras: {analysis['sample_size']} | Variação: {analysis['variation_score']:.0%}")
        
        # Gerar prompt
        prompt = generate_prompt(
            combo=combo,
            pages=item["pages"],
            distributor=item["distributor"],
            analysis=analysis
        )
        
        # Salvar prompt
        prompt_file = OUTPUT_DIR / f"{combo}_prompt.md"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        # Salvar lista de amostras
        samples_file = OUTPUT_DIR / f"{combo}_samples.txt"
        with open(samples_file, 'w', encoding='utf-8') as f:
            for sample in analysis["samples"]:
                f.write(f"{sample}\n")
        
        prompts_summary.append({
            "combo": combo,
            "total": analysis["total"],
            "samples": analysis["sample_size"],
            "variation": analysis["variation_score"],
            "prompt_file": str(prompt_file),
            "samples_file": str(samples_file),
            "sample_paths": [str(s) for s in analysis["samples"]]
        })
        
        print(f"   ✅ Prompt salvo: {prompt_file.name}")
    
    # Salvar resumo
    summary_file = OUTPUT_DIR / "prompts_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_combos_needed": len(combos_analysis),
            "prompts_generated": len(prompts_summary),
            "prompts": prompts_summary
        }, f, indent=2, ensure_ascii=False)
    
    # Resumo final
    print(f"\n{'=' * 70}")
    print("RESUMO")
    print("=" * 70)
    print(f"Total de combos sem mapa: {len(combos_analysis)}")
    print(f"Prompts gerados: {len(prompts_summary)}")
    print(f"\n📁 Arquivos salvos em: {OUTPUT_DIR}")
    print(f"   - {len(prompts_summary)} prompts (.md)")
    print(f"   - {len(prompts_summary)} listas de amostras (.txt)")
    print(f"   - 1 resumo (prompts_summary.json)")
    
    # Mostrar top 5 para ação imediata
    print(f"\n🎯 TOP 5 PRIORIDADES:")
    for i, item in enumerate(prompts_summary[:5], 1):
        print(f"   {i}. {item['combo']}: {item['total']} arquivos, {item['samples']} amostras")


if __name__ == "__main__":
    main()
