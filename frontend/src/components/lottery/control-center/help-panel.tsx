type HelpPanelProps = {
  title: string;
  whatIs: string;
  purpose: string;
  impact: string;
  example?: string;
  doWrite?: string;
  dontWrite?: string;
  validation?: string;
};

export function HelpPanel({
  title,
  whatIs,
  purpose,
  impact,
  example,
  doWrite,
  dontWrite,
  validation,
}: HelpPanelProps) {
  return (
    <aside className="rounded-md border bg-muted/30 p-3 text-sm">
      <div className="font-semibold">{title}</div>
      <dl className="mt-2 space-y-1.5 text-muted-foreground">
        <div>
          <dt className="font-medium text-foreground">Qué es</dt>
          <dd>{whatIs}</dd>
        </div>
        <div>
          <dt className="font-medium text-foreground">Para qué sirve</dt>
          <dd>{purpose}</dd>
        </div>
        <div>
          <dt className="font-medium text-foreground">Impacto</dt>
          <dd>{impact}</dd>
        </div>
        {example ? (
          <div>
            <dt className="font-medium text-foreground">Ejemplo</dt>
            <dd className="font-mono text-xs">{example}</dd>
          </div>
        ) : null}
        {doWrite ? (
          <div>
            <dt className="font-medium text-foreground">Qué escribir</dt>
            <dd>{doWrite}</dd>
          </div>
        ) : null}
        {dontWrite ? (
          <div>
            <dt className="font-medium text-foreground">Qué no escribir</dt>
            <dd>{dontWrite}</dd>
          </div>
        ) : null}
        {validation ? (
          <div>
            <dt className="font-medium text-foreground">Validación</dt>
            <dd>{validation}</dd>
          </div>
        ) : null}
      </dl>
    </aside>
  );
}
