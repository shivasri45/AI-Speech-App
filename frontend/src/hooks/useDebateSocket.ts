import { useCallback, useEffect, useRef, useState } from "react";
import type { PublicDebateRoom } from "../debateApi";
import { getCurrentIdToken } from "./useAuth";

// Server → client envelope shapes. Only `state` and `pong` are handled today;
// the `error` variant is kept in the union so future backend additions don't
// silently break the parser.
interface WSStateMessage {
  type: "state";
  state: PublicDebateRoom;
}

interface WSErrorMessage {
  type: "error";
  detail: string;
}

interface WSPongMessage {
  type: "pong";
}

type WSMessage = WSStateMessage | WSErrorMessage | WSPongMessage;

export interface UseDebateSocket {
  state: PublicDebateRoom | null;
  connected: boolean;
  error: string | null;
  sendPing: () => void;
}

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000];

async function buildSocketUrl(
  roomCode: string,
  participantId: string,
): Promise<string> {
  // Same-origin connection so the Vite dev proxy (or whatever serves the SPA
  // in prod) routes it to the FastAPI backend on port 8080.
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const params = new URLSearchParams({ participant_id: participantId });
  // Browsers can't set headers on WebSocket connections, so pass the Firebase
  // ID token as a query param. Backend reads `id_token` and verifies before
  // accepting the connection.
  const token = await getCurrentIdToken();
  if (token) params.set("id_token", token);
  return `${protocol}//${host}/debate/ws/${encodeURIComponent(
    roomCode,
  )}?${params.toString()}`;
}

export function useDebateSocket(
  code: string | null,
  participantId: string | null,
): UseDebateSocket {
  const [state, setState] = useState<PublicDebateRoom | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const closedByUserRef = useRef(false);

  const sendJson = useCallback((payload: unknown) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    try {
      ws.send(JSON.stringify(payload));
    } catch (err) {
      console.warn("debate ws send failed", err);
    }
  }, []);

  const sendPing = useCallback(() => sendJson({ type: "ping" }), [sendJson]);

  useEffect(() => {
    if (!code || !participantId) {
      setState(null);
      setConnected(false);
      return;
    }

    closedByUserRef.current = false;
    let cancelled = false;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current != null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const connect = async () => {
      if (cancelled) return;
      let url: string;
      try {
        url = await buildSocketUrl(code, participantId);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Could not build socket URL.";
        setError(message);
        scheduleReconnect();
        return;
      }
      if (cancelled) return;
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Could not open socket.";
        setError(message);
        scheduleReconnect();
        return;
      }
      socketRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        reconnectAttemptRef.current = 0;
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event: MessageEvent) => {
        if (cancelled) return;
        let parsed: WSMessage | null = null;
        try {
          parsed = JSON.parse(event.data as string) as WSMessage;
        } catch {
          return;
        }
        if (!parsed || typeof parsed.type !== "string") return;
        if (parsed.type === "state" && parsed.state) {
          setState(parsed.state);
        } else if (parsed.type === "error") {
          setError(parsed.detail);
        }
        // `pong` is ignored — the ping/pong pair is only for keepalive.
      };

      ws.onclose = (event) => {
        if (cancelled) return;
        setConnected(false);
        socketRef.current = null;
        if (closedByUserRef.current) return;
        // Codes 4401/4404 are auth/missing-room — don't retry, just surface.
        if (event.code === 4401 || event.code === 4404) {
          setError(
            event.code === 4404
              ? "This debate room no longer exists."
              : "This debate session is not valid.",
          );
          return;
        }
        scheduleReconnect();
      };

      ws.onerror = () => {
        if (cancelled) return;
        // Let onclose drive the retry; just note the failure.
        setError((prev) => prev ?? "Connection error — retrying…");
      };
    };

    const scheduleReconnect = () => {
      clearReconnectTimer();
      const attempt = reconnectAttemptRef.current;
      const delay =
        RECONNECT_DELAYS_MS[Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)];
      reconnectAttemptRef.current = attempt + 1;
      reconnectTimerRef.current = window.setTimeout(() => {
        void connect();
      }, delay);
    };

    void connect();

    return () => {
      cancelled = true;
      closedByUserRef.current = true;
      clearReconnectTimer();
      const ws = socketRef.current;
      socketRef.current = null;
      if (ws) {
        try {
          ws.close(1000, "client-unmount");
        } catch {
          // ignore
        }
      }
      setConnected(false);
    };
  }, [code, participantId]);

  return { state, connected, error, sendPing };
}
