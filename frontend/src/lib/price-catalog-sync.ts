/** Tipos y metadatos — indexación de catálogos de precios */

export interface PriceCatalogSyncSchedule {
  id: string;
  is_enabled: boolean;
  sync_days: number[];
  sync_hour_utc: number;
  include_file_lists: boolean;
  include_omega: boolean;
  include_ingram: boolean;
  include_cecomsa: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

export interface PriceCatalogSyncJob {
  id: string;
  trigger: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  summary: Record<string, unknown>;
  errors: string[];
}

export interface PriceCatalogSyncScheduleUpdate {
  is_enabled?: boolean;
  sync_days?: number[];
  sync_hour_utc?: number;
  include_file_lists?: boolean;
  include_omega?: boolean;
  include_ingram?: boolean;
  include_cecomsa?: boolean;
}

/** ISO weekday: 1=lunes … 7=domingo */
export const WEEKDAY_LABELS: Record<number, string> = {
  1: "Lunes",
  2: "Martes",
  3: "Miércoles",
  4: "Jueves",
  5: "Viernes",
  6: "Sábado",
  7: "Domingo",
};

/** Fuentes que alimentan el índice local de productos (solo listas de precio) */
export const INDEXING_SOURCES = [
  {
    id: "local_fs",
    page: "/documentos/precios",
    trigger: "Indexar listas locales · Sync programado",
    origin: "Archivos locales",
    path: "03_PROVEEDORES/ENTRADAS · PROCESADOS · LISTAS_PRECIOS",
    formats: "Excel (.xlsx, .xls) · CSV",
    fields: [
      "Proveedor · Fabricante · Marca",
      "SKU · MPN · Modelo · Descripción · Categoría",
      "Procesador · RAM · Almacenamiento · Pantalla · SO",
      "Precio (regular, descuento, rebate, preferido) · Moneda",
      "Stock · Tránsito · Garantía",
      "Clasificación comercial · Tipo de producto",
      "Fila original completa (auditoría)",
      "Fecha archivo · Fecha indexación · Versión",
    ],
  },
  {
    id: "onedrive_entradas",
    page: "/documentos/repositorios",
    trigger: "Sync repositorio ENTRADAS (cada ~15 min) · Sync programado",
    origin: "Microsoft 365 / OneDrive",
    path: "Justech-AI/03_PROVEEDORES/ENTRADAS",
    formats: "Excel · CSV descargados desde Graph",
    fields: [
      "Mismos campos que listas locales",
      "graph_file_id · Nombre archivo OneDrive",
      "Proveedor auto-detectado del path o nombre de archivo",
      "Etiqueta price_processed al completar",
    ],
  },
] as const;
