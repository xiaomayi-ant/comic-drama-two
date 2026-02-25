import type { ScriptData, Character, Scene, Prop, Shot } from '../components/ScriptView';

interface ParseOptions {
  userInput: string;
  title?: string;
  durationSec?: string;
  styleName?: string;
}

// ── helpers ───────────────────────────────────────────────────────

function isChinese(str: string): boolean {
  return /^[\u4e00-\u9fff]+$/.test(str);
}

/** Strip ``` fences and trim */
function cleanMarkdown(text: string): string {
  return text
    .replace(/^```[^\n]*\n?/gm, '')
    .replace(/```$/gm, '')
    .trim();
}

// Words that should NOT be treated as character names
const NAME_BLACKLIST = new Set([
  '勿外传', '元朝末年', '武当山', '明教', '太极', '乾坤', '九阳',
  '武林', '天下', '江湖', '中原', '少林', '峨眉', '昆仑', '崆峒',
  '正邪', '阴阳', '巅峰', '山巅', '金殿', '云雾', '寒气', '真气',
  '神功', '剑法', '掌法', '拳法', '内力', '寒毒', '冰封',
  '特写', '远景', '全景', '中景', '近景', '俯拍', '仰拍',
  '画面', '镜头', '背景', '前景', '构图', '色调', '光影',
  '整体', '风格', '质感', '氛围', '情绪', '动作', '场景',
]);

// ── section splitter ──────────────────────────────────────────────

function splitSections(text: string): { synopsis: string; shots: string; style: string } {
  const normalized = cleanMarkdown(text);

  let synopsis = '';
  let shots = '';
  let style = '';

  const shotIdx = normalized.search(/(?:^|\n)\s*(?:#{1,3}\s*)?分镜设计/);
  const styleIdx = normalized.search(/(?:^|\n)\s*(?:#{1,3}\s*)?视觉风格/);

  if (shotIdx !== -1 && styleIdx !== -1) {
    synopsis = normalized.slice(0, shotIdx).trim();
    shots = normalized.slice(shotIdx, styleIdx).trim();
    style = normalized.slice(styleIdx).trim();
  } else if (shotIdx !== -1) {
    synopsis = normalized.slice(0, shotIdx).trim();
    shots = normalized.slice(shotIdx).trim();
  } else if (styleIdx !== -1) {
    synopsis = normalized.slice(0, styleIdx).trim();
    style = normalized.slice(styleIdx).trim();
  } else {
    synopsis = normalized;
  }

  synopsis = synopsis
    .replace(/^(?:#{1,3}\s*)?剧本概览\s*/m, '')
    .replace(/^故事核心[：:]\s*/m, '')
    .trim();

  shots = shots.replace(/^(?:#{1,3}\s*)?分镜设计\s*/m, '').trim();
  style = style.replace(/^(?:#{1,3}\s*)?视觉风格\s*/m, '').trim();

  return { synopsis, shots, style };
}

// ── extract characters ────────────────────────────────────────────

function extractCharacters(synopsis: string, shotsText: string): Character[] {
  const allText = synopsis + '\n' + shotsText;
  const nameSet = new Set<string>();
  const characters: Character[] = [];

  // Pattern: 人名（角色描述）
  const rolePattern = /([^\s，。、；：""''（）【】\d]{2,4})(?:[（(]([^）)]+)[）)])/g;
  let m: RegExpExecArray | null;
  while ((m = rolePattern.exec(allText)) !== null) {
    const name = m[1];
    const desc = m[2];
    if (!nameSet.has(name) && isChinese(name) && !NAME_BLACKLIST.has(name) && name.length >= 2 && name.length <= 4) {
      nameSet.add(name);
      characters.push({
        id: String(characters.length + 1),
        name,
        description: desc,
      });
    }
  }

  // Fallback: names before action verbs, only if we found very few
  if (characters.length < 2) {
    const nameVerb = /(?:^|[，。；\s])([^\s，。、；：""''（）【】\d]{2,3})(?:以|与|和|向|持|挥|缓缓|双掌|单掌|飞身|腾空|出招|化解)/g;
    while ((m = nameVerb.exec(allText)) !== null) {
      const name = m[1];
      if (!nameSet.has(name) && isChinese(name) && !NAME_BLACKLIST.has(name) && name.length >= 2 && name.length <= 3) {
        nameSet.add(name);
        characters.push({
          id: String(characters.length + 1),
          name,
          description: '',
        });
      }
    }
  }

  return characters;
}

// ── extract scenes (real locations) ───────────────────────────────

function extractScenes(synopsis: string, shotsText: string): Scene[] {
  const allText = synopsis + '\n' + shotsText;
  const scenes: Scene[] = [];
  const nameSet = new Set<string>();

  // Pattern: 在XXX / XXX前 / XXX上 / XXX中 — location patterns
  const locationPatterns = [
    /(?:在|于)([^\s，。；：""''（）【】]{3,10}?)(?:之?[上中前巅顶边旁])/g,
    /场景[：:]\s*([^；。\n,，]+)/g,
    /([^\s，。；：""''（）【】]{2,6}(?:山巅|金殿|山谷|广场|大殿|客栈|庭院|山洞|峡谷|河畔|湖边|林中|密林|竹林|雪地|荒野|城楼|擂台|战场))/g,
  ];

  for (const pattern of locationPatterns) {
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(allText)) !== null) {
      const items = (m[1] || m[0]).split(/[,，、]/).map(s => s.trim()).filter(Boolean);
      for (const loc of items) {
        const clean = loc.replace(/^的/, '').trim();
        if (clean.length >= 2 && clean.length <= 12 && !nameSet.has(clean)) {
          nameSet.add(clean);
          scenes.push({
            id: String(scenes.length + 1),
            name: clean,
            description: '',
          });
        }
      }
    }
  }

  return scenes;
}

// ── extract props ─────────────────────────────────────────────────

function extractProps(allText: string): Prop[] {
  const props: Prop[] = [];
  const nameSet = new Set<string>();

  const propPatterns = [
    /(?:太极[剑拳]|乾坤大挪移|九阳[神真]功|明教令牌|屠龙[刀剑]|倚天[剑刀]|圣火令|冰魄银针|玄冥神掌|七伤拳)/g,
    /(?:物品[：:]\s*)([^；。\n]+)/g,
    /(?:道具[：:]\s*)([^；。\n]+)/g,
  ];

  for (const pattern of propPatterns) {
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(allText)) !== null) {
      const propStr = m[1] || m[0];
      const items = propStr.split(/[,，、]/).map(s => s.trim()).filter(Boolean);
      for (const item of items) {
        if (item.length >= 2 && item.length <= 8 && !nameSet.has(item)) {
          nameSet.add(item);
          props.push({
            id: String(props.length + 1),
            name: item,
            type: props.length === 0 ? '关键道具' : '普通道具',
          });
        }
      }
    }
  }

  return props;
}

// ── parse shots ───────────────────────────────────────────────────

function parseShotList(shotsText: string, synopsis: string): { parsed: Shot[]; count: number } {
  const shots: Shot[] = [];
  const parts = shotsText.split(/(?=【)/);

  for (const part of parts) {
    const nameMatch = part.match(/^【(.+?)】/);
    if (!nameMatch) continue;

    const shotName = nameMatch[1];
    const body = part.slice(nameMatch[0].length).replace(/^[\s\-—]+/, '').trim();

    // Extract dialogue from quotes
    const dialogueMatch = body.match(/[""「]([^""」]+)[""」]/);
    const dialogue = dialogueMatch ? dialogueMatch[1] : '';

    // Summary: first sentence or first ~30 chars
    const firstSentence = body.split(/[。；\n]/)[0]?.trim() || body.slice(0, 60);

    const shotId = shots.length + 1;

    // Only shot 1 gets narration — extracted from synopsis
    let narration = '';
    if (shotId === 1 && synopsis) {
      // Take first 1-2 sentences from synopsis as opening narration
      const sentences = synopsis.split(/[。！？]/).filter(s => s.trim());
      narration = (sentences.slice(0, 2).join('，') + '！').replace(/，！$/, '！');
    }

    shots.push({
      id: shotId,
      duration: `${(2 + Math.random() * 3).toFixed(1)}s`,
      summary: firstSentence.slice(0, 80),
      narration,
      hasNarration: shotId === 1 && !!narration,
      visualDesc: body,
      shotName,
    });
  }

  return { parsed: shots, count: shots.length };
}

// ── main export ───────────────────────────────────────────────────

export function parseScriptMarkdown(
  finalCopy: string,
  options: ParseOptions,
): ScriptData {
  const { synopsis, shots: shotsText, style: styleText } = splitSections(finalCopy);
  const { parsed: shotList, count: shotCount } = parseShotList(shotsText, synopsis);
  const characters = extractCharacters(synopsis, shotsText);
  const scenes = extractScenes(synopsis, shotsText);
  const props = extractProps(synopsis + '\n' + shotsText);

  const durationLabel = options.durationSec && options.durationSec !== 'auto'
    ? `${options.durationSec} 秒`
    : shotCount > 0
      ? `${(shotCount * 3).toFixed(1)} 秒`
      : '24 秒';

  const styleLabel = options.styleName || '日漫 电影质感';
  const title = options.title || options.userInput.slice(0, 20);

  return {
    title,
    totalShots: shotCount || 8,
    totalDuration: durationLabel,
    style: styleLabel,
    requirements: options.userInput,
    synopsis: synopsis || '暂无故事梗概',
    packagingStyle: styleText || '暂无包装风格描述',
    characters,
    scenes,
    props,
    shots: shotList,
  };
}
