interface SkeletonProps {
  className?: string;
  variant?: "text" | "circle" | "rectangle";
}

export function Skeleton({ className = "", variant = "rectangle" }: SkeletonProps) {
  const base = "animate-pulse bg-zinc-800/60";
  const variantClass = {
    text: "h-4 rounded",
    circle: "rounded-full",
    rectangle: "rounded-lg",
  }[variant];
  
  return <div className={`${base} ${variantClass} ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="card-glass p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton variant="circle" className="w-10 h-10" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <Skeleton className="h-20 w-full" />
    </div>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
