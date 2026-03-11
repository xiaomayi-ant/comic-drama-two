import { Plus, RefreshCw, ThumbsDown, ThumbsUp, User } from 'lucide-react';
import type { Character } from '../data/characters';

interface CharacterCardProps {
  character: Character;
  isBatchEditing: boolean;
  likedState: boolean | null;
  onToggleLike: (value: boolean) => void;
  onCharacterChange: (patch: Partial<Pick<Character, 'name' | 'voice' | 'appearance'>>) => void;
}

export function CharacterCard({
  character,
  isBatchEditing,
  likedState,
  onToggleLike,
  onCharacterChange,
}: CharacterCardProps) {
  return (
    <div className="bg-surface-light dark:bg-surface-dark p-6 rounded-xl shadow-sm border border-border-light dark:border-border-dark flex flex-col gap-6 group hover:border-primary/50 transition-colors">
      <div className="flex gap-5">
        <div className="flex flex-col items-center gap-2">
          <div className="w-32 h-32 flex-shrink-0 rounded-lg overflow-hidden relative bg-slate-50 dark:bg-slate-700/40 border border-dashed border-slate-300 dark:border-slate-600 flex items-center justify-center text-slate-400">
            {character.image ? (
              <img
                src={character.image}
                alt={character.name}
                className="w-full h-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : (
              <User size={48} />
            )}
          </div>
          {isBatchEditing && (
            <div className="flex items-center gap-2">
              <button
                title="添加参考素材"
                className="w-8 h-8 flex items-center justify-center rounded-md bg-slate-100 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:bg-slate-700 dark:text-slate-500 dark:hover:bg-slate-600 dark:hover:text-slate-300 transition-colors"
              >
                <Plus size={16} />
              </button>
              <button
                title="重新生成角色"
                className="w-8 h-8 flex items-center justify-center rounded-md bg-black text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-slate-200 transition-colors"
              >
                <RefreshCw size={16} />
              </button>
            </div>
          )}
        </div>

        <div className="flex-1 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">角色名称</label>
              <div className="flex items-center gap-2">
                {character.readonly ? (
                  <div className="text-base font-medium dark:text-white">{character.name}</div>
                ) : (
                  <input
                    className="text-base font-medium bg-transparent border-b border-transparent focus:border-primary outline-none dark:text-white"
                    value={character.name}
                    onChange={(e) => onCharacterChange({ name: e.target.value })}
                  />
                )}
                {isBatchEditing && (
                  <div className="flex items-center gap-1">
                    <button
                      title="点赞"
                      onClick={() => onToggleLike(true)}
                      className={`w-6 h-6 flex items-center justify-center rounded transition-colors ${
                        likedState === true
                          ? 'text-primary'
                          : 'text-slate-300 hover:text-primary dark:text-slate-600'
                      }`}
                    >
                      <ThumbsUp size={14} />
                    </button>
                    <button
                      title="不喜欢"
                      onClick={() => onToggleLike(false)}
                      className={`w-6 h-6 flex items-center justify-center rounded transition-colors ${
                        likedState === false
                          ? 'text-red-500 dark:text-red-400'
                          : 'text-slate-300 hover:text-red-400 dark:text-slate-600'
                      }`}
                    >
                      <ThumbsDown size={14} />
                    </button>
                  </div>
                )}
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">角色ID</label>
              <div className="text-sm font-mono text-slate-500 dark:text-slate-400">{character.id}</div>
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-2">声音特征</label>
            {character.readonly ? (
              <div className="bg-slate-100 dark:bg-slate-700/50 rounded-md p-3 text-sm text-slate-600 dark:text-slate-300 leading-relaxed min-h-[5rem]">
                {character.voice}
              </div>
            ) : (
              <textarea
                className="w-full bg-slate-100 dark:bg-slate-700/50 border border-transparent focus:border-primary focus:ring-1 focus:ring-primary rounded-md p-3 text-sm text-slate-600 dark:text-slate-300 resize-none h-24 leading-relaxed outline-none transition-all"
                value={character.voice}
                onChange={(e) => onCharacterChange({ voice: e.target.value })}
                placeholder="输入声音特征..."
              />
            )}
          </div>
        </div>
      </div>

      {character.appearance !== null && (
        <div>
          <label className="block text-xs text-slate-500 dark:text-slate-400 mb-2">外观特征</label>
          <textarea
            className="w-full bg-slate-100 dark:bg-slate-700/50 border border-transparent focus:border-primary focus:ring-1 focus:ring-primary rounded-md p-3 text-sm text-slate-600 dark:text-slate-300 resize-none h-20 leading-relaxed outline-none transition-all"
            value={character.appearance}
            onChange={(e) => onCharacterChange({ appearance: e.target.value })}
            placeholder="输入外观特征..."
          />
        </div>
      )}
    </div>
  );
}
