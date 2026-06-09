/** Mensajes proactivos del Assistant según módulo activo. */

export type ProactiveAction = {
  label: string;
  question?: string;
  href?: string;
};

export type ProactivePrompt = {
  message: string;
  state: "normal" | "alert" | "attention" | "success";
  actions: ProactiveAction[];
};

const DEFAULT: ProactivePrompt = {
  message:
    "Hola, soy JAIOS. Puedo analizar ventas, precios, documentos, licitaciones y tareas. ¿En qué te ayudo?",
  state: "normal",
  actions: [
    { label: "Ver resumen", question: "¿Qué debo revisar hoy?" },
    { label: "Buscar oportunidades", href: "/dgcp" },
  ],
};

export function getProactivePrompt(pathname: string): ProactivePrompt {
  if (pathname.startsWith("/dashboard")) {
    return {
      message:
        "Hola, encontré información importante para revisar hoy. ¿Quieres que te ayude con prioridades?",
      state: "attention",
      actions: [
        { label: "Ver resumen", question: "¿Qué debo revisar hoy?" },
        { label: "Crear tarea", href: "/tasks" },
        { label: "Revisar documentos", href: "/documents" },
      ],
    };
  }
  if (pathname.startsWith("/prices")) {
    return {
      message:
        "Puedo ayudarte a comparar proveedores, validar stock y preparar cotizaciones.",
      state: "normal",
      actions: [
        { label: "Comparar precios", question: "¿Quién me sale mejor laptop 16GB 512GB?" },
        { label: "Preparar cotización", href: "/prices/drafts" },
      ],
    };
  }
  if (pathname.startsWith("/dgcp") || pathname.startsWith("/oportunidades")) {
    return {
      message:
        "Puedo revisar requisitos, documentos faltantes y preparar expediente.",
      state: "normal",
      actions: [
        { label: "Buscar oportunidades", question: "¿Qué licitaciones hay de computadoras?" },
        { label: "Revisar licitaciones", href: "/dgcp" },
      ],
    };
  }
  if (pathname.startsWith("/documents")) {
    return {
      message:
        "Puedo revisar vigencias de RPE, DGII, TSS y Registro Mercantil.",
      state: "alert",
      actions: [
        { label: "Revisar documentos", question: "¿Tenemos DGII vigente?" },
        { label: "Ver repositorio", href: "/documents" },
      ],
    };
  }
  if (pathname.startsWith("/odoo")) {
    return {
      message: "Puedo analizar ventas, deudas, facturas y clientes.",
      state: "normal",
      actions: [
        { label: "Facturas vencidas", href: "/odoo" },
        { label: "Buscar cliente", question: "Busca todo sobre Banco Ademi" },
      ],
    };
  }
  if (pathname.startsWith("/tasks") || pathname.startsWith("/work")) {
    return {
      message: "Puedo mostrar tareas vencidas, críticas y pendientes por persona.",
      state: "attention",
      actions: [
        { label: "Ver tareas", question: "¿Qué tareas tiene Jennipher?" },
        { label: "Centro de trabajo", href: "/work" },
      ],
    };
  }
  return DEFAULT;
}

const CONV_KEY = "jaios_assistant_conversation_id";

export function getConversationId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem(CONV_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CONV_KEY, id);
  }
  return id;
}

export function resetConversationId(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CONV_KEY, crypto.randomUUID());
}

export function isAssistantDebugEnabled(): boolean {
  if (typeof window === "undefined") return false;
  return (
    localStorage.getItem("jaios-assistant-debug") === "1" ||
    new URLSearchParams(window.location.search).get("assistant_debug") === "1"
  );
}
