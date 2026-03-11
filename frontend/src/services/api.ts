import type { ScriptData } from '../components/ScriptView';

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

export interface ThreadListItem {
  thread_id: string;
  title: string;
  summary: string;
  latest_episode_id?: number | null;
  updated_at: string;
  last_message_at: string;
}

export interface PersistedThreadMessage {
  id: string;
  role: string;
  message_type: string;
  content_json: Record<string, unknown>;
  sequence: number;
  created_at: string;
}

export interface ThreadStateResponse {
  active_view: string;
  latest_task_id: string;
  latest_task_type: string;
  current_episode_id?: number | null;
  current_script_data_json: Record<string, unknown>;
  media_snapshot_json: Record<string, unknown>;
  editor_state_json: Record<string, unknown>;
  messages_snapshot_json: Record<string, unknown>[];
  updated_at?: string | null;
}

export interface ThreadDetailResponse {
  thread_id: string;
  title: string;
  summary: string;
  latest_episode_id?: number | null;
  created_at: string;
  updated_at: string;
  last_message_at: string;
  messages: PersistedThreadMessage[];
  state: ThreadStateResponse;
}

export interface UpdateThreadStateRequest {
  active_view?: string;
  latest_task_id?: string;
  latest_task_type?: string;
  current_episode_id?: number | null;
  current_script_data_json?: Record<string, unknown>;
  media_snapshot_json?: Record<string, unknown>;
  editor_state_json?: Record<string, unknown>;
  messages_snapshot_json?: Record<string, unknown>[];
}

export interface SSEEvent {
  type: 'node_start' | 'node_end' | 'token' | 'done' | 'error';
  node?: string;
  content?: string;
  output?: Record<string, unknown>;
  script_data?: ScriptData;
  error?: string;
}

export interface CreateEpisodeResponse {
  episode_id: number;
  title: string;
}

export interface GenerateStoryboardResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface GenerateAigcResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface AsyncTaskStatusResponse {
  task_id: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'obsolete' | 'expired';
  progress: number;
  message: string;
  result: string;
  error: string;
}

export interface CancelTaskResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface StoryboardMediaItem {
  storyboard_id: number;
  storyboard_number: number;
  title: string;
  duration: number;
  image_key: string;
  image_url: string;
  video_key: string;
  video_url: string;
  // Optional frame-level fields for future backend upgrades.
  start_frame_key?: string;
  start_frame_url?: string;
  end_frame_key?: string;
  end_frame_url?: string;
  keyframe_keys?: string[];
  keyframe_urls?: string[];
}

export interface CharacterImageItem {
  character_id: string;
  character_name: string;
  image_key: string;
  image_url: string;
  storyboard_number: number;
}

export interface EpisodeStoryboardMediaResponse {
  episode_id: number;
  total: number;
  generated_images: number;
  generated_videos: number;
  items: StoryboardMediaItem[];
  character_images: CharacterImageItem[];
}

export interface VideoMergeClipRequest {
  video_url: string;
  duration?: number;
  start_time?: number;
  end_time?: number;
  transition?: {
    type?: string;
    duration?: number;
  };
}

export interface VideoMergeResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface ManualEditCharacter {
  id: string;
  name: string;
  voice: string;
  appearance: string;
}

export interface ManualEditShot {
  storyboard_number: number;
  summary: string;
  visual_desc: string;
  narration: string;
  tags: string[];
  duration_seconds: number;
  start_frame_url?: string;
  end_frame_url?: string;
  keyframe_urls?: string[];
}

export interface SaveManualEditsRequest {
  characters: ManualEditCharacter[];
  shots: ManualEditShot[];
}

export interface SaveManualEditsResponse {
  episode_id: number;
  updated_storyboards: number;
  updated_characters: number;
  status: string;
  message: string;
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

export async function createThread(title?: string): Promise<ThreadDetailResponse> {
  const res = await fetch(`${API_BASE}/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    throw new Error(`Create thread failed: ${res.status}`);
  }
  return res.json();
}

export async function listThreads(): Promise<ThreadListItem[]> {
  const res = await fetch(`${API_BASE}/threads`);
  if (!res.ok) {
    throw new Error(`List threads failed: ${res.status}`);
  }
  return res.json();
}

export async function getThread(threadId: string): Promise<ThreadDetailResponse> {
  const res = await fetch(`${API_BASE}/threads/${threadId}`);
  if (!res.ok) {
    throw new Error(`Get thread failed: ${res.status}`);
  }
  return res.json();
}

export async function updateThreadState(
  threadId: string,
  payload: UpdateThreadStateRequest,
): Promise<ThreadStateResponse> {
  const res = await fetch(`${API_BASE}/threads/${threadId}/state`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Update thread state failed: ${res.status}`);
  }
  return res.json();
}

export async function deleteThread(threadId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/threads/${threadId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Delete thread failed: ${res.status}`);
  }
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

export async function createEpisodeFromScript(
  scriptData: ScriptData,
  threadId: string,
  title?: string,
): Promise<CreateEpisodeResponse> {
  const res = await fetch(`${API_BASE}/storyboard/episodes/from-script`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      script_data: scriptData,
      thread_id: threadId,
      title,
    }),
  });
  if (!res.ok) {
    throw new Error(`Create episode failed: ${res.status}`);
  }
  return res.json();
}

export async function generateStoryboards(episodeId: number): Promise<GenerateStoryboardResponse> {
  const res = await fetch(`${API_BASE}/storyboard/episodes/storyboards`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ episode_id: episodeId }),
  });
  if (!res.ok) {
    throw new Error(`Generate storyboard failed: ${res.status}`);
  }
  return res.json();
}

export async function getStoryboardTaskStatus(taskId: string): Promise<AsyncTaskStatusResponse> {
  const res = await fetch(`${API_BASE}/storyboard/tasks/${taskId}`);
  if (!res.ok) {
    throw new Error(`Query task status failed: ${res.status}`);
  }
  return res.json();
}

export async function cancelStoryboardTask(taskId: string): Promise<CancelTaskResponse> {
  const res = await fetch(`${API_BASE}/storyboard/tasks/${taskId}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Cancel task failed: ${res.status}`);
  }
  return res.json();
}

export async function generateAigc(episodeId: number): Promise<GenerateAigcResponse> {
  const res = await fetch(`${API_BASE}/storyboard/episodes/${episodeId}/generate-aigc`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Generate AIGC failed: ${res.status}`);
  }
  return res.json();
}

export async function getEpisodeStoryboardMedia(
  episodeId: number,
  expires = 3600,
): Promise<EpisodeStoryboardMediaResponse> {
  const res = await fetch(
    `${API_BASE}/storyboard/episodes/${episodeId}/storyboards/media?expires=${expires}`
  );
  if (!res.ok) {
    throw new Error(`Query storyboard media failed: ${res.status}`);
  }
  return res.json();
}

export async function mergeEpisodeVideos(
  clips: VideoMergeClipRequest[],
  outputFile: string,
): Promise<VideoMergeResponse> {
  const res = await fetch(`${API_BASE}/storyboard/videos/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      clips,
      output_file: outputFile,
    }),
  });
  if (!res.ok) {
    throw new Error(`Merge videos failed: ${res.status}`);
  }
  return res.json();
}

export interface RegenerateImageResponse {
  storyboard_id: number;
  storyboard_number: number;
  image_key: string;
  image_url: string;
  start_frame_key?: string;
  start_frame_url?: string;
  end_frame_key?: string;
  end_frame_url?: string;
  keyframe_keys?: string[];
  keyframe_urls?: string[];
}

export async function regenerateStoryboardImage(
  storyboardId: number,
  prompt: string,
): Promise<RegenerateImageResponse> {
  const res = await fetch(
    `${API_BASE}/storyboard/storyboards/${storyboardId}/regenerate-image`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    },
  );
  if (!res.ok) {
    throw new Error(`Regenerate image failed: ${res.status}`);
  }
  return res.json();
}

export async function saveEpisodeManualEdits(
  episodeId: number,
  payload: SaveManualEditsRequest,
): Promise<SaveManualEditsResponse> {
  const res = await fetch(`${API_BASE}/storyboard/episodes/${episodeId}/manual-edits`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Save manual edits failed: ${res.status}`);
  }
  return res.json();
}
