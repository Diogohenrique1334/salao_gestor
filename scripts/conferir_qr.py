# ---------------------------------------------------------------------------
# scripts/conferir_qr.py - confere se as artes geradas sao mesmo legiveis.
#
#   python -m scripts.conferir_qr
#
# Decodifica cada PNG de divulgacao/ em varias escalas (ate 25%) para simular
# a compressao do WhatsApp e a leitura de longe. Arte bonita com QR ilegivel e'
# pior que nenhuma arte.
# ---------------------------------------------------------------------------
from __future__ import annotations

import glob
import os
import sys

import cv2
import numpy as np

URL_ESPERADA = "https://salao-gestor.onrender.com"
ESCALAS = (1.0, 0.7, 0.5, 0.35, 0.25)


def main() -> None:
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arquivos = sorted(glob.glob(os.path.join(raiz, "divulgacao", "*.png")))
    if not arquivos:
        print("Nada em divulgacao/. Rode antes: python -m scripts.gerar_arte_qr")
        sys.exit(1)

    det = cv2.QRCodeDetector()
    falhou = False
    print("escalas: " + "  ".join(f"{int(e * 100)}%" for e in ESCALAS))
    for caminho in arquivos:
        # cv2.imread NAO abre caminho com acento no Windows (o projeto mora
        # em "Area de Trabalho"); fromfile+imdecode resolve.
        img = cv2.imdecode(np.fromfile(caminho, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"  {os.path.basename(caminho):24} NAO FOI POSSIVEL ABRIR")
            falhou = True
            continue
        marcas = []
        for e in ESCALAS:
            alvo = img if e == 1.0 else cv2.resize(
                img, None, fx=e, fy=e, interpolation=cv2.INTER_AREA
            )
            texto, _, _ = det.detectAndDecode(alvo)
            ok = texto == URL_ESPERADA
            falhou = falhou or not ok
            marcas.append("OK " if ok else "FALHA")
        print(f"  {os.path.basename(caminho):24} " + "  ".join(marcas))

    print("")
    if falhou:
        print("[X] alguma escala falhou - nao distribua ainda.")
        sys.exit(1)
    print("[OK] todas as artes decodificam para a URL correta.")


if __name__ == "__main__":
    main()
