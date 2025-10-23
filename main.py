#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descifrado de sustitución monoalfabética (no rotación fija) usando propiedades del español:
- 'e' es la letra más frecuente (semilla).
- Orden de frecuencias típico en español para inicializar.
- Búsqueda local con intercambio de letras (hill-climb + simulated annealing).
- Puntuación por bigramas/trigramas, palabras funcionales y estructura vocálica.
- TODO en minúsculas; se conservan signos/espacios y la ñ.

# COMENTARIO AGREGADO POR SILVIA
# Cambio 2 en mi RAMA

Uso:
  python descifrar_sustitucion_es.py -i mensaje.txt
  # o pegar por stdin

Parámetros opcionales (ver -h):
  --restarts  número de reinicios (por defecto 10)
  --iters     iteraciones por reinicio (por defecto 20000)
  --seed      semilla aleatoria
  --force-e   fuerza que la letra más frecuente del cifrado mapee a 'e'
"""

import math, random, argparse, sys
from collections import Counter

ALPH = list("abcdefghijklmnñopqrstuvwxyz")  # 27 letras (incluye ñ)
VOWELS = set("aeiou")

# Orden aproximado de frecuencia en español (puedes ajustar si quieres)
SPANISH_FREQ_ORDER = list("eaosrnidltucmpbgyvfqhxzjñkw")

# Bigrams y trigrams muy comunes en español (tabla pequeña pero útil)
BIGRAM_SCORES = {
    "de": 4.5, "en": 4.3, "es": 4.0, "la": 4.0, "el": 3.8, "que": 3.5, "qu": 3.2,
    "re": 3.0, "ra": 2.9, "os": 2.8, "ar": 2.8, "co": 2.7, "te": 2.7, "an": 2.6,
    "as": 2.6, "er": 2.5, "se": 2.5, "or": 2.4, "al": 2.4, "ci": 2.3, "to": 2.2,
    "nt": 2.2, "lo": 2.1, "no": 2.1, "pa": 2.0, "po": 1.9, "ma": 1.8, "is": 1.8,
    "ta": 1.8, "in": 1.7, "na": 1.7, "ro": 1.7, "mi": 1.6, "li": 1.5, "do": 1.5,
    "ue": 1.5, "me": 1.4, "pe": 1.4, "bi": 1.3, "ga": 1.2, "ya": 1.1, "ve": 1.1,
    "ho": 1.0, "va": 1.0, "mo": 1.0
}
TRIGRAM_SCORES = {
    "que": 7.0, "ent": 5.5, "con": 5.0, "los": 4.8, "las": 4.6, "del": 4.6,
    "una": 4.5, "por": 4.4, "est": 4.2, "ela": 3.8, "ela": 3.8, "aci": 3.5,
    "ara": 3.5, "res": 3.4, "dos": 3.3, "par": 3.2, "pro": 3.2, "men": 3.1,
    "ion": 3.0, "ara": 3.0, "era": 2.9, "tra": 2.9, "que": 7.0
}
# Palabras funcionales frecuentes
COMMON_WORDS = [
    "de","la","que","el","en","y","a","los","se","del","las","un","por","con",
    "no","una","su","para","es","al","lo","como","más","pero","sus","le","ya",
    "o","este","sí","porque","cuando","muy","sin","sobre","también","me","hasta"
]

# ---------------- Utilidades ---------------- #

def normalize(text: str) -> str:
    """Quita tildes (conserva ñ) y pasa a minúsculas. Conserva signos/espacios."""
    trans = str.maketrans("áéíóúÁÉÍÓÚüÜ", "aeiouAEIOUuU")
    return text.translate(trans).lower()

def only_letters(text: str) -> str:
    """Solo letras del alfabeto español (incluye ñ)."""
    return "".join([c for c in text if c in ALPH])

def count_letters(text: str) -> Counter:
    return Counter([c for c in text if c in ALPH])

def initial_key_from_freq(ciphertext_letters: str, force_e=True) -> dict:
    """Genera un mapeo inicial cifrada->clara por frecuencia."""
    freq = Counter(ciphertext_letters)
    cipher_order = [c for c,_ in freq.most_common()]
    # Rellenar con letras faltantes para tener permutación completa
    for c in ALPH:
        if c not in cipher_order:
            cipher_order.append(c)
    plain_order = SPANISH_FREQ_ORDER.copy()
    # Asegurar que 'e' esté asignada a la letra más frecuente si force_e
    if force_e and cipher_order:
        # poner 'e' al frente del orden de destino
        if "e" in plain_order:
            plain_order.remove("e")
        plain_order = ["e"] + [x for x in plain_order if x != "e"]
    # Construir mapeo
    mapping = {ciph: plain_order[i % len(plain_order)] for i, ciph in enumerate(cipher_order)}
    # Asegurar que sea una permutación (resolver colisiones)
    mapping = permute_fix(mapping)
    return mapping

def permute_fix(mapping: dict) -> dict:
    """Convierte mapping cifrada->clara en una permutación válida sobre ALPH."""
    used = set()
    result = {}
    for c in ALPH:
        p = mapping.get(c)
        if p in ALPH and p not in used:
            result[c] = p
            used.add(p)
        else:
            result[c] = None
    # Asignar letras faltantes
    leftovers = [x for x in ALPH if x not in used]
    for c in ALPH:
        if result[c] is None:
            result[c] = leftovers.pop(0)
    return result

def apply_mapping(text: str, mapping: dict) -> str:
    """Aplica mapeo cifrada->clara solo a letras ALPH; deja lo demás igual. Todo minúscula."""
    res = []
    for ch in text:
        if ch in ALPH:
            res.append(mapping[ch])
        else:
            res.append(ch)
    return "".join(res)

# ---------------- Scoring ---------------- #

def score_text(plain: str) -> float:
    """Función objetivo: bigramas + trigramas + palabras comunes + regularizadores suaves."""
    s = 0.0
    letters = only_letters(plain)
    n = len(letters)
    if n == 0:
        return -1e9

    # Bigramas
    for i in range(n-1):
        bg = letters[i:i+2]
        s += BIGRAM_SCORES.get(bg, -0.8)  # penalización por bigrama poco común

    # Trigramas
    for i in range(n-2):
        tg = letters[i:i+3]
        s += TRIGRAM_SCORES.get(tg, -0.5)

    # Palabras comunes (en el texto con espacios)
    words = plain.split()
    word_counter = Counter(words)
    for w in COMMON_WORDS:
        c = word_counter.get(w, 0)
        if c:
            s += 6.0 * c  # cada aparición suma

    # Regularizador de proporción vocálica (demasiado baja suele ser malo)
    vowels = sum(1 for ch in letters if ch in VOWELS)
    ratio = vowels / max(1, n)
    # target ~0.43-0.47; penaliza cuadráticamente si se va lejos
    s -= 50.0 * (ratio - 0.45)**2

    return s

# ---------------- Búsqueda (hill-climb + SA) ---------------- #

def random_swap_key(mapping: dict) -> dict:
    """Intercambia dos asignaciones en el rango de destino (claro)."""
    m = mapping.copy()
    # Elegir dos letras destino y permutarlas en la imagen del mapeo
    vals = list(set(m.values()))
    a, b = random.sample(vals, 2)
    # swap en todas las claves que apunten a a o b
    for k in m:
        if m[k] == a:
            m[k] = b
        elif m[k] == b:
            m[k] = a
    return m

def decipher(cipher_norm: str, restarts=10, iters=20000, seed=None, force_e=True):
    if seed is not None:
        random.seed(seed)

    letters_only = only_letters(cipher_norm)
    base_key = initial_key_from_freq(letters_only, force_e=force_e)
    best_key = base_key
    best_plain = apply_mapping(cipher_norm, best_key)
    best_score = score_text(best_plain)

    for r in range(restarts):
        # reinicio: opcionalmente barajar un poco la clave base
        current_key = base_key if r == 0 else shake_key(base_key, shakes=50)
        current_plain = apply_mapping(cipher_norm, current_key)
        current_score = score_text(current_plain)

        T0 = 2.0  # temperatura inicial
        Tmin = 0.01
        for t in range(1, iters+1):
            T = max(Tmin, T0 * (1 - t/iters))  # enfriamiento lineal
            new_key = random_swap_key(current_key)
            new_plain = apply_mapping(cipher_norm, new_key)
            new_score = score_text(new_plain)

            delta = new_score - current_score
            if delta >= 0 or random.random() < math.exp(delta / max(T, 1e-6)):
                # aceptar
                current_key, current_plain, current_score = new_key, new_plain, new_score

                if current_score > best_score:
                    best_key, best_plain, best_score = current_key, current_plain, current_score

    return best_plain, best_key, best_score

def shake_key(key: dict, shakes=30) -> dict:
    m = key.copy()
    for _ in range(shakes):
        m = random_swap_key(m)
    return m

# ---------------- Main ---------------- #

def main():
    ap = argparse.ArgumentParser(description="Descifra sustitución aleatoria usando propiedades del español (minúsculas).")
    ap.add_argument("-i","--input", help="Archivo con el mensaje cifrado. Si no, lee de stdin.")
    ap.add_argument("--restarts", type=int, default=10, help="Reinicios de la búsqueda (default: 10)")
    ap.add_argument("--iters", type=int, default=20000, help="Iteraciones por reinicio (default: 20000)")
    ap.add_argument("--seed", type=int, default=None, help="Semilla aleatoria")
    ap.add_argument("--force-e", action="store_true", help="Forzar que la letra cifrada más frecuente mapee a 'e'")
    args = ap.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        print("Pega el texto cifrado (Ctrl+D en Linux/macOS, Ctrl+Z+Enter en Windows):")
        raw = sys.stdin.read()

    cipher_norm = normalize(raw)  # TODO en minúsculas (con ñ)
    print("\n[+] Normalizado (minúsculas, sin tildes):")
    print(cipher_norm[:400] + ("..." if len(cipher_norm) > 400 else ""))

    # Descifrar
    plain, keymap, score = decipher(
        cipher_norm,
        restarts=args.restarts,
        iters=args.iters,
        seed=args.seed,
        force_e=args.force_e or True  # por defecto, útil en español
    )

    # Mostrar resultados
    print("\n================ RESULTADO ================\n")
    print(plain)
    print("\n================ MAPE0 (cifrada -> clara) ================\n")
    # ordenar por letra clara para entender el alfabeto resultante
    inv = {}
    for ciph, pla in keymap.items():
        inv.setdefault(pla, []).append(ciph)
    # mostrar como pares ordenados
    print("cifrada -> clara")
    for c in ALPH:
        holders = [k for k,v in keymap.items() if v == c]
        if holders:
            for h in sorted(holders):
                print(f"{h} -> {c}")
    print(f"\nScore: {score:.2f}")
    print("\nNota: todo se muestra en minúsculas y los signos/espacios se conservan.")

if __name__ == "__main__":
    main()
