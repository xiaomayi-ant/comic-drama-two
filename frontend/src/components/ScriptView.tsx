import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Video,
  User,
  MapPin,
  Sword,
  LayoutList,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export interface Character {
  id: string;
  name: string;
  role: '主角' | '配角' | '功能性角色';
  appearance: {
    age: string;
    identity: string;
    features: string;
  };
  voice: string;
  description: string;
}

export interface Scene {
  id: string;
  name: string;
  description: string;
}

export interface Prop {
  id: string;
  name: string;
  type: '普通道具' | '关键道具';
}

export interface Shot {
  id: number;
  duration: string;
  summary: string;
  narration: string;
  hasNarration: boolean;
  visualDesc: string;
  shotName: string;
}

export interface ScriptData {
  title: string;
  totalShots: number;
  totalDuration: string;
  style: string;
  requirements: string;
  synopsis: string;
  packagingStyle: string;
  characters: Character[];
  scenes: Scene[];
  props: Prop[];
  shots: Shot[];
}

interface ScriptViewProps {
  isOpen: boolean;
  onClose: () => void;
  scriptData?: ScriptData;
}

const MOCK_SCRIPT: ScriptData = {
  title: "张三丰张无忌武侠对决",
  totalShots: 3,
  totalDuration: "10.5 秒",
  style: "日漫 电影质感",
  requirements: "创作张三丰大战张无忌的武侠剧本，要求内容不超过500字。",
  synopsis: "张三丰与张无忌因门派理念冲突在武当山巅对峙...",
  packagingStyle: "日漫电影质感，色彩浓郁且对比鲜明...",
  characters: [
    { id: "1", name: "张三丰", role: "主角", appearance: { age: "八十余岁", identity: "武当派祖师", features: "白发白须，仙风道骨，身着灰色道袍" }, voice: "沉稳低沉，带有洞察世事的从容", description: "武当派创始人，太极拳法宗师" },
    { id: "2", name: "张无忌", role: "主角", appearance: { age: "二十出头", identity: "明教教主", features: "英俊青年，眉宇间透着正气与坚毅，身着黑色劲装" }, voice: "年轻有力，语气坚定中带有敬意", description: "明教教主，身兼九阳神功与乾坤大挪移" },
    { id: "3", name: "旁白", role: "功能性角色", appearance: { age: "", identity: "画外音叙述者", features: "" }, voice: "浑厚磁性的男声，低沉而富有故事感", description: "负责串联剧情、交代背景的画外音" }
  ],
  scenes: [
    { id: "1", name: "武当山金殿", description: "云雾缭绕的高山之巅，金殿巍峨耸立。" }
  ],
  props: [
    { id: "1", name: "太极剑", type: "普通道具" },
    { id: "2", name: "明教令牌", type: "关键道具" }
  ],
  shots: [
    { id: 1, duration: "3.5s", shotName: "寒谷初临", summary: "云雾缭绕的武当山巅，两位武林至尊对峙而立", narration: "张三丰与张无忌因门派理念冲突在武当山巅对峙，一场惊天对决即将展开！", hasNarration: true, visualDesc: "远景：云雾缭绕的武当山巅金殿前，张三丰白衣飘飘立于左侧，张无忌黑袍猎猎站于右侧，二人相距十丈，真气激荡间碎石飞扬。" },
    { id: 2, duration: "4.0s", shotName: "乾坤初动", summary: "张无忌飞身而至，施展乾坤大挪移", narration: "", hasNarration: false, visualDesc: "全景：张无忌从远处飞身而至，双掌推出，乾坤大挪移的力道扭曲了周围空气，张三丰以太极化劲轻松接住。" },
    { id: 3, duration: "3.0s", shotName: "太极破势", summary: "张三丰缓缓睁开眼，太极剑法化解攻势", narration: "", hasNarration: false, visualDesc: "特写：张三丰缓缓睁开眼，眼中精光一闪，右手缓缓画出一个太极圆弧，剑气如虹，将张无忌的攻势尽数化解。" }
  ]
};

const ShotCard: React.FC<{ shot: Shot }> = ({ shot }) => {
  const [visualOpen, setVisualOpen] = useState(true);

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
      {/* Header: 镜头 N [ShotName] ··· duration */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-bold text-gray-800 dark:text-gray-200">镜头 {shot.id}</span>
          <span className="bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 text-[10px] font-bold px-2 py-0.5 rounded">
            S{shot.id}
          </span>
          {shot.shotName && (
            <span className="text-xs text-gray-400 font-medium">{shot.shotName}</span>
          )}
        </div>
        <span className="text-xs text-gray-400 font-mono">{shot.duration}</span>
      </div>

      <div className="p-4 space-y-3">
        {/* Summary */}
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          {shot.summary}
        </p>

        {/* Narration — only for shots with hasNarration */}
        {shot.hasNarration && shot.narration && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-orange-500 bg-orange-50 dark:bg-orange-900/20 px-1.5 py-0.5 rounded">
                配音
              </span>
              <span className="text-[10px] text-gray-400">旁白</span>
            </div>
            <div className="border-l-3 border-orange-400 pl-3 py-1">
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed italic">
                {shot.narration}
              </p>
            </div>
          </div>
        )}

        {/* Visual Description — collapsible */}
        <div className="space-y-2">
          <button
            onClick={() => setVisualOpen(!visualOpen)}
            className="flex items-center gap-2 group"
          >
            <span className="text-[10px] font-bold text-cyan-600 bg-cyan-50 dark:bg-cyan-900/20 px-1.5 py-0.5 rounded">
              AIGC
            </span>
            <span className="text-[10px] text-gray-400 group-hover:text-gray-600 transition-colors">视觉描述</span>
            {visualOpen ? (
              <ChevronUp size={12} className="text-gray-400" />
            ) : (
              <ChevronDown size={12} className="text-gray-400" />
            )}
          </button>
          {visualOpen && (
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                {shot.visualDesc}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default function ScriptView({ isOpen, onClose, scriptData }: ScriptViewProps) {
  const [activeSection, setActiveSection] = useState('requirement');
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const script = scriptData || MOCK_SCRIPT;

  const sections = [
    { id: 'requirement', label: '需求', icon: <LayoutList size={16} /> },
    { id: 'synopsis', label: '故事梗概', icon: <LayoutList size={16} /> },
    { id: 'style', label: '包装风格', icon: <LayoutList size={16} /> },
    { id: 'characters', label: '角色设定', icon: <User size={16} />, count: script.characters.length },
    { id: 'scenes', label: '场景设定', icon: <MapPin size={16} />, count: script.scenes.length },
    { id: 'props', label: '道具设定', icon: <Sword size={16} />, count: script.props.length },
    { id: 'shots', label: '分镜详情', icon: <Video size={16} />, count: script.shots.length },
  ];

  useEffect(() => {
    const handleScroll = () => {
      if (!scrollContainerRef.current) return;

      const scrollPosition = scrollContainerRef.current.scrollTop;
      const sectionElements = sections.map(s => document.getElementById(`sv-${s.id}`));

      for (let i = sectionElements.length - 1; i >= 0; i--) {
        const el = sectionElements[i];
        if (el && el.offsetTop <= scrollPosition + 150) {
          setActiveSection(sections[i].id);
          break;
        }
      }
    };

    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
    }
    return () => container?.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    const element = document.getElementById(`sv-${id}`);
    if (element && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: element.offsetTop - 100,
        behavior: 'smooth'
      });
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: '70vw', opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ type: 'spring', damping: 28, stiffness: 260 }}
          className="h-full flex-shrink-0 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 overflow-hidden flex flex-col relative"
        >
          {/* Collapse button on left edge */}
          <button
            onClick={onClose}
            className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 z-10 w-7 h-14 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors shadow-md"
          >
            <ChevronRight size={16} />
          </button>

          {/* Header */}
          <div className="h-14 flex items-center justify-between px-6 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
            <div className="flex items-center gap-4 text-sm">
              <h2 className="text-base font-bold">剧本</h2>
              <span className="text-gray-400">镜头 {script.totalShots}</span>
              <span className="text-gray-400">时长 {script.totalDuration}</span>
              <span className="text-gray-600 dark:text-gray-300 font-medium truncate max-w-[200px]">{script.title}</span>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body: Content + Sidebar Nav */}
          <div className="flex flex-1 overflow-hidden">
            {/* Main scrollable content */}
            <main
              ref={scrollContainerRef}
              className="flex-1 overflow-y-auto p-6 scroll-smooth ios-scroll"
            >
              <div className="max-w-3xl space-y-10 pb-24">
                {/* Summary Card */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-sm border border-gray-200/50 dark:border-gray-800">
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-3">
                      <span className="bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-900 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider">故事</span>
                      <h2 className="text-xl font-bold">{script.title}</h2>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                      <span>总计 <strong>{script.totalShots} 个镜头</strong></span>
                      <span>总时长 <strong>{script.totalDuration}</strong></span>
                      <span className="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-full text-xs font-medium">
                        {script.style}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="h-px bg-gray-200 dark:bg-gray-800" />

                {/* Requirements */}
                <section id="sv-requirement" className="space-y-3">
                  <h3 className="text-base font-bold">需求</h3>
                  <p className="text-gray-700 dark:text-gray-300 leading-relaxed text-sm">
                    {script.requirements}
                  </p>
                </section>

                {/* Synopsis */}
                <section id="sv-synopsis" className="space-y-3">
                  <h3 className="text-base font-bold">故事梗概</h3>
                  <p className="text-gray-700 dark:text-gray-300 leading-relaxed text-sm">
                    {script.synopsis}
                  </p>
                </section>

                {/* Style */}
                <section id="sv-style" className="space-y-3">
                  <h3 className="text-base font-bold">包装风格</h3>
                  <div className="p-5 bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200/50 dark:border-gray-800">
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                      {script.packagingStyle}
                    </p>
                  </div>
                </section>

                {/* Characters */}
                <section id="sv-characters" className="space-y-4">
                  <h3 className="text-base font-bold">角色设定 ({script.characters.length})</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {script.characters.map((char, idx) => {
                      const roleColor = char.role === '主角'
                        ? 'bg-blue-500'
                        : char.role === '配角'
                          ? 'bg-indigo-400'
                          : 'bg-gray-400';
                      const hasAppearance = char.appearance && (char.appearance.age || char.appearance.identity || char.appearance.features);
                      return (
                        <div
                          key={char.id}
                          className="bg-white dark:bg-gray-900 p-4 rounded-xl border border-gray-200 dark:border-gray-800 flex gap-3 items-start"
                        >
                          <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 shrink-0 flex items-center justify-center">
                            <User size={18} className="text-blue-500" />
                          </div>
                          <div className="space-y-2 min-w-0 flex-1">
                            {/* Name + Role */}
                            <div className="flex items-center gap-2">
                              <span className={`${roleColor} text-white text-[10px] font-bold px-1.5 py-0.5 rounded`}>
                                R{idx + 1}
                              </span>
                              <h4 className="font-bold text-sm">{char.name}</h4>
                              <span className="text-[10px] text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">
                                {char.role || '角色'}
                              </span>
                            </div>
                            {/* Description */}
                            <p className="text-xs text-gray-500 leading-relaxed">
                              {char.description}
                            </p>
                            {/* Appearance */}
                            {hasAppearance && (
                              <div className="space-y-1">
                                <span className="text-[10px] font-bold text-purple-500">形象</span>
                                <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500">
                                  {char.appearance.age && <span>年龄: {char.appearance.age}</span>}
                                  {char.appearance.identity && <span>身份: {char.appearance.identity}</span>}
                                </div>
                                {char.appearance.features && (
                                  <p className="text-xs text-gray-500 leading-relaxed">{char.appearance.features}</p>
                                )}
                              </div>
                            )}
                            {/* Voice */}
                            {char.voice && (
                              <div className="space-y-0.5">
                                <span className="text-[10px] font-bold text-orange-500">声音</span>
                                <p className="text-xs text-gray-500 leading-relaxed">{char.voice}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>

                {/* Scenes */}
                <section id="sv-scenes" className="space-y-4">
                  <h3 className="text-base font-bold">场景设定 ({script.scenes.length})</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {script.scenes.map((scene, idx) => (
                      <div
                        key={scene.id}
                        className="bg-white dark:bg-gray-900 p-4 rounded-xl border border-gray-200 dark:border-gray-800 flex gap-3 items-start"
                      >
                        <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 shrink-0 flex items-center justify-center">
                          <MapPin size={18} className="text-green-500" />
                        </div>
                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="bg-green-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                              L{idx + 1}
                            </span>
                            <h4 className="font-bold text-sm">{scene.name}</h4>
                          </div>
                          {scene.description && (
                            <p className="text-xs text-gray-500 leading-relaxed">
                              {scene.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Props */}
                <section id="sv-props" className="space-y-4">
                  <h3 className="text-base font-bold">道具设定 ({script.props.length})</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {script.props.map((prop) => (
                      <div
                        key={prop.id}
                        className="bg-white dark:bg-gray-900 px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-800 flex items-center justify-between"
                      >
                        <span className="text-sm font-medium">{prop.name}</span>
                        <span className={`text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wider ${
                          prop.type === '关键道具' ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                        }`}>
                          {prop.type}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Shots */}
                <section id="sv-shots" className="space-y-4">
                  <h3 className="text-base font-bold">分镜详情 ({script.shots.length})</h3>
                  <div className="space-y-4">
                    {script.shots.map((shot) => (
                      <ShotCard key={shot.id} shot={shot} />
                    ))}
                  </div>
                </section>
              </div>
            </main>

            {/* Right sidebar nav */}
            <aside className="w-[180px] shrink-0 border-l border-gray-200 dark:border-gray-800 overflow-y-auto p-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">目录</h3>
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => scrollToSection(section.id)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg transition-all ${
                      activeSection === section.id
                        ? 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400'
                        : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700'
                    }`}
                  >
                    <span>{section.label}</span>
                    {section.count !== undefined && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        activeSection === section.id ? 'bg-purple-100 dark:bg-purple-900/30' : 'bg-gray-100 dark:bg-gray-800'
                      }`}>
                        {section.count}
                      </span>
                    )}
                  </button>
                ))}
              </nav>
            </aside>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
