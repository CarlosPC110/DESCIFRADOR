# 🔐 Descifrado de Sustitución Monoalfabética (en Español)

Este proyecto implementa un **descifrador de cifrado por sustitución monoalfabética**, optimizado para el idioma español.  
A diferencia del clásico cifrado César, aquí **no hay rotación fija**: cada letra se sustituye de manera arbitraria.

---

## 🧠 Principios del método

El descifrado se basa en las **propiedades estadísticas del español**:

- La letra **'e'** es la más frecuente (usada como semilla inicial).  
- Se emplea el **orden de frecuencias típico** del español para la inicialización.  
- Se aplica **búsqueda local** mediante **intercambio de letras** (*hill climbing* + *simulated annealing*).  
- La puntuación evalúa:
  - Frecuencias de **bigramas y trigramas**.
  - Presencia de **palabras funcionales comunes**.
  - **Estructura vocálica** del idioma.  
- El texto se procesa **todo en minúsculas**, pero se **conservan los signos, espacios y la letra ñ**.

---

## 🧩 Uso básico

```bash
python main.py -i text.txt --restarts 30 --iters 40000 --seed 42
