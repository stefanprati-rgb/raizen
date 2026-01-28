import shutil
import os
from pathlib import Path

dest_dir = Path(r"c:\Projetos\Raizen\output\revisao_manual_gemini")
dest_dir.mkdir(parents=True, exist_ok=True)

files_to_copy = [
    r"c:\Projetos\Raizen\contratos_por_paginas\05_paginas\CEMIG\SOLAR 70235 - TEREZA CRISTINA_ADT CONDICOES - 00416967000159 - Qualisign.pdf",
    r"c:\Projetos\Raizen\contratos_por_paginas\05_paginas\CEMIG\SOLAR 70244 - SALQUER_ADT 2 CONDICOES - 22680979000129 - Qualisign.pdf",
    r"c:\Projetos\Raizen\contratos_por_paginas\05_paginas\CEMIG\SOLAR 9119 - AUTO POSTO A2 LTDA - 19439445000109.pdf",
    r"c:\Projetos\Raizen\contratos_por_paginas\05_paginas\CEMIG\SOLAR 9144 - POSTO ESTANCIA REAL LTDA_CONDICOES - 14141582000130.pdf",
    r"c:\Projetos\Raizen\contratos_por_paginas\05_paginas\CPFL_PAULISTA\SOLAR - 13433 - AUTO POSTO LIDER ARARAQUARA LTDA - 04490125000106 - Clicksign.pdf"
]

print(f"Copiando arquivos para: {dest_dir}")
for src in files_to_copy:
    try:
        shutil.copy2(src, dest_dir)
        print(f"OK: {Path(src).name}")
    except Exception as e:
        print(f"ERRO ao copiar {src}: {e}")
