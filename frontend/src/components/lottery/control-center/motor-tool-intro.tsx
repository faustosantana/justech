import Link from "next/link";

/** Encabezado secundario para herramientas del motor (menú único J-10X). */
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
        <Link href="/lottery" className="text-primary underline-offset-2 hover:underline">
          ← Lottery IA Control Center
        </Link>
        <span className="mx-2">·</span>
        Herramienta de consulta · no altera fórmulas ni el histórico
      </p>
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <p className="max-w-3xl text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
