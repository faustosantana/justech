/** Guía de activos corporativos para fichas técnicas PDF — sincronizado con docs/FICHAS_TECNICAS_ACTIVOS_CORPORATIVOS.md */

export type BrandingAssetGuide = {
  key: "logo" | "signature" | "stamp";
  label: string;
  expectedFilename: string;
  format: string;
  sizeHint: string;
  backgroundHint: string;
  uploadHint: string;
  managePath: string;
  fieldKey?: string;
};

export const TECH_SHEET_BRANDING_GUIDE: Record<string, BrandingAssetGuide> = {
  logo: {
    key: "logo",
    label: "Logo",
    expectedFilename: "logo_justech.png (o *logo*.png)",
    format: "PNG recomendado",
    sizeHint: "700×340 px (mín. 350×170, horizontal ~2:1)",
    backgroundHint: "Blanco sólido o fondo corporativo",
    uploadHint: "Perfil Empresarial Justech → campo Logo · document_type=logo",
    managePath: "/apps/empresas-grupo/empresas",
    fieldKey: "logo",
  },
  signature: {
    key: "signature",
    label: "Firma",
    expectedFilename: "firma_fausto.png",
    format: "PNG",
    sizeHint: "600×200 px (mín. 400×130, horizontal)",
    backgroundHint: "Transparente recomendado",
    uploadHint: "Documentos → Identidad corporativa → Firma Fausto",
    managePath: "/documents/identity",
  },
  stamp: {
    key: "stamp",
    label: "Sello",
    expectedFilename: "sello_justech.png",
    format: "PNG",
    sizeHint: "400×400 px (mín. 300×300, cuadrado)",
    backgroundHint: "Transparente recomendado",
    uploadHint: "Documentos → Identidad corporativa → Sello Justech",
    managePath: "/documents/identity",
  },
};
