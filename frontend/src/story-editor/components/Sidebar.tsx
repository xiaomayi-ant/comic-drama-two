import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Check, Pencil, Play, Plus, RefreshCw, X } from 'lucide-react';
import type { Shot } from '../data/storyboard';
import type { Character } from '../data/characters';

interface SidebarProps {
  shot: Shot;
  characters: Character[];
  onShotChange: (shotId: number, patch: Partial<Shot>) => void;
  onRegenerateImage?: (shotId: number, prompt: string) => void;
  isRegeneratingImage?: boolean;
}

export function Sidebar({ shot, characters, onShotChange, onRegenerateImage, isRegeneratingImage = false }: SidebarProps) {
  const [tags, setTags] = useState<string[]>(shot.shotDescription.tags);
  const [voiceText, setVoiceText] = useState<string>(shot.voiceover.text);
  const [shotText, setShotText] = useState<string>(shot.shotDescription.text);
  const [sceneDesc, setSceneDesc] = useState<string>(shot.sceneDescription);
  const [isAdding, setIsAdding] = useState(false);
  const [newTag, setNewTag] = useState('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const activeCharacter = characters.find((character) => character.id === shot.voiceover.roleTag);
  const addInputRef = useRef<HTMLInputElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setTags(shot.shotDescription.tags);
    setVoiceText(shot.voiceover.text);
    setShotText(shot.shotDescription.text);
    setSceneDesc(shot.sceneDescription);
    setIsAdding(false);
    setEditingIndex(null);
  }, [shot.id]);

  useEffect(() => {
    if (isAdding) addInputRef.current?.focus();
  }, [isAdding]);

  useEffect(() => {
    if (editingIndex !== null) editInputRef.current?.focus();
  }, [editingIndex]);

  const handleRemoveTag = (index: number) => {
    const next = tags.filter((_, i) => i !== index);
    setTags(next);
    onShotChange(shot.id, {
      shotDescription: {
        ...shot.shotDescription,
        tags: next,
        text: shotText,
      },
    });
  };

  const handleAddTag = () => {
    const trimmed = newTag.trim();
    if (trimmed && !tags.includes(trimmed)) {
      const next = [...tags, trimmed];
      setTags(next);
      onShotChange(shot.id, {
        shotDescription: {
          ...shot.shotDescription,
          tags: next,
          text: shotText,
        },
      });
    }
    setNewTag('');
    setIsAdding(false);
  };

  const handleStartEdit = (index: number) => {
    setEditingIndex(index);
    setEditValue(tags[index]);
  };

  const handleConfirmEdit = () => {
    if (editingIndex === null) return;
    const trimmed = editValue.trim();
    if (trimmed) {
      const next = tags.map((t, i) => (i === editingIndex ? trimmed : t));
      setTags(next);
      onShotChange(shot.id, {
        shotDescription: {
          ...shot.shotDescription,
          tags: next,
          text: shotText,
        },
      });
    }
    setEditingIndex(null);
    setEditValue('');
  };

  return (
    <aside className="w-[450px] bg-surface-light dark:bg-surface-dark border-r border-border-light dark:border-border-dark flex flex-col overflow-y-auto shrink-0">
      <div className="p-6 space-y-8">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">分镜 {shot.id}</h2>
          <span className="text-slate-500 font-mono">{shot.duration}</span>
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">场景描述</label>
          <textarea
            className="w-full p-3 bg-white dark:bg-slate-800 border border-border-light dark:border-border-dark rounded-lg text-sm leading-relaxed text-slate-700 dark:text-slate-300 focus:ring-2 focus:ring-primary focus:border-primary transition-shadow resize-none outline-none"
            rows={3}
            value={sceneDesc}
            onChange={(e) => {
              const next = e.target.value;
              setSceneDesc(next);
              onShotChange(shot.id, { sceneDescription: next });
            }}
          />
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">配音</label>
          <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-border-light dark:border-border-dark space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-slate-900 dark:text-white">
                  {activeCharacter?.name ?? shot.voiceover.role}
                </span>
                <span className="text-xs px-1.5 py-0.5 bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded">{shot.voiceover.roleTag}</span>
                <span className="text-xs text-slate-400 ml-2">建议配音文案 {shot.voiceover.charRange} 字 (约 {shot.duration} 镜头)</span>
              </div>
            </div>
            <div className="flex gap-2">
              <textarea
                className="w-full bg-surface-light dark:bg-slate-700 border-border-light dark:border-slate-600 rounded-lg text-sm p-3 resize-none focus:ring-primary focus:border-primary outline-none"
                placeholder="输入配音文案..."
                rows={3}
                value={voiceText}
                onChange={(e) => {
                  const next = e.target.value;
                  setVoiceText(next);
                  onShotChange(shot.id, {
                    voiceover: {
                      ...shot.voiceover,
                      text: next,
                    },
                  });
                }}
              />
              <button
                onClick={() =>
                  onShotChange(shot.id, {
                    voiceover: {
                      ...shot.voiceover,
                      text: voiceText,
                    },
                  })
                }
                className="shrink-0 h-9 px-3 bg-black text-white text-xs font-medium rounded-lg hover:bg-slate-800 self-start mt-1"
              >
                保存
              </button>
            </div>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <select className="w-full pl-3 pr-10 py-2 bg-slate-200 dark:bg-slate-700 border-none rounded-lg text-sm appearance-none cursor-pointer focus:ring-2 focus:ring-primary outline-none">
                  <option>潇洒侠客</option>
                  <option>沉稳老者</option>
                </select>
                <ChevronDown className="absolute right-2 top-2 text-slate-500 pointer-events-none w-5 h-5" />
              </div>
              <button className="p-2 bg-slate-200 dark:bg-slate-700 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors">
                <Play className="text-slate-600 dark:text-slate-300 w-5 h-5 fill-current" />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">分镜描述</label>
          <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-t-xl border border-border-light dark:border-border-dark flex flex-wrap gap-2 items-center">
            {tags.map((tag, index) => (
              editingIndex === index ? (
                <span key={`edit-${index}`} className="inline-flex items-center gap-1 bg-white dark:bg-slate-700 border-2 border-primary rounded overflow-hidden">
                  <input
                    ref={editInputRef}
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleConfirmEdit();
                      if (e.key === 'Escape') setEditingIndex(null);
                    }}
                    className="w-24 px-2 py-1 text-xs bg-transparent outline-none"
                  />
                  <button
                    onClick={handleConfirmEdit}
                    className="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30"
                  >
                    <Check className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => setEditingIndex(null)}
                    className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ) : (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded text-xs text-slate-600 dark:text-slate-300 group/tag hover:border-primary transition-colors"
                >
                  {tag}
                  <button
                    onClick={() => handleStartEdit(index)}
                    className="ml-0.5 text-slate-300 hover:text-primary opacity-0 group-hover/tag:opacity-100 transition-opacity"
                    title="编辑"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => handleRemoveTag(index)}
                    className="text-slate-300 hover:text-red-500 opacity-0 group-hover/tag:opacity-100 transition-opacity"
                    title="删除"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )
            ))}

            {isAdding ? (
              <span className="inline-flex items-center gap-1 bg-white dark:bg-slate-700 border-2 border-primary rounded overflow-hidden">
                <input
                  ref={addInputRef}
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAddTag();
                    if (e.key === 'Escape') { setIsAdding(false); setNewTag(''); }
                  }}
                  placeholder="新标签..."
                  className="w-24 px-2 py-1 text-xs bg-transparent outline-none placeholder:text-slate-400"
                />
                <button
                  onClick={handleAddTag}
                  className="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30"
                >
                  <Check className="w-3 h-3" />
                </button>
                <button
                  onClick={() => { setIsAdding(false); setNewTag(''); }}
                  className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-600"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ) : (
              <button
                onClick={() => setIsAdding(true)}
                className="inline-flex items-center gap-1 px-2 py-1 border border-dashed border-slate-300 dark:border-slate-600 rounded text-xs text-slate-400 hover:border-primary hover:text-primary transition-colors"
              >
                <Plus className="w-3 h-3" />
                添加
              </button>
            )}
          </div>
          <div className="relative">
            <textarea
              className="w-full -mt-px p-4 bg-slate-100 dark:bg-slate-800 border border-border-light dark:border-border-dark rounded-b-xl text-sm leading-relaxed resize-none focus:ring-primary focus:border-primary outline-none"
              placeholder="描述分镜画面..."
              rows={6}
              value={shotText}
              onChange={(e) => {
                const next = e.target.value;
                setShotText(next);
                onShotChange(shot.id, {
                  shotDescription: {
                    ...shot.shotDescription,
                    tags,
                    text: next,
                  },
                });
              }}
            />
            <button
              onClick={() => onRegenerateImage?.(shot.id, shotText)}
              disabled={isRegeneratingImage || !shotText.trim()}
              className={`absolute bottom-3 right-3 flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                isRegeneratingImage || !shotText.trim()
                  ? 'bg-slate-300 dark:bg-slate-600 text-slate-500 dark:text-slate-400 cursor-not-allowed'
                  : 'bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200'
              }`}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRegeneratingImage ? 'animate-spin' : ''}`} />
              {isRegeneratingImage ? '生成中...' : '生成首帧图'}
            </button>
          </div>
        </div>

        <div className="space-y-3 pb-8">
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">镜头运动</label>
          <div className="w-full p-3 bg-slate-100 dark:bg-slate-800 border border-transparent dark:border-border-dark rounded-lg text-sm text-slate-600 dark:text-slate-400">
            {shot.cameraMovement}
          </div>
        </div>
      </div>
    </aside>
  );
}
