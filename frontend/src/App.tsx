/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  Plus,
  Library,
  MessageSquare,
  Image as ImageIcon,
  FileText,
  PanelLeftClose,
  HelpCircle,
  Sparkles,
  Crown,
  Smartphone,
  ChevronDown,
  LayoutGrid,
  Keyboard,
  ArrowRight,
  ExternalLink,
  CheckCircle2,
  Clock,
  Palette,
  Settings2,
  ChevronLeft,
  ChevronRight,
  Send,
  X,
  Lightbulb,
  Clapperboard,
  Users,
  MapPin,
  Package,
  Loader2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { sendChat, submitConfig, streamSSE, type ChatResponse, type SSEEvent } from './services/api';
import ScriptView from './components/ScriptView';
import type { ScriptData } from './components/ScriptView';
import { parseScriptMarkdown } from './utils/parseScript';

type MessageType = 'text' | 'tool-call' | 'action-card' | 'config-form' | 'user' | 'storyboard-card' | 'script-card';

interface ToolStep {
  label: string;
  status: 'completed' | 'loading' | 'pending';
  detail?: string;
}

// ── 节点展示映射：将后端节点名聚合为用户友好的步骤 ──
const NODE_DISPLAY_MAP: Record<string, string> = {
  intent_analysis:   '设置意图和更新配置参数',
  breakdown:         '进行剧本生成',
  analysis_report:   '进行剧本生成',
  reverse_engineer:  '进行剧本生成',
  move_plan:         '进行剧本生成',
  writing:           '进行剧本生成',
  verify:            '进行剧本生成',
  v2_preprocess:     '进行剧本生成',
  v2_analyst:        '进行剧本生成',
  v2_normalizer:     '进行剧本生成',
  v2_entity_mapper:  '进行剧本生成',
  v2_creator:        '进行剧本生成',
  proofread:         '剧本审核与润色',
  v2_qc:             '剧本审核与润色',
};

// 每个展示分组的"终结节点"——只有该节点 node_end 时才标记步骤完成
const GROUP_TERMINAL_NODES: Record<string, Set<string>> = {
  '设置意图和更新配置参数': new Set(['intent_analysis']),
  '进行剧本生成':         new Set(['verify', 'v2_creator']),
  '剧本审核与润色':       new Set(['proofread', 'v2_qc']),
};

interface ConfigOption {
  label: string;
  value: string;
}

interface ConfigSection {
  id: string;
  label: string;
  options: ConfigOption[];
}

interface Message {
  id: string;
  type: MessageType;
  content?: string;
  sender: 'ai' | 'user';
  timestamp: string;
  toolSteps?: ToolStep[];
  configData?: {
    threadId: string;
    title: string;
    sections: ConfigSection[];
    defaults: Record<string, string>;
  };
  cardData?: {
    title: string;
    description: string;
    duration?: string;
    style?: string;
    type?: string;
    actions: { label: string; primary?: boolean }[];
    icon?: React.ReactNode;
    stats?: { label: string; value: string; icon: React.ReactNode }[];
  };
}

function nowTimestamp(): string {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function renderScriptContent(content: string) {
  const lines = content.split('\n');
  return lines.map((line, idx) => {
    const trimmed = line.trim();

    // Skip code fences
    if (trimmed.startsWith('```')) {
      return null;
    }

    // 剧本概览
    if (trimmed.startsWith('## 剧本概览')) {
      return <h3 key={idx} className="text-lg font-bold mt-4 mb-2">剧本概览</h3>;
    }
    
    // 分镜设计
    if (trimmed.startsWith('## 分镜设计')) {
      return <h3 key={idx} className="text-lg font-bold mt-4 mb-2">分镜设计</h3>;
    }
    
    // 视觉风格
    if (trimmed.startsWith('## 视觉风格')) {
      return <h3 key={idx} className="text-lg font-bold mt-4 mb-2">视觉风格</h3>;
    }
    
    // 分镜项 - 匹配 - **[名称]** - 内容
    const match = trimmed.match(/^-\s*\*\*(.+?)\*\*\s*-\s*(.+)$/);
    if (match) {
      return (
        <div key={idx} className="ml-4 my-1">
          <span className="font-semibold">{match[1]}</span>
          <span className="text-gray-600"> - {match[2]}</span>
        </div>
      );
    }
    
    // 普通项 - 匹配 - 内容
    if (trimmed.startsWith('- ')) {
      return <div key={idx} className="ml-4 my-1 text-gray-700">{trimmed.substring(2)}</div>;
    }
    
    // 空行
    if (!trimmed) {
      return <br key={idx} />;
    }
    
    return <div key={idx} className="my-1 text-gray-700">{line}</div>;
  });
}

export default function App() {
  const [inputText, setInputText] = useState('');
  const [isChatMode, setIsChatMode] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [formSelections, setFormSelections] = useState<Record<string, Record<string, string>>>({});
  const [submittedForms, setSubmittedForms] = useState<Set<string>>(new Set());
  const [collapsedForms, setCollapsedForms] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [currentUserInput, setCurrentUserInput] = useState('');
  const [isScriptOpen, setIsScriptOpen] = useState(false);
  const [scriptData, setScriptData] = useState<ScriptData | undefined>(undefined);
  const [extractedTitle, setExtractedTitle] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isChatMode) {
      scrollToBottom();
    }
  }, [messages, isChatMode]);

  const handleOptionSelect = (msgId: string, sectionId: string, value: string) => {
    setFormSelections(prev => ({
      ...prev,
      [msgId]: {
        ...(prev[msgId] || {}),
        [sectionId]: value,
      }
    }));
  };

  const toggleFormCollapse = (msgId: string) => {
    setCollapsedForms(prev => {
      const newSet = new Set(prev);
      if (newSet.has(msgId)) {
        newSet.delete(msgId);
      } else {
        newSet.add(msgId);
      }
      return newSet;
    });
  };

  const getSelectedValue = (msgId: string, sectionId: string, defaultValue: string): string => {
    return formSelections[msgId]?.[sectionId] ?? defaultValue;
  };

  const handleConfigSubmit = async (msgId: string, configData: NonNullable<Message['configData']>) => {
    if (submittedForms.has(msgId)) return;

    // Lock the form
    setSubmittedForms(prev => new Set(prev).add(msgId));

    // Build selections from formSelections (fall back to defaults)
    const selections: Record<string, string> = {};
    for (const section of configData.sections) {
      selections[section.id] = getSelectedValue(msgId, section.id, configData.defaults[section.id] || '');
    }

    // Insert a "confirmed config" user message
    const confirmMsg: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: '我已确认配置',
      sender: 'user',
      timestamp: nowTimestamp(),
    };
    setMessages(prev => [...prev, confirmMsg]);

    // Insert a tool-call message that will update as SSE streams in
    const toolMsgId = (Date.now() + 1).toString();
    const toolMsg: Message = {
      id: toolMsgId,
      type: 'tool-call',
      sender: 'ai',
      timestamp: nowTimestamp(),
      toolSteps: [],
    };
    setMessages(prev => [...prev, toolMsg]);

    try {
      const response = await submitConfig(configData.threadId, currentUserInput, selections);

      const steps: ToolStep[] = [];
      let capturedTitle = '';
      let finalContent = '';

      const updateToolSteps = () => {
        setMessages(prev =>
          prev.map(m =>
            m.id === toolMsgId ? { ...m, toolSteps: [...steps] } : m
          )
        );
      };

      streamSSE(
        response,
        (event: SSEEvent) => {
          if (event.type === 'node_start') {
            const nodeName = event.node || '';
            const displayLabel = NODE_DISPLAY_MAP[nodeName];
            // simple_chat 及未映射的节点不展示步骤
            if (!displayLabel) return;

            const existing = steps.find(s => s.label === displayLabel);
            if (!existing) {
              steps.push({ label: displayLabel, status: 'loading' });
            } else if (existing.status === 'completed') {
              // 该分组已标记完成但又有新节点进入（如迭代重跑）
              existing.status = 'loading';
            }
            updateToolSteps();
          } else if (event.type === 'node_end') {
            const nodeName = event.node || '';
            const displayLabel = NODE_DISPLAY_MAP[nodeName];

            // Capture extracted_topic from intent_result（保留原有逻辑）
            if (nodeName === 'intent_analysis' && event.output) {
              const intentResult = (event.output as Record<string, unknown>).intent_result as Record<string, unknown> | undefined;
              if (intentResult?.extracted_topic) {
                capturedTitle = String(intentResult.extracted_topic);
                setExtractedTitle(capturedTitle);
              }
            }

            if (!displayLabel) return;

            // 只在该分组的终结节点完成时才标记步骤 completed
            const terminals = GROUP_TERMINAL_NODES[displayLabel];
            if (terminals?.has(nodeName)) {
              const idx = steps.findIndex(s => s.label === displayLabel);
              if (idx !== -1) {
                steps[idx] = { ...steps[idx], status: 'completed' };
              }
            }
            updateToolSteps();
          } else if (event.type === 'token' && event.content) {
            finalContent += event.content;
            setMessages(prev => {
              const lastMsg = prev[prev.length - 1];
              if (lastMsg && lastMsg.type === 'text' && lastMsg.id.startsWith('stream-')) {
                return prev.map(m =>
                  m.id === lastMsg.id
                    ? { ...m, content: (m.content || '') + event.content }
                    : m
                );
              }
              return [
                ...prev,
                {
                  id: `stream-${Date.now()}`,
                  type: 'text' as MessageType,
                  content: event.content || '',
                  sender: 'ai' as const,
                  timestamp: nowTimestamp(),
                },
              ];
            });
          } else if (event.type === 'done' && event.content) {
            // done 事件包含最终内容（可能是全量或增量）
            // 如果之前已有 token 流式内容，done 的 content 就是全量，不要重复追加
            if (!finalContent) {
              finalContent = event.content;
              setMessages(prev => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg && lastMsg.type === 'text' && lastMsg.id.startsWith('stream-')) {
                  return prev.map(m =>
                    m.id === lastMsg.id
                      ? { ...m, content: event.content }
                      : m
                  );
                }
                return [
                  ...prev,
                  {
                    id: `stream-${Date.now()}`,
                    type: 'text' as MessageType,
                    content: event.content || '',
                    sender: 'ai' as const,
                    timestamp: nowTimestamp(),
                  },
                ];
              });
            } else {
              // Already have token content, use done content as final version
              finalContent = event.content;
            }
          }
        },
        () => {
          for (const step of steps) {
            if (step.status === 'loading') step.status = 'completed';
          }

          // Parse final_copy into structured ScriptData
          if (finalContent) {
            const parsed = parseScriptMarkdown(finalContent, {
              userInput: currentUserInput,
              title: capturedTitle || undefined,
              durationSec: selections.target_duration,
              styleName: selections.style === 'anime' ? '日漫 电影质感'
                : selections.style === 'realistic' ? '写实 电影质感'
                : selections.style === '3d' ? '3D动画 电影质感'
                : selections.style === 'pixel' ? '像素 复古质感'
                : undefined,
            });
            setScriptData(parsed);
          }

          setMessages(prev => {
            const updated = prev.map(m =>
              m.id === toolMsgId
                ? { ...m, toolSteps: [...steps] }
                : m
            );
            // Append script summary card
            const scriptCard: Message = {
              id: `script-card-${Date.now()}`,
              type: 'script-card' as MessageType,
              sender: 'ai' as const,
              timestamp: new Date().toLocaleString('zh-CN', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit',
              }),
            };
            return [...updated, scriptCard];
          });
        },
        (error: string) => {
          setMessages(prev => [
            ...prev,
            {
              id: `error-${Date.now()}`,
              type: 'text' as MessageType,
              content: `生成出错：${error}`,
              sender: 'ai' as const,
              timestamp: nowTimestamp(),
            },
          ]);
        },
      );
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: 'text' as MessageType,
          content: `请求失败：${err instanceof Error ? err.message : String(err)}`,
          sender: 'ai' as const,
          timestamp: nowTimestamp(),
        },
      ]);
    }
  };

  const handleStartCreation = async () => {
    if (!inputText.trim() || isLoading) return;

    const userInput = inputText.trim();
    setCurrentUserInput(userInput);
    setIsChatMode(true);
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: userInput,
      sender: 'user',
      timestamp: nowTimestamp(),
    };

    setMessages([userMsg]);
    setInputText('');

    try {
      const chatResponse: ChatResponse = await sendChat(userInput);

      if (chatResponse.type === 'config_form') {
        const { data } = chatResponse;

        // Build defaults map
        const defaults: Record<string, string> = {};
        for (const field of data.fields) {
          defaults[field.id] = field.default;
        }

        const configMsg: Message = {
          id: (Date.now() + 1).toString(),
          type: 'config-form',
          sender: 'ai',
          timestamp: nowTimestamp(),
          configData: {
            threadId: data.thread_id,
            title: data.title,
            sections: data.fields.map(f => ({
              id: f.id,
              label: f.label,
              options: f.options.map(o => ({ label: o.label, value: o.value })),
            })),
            defaults,
          },
        };
        setMessages(prev => [...prev, configMsg]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: 'text' as MessageType,
          content: `请求失败：${err instanceof Error ? err.message : String(err)}`,
          sender: 'ai' as const,
          timestamp: nowTimestamp(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChatSend = async () => {
    if (!inputText.trim() || isLoading) return;

    const userInput = inputText.trim();
    setCurrentUserInput(userInput);
    setIsLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: userInput,
      sender: 'user',
      timestamp: nowTimestamp(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInputText('');

    try {
      const chatResponse: ChatResponse = await sendChat(userInput);

      if (chatResponse.type === 'config_form') {
        const { data } = chatResponse;

        const defaults: Record<string, string> = {};
        for (const field of data.fields) {
          defaults[field.id] = field.default;
        }

        const configMsg: Message = {
          id: (Date.now() + 1).toString(),
          type: 'config-form',
          sender: 'ai',
          timestamp: nowTimestamp(),
          configData: {
            threadId: data.thread_id,
            title: data.title,
            sections: data.fields.map(f => ({
              id: f.id,
              label: f.label,
              options: f.options.map(o => ({ label: o.label, value: o.value })),
            })),
            defaults,
          },
        };
        setMessages(prev => [...prev, configMsg]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: 'text' as MessageType,
          content: `请求失败：${err instanceof Error ? err.message : String(err)}`,
          sender: 'ai' as const,
          timestamp: nowTimestamp(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className={`w-[280px] flex-shrink-0 border-r border-gray-100 dark:border-gray-900 bg-gray-50/50 dark:bg-gray-900/50 flex flex-col h-full transition-all duration-300 ${isScriptOpen ? 'hidden' : ''}`}>
        <div className="h-16 flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-black dark:bg-white rounded-lg flex items-center justify-center text-white dark:text-black">
              <Sparkles size={20} />
            </div>
          </div>
          <button className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 transition-colors">
            <PanelLeftClose size={20} />
          </button>
        </div>

        <div className="px-4 py-2 space-y-2">
          <button
            onClick={() => { setIsChatMode(false); setMessages([]); setFormSelections({}); setSubmittedForms(new Set()); }}
            className="w-full flex items-center justify-center gap-2 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium py-3 px-4 rounded-xl transition-all shadow-sm border border-gray-200 dark:border-gray-700"
          >
            <Plus size={20} />
            新建
          </button>
          <button className="w-full flex items-center justify-center gap-2 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-white font-medium py-3 px-4 rounded-xl transition-all">
            <Library size={20} />
            资产库
          </button>
        </div>

        <div className="mt-6 flex-1 flex flex-col min-h-0">
          <div className="px-6 flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">历史记录</span>
            <button className="text-xs text-gray-400 hover:text-primary transition-colors">全部</button>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar px-4 pb-4 space-y-1">
          </div>
        </div>

        <div className="p-4 border-t border-gray-100 dark:border-gray-900">
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer transition-colors">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-bold">
              U
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">User Name</p>
              <p className="text-xs text-gray-500 truncate">user@example.com</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`flex-1 flex flex-col relative overflow-hidden bg-white dark:bg-gray-950 ${isScriptOpen ? 'min-w-[360px]' : ''}`}>
        {/* Top Bar */}
        <div className="h-16 flex items-center justify-end px-6 gap-4 z-10 border-b border-gray-50 dark:border-gray-900">
          <div className="flex items-center bg-purple-50 dark:bg-purple-900/20 px-3 py-1.5 rounded-full border border-purple-100 dark:border-purple-800">
            <Crown size={16} className="text-primary mr-1" />
            <span className="text-primary font-medium text-sm cursor-pointer hover:underline">订阅</span>
          </div>
          <button className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 text-gray-500 transition-colors">
            <HelpCircle size={20} />
          </button>
          <button className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 text-gray-500 transition-colors">
            <MessageSquare size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <AnimatePresence mode="wait">
            {!isChatMode ? (
              <motion.div
                key="hero"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full flex flex-col items-center justify-center w-full max-w-5xl mx-auto px-6 pb-20"
              >
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center mb-12"
                >
                  <h1 className="text-4xl md:text-5xl font-semibold mb-4 tracking-tight">
                    你好，你的创作空间已就绪。
                  </h1>
                </motion.div>

                {/* Input Area (Hero) */}
                <div className="w-full max-w-4xl relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/30 to-blue-500/30 rounded-3xl blur opacity-75 group-hover:opacity-100 transition duration-500"></div>
                  <div className="relative w-full bg-white dark:bg-gray-900 rounded-[2rem] border border-primary/20 dark:border-primary/40 shadow-xl flex flex-col min-h-[220px]">
                    <textarea
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleStartCreation();
                        }
                      }}
                      className="w-full flex-1 bg-transparent border-0 rounded-[2rem] p-8 text-lg md:text-xl text-gray-800 dark:text-gray-100 placeholder-gray-300 dark:placeholder-gray-600 focus:ring-0 resize-none outline-none"
                      placeholder="告诉我，你今天想创造一点什么？"
                    />
                    <div className="px-6 pb-6 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <button className="w-10 h-10 rounded-full bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-center text-gray-500 transition-colors" title="Upload file">
                          <Plus size={20} />
                        </button>
                        <button className="h-10 px-4 rounded-full bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 text-gray-700 dark:text-gray-300 transition-colors text-sm font-medium">
                          <LayoutGrid size={18} />
                          模式
                          <ChevronDown size={16} />
                        </button>
                        <button className="w-10 h-10 rounded-full bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-center text-gray-500 transition-colors" title="Templates">
                          <LayoutGrid size={20} />
                        </button>
                        <button className="w-10 h-10 rounded-full bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-center text-gray-500 transition-colors" title="Settings">
                          <Keyboard size={20} />
                        </button>
                      </div>
                      <button
                        onClick={handleStartCreation}
                        disabled={isLoading || !inputText.trim()}
                        className="bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 h-12 px-6 rounded-full flex items-center gap-2 font-medium transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isLoading ? (
                          <Loader2 size={18} className="animate-spin" />
                        ) : (
                          <Sparkles size={18} fill="currentColor" />
                        )}
                        <span>开始创作</span>
                        <ArrowRight size={18} />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Suggested Prompts */}
                <div className="mt-10 w-full max-w-4xl flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-sm text-gray-500">
                  {[
                    { text: '参考爆款视频', icon: 'tiktok' },
                    { text: '漫剧：超绝人物特写', img: 'https://picsum.photos/seed/comic/32/20' },
                    { text: '猫狗偷玩手机一秒装睡' },
                    { text: '香港电影 · 996' },
                    { text: '咖啡产品宣传图' },
                    { text: '《知否知否》MV制作' },
                  ].map((prompt, i) => (
                    <a key={i} href="#" className="flex items-center gap-2 hover:text-primary transition-colors group">
                      {prompt.icon === 'tiktok' && (
                        <span className="w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center group-hover:bg-primary/10">
                          <svg className="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"></path></svg>
                        </span>
                      )}
                      {prompt.img && (
                        <div className="w-8 h-5 rounded overflow-hidden relative">
                          <img src={prompt.img} alt="" className="object-cover w-full h-full opacity-80 group-hover:opacity-100" referrerPolicy="no-referrer" />
                        </div>
                      )}
                      <span>{prompt.text}</span>
                      <ExternalLink size={12} className="opacity-50" />
                    </a>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="chat"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-full max-w-4xl mx-auto px-6 py-10 space-y-8"
              >
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                    {msg.type === 'user' && (
                      <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-4 py-2 max-w-[80%] text-sm">
                        {msg.content}
                      </div>
                    )}

                    {msg.type === 'tool-call' && (
                      <div className="w-full bg-gray-50/50 dark:bg-gray-900/50 border border-gray-100 dark:border-gray-800 rounded-2xl p-6">
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-2 text-sm font-medium">
                            <Settings2 size={18} className="text-green-500" />
                            <span>工具调用</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-gray-400">
                            <span>{msg.toolSteps?.filter(s => s.status === 'completed').length}/{msg.toolSteps?.length} 项</span>
                            <ChevronDown size={14} />
                          </div>
                        </div>
                        <div className="space-y-3">
                          {msg.toolSteps?.map((step, i) => (
                            <div key={i} className="flex items-center justify-between text-sm">
                              <div className="flex items-center gap-3">
                                <div className={`w-1.5 h-1.5 rounded-full ${step.status === 'loading' ? 'bg-blue-500 animate-pulse' : step.status === 'completed' ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
                                <span className="font-medium">{step.label}</span>
                                {step.detail && <span className="text-gray-400">{step.detail}</span>}
                              </div>
                              {step.status === 'completed' && <CheckCircle2 size={16} className="text-green-500" />}
                              {step.status === 'loading' && <Loader2 size={16} className="text-blue-500 animate-spin" />}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {msg.type === 'config-form' && msg.configData && (
                      <div className="w-full bg-gray-50/50 dark:bg-gray-900/50 border border-gray-100 dark:border-gray-800 rounded-2xl p-6">
                        <div className="flex items-center justify-between mb-6">
                          <div className="flex items-center gap-2 font-medium">
                            <FileText size={18} />
                            <span>{msg.configData.title}</span>
                          </div>
                          <button 
                            onClick={() => toggleFormCollapse(msg.id)}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                          >
                            <ChevronDown 
                              size={18} 
                              className={`transition-transform ${collapsedForms.has(msg.id) ? '-rotate-90' : ''}`} 
                            />
                          </button>
                        </div>
                        {!collapsedForms.has(msg.id) && (
                        <div className="space-y-6">
                          {msg.configData.sections.map((section) => {
                            const selectedValue = getSelectedValue(msg.id, section.id, msg.configData!.defaults[section.id] || '');
                            return (
                              <div key={section.id} className="space-y-3">
                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">{section.label}</h4>
                                <div className="flex flex-wrap gap-2">
                                  {section.options.map((opt) => (
                                    <button
                                      key={opt.value}
                                      onClick={() => handleOptionSelect(msg.id, section.id, opt.value)}
                                      disabled={submittedForms.has(msg.id)}
                                      className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
                                        selectedValue === opt.value
                                          ? 'bg-purple-100 dark:bg-purple-900/30 text-primary border border-primary/30'
                                          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                                      } ${submittedForms.has(msg.id) ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
                                    >
                                      {opt.label}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        )}
                        <div className="mt-8 flex justify-end">
                          {submittedForms.has(msg.id) ? (
                            <button className="px-6 py-2 bg-gray-100 dark:bg-gray-800 text-gray-400 rounded-lg text-sm font-medium cursor-not-allowed" disabled>
                              已提交
                            </button>
                          ) : (
                            <button
                              onClick={() => handleConfigSubmit(msg.id, msg.configData!)}
                              className="px-6 py-2 bg-black dark:bg-white text-white dark:text-black rounded-lg text-sm font-medium hover:opacity-90 transition-all"
                            >
                              确认提交
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {msg.type === 'text' && (
                      <div className="w-full bg-white dark:bg-gray-950 rounded-2xl px-1 py-2 max-w-[90%]">
                        <div className="text-sm leading-relaxed">{renderScriptContent(msg.content)}</div>
                      </div>
                    )}

                    {msg.type === 'script-card' && (
                      <div className="w-full bg-gray-50/50 dark:bg-gray-900/50 border border-gray-100 dark:border-gray-800 rounded-2xl overflow-hidden mt-4">
                        <div className="p-6">
                          {/* Header: 剧本 + 时长 */}
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                              <FileText size={18} />
                              <span className="font-medium">剧本</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-gray-400">
                              <Clock size={14} />
                              <span>{scriptData?.totalDuration || '24秒'}</span>
                            </div>
                          </div>

                          {/* 故事标签 + 标题 + 风格 */}
                          <div className="flex items-center gap-2 mb-4">
                            <span className="bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded text-xs font-medium">
                              故事
                            </span>
                            <span className="text-sm text-gray-700 dark:text-gray-300 truncate">{scriptData?.title || currentUserInput || '剧本创作'}</span>
                            <div className="flex-1" />
                            <div className="flex items-center gap-1.5 bg-purple-100 dark:bg-purple-900/30 text-primary px-2 py-1 rounded-full text-xs font-medium">
                              <Palette size={14} />
                              <span>{scriptData?.style || '日漫 电影质感'}</span>
                            </div>
                          </div>

                          {/* 引导提示 */}
                          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800/50 rounded-xl p-4 flex items-start gap-3 relative">
                            <div className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                              <Lightbulb size={20} className="text-primary" />
                            </div>
                            <div className="flex-1">
                              <h4 className="text-sm font-semibold text-primary mb-1">开始创作您的视频</h4>
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                点击"生成分镜"开始下一步，您也可以继续对话完善您的视频分镜
                              </p>
                            </div>
                            <button className="text-gray-400 hover:text-gray-600">
                              <X size={16} />
                            </button>
                          </div>
                        </div>

                        {/* Footer: 时间 + 操作按钮 */}
                        <div className="px-6 py-4 bg-gray-100/50 dark:bg-gray-800/50 flex items-center justify-between">
                          <span className="text-xs text-gray-400">{msg.timestamp}</span>
                          <div className="flex gap-2">
                            <button 
                              onClick={() => setIsScriptOpen(true)}
                              className="px-4 py-1.5 rounded-lg text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-all"
                            >
                              查看剧本
                            </button>
                            <button className="px-4 py-1.5 rounded-lg text-sm font-medium bg-black dark:bg-white text-white dark:text-black hover:opacity-90 transition-all">
                              生成分镜
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {(msg.type === 'action-card' || msg.type === 'storyboard-card') && msg.cardData && (
                      <div className="w-full bg-gray-50/50 dark:bg-gray-900/50 border border-gray-100 dark:border-gray-800 rounded-2xl overflow-hidden mt-4">
                        <div className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                              {msg.cardData.icon}
                              <span className="font-medium">{msg.cardData.title}</span>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-400">
                              <Clock size={14} />
                              <span>{msg.cardData.duration}</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 mb-4">
                            <span className="bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded text-xs font-medium">
                              故事
                            </span>
                            {msg.type === 'action-card' && <span className="text-sm text-gray-500">{msg.cardData.description}</span>}
                            <div className="flex-1" />
                            <div className="flex items-center gap-1.5 bg-purple-100 dark:bg-purple-900/30 text-primary px-2 py-1 rounded-full text-xs font-medium">
                              <Palette size={14} />
                              <span>{msg.cardData.style}</span>
                            </div>
                          </div>

                          {msg.type === 'storyboard-card' && (
                            <div className="mb-6 p-4 bg-white dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-800">
                              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 mb-4 leading-relaxed">
                                {msg.cardData.description}
                              </p>
                              <div className="flex flex-wrap gap-4">
                                {msg.cardData.stats?.map((stat, i) => (
                                  <div key={i} className="flex items-center gap-1.5 text-xs text-gray-500">
                                    {stat.icon}
                                    <span>{stat.value}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800/50 rounded-xl p-4 flex items-start gap-3 relative">
                            <div className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                              <Lightbulb size={20} className="text-primary" />
                            </div>
                            <div className="flex-1">
                              <h4 className="text-sm font-semibold text-primary mb-1">
                                {msg.type === 'storyboard-card' ? '完成您的视频创作' : '开始创作您的视频'}
                              </h4>
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                {msg.type === 'storyboard-card'
                                  ? '您可以点击"生成视频"直接生成，或点击"手动编辑分镜"编辑后生成视频'
                                  : '点击"生成分镜"开始下一步，您也可以继续对话完善您的视频分镜'}
                              </p>
                            </div>
                            <button className="text-gray-400 hover:text-gray-600">
                              <X size={16} />
                            </button>
                          </div>
                        </div>
                        <div className="px-6 py-4 bg-gray-100/50 dark:bg-gray-800/50 flex items-center justify-between">
                          <span className="text-xs text-gray-400">{msg.timestamp}</span>
                          <div className="flex gap-2">
                            {msg.cardData.actions.map((action, i) => (
                              <button
                                key={i}
                                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                                  action.primary
                                    ? 'bg-black dark:bg-white text-white dark:text-black hover:opacity-90'
                                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                                }`}
                              >
                                {action.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Bottom Input Area (Chat Mode) */}
        <AnimatePresence>
          {isChatMode && (
            <motion.div
              initial={{ y: 100 }}
              animate={{ y: 0 }}
              className="p-6 border-t border-gray-50 dark:border-gray-900 bg-white dark:bg-gray-950"
            >
              <div className="max-w-4xl mx-auto">
                <div className="relative bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-2xl shadow-sm">
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleChatSend();
                      }
                    }}
                    className="w-full bg-transparent border-0 rounded-2xl p-4 pr-20 text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400 focus:ring-0 resize-none outline-none min-h-[60px]"
                    placeholder="与综合助手对话，支持多种能力..."
                  />
                  <div className="px-4 pb-3 flex items-center justify-between">
                    <div className={`flex items-center gap-2 ${isScriptOpen ? 'hidden' : ''}`}>
                      <button className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 transition-colors">
                        <Plus size={18} />
                      </button>
                      <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs font-medium transition-colors">
                        <LayoutGrid size={14} />
                        <span>自动</span>
                      </button>
                      <div className="h-4 w-px bg-gray-200 dark:bg-gray-800 mx-1" />
                      <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs font-medium transition-colors">
                        <Sparkles size={14} />
                        <span>自动模式</span>
                      </button>
                      <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-400 text-xs font-medium transition-colors">
                        <Users size={14} />
                        <span>参与创作</span>
                      </button>
                    </div>
                    <div className="flex items-center gap-4 ml-auto">
                      <span className={`text-[10px] text-gray-400 ${isScriptOpen ? 'hidden' : ''}`}>视频生成按 1 秒钟 1 积分扣除</span>
                      <button
                        disabled={!inputText.trim() || isLoading}
                        onClick={handleChatSend}
                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                          inputText.trim() && !isLoading
                            ? 'bg-black dark:bg-white text-white dark:text-black shadow-md'
                            : 'bg-gray-200 dark:bg-gray-800 text-gray-400'
                        }`}
                      >
                        {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                      </button>
                    </div>
                  </div>
                </div>
                <p className="text-center text-[10px] text-gray-400 mt-4">
                  AI 可能会犯错，内容仅供参考，请核查重要信息。
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Collapse toggle on right edge — open script panel */}
        {!isScriptOpen && (
          <button
            onClick={() => setIsScriptOpen(true)}
            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-10 w-7 h-14 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors shadow-md"
          >
            <ChevronLeft size={16} />
          </button>
        )}
      </main>

      {/* Script Detail Drawer */}
      <ScriptView
        isOpen={isScriptOpen}
        onClose={() => setIsScriptOpen(false)}
        scriptData={scriptData}
      />
    </div>
  );
}
