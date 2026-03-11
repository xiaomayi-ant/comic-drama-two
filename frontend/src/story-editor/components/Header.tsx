import { Film, User, RotateCcw, X } from 'lucide-react';

interface HeaderProps {
  activeView: 'storyboard' | 'roles';
  onViewChange: (view: 'storyboard' | 'roles') => void;
  onSave?: () => void;
  isSaving?: boolean;
  saveDisabled?: boolean;
  onClose: () => void;
}

export function Header({
  activeView,
  onViewChange,
  onSave,
  isSaving = false,
  saveDisabled = false,
  onClose,
}: HeaderProps) {
  return (
    <header className="h-16 bg-surface-light dark:bg-surface-dark border-b border-border-light dark:border-border-dark flex items-center justify-between px-6 shrink-0 z-20">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold text-slate-900 dark:text-white">分镜编辑</h1>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={() => onViewChange('storyboard')}
          className={`flex items-center gap-2 px-4 py-2 font-medium rounded-lg transition-colors ${
            activeView === 'storyboard'
              ? 'bg-indigo-50 dark:bg-indigo-900/30 text-primary hover:bg-indigo-100 dark:hover:bg-indigo-900/50'
              : 'hover:bg-slate-100 dark:hover:bg-slate-700/50 text-slate-600 dark:text-slate-300'
          }`}
        >
          <Film className="w-5 h-5" />
          分镜
        </button>
        <button
          onClick={() => onViewChange('roles')}
          className={`flex items-center gap-2 px-4 py-2 font-medium rounded-lg transition-colors ${
            activeView === 'roles'
              ? 'bg-indigo-50 dark:bg-indigo-900/30 text-primary hover:bg-indigo-100 dark:hover:bg-indigo-900/50'
              : 'hover:bg-slate-100 dark:hover:bg-slate-700/50 text-slate-600 dark:text-slate-300'
          }`}
        >
          <User className="w-5 h-5" />
          角色
        </button>
        <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-2"></div>
        <button className="flex items-center gap-2 px-3 py-2 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
          <RotateCcw className="w-5 h-5" />
          重置
        </button>
        <button
          onClick={onSave}
          disabled={saveDisabled || isSaving}
          className={`px-5 py-2 font-medium rounded-lg transition-colors ${
            saveDisabled || isSaving
              ? 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'
              : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600'
          }`}
        >
          {isSaving ? '保存中...' : '保存'}
        </button>
        <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
          <X className="w-6 h-6" />
        </button>
      </div>
    </header>
  );
}
