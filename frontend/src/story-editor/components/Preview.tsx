import { useEffect, useState } from 'react';
import { ImageOff } from 'lucide-react';
import type { Shot, ShotFrame } from '../data/storyboard';

interface PreviewProps {
  shot: Shot;
  frame?: ShotFrame | null;
}

export function Preview({ shot, frame }: PreviewProps) {
  const [imgError, setImgError] = useState(false);
  const previewSrc = frame?.imageUrl || shot.previewImage;
  const frameLabel = frame?.label || '首帧';
  const imgKey = `${shot.id}-${frame?.id || previewSrc}`;
  const hasImage = Boolean(previewSrc);

  useEffect(() => {
    setImgError(false);
  }, [imgKey]);

  return (
    <div className="flex-1 relative bg-slate-100 dark:bg-black rounded-lg overflow-hidden border border-border-light dark:border-border-dark shadow-sm group">
      {hasImage && !imgError ? (
        <img
          alt={`分镜${shot.id} ${frameLabel}`}
          className="w-full h-full object-cover transition-opacity duration-300"
          src={previewSrc}
          referrerPolicy="no-referrer"
          onError={() => setImgError(true)}
          onLoad={() => setImgError(false)}
        />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-slate-400">
          <ImageOff className="w-16 h-16" />
          <span className="text-lg font-semibold">分镜 {shot.id}</span>
          <span className="text-sm">{hasImage ? shot.sceneDescription : '当前帧素材待生成'}</span>
        </div>
      )}
      <div className="absolute top-4 left-4 bg-black/70 text-white text-sm px-3 py-1 rounded-lg backdrop-blur-sm font-bold">
        分镜 {shot.id}
      </div>
      <div className="absolute top-4 right-4 bg-black/70 text-white text-xs px-2 py-1 rounded backdrop-blur-sm">
        {shot.duration}
      </div>
      <div className="absolute top-14 left-4 bg-black/60 text-white text-[11px] px-2 py-1 rounded backdrop-blur-sm">
        {frameLabel}
      </div>
    </div>
  );
}
