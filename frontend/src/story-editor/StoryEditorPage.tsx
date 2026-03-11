import { useEffect, useMemo, useRef, useState } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Preview } from './components/Preview';
import { Timeline } from './components/Timeline';
import { RoleSettingsView } from './components/RoleSettingsView';
import { shots as mockShots, type Shot, type ShotFrame } from './data/storyboard';
import { characters as mockCharacters, type Character } from './data/characters';
import { findFrameById, getDefaultFrameId, getShotFrames } from './utils/shotFrames';
import type { ScriptData } from '../components/ScriptView';
import { regenerateStoryboardImage } from '../services/api';
import type { CharacterImageItem, SaveManualEditsRequest, StoryboardMediaItem } from '../services/api';

interface StoryEditorPageProps {
  onClose: () => void;
  scriptData?: ScriptData;
  mediaItems?: StoryboardMediaItem[];
  characterImages?: CharacterImageItem[];
  loadingMedia?: boolean;
  onSave?: (payload: SaveManualEditsRequest) => Promise<void>;
  initialState?: {
    activeShotId?: number;
    activeFrameByShotId?: Record<number, string>;
    activeView?: 'storyboard' | 'roles';
  };
  onStateChange?: (state: {
    activeShotId: number;
    activeFrameByShotId: Record<number, string>;
    activeView: 'storyboard' | 'roles';
  }) => void;
}

function parseDurationSeconds(raw: string | undefined): number {
  const text = (raw || '').trim().toLowerCase().replace('秒', '').replace('s', '');
  const value = Number(text);
  if (!Number.isFinite(value) || value <= 0) return 3;
  return value;
}

function calcTimelineWidth(durationSeconds: number): string {
  const width = Math.round(Math.max(220, Math.min(360, durationSeconds * 42)));
  return `${width}px`;
}

function cleanUrl(value: string | undefined): string {
  return (value || '').trim();
}

function buildTimelineFrames(
  storyboardNumber: number,
  media: StoryboardMediaItem | undefined,
  fallbackImage: string,
): ShotFrame[] {
  const defaultImage = cleanUrl(media?.image_url) || fallbackImage;
  const startUrl = cleanUrl(media?.start_frame_url) || defaultImage;
  const endUrl = cleanUrl(media?.end_frame_url) || defaultImage || startUrl;
  const keyframeUrls = (media?.keyframe_urls || [])
    .map((url) => cleanUrl(url))
    .filter(Boolean)
    .slice(0, 1);

  const frames: ShotFrame[] = [
    {
      id: `${storyboardNumber}-start`,
      type: 'start',
      imageUrl: startUrl,
      label: '首帧',
    },
    ...keyframeUrls.map((url, index) => ({
      id: `${storyboardNumber}-key-${index + 1}`,
      type: 'key' as const,
      imageUrl: url,
      label: `关键帧${index + 1}`,
    })),
    {
      id: `${storyboardNumber}-end`,
      type: 'end',
      imageUrl: endUrl,
      label: '尾帧',
    },
  ];

  return frames.filter((frame) => Boolean(cleanUrl(frame.imageUrl)));
}

export default function StoryEditorPage({
  onClose,
  scriptData,
  mediaItems = [],
  characterImages = [],
  loadingMedia = false,
  onSave,
  initialState,
  onStateChange,
}: StoryEditorPageProps) {
  const [activeShotId, setActiveShotId] = useState(initialState?.activeShotId || 1);
  const [activeFrameByShotId, setActiveFrameByShotId] = useState<Record<number, string>>(initialState?.activeFrameByShotId || {});
  const [activeView, setActiveView] = useState<'storyboard' | 'roles'>(initialState?.activeView || 'storyboard');
  const lastAppliedInitialStateRef = useRef('');

  const mediaByNumber = useMemo(() => {
    const map = new Map<number, StoryboardMediaItem>();
    for (const item of mediaItems) {
      map.set(item.storyboard_number, item);
    }
    return map;
  }, [mediaItems]);

  const mappedCharacters = useMemo<Character[]>(() => {
    if (!scriptData?.characters?.length) {
      return mockCharacters;
    }
    const imageByCharacterId = new Map<string, string>();
    const imageByCharacterName = new Map<string, string>();
    for (const item of characterImages) {
      const url = (item.image_url || '').trim();
      if (!url) continue;
      const cid = (item.character_id || '').trim();
      const cname = (item.character_name || '').trim().toLowerCase();
      if (cid) imageByCharacterId.set(cid, url);
      if (cname) imageByCharacterName.set(cname, url);
    }

    const fallbackImageByIndex = mediaItems
      .map((item) => item.image_url)
      .filter(Boolean);

    const findCharacterImage = (name: string, index: number): string | null => {
      const shots = scriptData?.shots || [];
      for (const s of shots) {
        const text = `${s.shotName} ${s.summary} ${s.visualDesc} ${s.narration}`.toLowerCase();
        if (!name || !text.includes(name.toLowerCase())) continue;
        const sid = Number(s.id);
        if (Number.isFinite(sid)) {
          const matched = mediaByNumber.get(sid)?.image_url;
          if (matched) return matched;
        }
      }
      return fallbackImageByIndex[index] || null;
    };

    return scriptData.characters.map((c, index) => {
      const appearance = [c.appearance.age, c.appearance.identity, c.appearance.features]
        .filter(Boolean)
        .join('，');
      const directImage = imageByCharacterId.get(c.id)
        || imageByCharacterName.get((c.name || '').toLowerCase())
        || findCharacterImage(c.name || '', index);
      return {
        id: c.id || `R${index}`,
        name: c.name || `角色${index + 1}`,
        voice: c.voice || '',
        appearance: appearance || null,
        image: directImage,
        readonly: c.name.includes('旁白') || c.role === '功能性角色',
      };
    });
  }, [scriptData, mediaItems, mediaByNumber, characterImages]);

  const [characters, setCharacters] = useState<Character[]>(mappedCharacters);
  const mappedShots = useMemo<Shot[]>(() => {
    if (!scriptData?.shots?.length) {
      return mockShots;
    }
    return scriptData.shots.map((shot, index) => {
      const storyboardNumber = Number(shot.id) || (index + 1);
      const media = mediaByNumber.get(storyboardNumber);
      const durationSeconds = typeof media?.duration === 'number' && media.duration > 0
        ? media.duration
        : parseDurationSeconds(shot.duration);
      const timelineFrames = buildTimelineFrames(storyboardNumber, media, '');
      const previewImage = timelineFrames[0]?.imageUrl || cleanUrl(media?.image_url);
      const timelineImageList = timelineFrames.map((frame) => frame.imageUrl).filter(Boolean);
      const narration = (shot.narration || '').trim();
      const roleName = narration ? '旁白' : '角色';
      const roleTag = narration ? 'R0' : (mappedCharacters[0]?.id || 'R1');

        return {
          id: storyboardNumber,
          duration: `${durationSeconds.toFixed(1)}s`,
          durationSeconds,
        previewImage,
        sceneDescription: shot.summary || shot.shotName || `分镜 ${storyboardNumber}`,
        voiceover: {
          role: roleName,
          roleTag,
          text: narration || '（无旁白）',
          charRange: narration ? `${Math.max(1, narration.length - 6)}-${narration.length + 6}` : '0-0',
        },
        shotDescription: {
          tags: [
            shot.shotName ? `${shot.shotName}` : `分镜${storyboardNumber}`,
            shot.hasNarration ? '含旁白' : '无旁白',
          ],
          text: shot.visualDesc || shot.summary || '',
        },
        cameraMovement: shot.summary || '固定镜头',
        timelineFrames,
        timelineImages: timelineImageList.length
          ? timelineImageList
          : previewImage
            ? [previewImage]
            : [],
        timelineWidth: calcTimelineWidth(durationSeconds),
      };
    });
  }, [scriptData, mediaByNumber, mappedCharacters]);

  const [editorShots, setEditorShots] = useState<Shot[]>(mappedShots);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [isRegeneratingImage, setIsRegeneratingImage] = useState(false);

  useEffect(() => {
    setCharacters(mappedCharacters);
  }, [mappedCharacters]);

  useEffect(() => {
    if (!initialState) return;
    const serialized = JSON.stringify({
      activeShotId: initialState.activeShotId || 0,
      activeFrameByShotId: initialState.activeFrameByShotId || {},
      activeView: initialState.activeView || 'storyboard',
    });
    if (lastAppliedInitialStateRef.current === serialized) return;
    lastAppliedInitialStateRef.current = serialized;

    if (initialState.activeShotId && initialState.activeShotId !== activeShotId) {
      setActiveShotId(initialState.activeShotId);
    }
    if (
      initialState.activeFrameByShotId
      && JSON.stringify(initialState.activeFrameByShotId) !== JSON.stringify(activeFrameByShotId)
    ) {
      setActiveFrameByShotId(initialState.activeFrameByShotId);
    }
    if (initialState.activeView && initialState.activeView !== activeView) {
      setActiveView(initialState.activeView);
    }
  }, [initialState, activeFrameByShotId, activeShotId, activeView]);

  useEffect(() => {
    setEditorShots(mappedShots);
    if (!mappedShots.length) return;
    if (!mappedShots.some((s) => s.id === activeShotId)) {
      setActiveShotId(mappedShots[0].id);
    }
  }, [mappedShots, activeShotId]);

  useEffect(() => {
    if (!editorShots.length) {
      setActiveFrameByShotId({});
      return;
    }

    setActiveFrameByShotId((prev) => {
      let changed = false;
      const next: Record<number, string> = {};

      for (const shot of editorShots) {
        const current = prev[shot.id];
        const frame = findFrameById(shot, current);
        const fallbackId = getDefaultFrameId(shot);
        const nextId = frame?.id || fallbackId;
        if (nextId) {
          next[shot.id] = nextId;
          if (prev[shot.id] !== nextId) changed = true;
        }
      }

      if (Object.keys(prev).length !== Object.keys(next).length) changed = true;
      return changed ? next : prev;
    });
  }, [editorShots]);

  useEffect(() => {
    onStateChange?.({
      activeShotId,
      activeFrameByShotId,
      activeView,
    });
  }, [activeShotId, activeFrameByShotId, activeView, onStateChange]);

  const activeShot = editorShots.find((s) => s.id === activeShotId)
    ?? editorShots[0]
    ?? mappedShots[0]
    ?? null;
  const activeFrame = activeShot
    ? findFrameById(activeShot, activeFrameByShotId[activeShot.id])
    : null;

  const handleSelectShot = (shotId: number) => {
    setActiveShotId(shotId);
    const targetShot = editorShots.find((shot) => shot.id === shotId);
    if (!targetShot) return;
    const defaultFrameId = getDefaultFrameId(targetShot);
    if (!defaultFrameId) return;
    setActiveFrameByShotId((prev) => ({ ...prev, [shotId]: defaultFrameId }));
  };

  const handleSelectFrame = (shotId: number, frameId: string) => {
    setActiveShotId(shotId);
    setActiveFrameByShotId((prev) => ({ ...prev, [shotId]: frameId }));
  };

  const handleShotChange = (shotId: number, patch: Partial<Shot>) => {
    setEditorShots((prev) =>
      prev.map((shot) => {
        if (shot.id !== shotId) return shot;
        return {
          ...shot,
          ...patch,
          voiceover: patch.voiceover
            ? { ...shot.voiceover, ...patch.voiceover }
            : shot.voiceover,
          shotDescription: patch.shotDescription
            ? {
                ...shot.shotDescription,
                ...patch.shotDescription,
                tags: patch.shotDescription.tags ?? shot.shotDescription.tags,
              }
            : shot.shotDescription,
        };
      })
    );
  };

  const handleSave = async () => {
    if (!onSave || isSaving) return;
    setIsSaving(true);
    setSaveMessage('');
    try {
      const payload: SaveManualEditsRequest = {
        characters: characters.map((c) => ({
          id: c.id,
          name: c.name,
          voice: c.voice,
          appearance: c.appearance || '',
        })),
        shots: editorShots.map((shot) => {
          const frames = getShotFrames(shot);
          const startFrame = frames.find((f) => f.type === 'start');
          const endFrame = frames.find((f) => f.type === 'end');
          const keyframes = frames.filter((f) => f.type === 'key');
          return {
            storyboard_number: shot.id,
            summary: shot.sceneDescription || '',
            visual_desc: shot.shotDescription.text || '',
            narration: shot.voiceover.text === '（无旁白）' ? '' : shot.voiceover.text,
            tags: shot.shotDescription.tags || [],
            duration_seconds: shot.durationSeconds || 0,
            start_frame_url: startFrame?.imageUrl || undefined,
            end_frame_url: endFrame?.imageUrl || undefined,
            keyframe_urls: keyframes.length > 0
              ? keyframes.map((f) => f.imageUrl).filter(Boolean)
              : undefined,
          };
        }),
      };
      await onSave(payload);
      setSaveMessage('已保存到后端');
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleRegenerateImage = async (shotId: number, prompt: string) => {
    if (isRegeneratingImage) return;
    const media = mediaByNumber.get(shotId);
    if (!media) {
      setSaveMessage('未找到对应分镜的媒体数据，请先保存');
      return;
    }
    setIsRegeneratingImage(true);
    setSaveMessage('');
    try {
      const result = await regenerateStoryboardImage(media.storyboard_id, prompt);
      const startUrl = cleanUrl(result.start_frame_url) || cleanUrl(result.image_url);
      const endUrl = cleanUrl(result.end_frame_url) || startUrl;
      const keyframeUrls = (result.keyframe_urls || []).map((url) => cleanUrl(url)).filter(Boolean).slice(0, 1);
      setEditorShots((prev) =>
        prev.map((shot) => {
          if (shot.id !== shotId) return shot;
          const newFrames: ShotFrame[] = [
            {
              id: `${shotId}-start`,
              type: 'start' as const,
              imageUrl: startUrl,
              label: '首帧',
            },
            ...keyframeUrls.map((url, index) => ({
              id: `${shotId}-key-${index + 1}`,
              type: 'key' as const,
              imageUrl: url,
              label: `关键帧${index + 1}`,
            })),
            {
              id: `${shotId}-end`,
              type: 'end' as const,
              imageUrl: endUrl,
              label: '尾帧',
            },
          ].filter((frame) => Boolean(cleanUrl(frame.imageUrl)));
          return {
            ...shot,
            previewImage: startUrl,
            timelineFrames: newFrames,
            timelineImages: newFrames.map((f) => f.imageUrl).filter(Boolean),
          };
        }),
      );
      setSaveMessage(keyframeUrls.length ? '首尾帧和关键帧已重新生成' : '首尾帧已重新生成');
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setIsRegeneratingImage(false);
    }
  };

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-800 dark:text-slate-100 font-display antialiased h-full flex flex-col overflow-hidden selection:bg-primary selection:text-white">
      <Header
        activeView={activeView}
        onViewChange={setActiveView}
        onSave={handleSave}
        isSaving={isSaving}
        saveDisabled={!onSave}
        onClose={onClose}
      />
      {activeView === 'storyboard' ? (
        <main className="flex-1 flex flex-col overflow-hidden">
          {activeShot ? (
            <>
              <section className="flex-1 flex overflow-hidden min-h-0">
                <Sidebar shot={activeShot} characters={characters} onShotChange={handleShotChange} onRegenerateImage={handleRegenerateImage} isRegeneratingImage={isRegeneratingImage} />
                <section className="flex-1 bg-white dark:bg-slate-900 flex flex-col min-w-0 relative">
                  <div className="flex-1 flex p-6 overflow-hidden">
                    <Preview shot={activeShot} frame={activeFrame} />
                  </div>
                  {loadingMedia && (
                    <div className="absolute top-4 right-4 text-xs px-3 py-1.5 rounded-full bg-white/90 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-300">
                      正在加载最新分镜素材...
                    </div>
                  )}
                  {saveMessage && (
                    <div className="absolute top-4 left-4 text-xs px-3 py-1.5 rounded-full bg-white/90 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-300">
                      {saveMessage}
                    </div>
                  )}
                </section>
              </section>
              <Timeline
                shots={editorShots}
                activeShotId={activeShotId}
                activeFrameId={activeFrame?.id || ''}
                onSelectShot={handleSelectShot}
                onSelectFrame={handleSelectFrame}
              />
            </>
          ) : (
            <section className="flex-1 bg-white dark:bg-slate-900 flex items-center justify-center text-sm text-slate-500 dark:text-slate-400">
              暂无可编辑分镜数据
            </section>
          )}
        </main>
      ) : (
        <RoleSettingsView characters={characters} onCharactersChange={setCharacters} />
      )}
    </div>
  );
}
