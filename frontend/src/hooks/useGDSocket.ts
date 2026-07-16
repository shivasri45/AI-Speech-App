import { useCallback, useEffect, useRef, useState } from "react";
import type { PublicGDRoom } from "../gdApi";
import { getCurrentIdToken } from "./useAuth";

interface WSStateMessage {
  type: "state";
  state: PublicGDRoom;
}

interface WSPongMessage {
  type: "pong";
}

type WSMessage = WSStateMessage | WSPongMessage;

export interface UseGDSocket {
  state: PublicGDRoom | null;
  connected: boolean;
  error: string | null;
  sendPing: () => void;
}

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000];

async function buildSocketUrl(
  roomCode: string,
  participantId: string,
): Promise<string> {
  const apiBaseUrl = import.meta.env.VITE_API_URL;
  let wsBase: string;
  if (apiBaseUrl) {
    wsBase = apiBaseUrl.replace(/^https?:/, (m: string) =>
      m === "https:" ? "wss:" : "ws:",
    );
  } else {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    wsBase = `${protocol}//${window.location.host}`;
  }
  const params = new URLSearchParams({ participant_id: participantId });
  const token = await getCurrentIdToken();
  if (token) params.set("id_token", token);
  return `${wsBase}/gd/ws/${encodeURIComponent(roomCode)}?${params.toString()}`;
}

export function useGDSocket(
  code: string | null,
  participantId: string | null,
): UseGDSocket {
  const [state, setState] = useState<PublicGDRoom | null>(null);
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
      console.warn("gd ws send failed", err);
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
        setError(err instanceof Error ? err.message : "Socket URL failed");
        scheduleReconnect();
        return;
      }
      if (cancelled) return;

      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Socket open failed");
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
        }
      };

      ws.onclose = (event) => {
        if (cancelled) return;
        setConnected(false);
        socketRef.current = null;
        if (closedByUserRef.current) return;
        if (event.code === 4401 || event.code === 4404) {
          setError(
            event.code === 4404
              ? "GD room no longer exists."
              : "Invalid session.",
          );
          return;
        }
        scheduleReconnect();
      };

      ws.onerror = () => {
        if (cancelled) return;
        setError((prev) => prev ?? "Connection error - retrying");
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
