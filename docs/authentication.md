# Autenticación — JAIOS

## Flujo de login

```
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "********",
  "tenant_slug": "justech"  // opcional
}
```

**Respuesta:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "abc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "tenant_id": "uuid",
  "role": "owner"
}
```

## Headers requeridos en requests autenticados

| Header | Descripción |
|--------|-------------|
| `Authorization` | `Bearer <access_token>` |
| `X-Tenant-ID` | UUID del tenant activo |

## Refresh

```
POST /api/v1/auth/refresh
{ "refresh_token": "abc..." }
```

## Roles RBAC

| Rol | Descripción |
|-----|-------------|
| `owner` | Control total del tenant |
| `admin` | Administración sin transferencia |
| `manager` | Gestión operativa |
| `member` | Acceso estándar |
| `viewer` | Solo lectura |

## Seed de desarrollo

```bash
make seed
# admin@justech.do / JaiosAdmin2026!
# Tenant: justech
```
