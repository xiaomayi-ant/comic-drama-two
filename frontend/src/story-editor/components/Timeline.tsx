import { useEffect, useMemo, useRef } from 'react';
import type { Shot, ShotFrame } from '../data/storyboard';
import { getShotFrames } from '../utils/shotFrames';

interface TimelineProps {
  shots: Shot[];
  activeShotId: number;
  activeFrameId: string;
  onSelectShot: (id: number) => void;
  onSelectFrame: (shotId: number, frameId: string) => void;
}

const GAP_PX = 4;

function splitFrames(frames: ShotFrame[]) {
  if (!frames.length) {
    return {
      startFrame: null as ShotFrame | null,
      endFrame: null as ShotFrame | null,
      keyFrames: [] as ShotFrame[],
    };
  }

  const startFrame = frames.find((frame) => frame.type === 'start') || frames[0];
  const endFrame = [...frames].reverse().find((frame) => frame.type === 'end') || frames[frames.length - 1];
  const keyFrames = frames.filter((frame) => frame.type === 'key').slice(0, 3);

  return { startFrame, endFrame, keyFrames };
}

function renderFrameButton(
  frame: ShotFrame | null,
  options: {
    isActive: boolean;
    title: string;
    label: string;
    className: string;
    onClick: () => void;
  },
) {
  const { isActive, title, label, className, onClick } = options;
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        if (frame) onClick();
      }}
      className={`${className} relative overflow-hidden rounded-md border transition-all ${
        isActive
          ? 'border-primary ring-2 ring-primary/40'
          : 'border-slate-300 dark:border-slate-600 hover:border-primary/60'
      }`}
      title={title}
    >
      {frame ? (
        <img
          alt={title}
          className="w-full h-full object-cover"
          src={frame.imageUrl}
          referrerPolicy="no-referrer"
        />
      ) : (
        <div className="w-full h-full bg-slate-200 dark:bg-slate-700" />
      )}
      <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1 py-0.5 text-[9px] text-white">
        {label}
      </span>
    </button>
  );
}

export function Timeline({
  shots,
  activeShotId,
  activeFrameId,
  onSelectShot,
  onSelectFrame,
}: TimelineProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const { totalWidthPx, tickMarks } = useMemo(() => {
    if (!shots.length) {
      return { totalWidthPx: 0, tickMarks: [] as { time: number; leftPx: number }[] };
    }

    const widths = shots.map((s) => parseInt(s.timelineWidth, 10));
    const total = widths.reduce((sum, width, index) => sum + width + (index > 0 ? GAP_PX : 0), 0);
    const ticks: { time: number; leftPx: number }[] = [];
    let elapsed = 0;
    let offset = 0;

    shots.forEach((shot, index) => {
      elapsed += shot.durationSeconds;
      offset += widths[index];
      ticks.push({ time: elapsed, leftPx: offset + (index * GAP_PX) });
    });

    return { totalWidthPx: total, tickMarks: ticks };
  }, [shots]);

  const totalDuration = useMemo(() => {
    const total = shots.reduce((sum, shot) => sum + shot.durationSeconds, 0);
    return `${total.toFixed(1)}s`;
  }, [shots]);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    const active = container.querySelector<HTMLElement>(`[data-shot-id="${activeShotId}"]`);
    if (!active) return;
    const left = active.offsetLeft - 40;
    container.scrollTo({ left: Math.max(0, left), behavior: 'smooth' });
  }, [activeShotId]);

  if (!shots.length) {
    return (
      <div className="h-52 shrink-0 border-t border-border-light bg-surface-light dark:border-border-dark dark:bg-surface-dark flex items-center justify-center text-sm text-slate-500 dark:text-slate-400">
        暂无可编辑分镜
      </div>
    );
  }

  const axisWidth = Math.max(160, Math.round(totalWidthPx * 0.2));
  const axisLeft = Math.max(24, Math.round((totalWidthPx - axisWidth) / 2) + 8);

  return (
    <div className="h-52 shrink-0 border-t border-border-light bg-surface-light dark:border-border-dark dark:bg-surface-dark flex flex-col">
      <div className="h-9 px-4 flex items-center justify-between border-b border-border-light dark:border-slate-700/50">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">时间轴</h3>
        <span className="text-xs font-mono text-slate-500 dark:text-slate-400">总时长: {totalDuration}</span>
      </div>

      <div
        ref={scrollRef}
        className="relative flex-1 overflow-x-auto overflow-y-hidden px-3 pt-2 pb-2 custom-scrollbar touch-pan-x"
        onWheel={(event) => {
          const container = scrollRef.current;
          if (!container) return;
          if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
          event.preventDefault();
          container.scrollLeft += event.deltaY;
        }}
      >
        <div
          className="relative h-5 mb-2 text-[9px] text-slate-400 font-mono"
          style={{ width: `${totalWidthPx}px`, marginLeft: '8px', marginRight: '8px' }}
        >
          {tickMarks.map((tick) => (
            <div
              key={`${tick.time}-${tick.leftPx}`}
              className="absolute top-0 bottom-0 flex flex-col items-end justify-start"
              style={{ left: `${tick.leftPx}px` }}
            >
              <span className="relative -right-2 leading-none">{tick.time.toFixed(1)}s</span>
            </div>
          ))}
        </div>

        <div
          className="pointer-events-none absolute left-8 top-[36px] z-0"
          style={{ width: `${axisWidth}px`, left: `${axisLeft}px` }}
        >
          <div className="h-px bg-primary/35" />
        </div>

        <div className="relative z-10 flex min-w-max gap-[4px] px-2 pb-1">
          {shots.map((shot) => {
            const isActive = shot.id === activeShotId;
            const frames = getShotFrames(shot);
            const { startFrame, endFrame, keyFrames } = splitFrames(frames);
            const keyFrame = keyFrames[0] || null;

            return (
              <div
                key={shot.id}
                data-shot-id={shot.id}
                onClick={() => onSelectShot(shot.id)}
                className={`relative flex flex-col rounded-md transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-primary/5 ring-1 ring-primary/25'
                    : 'hover:bg-slate-100/80 dark:hover:bg-slate-800/40'
                }`}
                style={{ width: shot.timelineWidth }}
              >
                <div className="px-1.5 py-1.5">
                  <div className="flex h-[86px] items-stretch gap-1.5">
                    {renderFrameButton(startFrame, {
                      isActive: isActive && startFrame?.id === activeFrameId,
                      title: `分镜${shot.id}首帧`,
                      label: '首帧',
                      className: 'w-[64px] shrink-0',
                      onClick: () => onSelectFrame(shot.id, startFrame!.id),
                    })}

                    {renderFrameButton(keyFrame, {
                      isActive: isActive && keyFrame?.id === activeFrameId,
                      title: keyFrame?.label || `分镜${shot.id}关键帧`,
                      label: keyFrame?.label || '关键',
                      className: 'w-[52px] shrink-0',
                      onClick: () => {
                        if (keyFrame) onSelectFrame(shot.id, keyFrame.id);
                      },
                    })}

                    {renderFrameButton(endFrame, {
                      isActive: isActive && endFrame?.id === activeFrameId,
                      title: `分镜${shot.id}尾帧`,
                      label: '尾帧',
                      className: 'w-[64px] shrink-0',
                      onClick: () => onSelectFrame(shot.id, endFrame!.id),
                    })}
                  </div>
                </div>

                <div className="pointer-events-none absolute left-1 top-1 rounded bg-white/85 px-1 py-0.5 text-[8px] font-semibold text-slate-600 shadow-sm dark:bg-slate-900/85 dark:text-slate-300">
                  S{shot.id}
                </div>
                <div className="pointer-events-none absolute right-1 top-1 rounded bg-white/85 px-1 py-0.5 text-[8px] font-mono text-slate-500 shadow-sm dark:bg-slate-900/85 dark:text-slate-400">
                  {shot.durationSeconds.toFixed(1)}s
                </div>
                <div className="pointer-events-none absolute right-0 top-1 bottom-1 w-px bg-slate-200 dark:bg-slate-700/50" />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
