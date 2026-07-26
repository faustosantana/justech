# Baselines / controles (W3)

Definición: hit si predicción ∩ números FEATURED del día siguiente ≠ ∅.  
Denom = 794 (días con fuerte y draws al día siguiente).  
Seed = 20260726.

| Control | hits | denom | hit_rate | IC95 |
|---------|-----:|------:|---------:|------|
| Oficial T1×T2 | 226 | 794 | 0.284635 | [0.254343, 0.317001] |
| Random one | 152 | 794 | 0.191436 | [0.165581, 0.220262] |
| Random same-k | 212 | 794 | 0.267003 | [0.237406, 0.298843] |
| T1 sin confirmación | 148 | 794 | 0.186398 | [0.160843, 0.214973] |
| Direct T2 (rechazado) | 305 | 794 | 0.384131 | [0.350934, 0.418444] |
| Frecuencia prior top-k | 234 | 794 | 0.29471 | [0.264048, 0.32735] |

Cobertura media día siguiente: 0.18597  
avg k: 1.6855  
Lift oficial / random same-k: **1.066**
