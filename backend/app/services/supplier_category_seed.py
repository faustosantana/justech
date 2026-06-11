"""Categorías base del directorio de proveedores."""

from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "categoria"


BASE_SUPPLIER_CATEGORIES: list[dict] = [
    {
        "name": "Toners y consumibles",
        "synonyms": ["toner", "toners", "cartucho", "cartuchos", "consumible", "consumibles", "tinta", "tintas", "recarga"],
    },
    {
        "name": "Computadoras nuevas",
        "synonyms": ["computadora nueva", "pc nueva", "desktop nuevo", "equipo nuevo"],
    },
    {
        "name": "Computadoras usadas",
        "synonyms": ["computadora usada", "pc usada", "equipo usado", "refurbished", "reacondicionada"],
    },
    {
        "name": "Laptops",
        "synonyms": ["laptop", "portátil", "portatil", "notebook", "ultrabook"],
    },
    {
        "name": "Servidores",
        "synonyms": ["server", "servidor", "rack server", "torre servidor"],
    },
    {
        "name": "Networking",
        "synonyms": ["red", "network", "switch", "switches", "router", "routers", "access point", "wifi"],
    },
    {
        "name": "Cableado estructurado",
        "synonyms": ["cable", "cables", "patch panel", "rack", "racks", "utp", "fibra", "canaleta"],
    },
    {
        "name": "Cámaras de seguridad",
        "synonyms": ["cámara", "camara", "camaras", "cctv", "videovigilancia", "dvr", "nvr"],
    },
    {
        "name": "Control de acceso",
        "synonyms": ["acceso", "biométrico", "biometrico", "tarjeta proximidad", "torniquete"],
    },
    {
        "name": "Alarmas",
        "synonyms": ["alarma", "intrusión", "intrusion", "sensor", "panel alarma"],
    },
    {
        "name": "UPS y energía",
        "synonyms": ["ups", "batería", "bateria", "regulador", "pdu", "energía", "energia"],
    },
    {
        "name": "Licencias Microsoft",
        "synonyms": ["microsoft", "office 365", "microsoft 365", "windows", "licencia microsoft", "csp"],
    },
    {
        "name": "Software",
        "synonyms": ["software", "aplicación", "aplicacion", "licencia software", "saas"],
    },
    {
        "name": "Impresoras",
        "synonyms": ["impresora", "multifuncional", "plotter", "printer"],
    },
    {
        "name": "Repuestos",
        "synonyms": ["repuesto", "spare part", "refacción", "refaccion", "componente"],
    },
    {
        "name": "Muebles de oficina",
        "synonyms": ["mueble", "muebles", "escritorio", "silla", "archivador", "mobiliario"],
    },
    {
        "name": "Papelería",
        "synonyms": ["papeleria", "papel", "útiles", "utiles", "oficina"],
    },
    {
        "name": "Equipos audiovisuales",
        "synonyms": ["audio", "video", "pantalla", "monitor", "televisor", "soundbar"],
    },
    {
        "name": "Proyectores",
        "synonyms": ["proyector", "projector", "pantalla proyección"],
    },
    {
        "name": "Telefonía IP",
        "synonyms": ["telefonia", "teléfono ip", "telefono ip", "pbx", "voip", "grandstream", "yealink"],
    },
    {
        "name": "Servicios técnicos",
        "synonyms": ["servicio técnico", "servicio tecnico", "soporte", "mantenimiento", "reparación"],
    },
    {
        "name": "Instaladores",
        "synonyms": ["instalador", "instalación", "instalacion", "montaje", "implementación"],
    },
    {
        "name": "Transporte y mensajería",
        "synonyms": ["transporte", "mensajería", "mensajeria", "courier", "envío", "envio", "logística"],
    },
    {
        "name": "Consultoría",
        "synonyms": ["consultoría", "consultoria", "consultor", "asesoría", "asesoria"],
    },
]

# Mapeo licitaciones → categorías
TENDER_REQUIREMENT_KEYWORDS: dict[str, list[str]] = {
    "laptops": ["laptop", "portátil", "portatil", "notebook"],
    "impresoras": ["impresora", "multifuncional", "printer"],
    "toners": ["toner", "cartucho", "consumible", "tinta"],
    "camaras": ["cámara", "camara", "cctv", "hikvision", "dahua"],
    "licencias": ["licencia", "microsoft", "office 365", "software"],
    "servidores": ["servidor", "server", "storage"],
    "software": ["software", "aplicación", "saas"],
    "networking": ["switch", "router", "networking", "ubiquiti"],
    "ups": ["ups", "energía", "batería"],
    "cableado": ["cable", "patch panel", "rack", "utp"],
}
