import { useCallback, useEffect, useRef, useState } from "react";
import type { PlayerScore, RoomState } from "../battleApi";
import { getCurrentIdToken } from "./useAuth";

interface WSStateMessage {
  type: "state";
  state: RoomState;
}

interface WSErrorMessage {
  type: "error";
  detail: string;
}

interface WSPongMessage {
  type: "pong";
}

type WSMessage = WSStateMessage | WSErrorMessage | WSPongMessage;

export interface UseBattleSocket {
  state: RoomState | null;
  connected: boolean;
  error: string | null;
  sendReady: () => void;
  sendScore: (score: PlayerScore) => void;
}

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000];

async function buildSocketUrl(
  roomCode: string,
  playerId: string,
): Promise<string> {
  // In development: same-origin connection via Vite dev proxy
  // In production with VITE_API_URL: use that base URL converted to WebSocket protocol
  const apiBaseUrl = import.meta.env.VITE_API_URL;
  
  let wsBase: string;
  if (apiBaseUrl) {
    // Convert HTTP(S) base URL to WS(S) protocol
    wsBase = apiBaseUrl.replace(/^https?:/, (m: string) => (m === "https:" ? "wss:" : "ws:"));
  } else {
    // Same-origin (Vite dev proxy or static SPA serving)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    wsBase = `${protocol}//${host}`;
  }
  
  const params = new URLSearchParams({ player_id: playerId });
  // Browsers can't set headers on WebSocket connections, so pass the Firebase
  // ID token as a query param. Backend reads `id_token` and verifies before
  // accepting the connection.
  const token = await getCurrentIdToken();
  if (token) params.set("id_token", token);
  return `${wsBase}/battle/ws/${encodeURIComponent(
    roomCode,
  )}?${params.toString()}`;
}

export function useBattleSocket(
  roomCode: string | null,
  playerId: string | null,
): UseBattleSocket {
  const [state, setState] = useState<RoomState | null>(null);
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
      console.warn("battle ws send failed", err);
    }
  }, []);

  const sendReady = useCallback(() => sendJson({ type: "ready" }), [sendJson]);
  const sendScore = useCallback(
    (score: PlayerScore) => sendJson({ type: "score_submitted", score }),
    [sendJson],
  );

  useEffect(() => {
    if (!roomCode || !playerId) {
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
        url = await buildSocketUrl(roomCode, playerId);
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
          setError(parsed.state.error ?? null);
        } else if (parsed.type === "error") {
          setError(parsed.detail);
        }
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
              ? "This battle room no longer exists."
              : "This battle session is not valid.",
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
  }, [roomCode, playerId]);

  return { state, connected, error, sendReady, sendScore };
}
