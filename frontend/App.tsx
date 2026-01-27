
import React, { useState } from 'react';
import { Sparkles, Send, Copy, Check, GitCompare, ShieldCheck } from 'lucide-react';

const DEFAULT_INSTRUCTIONS =
  '请对这段文案进行仿写：保持原有结构与节奏，表达更自然，避免抄袭，输出完整可用的新版本。';

const DEFAULT_SPECS_JSON = `{
  "product_name": "无糖气泡水",
  "category": "饮料/气泡水",
  "target_audience": "吃辣/重口味人群、控糖人群、想喝爽口饮料的人",
  "core_benefit": "0糖0脂，气泡足，解辣解腻",
  "proof_points": ["配料表干净：水+赤藓糖醇+果汁（按你真实 specs 修改）"],
  "offer": "一箱49.9，活动再减10（按你真实 specs 修改）",
  "cta_url": ""
}`;

type GenerateResponse = {
  success?: boolean;
  final_copy?: string | null;
  draft_copy?: string | null;
  error?: string | null;
  detail?: string | null;
  iteration_count?: number;
  preprocess_result?: any;
  verification_result?: any;
  qc_report?: any;
  skeleton_v2?: any;
  entity_mapping?: any;
  writing_meta?: any;
  proofread_result?: any;
};

const App: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [specsText, setSpecsText] = useState(DEFAULT_SPECS_JSON);
  const [cleanRoom, setCleanRoom] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const [v1Text, setV1Text] = useState('');
  const [v2Text, setV2Text] = useState('');
  const [v1Raw, setV1Raw] = useState<GenerateResponse | null>(null);
  const [v2Raw, setV2Raw] = useState<GenerateResponse | null>(null);

  const [copiedV1, setCopiedV1] = useState(false);
  const [copiedV2, setCopiedV2] = useState(false);

  const parseSpecs = (): { ok: true; value: any | null } | { ok: false; error: string } => {
    try {
      const raw = specsText.trim();
      if (!raw) return { ok: true, value: null }; // empty => v2 imitate-mode
      const v = JSON.parse(raw);
      if (!v || typeof v !== 'object') return { ok: false, error: 'Specs 必须是 JSON object' };
      return { ok: true, value: v };
    } catch (e: any) {
      return { ok: false, error: `Specs JSON 解析失败：${String(e?.message || e)}` };
    }
  };

  const requestGenerate = async (payload: any): Promise<GenerateResponse> => {
    const resp = await fetch('/api/v1/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = (await resp.json().catch(() => ({}))) as GenerateResponse;
    if (!resp.ok) {
      return { ...data, error: (data && (data.detail || data.error)) ? (data.detail || data.error) : 'Request failed.' };
    }
    return data;
  };

  const prettyJson = (v: any) => {
    try {
      return JSON.stringify(v, null, 2);
    } catch {
      return String(v);
    }
  };

  const handleCompare = async () => {
    if (!inputText.trim()) return;

    setIsGenerating(true);
    setV1Text('Generating v1...');
    setV2Text('Generating v2...');
    setV1Raw(null);
    setV2Raw(null);

    try {
      const specs = parseSpecs();
      if (!specs.ok) {
        const r1 = await requestGenerate({
          user_input: inputText,
          user_instructions: DEFAULT_INSTRUCTIONS,
          pipeline_version: 'v1',
        });
        setV1Raw(r1);
        setV1Text(r1.final_copy || r1.draft_copy || r1.error || 'No result returned.');

        const errText = (specs as { ok: false; error: string }).error;
        setV2Raw({ error: errText });
        setV2Text(errText);
        return;
      }

      const [r1, r2] = await Promise.all([
        requestGenerate({
          user_input: inputText,
          user_instructions: DEFAULT_INSTRUCTIONS,
          pipeline_version: 'v1',
        }),
        requestGenerate({
          user_input: inputText,
          user_instructions: DEFAULT_INSTRUCTIONS,
          pipeline_version: 'v2',
          clean_room: cleanRoom,
          ...(specs.value ? { new_product_specs: specs.value } : {}),
        }),
      ]);

      setV1Raw(r1);
      setV2Raw(r2);
      setV1Text(r1.final_copy || r1.draft_copy || r1.error || 'No result returned.');
      setV2Text(r2.final_copy || r2.draft_copy || r2.error || 'No result returned.');
    } catch (error) {
      console.error('Error generating content:', error);
      setV1Text('An error occurred while generating v1. Please try again.');
      setV2Text('An error occurred while generating v2. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async (text: string, which: 'v1' | 'v2') => {
    try {
      // 尝试使用现代 Clipboard API
      await navigator.clipboard.writeText(text);
      if (which === 'v1') setCopiedV1(true);
      else setCopiedV2(true);
      setTimeout(() => {
        if (which === 'v1') setCopiedV1(false);
        else setCopiedV2(false);
      }, 2000);
    } catch (err) {
      // 备用方案：使用传统的 execCommand 方法
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        if (which === 'v1') setCopiedV1(true);
        else setCopiedV2(true);
        setTimeout(() => {
          if (which === 'v1') setCopiedV1(false);
          else setCopiedV2(false);
        }, 2000);
      } catch (e) {
        console.error('Failed to copy:', e);
        alert('复制失败，请手动复制文本');
      }
      document.body.removeChild(textArea);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center p-4 md:p-8 min-h-screen bg-[#F0EEE9]">
      <header className="mb-12 text-center">
        <h1 className="text-3xl md:text-4xl font-light tracking-tight text-stone-700 flex items-center justify-center gap-3">
          <Sparkles className="text-stone-400" size={32} />
          Copywriting <span className="font-semibold italic">Imitator</span>
        </h1>
        <p className="mt-2 text-stone-500 font-medium">文案仿写小助手</p>
      </header>

      <main className="w-full max-w-7xl flex flex-col lg:flex-row gap-8 lg:gap-12 items-stretch">
        {/* Left Panel: Input */}
        <section className="flex-1 lg:flex-[0.9] flex flex-col gap-4">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-sm font-bold uppercase tracking-widest text-stone-400">原始文案</h2>
            <span className="text-xs text-stone-400 font-mono">{inputText.length} chars</span>
          </div>
          
          <div className="embedded-container p-6 flex flex-col h-[460px]">
            <textarea
              className="embedded-textarea p-4 rounded-xl text-stone-700 bg-stone-50/50 placeholder-stone-400 resize-none leading-relaxed h-[240px]"
              placeholder="Paste the original content here..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
            />

            <div className="mt-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-xs text-stone-600">
                <input
                  id="cleanRoom"
                  type="checkbox"
                  checked={cleanRoom}
                  onChange={(e) => setCleanRoom(e.target.checked)}
                />
                <label htmlFor="cleanRoom">Clean Room（v2）</label>
              </div>
              <span className="text-xs text-stone-400">输出侧对比 v1 vs v2</span>
            </div>

            <textarea
              className="embedded-textarea mt-3 p-4 rounded-xl text-stone-700 bg-stone-50/50 placeholder-stone-400 resize-none leading-relaxed h-[120px] font-mono text-xs"
              placeholder="v2: new_product_specs JSON（可选：留空=同品类/同商品仿写；填写=跨品类/换商品迁移）"
              value={specsText}
              onChange={(e) => setSpecsText(e.target.value)}
            />

            <button
              onClick={handleCompare}
              disabled={isGenerating || !inputText.trim()}
              className={`mt-6 py-3 px-6 rounded-full flex items-center justify-center gap-2 font-semibold transition-all shadow-lg active:shadow-inner ${
                isGenerating || !inputText.trim()
                  ? 'bg-stone-300 text-stone-500 cursor-not-allowed'
                  : 'bg-stone-800 text-stone-100 hover:bg-stone-900 hover:-translate-y-0.5'
              }`}
            >
              {isGenerating ? (
                <div className="animate-spin h-5 w-5 border-2 border-stone-100 border-t-transparent rounded-full" />
              ) : (
                <>
                  <GitCompare size={18} />
                  <span>Compare v1 vs v2</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* Right Panel: Output */}
        <section className="flex-1 lg:flex-[1.1] flex flex-col gap-4">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-sm font-bold uppercase tracking-widest text-stone-400">结果对比</h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* v1 */}
            <div className="embedded-container p-6 flex flex-col h-[620px]">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-stone-700 flex items-center gap-2">
                  <Send size={16} className="text-stone-500" />
                  v1（Ten-move）
                </div>
                {v1Text && !isGenerating && (
                  <button
                    onClick={() => handleCopy(v1Text, 'v1')}
                    className="text-xs text-stone-500 hover:text-stone-800 flex items-center gap-1 transition-colors"
                  >
                    {copiedV1 ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
                    {copiedV1 ? 'Copied' : 'Copy'}
                  </button>
                )}
              </div>
              <div className="embedded-textarea flex-1 p-4 rounded-xl text-stone-800 bg-stone-100/30 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {v1Text || <span className="text-stone-400 italic">v1 result will appear here...</span>}
              </div>
            </div>

            {/* v2 */}
            <div className="embedded-container p-6 flex flex-col h-[620px]">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-stone-700 flex items-center gap-2">
                  <ShieldCheck size={16} className="text-stone-500" />
                  v2（Skeleton v2 + QC）
                </div>
                {v2Text && !isGenerating && (
                  <button
                    onClick={() => handleCopy(v2Text, 'v2')}
                    className="text-xs text-stone-500 hover:text-stone-800 flex items-center gap-1 transition-colors"
                  >
                    {copiedV2 ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
                    {copiedV2 ? 'Copied' : 'Copy'}
                  </button>
                )}
              </div>

              {/* QC summary */}
              {v2Raw?.qc_report && (
                <div className="mb-3 text-xs text-stone-600 bg-stone-50/60 rounded-xl p-3 border border-stone-200/50">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">QC</span>
                    <span className={v2Raw.qc_report.is_passed ? 'text-green-700' : 'text-rose-700'}>
                      {v2Raw.qc_report.is_passed ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                  {Array.isArray(v2Raw.qc_report.issues) && v2Raw.qc_report.issues.length > 0 && (
                    <div className="mt-2 whitespace-pre-wrap">
                      {v2Raw.qc_report.issues.slice(0, 6).map((x: any, i: number) => (
                        <div key={i}>- {String(x)}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* skeleton quick view */}
              {v2Raw?.skeleton_v2?.move_sequence && Array.isArray(v2Raw.skeleton_v2.move_sequence) && (
                <div className="mb-3 text-xs text-stone-600 bg-stone-50/60 rounded-xl p-3 border border-stone-200/50">
                  <div className="font-semibold mb-1">Skeleton v2（moves）</div>
                  <div className="grid grid-cols-1 gap-1">
                    {v2Raw.skeleton_v2.move_sequence.slice(0, 8).map((m: any) => (
                      <div key={String(m.move_id)}>
                        <span className="font-mono text-stone-700">#{m.move_id}</span>{' '}
                        <span className="text-stone-700">{String(m.primary_intent || '')}</span>{' '}
                        <span className="text-stone-500">/ {String(m.micro_rhetoric?.tag || '')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="embedded-textarea flex-1 p-4 rounded-xl text-stone-800 bg-stone-100/30 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {v2Text || <span className="text-stone-400 italic">v2 result will appear here...</span>}
              </div>
            </div>
          </div>

          {/* v2 execution trace */}
          {v2Raw && (
            <div className="embedded-container p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-stone-700">v2 Trace（节点输出）</div>
                <div className="text-xs text-stone-500 font-mono">
                  iter={String(v2Raw.iteration_count ?? '')}
                </div>
              </div>

              <div className="space-y-3">
                <details className="bg-stone-50/60 rounded-xl p-4 border border-stone-200/50">
                  <summary className="cursor-pointer text-sm font-semibold text-stone-700">
                    Node1: v2_preprocess（抽取 source_entities / sentences / mode）
                  </summary>
                  <pre className="mt-3 text-xs text-stone-700 overflow-auto whitespace-pre-wrap">
                    {prettyJson(v2Raw.preprocess_result)}
                  </pre>
                </details>

                <details className="bg-stone-50/60 rounded-xl p-4 border border-stone-200/50">
                  <summary className="cursor-pointer text-sm font-semibold text-stone-700">
                    Node2: v2_analyst + v2_normalizer（Skeleton v2）
                  </summary>
                  <pre className="mt-3 text-xs text-stone-700 overflow-auto whitespace-pre-wrap">
                    {prettyJson(v2Raw.skeleton_v2)}
                  </pre>
                </details>

                <details className="bg-stone-50/60 rounded-xl p-4 border border-stone-200/50">
                  <summary className="cursor-pointer text-sm font-semibold text-stone-700">
                    Node3: v2_entity_mapper（实体槽位映射）
                  </summary>
                  <pre className="mt-3 text-xs text-stone-700 overflow-auto whitespace-pre-wrap">
                    {prettyJson(v2Raw.entity_mapping)}
                  </pre>
                </details>

                <details className="bg-stone-50/60 rounded-xl p-4 border border-stone-200/50">
                  <summary className="cursor-pointer text-sm font-semibold text-stone-700">
                    Node4: v2_creator（按 move 生成 + rendered_by_move）
                  </summary>
                  <pre className="mt-3 text-xs text-stone-700 overflow-auto whitespace-pre-wrap">
                    {prettyJson({
                      draft_copy: v2Raw.draft_copy,
                      rendered_by_move: v2Raw.writing_meta?.rendered_by_move,
                      writing_meta: v2Raw.writing_meta,
                    })}
                  </pre>
                </details>

                <details className="bg-stone-50/60 rounded-xl p-4 border border-stone-200/50">
                  <summary className="cursor-pointer text-sm font-semibold text-stone-700">
                    Node5: v2_qc（规则质检）
                  </summary>
                  <pre className="mt-3 text-xs text-stone-700 overflow-auto whitespace-pre-wrap">
                    {prettyJson(v2Raw.qc_report)}
                  </pre>
                </details>

                <details className="bg-stone-50/60 rounded-xl p-4 border border-stone-200/50">
                  <summary className="cursor-pointer text-sm font-semibold text-stone-700">
                    Node6: proofread（评测/润色）
                  </summary>
                  <pre className="mt-3 text-xs text-stone-700 overflow-auto whitespace-pre-wrap">
                    {prettyJson(v2Raw.proofread_result)}
                  </pre>
                </details>
              </div>
            </div>
          )}
        </section>
      </main>

    </div>
  );
};

export default App;
