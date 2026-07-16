import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="card-glass p-8 md:p-12 flex flex-col items-center gap-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-zinc-800/60 flex items-center justify-center">
        <Icon className="w-8 h-8 text-zinc-500" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-zinc-100">{title}</h3>
        {description && (
          <p className="text-sm text-zinc-500 mt-1 max-w-md">{description}</p>
        )}
      </div>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="btn-primary px-4 py-2 mt-2"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
