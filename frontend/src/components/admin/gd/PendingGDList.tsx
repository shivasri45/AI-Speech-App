import { useEffect, useState } from "react";
import { Loader2, Users2, Clock, Trash2, Eye } from "lucide-react";
import { EmptyState } from "../../EmptyState";
import { useToast } from "../../Toast";
import { getCurrentIdToken } from "../../../hooks/useAuth";

interface GDSessionSummary {
  session_id: string;
  code: string;
  topic_title: string;
  participant_count: number;
  total_speeches: number;
  duration_seconds: number;
  completed_at: number;
  has_teacher_reviews: boolean;
}

interface Props {
  onOpenSession: (sessionId: string) => void;
}

async function fetchGDSessions(): Promise<GDSessionSummary[]> {
  const token = await getCurrentIdToken();
  const res = await fetch("/admin/gd", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

async function deleteGDSession(sessionId: string) {
  const token = await getCurrentIdToken();
  const res = await fetch(`/admin/gd/${sessionId}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export function PendingGDList({ onOpenSession }: Props) {
  const [sessions, setSessions] = useState<GDSessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchGDSessions();
      setSessions(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleDelete = async (sessionId: string, code: string) => {
    if (!confirm(`Delete GD session ${code}? This cannot be undone.`)) return;
    try {
      await deleteGDSession(sessionId);
      toast.success("Session deleted", `${code} removed successfully`);
      await load();
    } catch (err) {
      toast.error("Delete failed", err instanceof Error ? err.message : "");
    }
  };

  if (loading) {
    return (
      <div className="card-glass p-8 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-300" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-glass p-4 border-rose-500/40 text-sm text-rose-300">
        {error}
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <EmptyState
        icon={Users2}
        title="No GD sessions yet"
        description="Group Discussion sessions will appear here once students complete them."
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm text-zinc-400">
          {sessions.length} completed session{sessions.length !== 1 ? "s" : ""}
        </div>
      </div>

      {sessions.map((s) => (
        <div key={s.session_id} className="card-glass p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="chip bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                  <Users2 className="w-3 h-3" />
                  {s.code}
                </span>
                <span className="text-xs text-zinc-500">
                  {new Date(s.completed_at * 1000).toLocaleString()}
                </span>
              </div>
              <h3 className="font-semibold text-zinc-100 truncate">{s.topic_title}</h3>
              <div className="flex flex-wrap gap-3 mt-2 text-xs text-zinc-400">
                <span className="inline-flex items-center gap-1">
                  <Users2 className="w-3 h-3" />
                  {s.participant_count} participants
                </span>
                <span>{s.total_speeches} speeches</span>
                <span className="inline-flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {Math.floor(s.duration_seconds / 60)}m
                </span>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => onOpenSession(s.session_id)}
                className="btn-primary px-3 py-1.5 text-xs"
                aria-label="Review session"
              >
                <Eye className="w-3.5 h-3.5" />
                Review
              </button>
              <button
                type="button"
                onClick={() => handleDelete(s.session_id, s.code)}
                className="btn-ghost px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-500/10"
                aria-label="Delete session"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
