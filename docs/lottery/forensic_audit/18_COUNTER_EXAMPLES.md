# 18 — Contraejemplos

El histórico **no** es uniforme. Contraejemplos documentados:

## C1 — Miss sin ninguna relación (dist 5)

Conteo global: **1**
de 552 misses (0.18%).

Casos en la muestra educativa:
- FX-009 (2022-03-22, fuerte 96)

## C2 — Miss donde lo más cercano es vecino T2, no compañero

42 casos
(7.61% de misses). Ver FX con bucket `VECINO_TABLA2`.

## C3 — Exacto tardío (D4–D7)

Existen hits cuya primera aparición ocurre al final de la ventana
(capítulo 08). “Salió” no implica “salió rápido”.

## C4 — Multi-confirmación con miss

Hay activaciones con ≥2 confirmadores que aun así no ven el exacto en 7 días
(ver `confirmation_level_stats` en JSON).

Estos contraejemplos impiden afirmar reglas del tipo “siempre” o “nunca”.
