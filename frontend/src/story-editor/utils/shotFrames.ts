import type { Shot, ShotFrame } from '../data/storyboard';

function cleanUrl(value: string | undefined): string {
  return (value || '').trim();
}

export function getShotFrames(shot: Shot): ShotFrame[] {
  const fromShot = (shot.timelineFrames || []).filter((frame) => cleanUrl(frame.imageUrl));
  if (fromShot.length) return fromShot;

  const fallbackUrls = shot.timelineImages.map((item) => cleanUrl(item)).filter(Boolean);
  const preview = cleanUrl(shot.previewImage);
  const startUrl = fallbackUrls[0] || preview;
  if (!startUrl) return [];

  const endUrl = fallbackUrls.length > 1 ? fallbackUrls[fallbackUrls.length - 1] : startUrl;
  const keyframeUrls = fallbackUrls.slice(1, -1).slice(0, 3);

  const frames: ShotFrame[] = [
    {
      id: `${shot.id}-start`,
      type: 'start',
      imageUrl: startUrl,
      label: '首帧',
    },
    ...keyframeUrls.map((url, index) => ({
      id: `${shot.id}-key-${index + 1}`,
      type: 'key' as const,
      imageUrl: url,
      label: `关键帧${index + 1}`,
    })),
    {
      id: `${shot.id}-end`,
      type: 'end',
      imageUrl: endUrl,
      label: '尾帧',
    },
  ];

  return frames;
}

export function getDefaultFrameId(shot: Shot): string {
  return getShotFrames(shot)[0]?.id || '';
}

export function findFrameById(shot: Shot, frameId?: string): ShotFrame | null {
  const frames = getShotFrames(shot);
  if (!frames.length) return null;
  if (!frameId) return frames[0];
  return frames.find((frame) => frame.id === frameId) || frames[0];
}
