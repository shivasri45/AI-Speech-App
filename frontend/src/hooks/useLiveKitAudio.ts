/**
 * Hook for LiveKit live audio in GD rooms.
 * Handles joining/leaving audio rooms and managing local audio.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  Track,
  RemoteParticipant,
  ConnectionState,
} from "livekit-client";

interface UseLiveKitAudioOptions {
  serverUrl: string | null;
  token: string | null;
  enabled: boolean;
}

interface LiveKitAudioState {
  isJoined: boolean;
  isConnecting: boolean;
  isMuted: boolean;
  error: string | null;
  participantCount: number;
  connectionState: string;
}

export function useLiveKitAudio({ serverUrl, token, enabled }: UseLiveKitAudioOptions) {
  const roomRef = useRef<Room | null>(null);
  const [state, setState] = useState<LiveKitAudioState>({
    isJoined: false,
    isConnecting: false,
    isMuted: false,
    error: null,
    participantCount: 0,
    connectionState: "disconnected",
  });

  // Join the LiveKit room
  const join = useCallback(async () => {
    if (!serverUrl || !token || !enabled || roomRef.current) return;

    setState((s) => ({ ...s, isConnecting: true, error: null }));

    try {
      // Create Room instance
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        // Audio only settings
        videoCaptureDefaults: {
          resolution: { width: 0, height: 0, frameRate: 0 },
        },
      });

      roomRef.current = room;

      // Set up event listeners
      room.on(RoomEvent.Connected, () => {
        console.log("[LiveKit] Connected to room");
        setState((s) => ({
          ...s,
          isJoined: true,
          isConnecting: false,
          connectionState: "connected",
          participantCount: room.numParticipants,
        }));
      });

      room.on(RoomEvent.Disconnected, () => {
        console.log("[LiveKit] Disconnected from room");
        setState((s) => ({
          ...s,
          isJoined: false,
          isConnecting: false,
          connectionState: "disconnected",
          participantCount: 0,
        }));
      });

      room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
        console.log("[LiveKit] Connection state:", state);
        setState((s) => ({ ...s, connectionState: state }));
      });

      room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        console.log("[LiveKit] Participant connected:", participant.identity);
        setState((s) => ({ ...s, participantCount: room.numParticipants }));
      });

      room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        console.log("[LiveKit] Participant disconnected:", participant.identity);
        setState((s) => ({ ...s, participantCount: room.numParticipants }));
      });

      room.on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
        if (track.kind === Track.Kind.Audio) {
          // Attach audio track to play it
          const audioElement = track.attach();
          document.body.appendChild(audioElement);
          console.log("[LiveKit] Audio track subscribed from:", participant.identity);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach().forEach((el) => el.remove());
        }
      });

      // Connect to the room
      await room.connect(serverUrl, token);

      // Enable microphone
      await room.localParticipant.setMicrophoneEnabled(true);
      console.log("[LiveKit] Microphone enabled");

    } catch (err) {
      console.error("[LiveKit] Failed to join room:", err);
      setState((s) => ({
        ...s,
        error: err instanceof Error ? err.message : "Failed to join audio",
        isConnecting: false,
      }));
      roomRef.current = null;
    }
  }, [serverUrl, token, enabled]);

  // Leave the LiveKit room
  const leave = useCallback(async () => {
    if (roomRef.current) {
      try {
        await roomRef.current.disconnect();
      } catch (err) {
        console.warn("[LiveKit] Error leaving room:", err);
      }
      roomRef.current = null;
      setState((s) => ({
        ...s,
        isJoined: false,
        isConnecting: false,
        participantCount: 0,
        connectionState: "disconnected",
      }));
    }
  }, []);

  // Toggle mute
  const toggleMute = useCallback(async () => {
    if (roomRef.current?.localParticipant) {
      const newMuted = !state.isMuted;
      await roomRef.current.localParticipant.setMicrophoneEnabled(!newMuted);
      setState((s) => ({ ...s, isMuted: newMuted }));
    }
  }, [state.isMuted]);

  // Auto-join when token becomes available and enabled
  useEffect(() => {
    if (serverUrl && token && enabled && !state.isJoined && !state.isConnecting) {
      void join();
    }
  }, [serverUrl, token, enabled, state.isJoined, state.isConnecting, join]);

  // Auto-leave when disabled or token changes
  useEffect(() => {
    if (!enabled || !token) {
      void leave();
    }
  }, [enabled, token, leave]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (roomRef.current) {
        void roomRef.current.disconnect().catch(() => {});
        roomRef.current = null;
      }
    };
  }, []);

  return {
    ...state,
    join,
    leave,
    toggleMute,
  };
}
