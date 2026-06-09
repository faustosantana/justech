import type { AssistantAction } from "@/lib/assistant-types";

const JAIOS_PATHS: Record<string, (id: string) => string> = {
  product: (id) => `/odoo/products/${id}`,
  customer: (id) => `/odoo/customers/${id}`,
  invoice: (id) => `/odoo/invoices/${id}`,
  vendor: (id) => `/odoo/vendors/${id}`,
  dgcp: (id) => `/dgcp/${id}`,
  task: (id) => `/tasks/${id}`,
};

export function buildQuickViewActions(entityType: string, entityId: string): AssistantAction[] {
  const pathFn = JAIOS_PATHS[entityType];
  const actions: AssistantAction[] = [];
  if (pathFn) {
    actions.push({
      label: "Ver en JAIOS",
      type: "internal_link",
      url: pathFn(entityId),
    });
  }
  return actions;
}
