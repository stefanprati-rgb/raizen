import pandas as pd
try:
    df = pd.read_excel('C:/Projetos/Raizen/output/DATASET_FINAL_GOLDEN_RAIZEN.xlsx')
    print("="*40)
    print("📊 ESTATÍSTICAS FINAIS - BASE OURO")
    print("="*40)
    
    total = len(df)
    sucesso = len(df[df.status_proc.astype(str).str.contains("OK")])
    
    # Calcular Score numérico
    df['score_val'] = df['score_confianca'].astype(str).str.split('/').str[0]
    df['score_val'] = pd.to_numeric(df['score_val'], errors='coerce')
    
    media = df['score_val'].mean()
    perfeitos = len(df[df.score_val == 11])
    
    print(f"📄 Total Documentos: {total}")
    print(f"✅ Taxa de Sucesso: {sucesso}/{total} ({(sucesso/total)*100:.1f}%)")
    print(f"⭐ Score Médio IA: {media:.2f}/11")
    print(f"🏆 Extração Perfeita (11/11): {perfeitos} ({(perfeitos/total)*100:.1f}%)")
    print("-" * 40)
    print("🏭 Top 5 Distribuidoras:")
    print(df['Distribuidora'].value_counts().head(5).to_string())
    print("-" * 40)
except Exception as e:
    print(f"Erro ao ler estatísticas: {e}")
