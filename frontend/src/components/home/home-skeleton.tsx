export function HomeSkeleton() {
  return (
    <div className="mx-auto max-w-[1600px] animate-pulse space-y-8 p-2">
      <div className="space-y-4">
        <div className="h-10 w-72 rounded-xl bg-muted" />
        <div className="h-4 w-96 max-w-full rounded bg-muted" />
        <div className="flex gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-5 w-32 rounded bg-muted" />
          ))}
        </div>
        <div className="h-12 max-w-2xl rounded-2xl bg-muted" />
      </div>
      <div className="grid grid-cols-4 gap-3 sm:grid-cols-6 md:grid-cols-8">
        {Array.from({ length: 16 }).map((_, i) => (
          <div key={i} className="flex flex-col items-center gap-2">
            <div className="h-14 w-14 rounded-2xl bg-muted" />
            <div className="h-3 w-12 rounded bg-muted" />
          </div>
        ))}
      </div>
      <div className="h-48 rounded-2xl bg-muted" />
    </div>
  );
}
