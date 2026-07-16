# Just Office SRL

Range id=1 prefix=B01

- A_depleted: PASS → {'ok': True, 'state': 'depleted', 'remaining': 0, 'pct': 100.0, 'blocked': True, 'alert_new': True, 'idempotent': True, 'cross_recipients': 0}
- B_expand: PASS → {'ok': True, 'state': 'active', 'next': 344, 'preserved': 344, 'available': 54, 'pct': 3.57, 'authorized': 56, 'consumed': 2}
- C_preventive: PASS → {'ok': True, 'remaining': 20, 'threshold': 20, 'idempotent': True}
- D_critical: PASS → {'ok': True, 'remaining': 5, 'threshold': 5, 'idempotent': True}
- E_expired: PASS → {'ok': True, 'state': 'expired', 'remaining': 31, 'blocked': True}
- F_closed: PASS → {'ok': True, 'state': 'cancelled'}

Empresa OK: True
