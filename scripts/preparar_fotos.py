# ---------------------------------------------------------------------------
# scripts/preparar_fotos.py - prepara a foto de um profissional p/ o avatar.
#
# As fotos chegam como o cliente manda: retrato de estudio, selfie de celular,
# print ja recortado. O card do app mostra um CIRCULO pequeno, entao o que
# importa e' o rosto ocupar o quadro - e nao a imagem original inteira.
#
# O que faz: acha o rosto (OpenCV), recorta um QUADRADO centrado nele com folga,
# redimensiona e salva JPEG otimizado em assets/profissionais/.
#
# Sem rosto detectado (perfil fechado, pouca luz), cai num recorte quadrado
# alinhado ao TOPO - em retrato de pessoa o rosto quase sempre esta no terco
# superior, o que erra menos do que centralizar na imagem toda.
#
# I/O e' PIL, nao cv2.imread: o projeto mora em "Area de Trabalho" e o OpenCV
# nao abre caminho com acento no Windows. O cv2 recebe um array em memoria.
#
#   python -m scripts.preparar_fotos <origem.jpg> <nome-no-destino>
#   python -m scripts.preparar_fotos C:\\...\\marcos.jpeg marcos
# ---------------------------------------------------------------------------
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

LADO = 400          # px do lado do quadrado final (card usa ~60px; 400 cobre 3x+)
FOLGA = 2.3         # quantas "alturas de rosto" o quadrado tera
QUALIDADE = 86

_RAIZ = Path(__file__).resolve().parents[1]
DESTINO = _RAIZ / "assets" / "profissionais"


def _detectar_rosto(img: Image.Image):
    """(cx, cy, lado_rosto) do maior rosto, ou None. Tenta frontal e perfil."""
    cinza = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    for arquivo in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
        casc = cv2.CascadeClassifier(cv2.data.haarcascades + arquivo)
        if casc.empty():
            continue
        achados = casc.detectMultiScale(cinza, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(achados):
            x, y, w, h = max(achados, key=lambda r: r[2] * r[3])
            return x + w / 2, y + h / 2, max(w, h)
    return None


def _quadrado(img: Image.Image, folga: float = FOLGA):
    """Caixa (l, t, r, b) quadrada: centrada no rosto, ou no terco superior."""
    L, A = img.size
    achado = _detectar_rosto(img)
    if achado:
        cx, cy, lado_rosto = achado
        lado = min(L, A, lado_rosto * folga)
        origem = "rosto detectado"
    else:
        lado = min(L, A)
        cx, cy = L / 2, lado / 2      # alinhado ao topo
        origem = "sem rosto - recorte pelo topo"

    l = max(0, min(L - lado, cx - lado / 2))
    t = max(0, min(A - lado, cy - lado / 2))
    return (int(l), int(t), int(l + lado), int(t + lado)), origem


def preparar(origem: Path, nome: str, folga: float = FOLGA) -> Path:
    img = Image.open(origem)
    caixa, origem_corte = _quadrado(img, folga)
    recorte = img.convert("RGB").crop(caixa).resize((LADO, LADO), Image.LANCZOS)

    DESTINO.mkdir(parents=True, exist_ok=True)
    saida = DESTINO / f"{nome}.jpg"
    recorte.save(saida, "JPEG", quality=QUALIDADE, optimize=True)

    kb_antes = origem.stat().st_size / 1024
    kb_depois = saida.stat().st_size / 1024
    print(f"{origem.name:>18} {img.size[0]}x{img.size[1]} ({kb_antes:.0f} KB)"
          f"  ->  {saida.name} {LADO}x{LADO} ({kb_depois:.0f} KB)   [{origem_corte}]")
    return saida


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(__doc__ or "", file=sys.stderr)
        print("uso: python -m scripts.preparar_fotos <origem> <nome> [folga]", file=sys.stderr)
        return 2
    origem = Path(sys.argv[1])
    if not origem.is_file():
        print(f"arquivo nao encontrado: {origem}", file=sys.stderr)
        return 1
    folga = float(sys.argv[3]) if len(sys.argv) == 4 else FOLGA
    preparar(origem, sys.argv[2].strip().lower(), folga)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
