const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

export interface ChatResponse {
  type: 'config_form';
  data: {
    thread_id: string;
    title: string;
    fields: {
      id: string;
      label: string;
      options: { label: string; value: string }[];
      default: string;
    }[];
  };
}

export interface SSEEvent {
  type: 'node_start' | 'node_end' | 'token' | 'done' | 'error';
  node?: string;
  content?: string;
  output?: Record<string, unknown>;
  error?: string;
}

export async function sendChat(
  userInput: string,
  threadId?: string,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_input: userInput, thread_id: threadId }),
  });
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }
  return res.json();
}

export async function submitConfig(
  threadId: string,
  userInput: string,
  selections: Record<string, string>,
): Promise<Response> {
  const res = await fetch(`${API_BASE}/chat/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      thread_id: threadId,
      user_input: userInput,
      selections,
    }),
  });
  if (!res.ok) {
    throw new Error(`Config submit failed: ${res.status}`);
  }
  return res;
}

export function streamSSE(
  response: Response,
  onEvent: (event: SSEEvent) => void,
  onDone: () => void,
  onError: (error: string) => void,
): void {
  const reader = response.body?.getReader();
  if (!reader) {
    onError('No response body');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  const read = (): void => {
    reader
      .read()
      .then(({ done, value }) => {
        if (done) {
          onDone();
          return;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const jsonStr = trimmed.slice(6);
          if (!jsonStr) continue;

          try {
            const event: SSEEvent = JSON.parse(jsonStr);
            if (event.type === 'error') {
              onError(event.error || 'Unknown error');
            } else if (event.type === 'done') {
              // done 事件可能携带最终内容，先回调 onEvent 再结束
              if (event.content) {
                onEvent(event);
              }
              onDone();
              reader.cancel();
              return;
            } else {
              onEvent(event);
            }
          } catch {
            // skip malformed lines
          }
        }

        read();
      })
      .catch((err) => {
        onError(String(err));
      });
  };

  read();
}
