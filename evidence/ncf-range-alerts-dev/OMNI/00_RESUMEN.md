# Omni Solutions SRL

Range id=5 prefix=B01

- A_depleted: PASS → {'ok': True, 'state': 'depleted', 'remaining': 0, 'pct': 100.0, 'blocked': True, 'alert_new': True, 'idempotent': True, 'cross_recipients': 0}
- B_expand: PASS → {'ok': True, 'state': 'active', 'next': 47, 'preserved': 47, 'available': 45, 'pct': 19.64, 'authorized': 56, 'consumed': 11}
- C_preventive: PASS → {'ok': True, 'remaining': 20, 'threshold': 20, 'idempotent': True}
- D_critical: PASS → {'ok': True, 'remaining': 5, 'threshold': 5, 'idempotent': True}
- E_expired: PASS → {'ok': True, 'state': 'expired', 'remaining': 31, 'blocked': True}
- F_closed: PASS → {'ok': True, 'state': 'cancelled'}

Empresa OK: True
