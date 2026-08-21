/**
 * Superficie API DGCP vigente — contrato anti-truncado de `api.ts`.
 * Si alguien elimina wrappers críticos, el test de superficie falla en CI.
 */

export const DGCP_API_SURFACE_CRITICAL = [
  // Listado / oportunidad
  "getDGCPDashboard",
  "getDGCPOpportunities",
  "getDGCPOpportunity",
  "createDGCPOpportunity",
  "applyDGCPAction",
  // Análisis / checklist / documentos
  "analyzeDGCPRequirements",
  "getDGCPAnalysisStatus",
  "getDGCPChecklist",
  "getDGCPBidPackage",
  "getDGCPDocumentMatches",
  "getDGCPProcessDocuments",
  "uploadDGCPProcessDocument",
  "uploadDGCPChecklistDocument",
  "associateDGCPChecklistDocument",
  "manualValidateDGCPRequirement",
  // Expediente
  "prepareDGCPExpediente",
  "getDGCPExpedienteStatus",
  "getDGCPExpedienteDashboard",
  "getDGCPExpedienteScore",
  "getDGCPExpedientePreview",
  "validateDGCPExpedienteFinal",
  "getDGCPComplianceMatrix",
  "markDGCPExpedienteReady",
  "downloadDGCPExpediente",
  "bootstrapDGCPExpedienteContext",
  // Formularios / autollenado
  "previewDGCPForm",
  "autofillDGCPForm",
  "generateDGCPForm",
  "getDGCPRequiredForms",
  "getDGCPMissingFields",
  "resolveDGCPMissingField",
  "getDGCPAutofillTemplates",
  "getDGCPAutofillCanonicalFields",
  "saveDGCPAliasMapping",
  "downloadDGCPAutofillPdf",
  // Process updates
  "getDGCPProcessUpdatesDashboard",
  "getDGCPProcessUpdates",
  "checkDGCPProcessUpdates",
  "markDGCPProcessUpdateReviewed",
  "markDGCPProcessUpdateApplied",
  // Product intelligence / oferta
  "getDGCPProductIntelligence",
  "runDGCPProductIntelligence",
  "searchDGCPProductCandidates",
  "buildDGCPComplianceMatrix",
  "approveDGCPProductIntelligence",
  "rejectDGCPProductIntelligence",
  "getDGCPOfferPreparationCenter",
  "generateDGCPConsolidatedTechnicalOffer",
  // Prep / my-work
  "getDGCPPrepChecklist",
  "setDGCPPrepResponsible",
  "toggleDGCPPrepTask",
  "addDGCPPrepTask",
  "applyDGCPPrepTemplate",
  // Odoo soft bridge
  "retryDGCPOdooSync",
  "getDGCPOdooProductMatches",
  "runDGCPOdooProductMatches",
  "decideDGCPOdooProductMatch",
  // Inteligencia histórica
  "getDGCPHistoricalIntelligence",
  "getDGCPHistoricalSimilar",
  // Fichas técnicas
  "getDGCPTechnicalSheets",
  "detectDGCPTechnicalSheets",
] as const;

export type DgcpApiSurfaceMethod = (typeof DGCP_API_SURFACE_CRITICAL)[number];
