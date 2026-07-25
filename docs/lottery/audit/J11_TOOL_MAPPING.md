# J-11 — Tool Mapping (existing → authorized tools)

Legend: **R**=reusable direct · **A**=adapter · **F**=refactor · **N**=new · **X**=must not expose to chat

| Tool | Source | Status | Perms | Risks |
|------|--------|--------|-------|-------|
| get_number_profile | `POST .../history/numbers/profile` | R/A | analyze | Heavy; require dates |
| get_number_history | profile + occurrences | A | analyze | Payload size |
| get_number_occurrences | `.../numbers/occurrences` | R | analyze | Pagination mandatory |
| get_table1_group | `GET .../groups` / tables | R | analyze | OK |
| get_table2_group | same | R | analyze | OK |
| get_companions | analyze / tables number detail | A | analyze | Keep motor-only math |
| get_confirmers | same | A | analyze | Never “strengthen” confirmer |
| get_why_strengthened | `.../why-strengthened` | R | analyze | OK |
| get_next_seven_draws | `.../next-draws` | R | analyze | Horizon clamp |
| compare_numbers | `.../numbers/compare` + history/compare | R/A | analyze | Mode enum internal |
| get_current_signals | profile charts.senales | A | analyze | OK |
| get_signal_detail | occurrence detail | A | analyze | OK |
| get_lottery_results | dashboard/catalog APIs | R | read | Featured only |
| get_active_lotteries | catalog featured / active_scope | R | read | OK |
| get_historical_case | occurrence detail + evidence/by-draw | A | analyze | OK |
| get_frequency_analysis | statistics/matrix endpoints | A | analyze | Advanced |
| get_cycle_analysis | `.../cycles` | R | analyze | OK |
| audit_number | FE auditoria orchestration → APIs | A/F | analyze | Today multi-call in FE |
| explain_methodology | static + presentation helpers | A/N | read | No LLM invent |
| explain_table1 / table2 | tables + copy | A | read | OK |
| get_system_status | admin sync/health | R | **admin only** | Leak risk |
| get_recent_changes | audit logs / sync runs | A | admin | OK |
| get_evidence_summary | Evidence Builder (new) | N | analyze | Core J-11A |
| search_number_relations | relations analyze / conditions search | A | analyze | OK |
| sync_write / dry_run | sync APIs | **X** | — | Ban from conversation |

Each tool schema must include: `methodology_version`, `analysis_scope=FEATURED_SEVEN`, `trace_id`, sample warnings.
