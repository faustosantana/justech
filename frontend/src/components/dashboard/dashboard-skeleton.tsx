export function DashboardSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 animate-pulse">
      <div className="brand-surface-accent h-40 rounded-2xl" />
      <div className="brand-surface h-36 rounded-2xl" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="brand-surface h-28 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="brand-surface h-64 rounded-2xl" />
        <div className="brand-surface h-64 rounded-2xl" />
      </div>
    </div>
  );
}
