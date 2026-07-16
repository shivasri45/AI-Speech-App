import { useEffect, useState } from "react";
import {
  HardDrive,
  FileText,
  Users,
  MessageSquareText,
  Users2,
  Loader2,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { getCurrentIdToken } from "../../hooks/useAuth";

interface StorageData {
  total_submissions: number;
  reviewed: number;
  pending: number;
  total_debates: number;
  total_gd_sessions: number;
  total_students: number;
  storage_size_mb: number;
}

async function fetchStorageStats(): Promise<StorageData> {
  const token = await getCurrentIdToken();
  const res = await fetch("/admin/storage-stats", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

interface StatCardProps {
  icon: typeof HardDrive;
  label: string;
  value: string | number;
  accent: string;
}

function StatCard({ icon: Icon, label, value, accent }: StatCardProps) {
  return (
    <div className="card-glass p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${accent}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-2xl font-bold text-zinc-100">{value}</div>
        <div className="text-xs text-zinc-500 uppercase tracking-widest">{label}</div>
      </div>
    </div>
  );
}

export function StorageStats() {
  const [stats, setStats] = useState<StorageData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStorageStats()
      .then(setStats)
      .catch((err) => console.warn("Stats fetch failed:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="card-glass p-8 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-brand-300" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="card-glass p-4 text-sm text-zinc-500">
        Failed to load storage stats
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-zinc-100">Platform Statistics</h2>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={Users}
          label="Students"
          value={stats.total_students}
          accent="bg-cyan-500/10 text-cyan-300"
        />
        <StatCard
          icon={FileText}
          label="Interviews"
          value={stats.total_submissions}
          accent="bg-amber-500/10 text-amber-300"
        />
        <StatCard
          icon={MessageSquareText}
          label="Debates"
          value={stats.total_debates}
          accent="bg-violet-500/10 text-violet-300"
        />
        <StatCard
          icon={Users2}
          label="Group Discussions"
          value={stats.total_gd_sessions}
          accent="bg-emerald-500/10 text-emerald-300"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <StatCard
          icon={CheckCircle2}
          label="Reviewed"
          value={stats.reviewed}
          accent="bg-emerald-500/10 text-emerald-300"
        />
        <StatCard
          icon={Clock}
          label="Pending Review"
          value={stats.pending}
          accent="bg-rose-500/10 text-rose-300"
        />
        <StatCard
          icon={HardDrive}
          label="Storage (MB)"
          value={stats.storage_size_mb}
          accent="bg-zinc-500/10 text-zinc-300"
        />
      </div>
    </div>
  );
}
