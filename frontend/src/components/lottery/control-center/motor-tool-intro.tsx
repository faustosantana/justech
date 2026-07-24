import Link from "next/link";

/** Encabezado secundario J-10 para herramientas del motor (después del análisis). */
export function MotorToolIntro({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        <Link href="/lottery/admin/control-center" className="text-primary underline-offset-2 hover:underline">
          ← Inteligencia (7 destacadas)
        </Link>
        <span className="mx-2">·</span>
        Herramienta de consulta · no altera fórmulas ni el histórico
      </p>
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <p className="max-w-3xl text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
