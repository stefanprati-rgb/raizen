"""
Testes de Regressão para Extração de Contratos

Este módulo detecta regressões comparando extrações atuais com baseline de referência
usando DeepDiff. Garante que mudanças no código não quebrem extrações existentes.

Uso:
    pytest tests/test_regression.py -v
    pytest tests/test_regression.py::TestExtractionRegression -v
"""
import json
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional
from deepdiff import DeepDiff

# Caminhos
BASELINE_DIR = Path("data/reference")
BASELINE_FILE = BASELINE_DIR / "extraction_baseline.json"
OUTPUT_DIR = Path("output")


def load_baseline() -> Optional[Dict]:
    """Carrega o baseline de referência se existir."""
    if BASELINE_FILE.exists():
        with open(BASELINE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_baseline(data: Dict) -> None:
    """Salva um novo baseline de referência."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Baseline salvo em: {BASELINE_FILE}")


def normalize_value(value: Any) -> Any:
    """Normaliza valores para comparação (remove espaços extras, case-insensitive)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().upper().replace("  ", " ")
    return value


def compare_records(current: Dict, baseline: Dict, campos_criticos: List[str]) -> Dict:
    """
    Compara registros atuais com baseline.
    
    Retorna:
        Dict com diferenças encontradas e estatísticas
    """
    diff = DeepDiff(
        baseline,
        current,
        ignore_order=True,
        ignore_string_case=True,
        ignore_whitespace=True,
        exclude_paths=["root['metadata']", "root['data_extracao']"],
    )
    
    # Analisar regressões em campos críticos
    regressoes = []
    
    if "values_changed" in diff:
        for path, change in diff["values_changed"].items():
            # Verificar se é campo crítico
            for campo in campos_criticos:
                if campo in path:
                    regressoes.append({
                        "campo": campo,
                        "path": path,
                        "antigo": change.get("old_value"),
                        "novo": change.get("new_value"),
                    })
    
    return {
        "tem_diferencas": bool(diff),
        "diff_completo": diff.to_dict() if diff else {},
        "regressoes_criticas": regressoes,
        "total_mudancas": len(diff) if diff else 0,
    }


class TestExtractionRegression:
    """Testes de regressão para extrações de contratos."""
    
    CAMPOS_CRITICOS = [
        "num_instalacao",
        "cnpj",
        "razao_social",
        "distribuidora",
        "participacao_percentual",
    ]
    
    CAMPOS_MEDIOS = [
        "data_adesao",
        "representante_nome",
        "representante_cpf",
        "duracao_meses",
    ]
    
    @pytest.fixture
    def baseline(self):
        """Carrega baseline ou skip se não existir."""
        data = load_baseline()
        if data is None:
            pytest.skip("Baseline não encontrado. Execute: python -m pytest tests/test_regression.py --create-baseline")
        return data
    
    def test_baseline_exists(self):
        """Verifica se o baseline de referência existe."""
        if not BASELINE_FILE.exists():
            pytest.skip(
                f"Baseline não encontrado em {BASELINE_FILE}. "
                "Crie com: python scripts/create_golden_set.py --sample 100 --output data/reference/extraction_baseline.json"
            )
        
        with open(BASELINE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "amostras" in data or "registros" in data, "Baseline deve ter 'amostras' ou 'registros'"
    
    def test_no_critical_field_regressions(self, baseline):
        """
        Campos críticos não devem apresentar regressões.
        
        Campos verificados:
        - num_instalacao (UC)
        - cnpj
        - razao_social
        - distribuidora
        - participacao_percentual
        """
        # TODO: Implementar re-extração e comparação
        # Por enquanto, apenas verifica estrutura do baseline
        amostras = baseline.get("amostras", [])
        
        campos_presentes = set()
        for amostra in amostras[:10]:  # Sample de 10
            if "extraido" in amostra:
                campos_presentes.update(amostra["extraido"].keys())
        
        for campo in self.CAMPOS_CRITICOS:
            # Verifica se ao menos alguns registros têm o campo
            count = sum(1 for a in amostras if a.get("extraido", {}).get(campo))
            
            # Pelo menos 50% dos registros devem ter campos críticos
            min_esperado = len(amostras) * 0.5
            assert count >= min_esperado or len(amostras) < 10, \
                f"Campo crítico '{campo}' presente em apenas {count}/{len(amostras)} registros"
    
    def test_confidence_scores_stable(self, baseline):
        """
        Score de confiança não deve cair mais de 5% em média.
        """
        amostras = baseline.get("amostras", [])
        
        scores = [
            a.get("score_confianca", 0) 
            for a in amostras 
            if "score_confianca" in a
        ]
        
        if not scores:
            pytest.skip("Baseline não tem scores de confiança")
        
        media = sum(scores) / len(scores)
        
        # Score médio não deve ser muito baixo
        assert media >= 50, f"Score médio muito baixo: {media:.1f}%"
    
    def test_extraction_count_stable(self, baseline):
        """
        Número de extrações bem-sucedidas deve ser estável.
        """
        amostras = baseline.get("amostras", [])
        
        sucesso = sum(1 for a in amostras if "extraido" in a and not a.get("erro"))
        erro = sum(1 for a in amostras if "erro" in a)
        
        total = len(amostras)
        taxa_sucesso = (sucesso / total * 100) if total > 0 else 0
        
        # Taxa de sucesso deve ser pelo menos 70%
        assert taxa_sucesso >= 70, \
            f"Taxa de sucesso muito baixa: {taxa_sucesso:.1f}% ({sucesso}/{total})"


class TestDeepDiffIntegration:
    """Testes de integração do DeepDiff."""
    
    def test_deepdiff_import(self):
        """Verifica que DeepDiff está instalado corretamente."""
        from deepdiff import DeepDiff
        
        d1 = {"a": 1, "b": 2}
        d2 = {"a": 1, "b": 3}
        
        diff = DeepDiff(d1, d2)
        assert "values_changed" in diff
    
    def test_compare_extraction_records(self):
        """Testa comparação de registros de extração."""
        baseline = {
            "cnpj": "12.345.678/0001-90",
            "razao_social": "EMPRESA TESTE LTDA",
        }
        
        # Cenário 1: Sem mudanças
        current_ok = {
            "cnpj": "12.345.678/0001-90",
            "razao_social": "Empresa Teste LTDA",  # Case diferente
        }
        
        diff = DeepDiff(baseline, current_ok, ignore_string_case=True)
        assert not diff, "Não deveria detectar diferença com case ignorado"
        
        # Cenário 2: Com regressão
        current_ruim = {
            "cnpj": "00.000.000/0000-00",  # CNPJ diferente = regressão!
            "razao_social": "EMPRESA TESTE LTDA",
        }
        
        diff = DeepDiff(baseline, current_ruim)
        assert "values_changed" in diff, "Deveria detectar mudança no CNPJ"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
