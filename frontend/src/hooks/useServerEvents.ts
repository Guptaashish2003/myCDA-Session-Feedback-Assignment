"use client";

import { useEffect, useRef } from "react";
import { api } from "@/lib/api";

interface ServerEvent {
  event: string;
  data: unknown;
}

const RECONNECT_DELAY_MS = 3000;

/** Parse one SSE frame ("event: x" + "data: {...}") into an event, or null for comments. */
function parseFrame(frame: string): ServerEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}

/**
 * Subscribes to a Server-Sent Events endpoint while mounted.
 *
 * Uses fetch rather than EventSource because EventSource cannot send the
 * Authorization header. Reconnects automatically after a drop.
 */
export function useServerEvents<T>(path: string, onEvent: (data: T, event: string) => void) {
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function connect() {
      try {
        const res = await api.stream(path, controller.signal);
        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const parsed = parseFrame(frame);
            if (parsed) handler.current(parsed.data as T, parsed.event);
          }
        }
      } catch {
        // aborted (unmount) or network error: fall through to reconnect
      }
      if (!controller.signal.aborted) timer = setTimeout(connect, RECONNECT_DELAY_MS);
    }

    connect();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [path]);
}
