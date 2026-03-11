import { useState } from 'react';
import { Mic } from 'lucide-react';
import { CharacterCard } from './CharacterCard';
import type { Character } from '../data/characters';

interface RoleSettingsViewProps {
  characters: Character[];
  onCharactersChange: (characters: Character[]) => void;
}

export function RoleSettingsView({ characters, onCharactersChange }: RoleSettingsViewProps) {
  const [isBatchEditing, setIsBatchEditing] = useState(false);
  const [likedCharacters, setLikedCharacters] = useState<Record<string, boolean | null>>({});

  return (
    <main className="flex-1 flex flex-col h-full relative overflow-hidden">
      <div className="bg-surface-light dark:bg-surface-dark px-8 py-5 flex items-center justify-between flex-shrink-0 border-b border-border-light/70 dark:border-border-dark/70">
        <div className="flex items-center space-x-2 text-slate-900 dark:text-white font-medium text-lg">
          <Mic size={20} />
          <h2>角色设定</h2>
        </div>
        {isBatchEditing ? (
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsBatchEditing(false)}
              className="bg-black text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-slate-200 px-5 py-2 rounded-md text-sm font-medium transition-colors shadow-sm"
            >
              取消
            </button>
            <button className="bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 px-5 py-2 rounded-md text-sm font-medium transition-colors shadow-sm">
              保存
            </button>
          </div>
        ) : (
          <button
            onClick={() => setIsBatchEditing(true)}
            className="bg-black text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-slate-200 px-5 py-2 rounded-md text-sm font-medium transition-colors shadow-sm"
          >
            批量编辑
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-background-light dark:bg-background-dark custom-scrollbar">
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {characters.map((character) => (
            <div key={character.id}>
              <CharacterCard
                character={character}
                isBatchEditing={isBatchEditing}
                likedState={likedCharacters[character.id] ?? null}
                onToggleLike={(value) =>
                  setLikedCharacters((prev) => ({
                    ...prev,
                    [character.id]: prev[character.id] === value ? null : value,
                  }))
                }
                onCharacterChange={(patch) =>
                  onCharactersChange(
                    characters.map((item) =>
                      item.id === character.id
                        ? {
                            ...item,
                            ...patch,
                          }
                        : item
                    )
                  )
                }
              />
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
