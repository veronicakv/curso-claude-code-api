"""Normalización de texto previa a validar y guardar.

El contrato la define para ``title`` de tarea y este proyecto la aplica también
al ``name`` de proyecto: se recortan los extremos y se rechaza el valor que no
deja **ningún carácter visible**. No basta ``strip()``: hay invisibles —como
``U+200B``— que lo atraviesan, así que la comprobación es por categoría Unicode,
rechazando ``Cc``, ``Cf``, ``Zl``, ``Zp`` y ``Zs``.
"""

import unicodedata

_CATEGORIAS_INVISIBLES = {"Cc", "Cf", "Zl", "Zp", "Zs"}


def normalizar_texto_requerido(valor: str) -> str:
    """Recorta ``valor`` y exige al menos un carácter visible.

    Levanta ``ValueError`` si tras recortar no queda nada o si todos los
    caracteres restantes son de control o separadores.
    """
    recortado = valor.strip()
    if not recortado:
        raise ValueError("no puede quedar vacío tras recortar los extremos")
    if all(unicodedata.category(ch) in _CATEGORIAS_INVISIBLES for ch in recortado):
        raise ValueError("debe contener al menos un carácter visible")
    return recortado
