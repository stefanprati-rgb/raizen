"""
Gerador de relatórios HTML para revisão de dados extraídos.
"""
import html
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime


def generate_html_report(
    valid_records: List[Dict[str, Any]],
    review_records: List[Dict[str, Any]],
    output_path: str
) -> None:
    """Gera relatório HTML com resumo da extração e lista de revisão."""
    
    # Estatísticas
    total = len(valid_records) + len(review_records)
    success_rate = (len(valid_records) / total * 100) if total > 0 else 0
    
    # Contar por tipo de alerta
    alert_counts = {}
    for record in review_records:
        alerts = record.get('alertas', '').split('; ')
        for alert in alerts:
            if alert:
                alert_type = alert.split(':')[0] if ':' in alert else alert[:50]
                alert_counts[alert_type] = alert_counts.get(alert_type, 0) + 1
    
    # Contar por modelo
    model_counts = {}
    for record in valid_records + review_records:
        model = record.get('modelo_detectado', 'Desconhecido')
        model_counts[model] = model_counts.get(model, 0) + 1
    
    # Gerar HTML
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Extração - Contratos Raízen</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #ff6b00;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .stat-card.success .value {{ color: #28a745; }}
        .stat-card.warning .value {{ color: #ffc107; }}
        .stat-card.danger .value {{ color: #dc3545; }}
        
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        
        .alert-list {{
            max-height: 100px;
            overflow-y: auto;
            font-size: 12px;
            color: #666;
        }}
        
        .progress-bar {{
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s;
        }}
        
        footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Relatório de Extração - Contratos Raízen</h1>
        <p>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total de Registros</h3>
                <div class="value">{total:,}</div>
            </div>
            <div class="stat-card success">
                <h3>Extraídos com Sucesso</h3>
                <div class="value">{len(valid_records):,}</div>
            </div>
            <div class="stat-card warning">
                <h3>Para Revisão</h3>
                <div class="value">{len(review_records):,}</div>
            </div>
            <div class="stat-card {'success' if success_rate >= 95 else 'warning' if success_rate >= 80 else 'danger'}">
                <h3>Taxa de Sucesso</h3>
                <div class="value">{success_rate:.1f}%</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Progresso Geral</h2>
            <div class="progress-bar">
                <div class="progress-bar-fill" style="width: {success_rate}%"></div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Distribuição por Modelo</h2>
            <table>
                <tr>
                    <th>Modelo</th>
                    <th>Quantidade</th>
                    <th>Percentual</th>
                </tr>
                {''.join(f'''
                <tr>
                    <td>{model}</td>
                    <td>{count:,}</td>
                    <td>{count/total*100:.1f}%</td>
                </tr>
                ''' for model, count in sorted(model_counts.items(), key=lambda x: -x[1]))}
            </table>
        </div>
        
        <div class="section">
            <h2>⚠️ Tipos de Alerta Mais Comuns</h2>
            <table>
                <tr>
                    <th>Tipo de Alerta</th>
                    <th>Ocorrências</th>
                </tr>
                {''.join(f'''
                <tr>
                    <td>{html.escape(alert_type)}</td>
                    <td>{count:,}</td>
                </tr>
                ''' for alert_type, count in sorted(alert_counts.items(), key=lambda x: -x[1])[:10])}
            </table>
        </div>
        
        <div class="section">
            <h2>🔍 Registros para Revisão Manual ({len(review_records):,})</h2>
            <table>
                <tr>
                    <th>Arquivo</th>
                    <th>Razão Social</th>
                    <th>CNPJ</th>
                    <th>Score</th>
                    <th>Alertas</th>
                </tr>
                {''.join(f'''
                <tr>
                    <td>{html.escape(str(r.get("arquivo_origem", "N/A")))}</td>
                    <td>{html.escape(str(r.get("razao_social", "N/A"))[:50])}</td>
                    <td>{html.escape(str(r.get("cnpj", "N/A")))}</td>
                    <td>
                        <span class="badge {'badge-success' if r.get('confianca_score', 0) >= 70 else 'badge-warning' if r.get('confianca_score', 0) >= 50 else 'badge-danger'}">
                            {r.get('confianca_score', 0)}%
                        </span>
                    </td>
                    <td>
                        <div class="alert-list">{html.escape(str(r.get("alertas", "")))}</div>
                    </td>
                </tr>
                ''' for r in review_records[:100])}
                {f'<tr><td colspan="5" style="text-align:center; color:#666;">... e mais {len(review_records)-100} registros</td></tr>' if len(review_records) > 100 else ''}
            </table>
        </div>
        
        <footer>
            <p>Extrator de Contratos Raízen - Desenvolvido com ❤️</p>
        </footer>
    </div>
</body>
</html>"""
    
    Path(output_path).write_text(html_content, encoding='utf-8')
