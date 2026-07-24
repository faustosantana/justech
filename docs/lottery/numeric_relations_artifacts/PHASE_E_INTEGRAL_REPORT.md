# Fase E — Reporte integral de validación

**Ambiente:** `jaios_lottery_dev` (read-only)
**Recomendación:** **GO_CONDICIONADO**

Motor/histórico/API/chat OK en DEV. Riesgo residual de draws duplicados por sync aceptado temporalmente. UI visual requiere verificación en navegador admin. Producción no autorizada.

## Pruebas automatizadas (rama)

- `tests/test_lottery_numeric_relations_*.py` → **43 passed**
- Incluye math, analysis, grouping, metadata dedupe, phase C+D
- Fallos preexistentes del entorno local (no introducidos por esta rama):
  - `test_lottery_phase4_chat.py`: falta `httpx` en venv mínimo
  - `test_lottery_ai_admin_center.py`: SQLAlchemy/`Mapped[str | None]` con Python 3.9 al importar modelos completos

## Confirmaciones

- Sync modificado: **NO**
- Producción modificada: **NO**
- Fórmulas / rango alterados: **NO**

## A — Motor matemático

- OK: `{'ok': True, 'table1_rows': 100, 'table2_rows': 100, 'table1_groups': 30, 'table2_groups': 43, 'range': '1..100', 'tables_separate': True, 'example_t1_1': {'visible': '0.0008196721', 'code': 34}, 'example_t2_1': {'visible': '1220.00000000', 'code': 5}}`

## B — Histórico real

- Target draw 26: `{'draw_id': 'a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad', 'numbers': ['29', '01', '26'], 'expected': ['29', '01', '26'], 'ok': True}`
- Limits: `{"last_5": {"count": 5, "draw_ids": ["a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad", "56521f71-0a78-4b77-8125-db9075099e75", "ff8029d0-cafa-4207-b9b2-6686d2fda63b", "8d654a4f-bbdf-457c-a38c-297105fa85a5", "cbe734de-192c-4cce-a942-1ed4f13aca13"], "null_times": 5, "includes_target": true}, "last_10": {"count": 10, "draw_ids": ["a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad", "56521f71-0a78-4b77-8125-db9075099e75", "ff8029d0-cafa-4207-b9b2-6686d2fda63b", "8d654a4f-bbdf-457c-a38c-297105fa85a5", "cbe734de-192c-4cce-a942-1ed4f13aca13", "1ea5396e-b6ed-42cf-a743-77f260e61d5e", "5d4f6a83-658d-496f-a514-890d13e7b306", "925dfaa6-3be9-4546-8ca5-500aab0e3426", "1f77a7f3-94a6-42cf-adce-b5f5bef86635", "9815d123-273b-4ef1-b47c-207944caaa48"], "null_times": 10, "includes_target": true}, "last_20": {"count": 20, "draw_ids": ["a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad", "56521f71-0a78-4b77-8125-db9075099e75", "ff8029d0-cafa-4207-b9b2-6686d2fda63b", "8d654a4f-bbdf-457c-a38c-297105fa85a5", "cbe734de-192c-4cce-a942-1ed4f13aca13", "1ea5396e-b6ed-42cf-a743-77f260e61d5e", "5d4f6a83-658d-496f-a514-890d13e7b306", "925dfaa6-3be9-4546-8ca5-500aab0e3426", "1f77a7f3-94a6-42cf-adce-b5f5bef86635", "9815d123-273b-4ef1-b47c-207944caaa48", "48a74b57-f371-403d-9ad8-8894750e87f9", "cabb6301-a668-4b58-b4f6-cbdfc58ea29a", "f6c46036-a17d-449b-bd66-82894115f6ac", "6070919b-53fd-448f-972e-a8c46cc0bcb0", "51573ed9-4947-45d3-b191-c1dfdf696d9b", "a5ba9dd3-6950-48f3-8b19-afd2eea9e3ab", "8c058778-782a-4caf-8582-3d55ebec968f", "7128bcf5-864a-45d0-b033-41acf12cad15", "2726ab8d-869c-41b7-a991-8cad481a73ea", "3968f5fd-0ab7-4fef-bde1-f163d98e1ba9"], "null_times": 20, "includes_target": true}, "all": {"count": 106, "draw_ids": ["a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad", "56521f71-0a78-4b77-8125-db9075099e75", "ff8029d0-cafa-4207-b9b2-6686d2fda63b", "8d654a4f-bbdf-457c-a38c-297105fa85a5", "cbe734de-192c-4cce-a942-1ed4f13aca13", "1ea5396e-b6ed-42cf-a743-77f260e61d5e", "5d4f6a83-658d-496f-a514-890d13e7b306", "925dfaa6-3be9-4546-8ca5-500aab0e3426"…`

## C/D — Reglas + dedupe metadata

- `{'has_draw_ids_count': True, 'has_internal_discarded': True, 'has_content_dup_flag': True, 'kept_separate': True, 'sample': {'draw_ids_analyzed_count': 10, 'internal_dedupe_discarded_count': 0, 'possible_content_duplicate_draws_detected': False, 'sync_duplicate_policy': 'Draws with identical lottery/date/numbers but different draw_id remain separate occurrences. Sync is not modified; duplicates are not hidden.'}}`

## E — API schemas

- `{'rejects_0': True, 'rejects_101': True, 'all_ok': True, 'requires_k': True}`

## G — Chat / Huawei

- `{"Analiza el 26 en las últimas 10 veces que salió en Leidsa.": {"kind": "tool", "tool": "lottery_analyze_numeric_relations", "params": {"observed_number": 26, "number": "26", "lotteries": ["Leidsa"], "occurrence_mode": "last_k", "occurrence_k": 10, "lottery": "Leidsa"}, "ok": true}, "Analiza el 34 en todas las ocurrencias disponibles en Leidsa.": {"kind": "tool", "tool": "lottery_analyze_numeric_relations", "params": {"observed_number": 34, "number": "34", "lotteries": ["Leidsa"], "occurrence_mode": "all", "lottery": "Leidsa"}, "ok": true}, "Analiza el 45 en Leidsa y Loteka con las últimas 20 veces.": {"kind": "tool", "tool": "lottery_analyze_numeric_relations", "params": {"observed_number": 45, "number": "45", "lotteries": ["Leidsa", "Loteka"], "occurrence_mode": "last_k", "occurrence_k": 20}, "ok": true}, "¿Cuáles compañeros están más fuertes cuando sale el 18?": {"kind": "clarify", "tool": null, "params": {"number": "18", "observed_number": 18, "pending_slots": ["lottery", "occurrence_limit"]}, "ok": true}, "Analiza el 26.": {"kind": "clarify", "tool": null, "params": {"number": "26", "pending_slots": ["lottery", "period"]}, "ok": true}, "empty_no_invention": {"ok": true, "excerpt": "Analicé el número observado 26 (código madre 26) en Leidsa con límite «todas las ocurrencias». No encontré ocurrencias históricas donde saliera ese número, así que no hay compañeros fortalecidos ni ranking que reportar. No invento compañero"}}`

## I — E2E (resumen)

### E2E 1: N=26
- Loterías: ['Leidsa']
- Límite: {'mode': 'last_k', 'k': 10}
- Ocurrencias usadas/encontradas: 10/106
- Compañeros: [27, 38]
- draw_ids: ['a1c9bcef-cbb5-4c61-a878-c9c8723aa1ad', '56521f71-0a78-4b77-8125-db9075099e75', 'ff8029d0-cafa-4207-b9b2-6686d2fda63b', '8d654a4f-bbdf-457c-a38c-297105fa85a5', 'cbe734de-192c-4cce-a942-1ed4f13aca13', '1ea5396e-b6ed-42cf-a743-77f260e61d5e', '5d4f6a83-658d-496f-a514-890d13e7b306', '925dfaa6-3be9-4546-8ca5-500aab0e3426', '1f77a7f3-94a6-42cf-adce-b5f5bef86635', '9815d123-273b-4ef1-b47c-207944caaa48']
- Ranking top: 27=0, 38=0
- Metadata dedupe: discarded=0, content_dups=False
- Target draw numbers: [29, 1, 26]

```
Analicé el número observado 26 (código madre 26) en Leidsa.
Límite solicitado: últimas 10 ocurrencias. Ocurrencias encontradas en histórico: 106; usadas: 10.
Compañeros de Tabla 1: 27, 38.
Primero en el ranking: 27 con puntuación 0.
Ranking completo (incluye score 0):
1. 27 — score 0 (T2=53, vecinos 68, 76, 92)
2. 38 — score 0 (T2=44, vecinos )
Aclaración: es una señal histórica del método de relaciones numéricas; no es certeza ni garantía de resultados futuros, ni recomendación de apuestas.
```

### E2E 2: N=34
- Loterías: ['Leidsa']
- Límite: {'mode': 'all'}
- Ocurrencias usadas/encontradas: 115/115
- Compañeros: [1, 17, 33, 49, 76]
- draw_ids: ['1871b32e-6d26-4a30-9ce5-8f855f4685d5', '6b8cf2d3-e12b-449a-8683-098001adb73d', 'b2a92b86-edc3-4d66-9d19-8d00bde69cb5', 'ae7e982e-bbad-4ea5-a6dd-66f402b66b0e', 'f651d94f-8e4d-423b-b998-1af9832364f5', 'eb22ab80-8a99-4b59-b8fb-abe6ca60c3d4', '3bc1412a-27cf-4992-81cb-89c2a5f931e9', '8e93b360-1ff3-46c8-8053-a1d97c08c4c8', 'be7aba80-24b7-4552-bfe1-5640070ba2fa', 'efb060d0-6c2a-4a82-9d2a-8e35dfd40444', 'ee44a49e-3013-4346-b497-a3b93d824e8c', '3b261d81-2ccb-4258-a97d-7da080913211', '3076ddee-2c8f-4130-80a5-dc186c8c67a6', '74e088ff-53df-4755-a5a9-18c007555334', '2b49f69b-b81a-4729-96e5-28b63da6f463', 'aebd4f61-4f06-4919-815f-772145c16895', '1a690a77-379b-4fe9-83e9-fc05648d702c', 'a7edab89-170e-4dac-bc3a-b25d09770d6f', 'b5806b86-db69-4bf9-8635-ef91bb5437eb', '0a308122-798a-4f6a-993d-0a446e2e2c23', '0407fa7f-4bad-4d97-8f11-04ebdfaac35d', '3ddccb83-02f7-4476-b498-97a1f14697a9', '128dbbf4-03d6-4918-b8d4-8d592fc465a6', 'bd598603-2883-4b98-b7e8-c0d96f138ce5', '39843a64-f27e-47b0-bfe2-da88eed57767', '1bc48c49-9f5b-4a04-b798-0f4c87756df4', 'be2e694c-8687-47c2-afbc-103f1d823f47', '630e6014-bccb-47f6-b1d1-69b323ea5ff2', 'e77e1761-69cc-4274-b57d-97674ab57d06', '4b816ea0-ca6f-41be-bf75-6c2c4b2c0804', '96fbf740-9a83-4295-a6cf-c92ee941c364', '3bf58b64-de2a-48e1-8279-4c22291c1800', 'b3b53e37-5955-4b01-8487-ec4649e7827a', '1b6ee2cb-7445-41b9-9ac7-7ba55d0c3f60', '9f7bec9a-fc9d-4408-9989-09380b9efe3b', 'dbe2cf59-ba5b-4a85-ab49-bfb1f149d67c', '11fc52e4-2709-4a86-9790-b02e1b2b5b16', '1d3add6e-acf1-473c-8b5a-77552c36d101', '3e6b3031-6c3f-42c4-9ba5-70d3170bb245', '237f784b-f405-4909-b2b1-4bbb844dc091', '73a3974b-da3f-4be6-9a46-319a4c3ea882', '05a69da7-c744-468b-b40c-a2f9f9150779', 'f529c04d-6fa5-4914-9ba6-f597d9a29e8b', 'e5d5de5d-e79b-4567-97c3-1d0b4ff219cd', '0a694245-15bc-4c8f-8e4a-d9c5b265c3dd', 'c9539a9e-4fbf-4d71-9129-838bbb29a24b', 'e7b2f05a-8c8c-4785-932e-d9686a96c197', '3a1aad0e-eba8-4e9e-94e3-ac1399446c21', '9202fa4d-cb10-4040-be5c-ef719f0ff3ef', '321abf84-3c11-4b60-83f5-5e20ef8496c0', '2114cbe0-4e58-4321-982a-ec725fd926cb', 'ba817fdf-5857-4520-9ad9-be33ad8db8fd', '65612906-d2f9-4980-9e7a-38d34e732a60', '91406dde-02a6-4b39-9f1d-03d4e703d74c', '5f83688c-55e1-4a9f-b4cc-f43bcff3d786', '6f38bb51-0a16-4a74-a84e-140967af5881', '6ac069c9-dca5-4789-9320-3954d75a7b63', 'a8524bfd-ba58-4722-835c-445b83294629', '5b311702-98a7-4dda-a8eb-98ad801556db', '3a0123a1-c769-41e8-a3f0-759a2c3ff4e6', '0b2e0d9a-2ec9-4c90-aa29-12394edc56df', 'f7e75f7d-ea78-4582-af38-bcd5e421eb5c', '9c11c954-bf69-4c76-8129-6ed159a1c661', 'a6482a39-b5f9-4a46-93dc-e4561eafef6e', 'c5396aa6-36c3-4321-bf37-729a5caa8e7f', '938535c3-c719-435e-b96a-7dc223c3a191', '17337227-49d1-46a6-b9af-c52aef88d81e', '51c06ac7-bc31-4dd4-8b94-192967bea64f', 'e403f1cd-274c-4562-a0bf-5706a57ba410', '2f392ab9-ee5d-4c31-960d-b1cef82c9877', 'abc40342-110b-446e-8604-41ce1e98008b', 'df238bbf-83e5-4c91-9578-01429e032611', 'c278c10f-ea4c-4067-9589-6472ada66cd5', 'cab8b485-08c0-448d-afb6-af34b93bb6f2', '04cf9cae-44b1-4dce-852e-fe589a940cee', '7085a99a-eb20-4099-b87b-af216019810d', '79e3e2fd-2587-4f92-ae3a-94d9f1d92dff', '6bc33be3-9a86-467a-be7e-65f6e5ec42e9', '8eb9770e-a667-49fd-9f6d-7cbc41a7a68b', 'f194da35-2f5e-4c67-be88-8eb0dfd730fe', '22df2a8f-35ce-4cd6-b0a9-5a315e657e0f', '8bcc2955-1cb6-4ccb-a75d-770a173b70c4', 'fbe2f68d-c172-4926-b9a9-f964435b94b0', 'd45e3cbb-3b50-4431-915e-aa7cf21be328', 'add9f0e2-951e-4a15-ab1d-bad11a3cf20e', 'efd139f6-5356-4240-8a51-aaf1a67a8f6f', '464532c3-6127-4d01-8ea3-5801a5d655c6', '1c91831e-ddb1-44c1-9bfd-22e2a74ad9dc', 'c681e79b-c668-4901-bc2d-45df7fd24241', 'd7c0cd4a-2464-47b6-acd7-b9527b0b6a00', 'c8bf87d4-9b32-4ca3-8576-407deb21fc58', '08544580-4e65-4a4d-9bae-778b1a115fe6', 'fc743e20-5840-4c69-99cb-2868aac8f322', '56d6fccd-254a-478c-b946-621003ebcb95', '1f891177-27e2-43b1-9010-7c90980aefaa', '58982cb1-65be-46f4-a6a5-599bbdef5ebe', '0eb08cb6-0cce-458f-ac1a-fb313d29452c', '1049c6e3-b273-4745-9c15-8549cfaa62b9', '60ab475a-1f44-46bd-9d55-72ae6025c3db', '482fcba8-e116-4431-a11e-6b16bcc5db54', '4fa18222-589f-452f-ab0b-50904c6f99c1', '9d28aa48-57e3-4ce0-8a28-6d4de4820a2f', '0bef7f8e-73e2-4f53-afba-165ff8c5266d', 'a22aaf21-f454-47c9-bec5-0084665b1a44', '3fb6235d-5b66-4710-bb24-a67b64e22a7a', 'daff3c76-f584-443a-b301-2b0bcf6eb554', '6265abcd-3a3d-4285-972c-85c28d2dddb5', 'ed3d58bf-9cfc-4c8e-97f1-215206815d50', 'c5fac68d-ebbb-4497-894d-51d322f166f1', '04f33444-0853-4e1b-bac3-b1a5b984ada2', '37ee956c-d662-4dbe-9f89-a58981557767', '5d76e47f-b31d-4a76-b199-d6aeeefe60ca', 'aca3c91b-4726-46d1-be24-3f78b9b3ff43', '0395603c-a44a-4b9a-b34e-c25d80074e4c', '01105fc3-7a8a-4f44-9f4b-65a048c3846e']
- Ranking top: 76=9, 17=2, 1=0, 33=0, 49=0
- Metadata dedupe: discarded=0, content_dups=False

```
Analicé el número observado 34 (código madre 34) en Leidsa.
Límite solicitado: todas las ocurrencias. Ocurrencias encontradas en histórico: 115; usadas: 115.
Compañeros de Tabla 1: 1, 17, 33, 49, 76.
Primero en el ranking: 76 con puntuación 9.
Vecinos que lo fortalecieron: 27, 68, 92.
Sorteos de refuerzo: 68 en Quiniela Leidsa (2025-09-14, pos 3); 92 en Quiniela Leidsa (2024-11-01, pos 2); 68 en Quiniela Leidsa (2023-07-25, pos 3); 27 en Quiniela Leidsa (2020-10-08, pos 1); 92 en Quiniela Leidsa (2020-09-27, pos 2); 68 en Quiniela Leidsa (2019-06-19, pos 3).
Ranking completo (incluye score 0):
1. 76 — score 9 (T2=53, vecinos 27, 68, 92)
2. 17 — score 2 (T2=59, vecinos 13)
3. 1 — score 0 (T2=5, vecinos 10, 100)
4. 33 — score 0 (T2=85, vecinos )
5. 49 — score 0 (T2=72, vecinos )
Aclaración: es una señal histórica del método de relaciones numéricas; no es certeza ni garantía de resultados futuros, ni recomendación de apuestas.
```

### E2E 3: N=45
- Loterías: ['Leidsa', 'Loteka']
- Límite: {'mode': 'last_k', 'k': 20}
- Ocurrencias usadas/encontradas: 20/240
- Compañeros: [69, 80]
- draw_ids: ['9291acde-9274-4aba-bc9a-b4f286c5124b', '554317bf-afe3-4eaf-84b0-679d294ab966', 'b6459b0b-7f53-4395-9166-ac681a511171', '401e96d7-3a95-43ae-a175-2d33478b3b82', 'c6ba1b7a-4e4a-46ec-b3b6-4abbe5ec0c65', '198a86ef-7d88-4f92-ac18-8f8d72e69e03', '317ccb4d-73c7-4e6e-bbc5-05680e68818a', 'a4410235-0d48-495f-a5eb-fb51518ee78e', '3c728a13-23b0-457b-b4d1-64e87d7a9d16', '4b7cc8f1-9bad-46bd-aa3d-90cc6c3f931b', 'f56a2253-9291-4a38-b86e-f1b97ed3f1c0', '2a0340a0-efba-4c9f-a244-b8720e8b72d1', 'c27d9432-c4c3-4cce-a087-691481998d96', '2e6c6d1c-130d-4f43-a2fb-4e00ac61adaa', '232e9858-67ec-4f4e-956b-8cfe4401ff99', '2374c9be-d002-4ee1-a2db-b36cf612fb30', 'e727eee5-06ae-4b9b-a1a1-c8f5f7d42621', '3bbcbcd6-5426-4a86-b717-a285ea3ec008', '4f93a13f-0199-4efc-bad9-7aea78cfcc30', '5d36d0b7-3b2b-4761-9aed-c4c25b70b260']
- Ranking top: 69=4, 80=0
- Metadata dedupe: discarded=0, content_dups=False

```
Analicé el número observado 45 (código madre 45) en Leidsa, Loteka.
Límite solicitado: últimas 20 ocurrencias. Ocurrencias encontradas en histórico: 240; usadas: 20.
Compañeros de Tabla 1: 69, 80.
Primero en el ranking: 69 con puntuación 4.
Vecinos que lo fortalecieron: 57, 91.
Sorteos de refuerzo: 57 en Quiniela Leidsa (2026-06-01, pos 1); 57 en Quiniela Loteka (2026-04-28, pos 1); 91 en Quiniela Leidsa (2026-01-31, pos 1); 91 en Quiniela Loteka (2025-12-05, pos 1).
Ranking completo (incluye score 0):
1. 69 — score 4 (T2=47, vecinos 11, 57, 91)
2. 80 — score 0 (T2=13, vecinos 8)
Aclaración: es una señal histórica del método de relaciones numéricas; no es certeza ni garantía de resultados futuros, ni recomendación de apuestas.
```

## Riesgos residuales

[
  {
    "id": "SYNC_CONTENT_DUPLICATE_DRAWS",
    "severity": "accepted_temporary",
    "description": "Distinct draw_id may share lottery/date/identical numbers with different source_reference. Counted as separate occurrences. Sync not modified."
  }
]

## Fallos introducidos

[]

## Fallos pendientes

- Verificación visual completa en navegador (capturas) pendiente de sesión admin autenticada.
- Suite frontend e2e del monorepo no ejecutada en este entorno mínimo.

## Pruebas automatizadas

Ver `PHASE_E_PYTEST.txt` (generado por el runner).
