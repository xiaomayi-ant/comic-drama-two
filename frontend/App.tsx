
import React, { useState, useCallback } from 'react';
import { Star, Sparkles, Send, Copy, Check } from 'lucide-react';

const DEFAULT_INSTRUCTIONS =
  '请对这段文案进行仿写：保持原有结构与节奏，表达更自然，避免抄袭，输出完整可用的新版本。';

const App: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [rating, setRating] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleRewrite = async () => {
    if (!inputText.trim()) return;

    setIsGenerating(true);
    setRating(0);
    setOutputText('Crafting your masterpiece...');

    try {
      // 调用后端 FastAPI（copywriting-assistant-2）：/api/v1/generate
      const resp = await fetch('/api/v1/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: inputText,
          user_instructions: DEFAULT_INSTRUCTIONS,
        }),
      });

      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setOutputText(
          (data && (data.detail || data.error)) ? (data.detail || data.error) : 'Request failed.'
        );
        return;
      }

      setOutputText(data.final_copy || data.draft_copy || data.error || 'No result returned.');
    } catch (error) {
      console.error('Error generating content:', error);
      setOutputText('An error occurred while generating the copy. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    try {
      // 尝试使用现代 Clipboard API
      await navigator.clipboard.writeText(outputText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // 备用方案：使用传统的 execCommand 方法
      const textArea = document.createElement('textarea');
      textArea.value = outputText;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
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

      <main className="w-full max-w-6xl flex flex-col lg:flex-row gap-8 lg:gap-12 items-stretch">
        {/* Left Panel: Input */}
        <section className="flex-1 flex flex-col gap-4">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-sm font-bold uppercase tracking-widest text-stone-400">原始文案</h2>
            <span className="text-xs text-stone-400 font-mono">{inputText.length} chars</span>
          </div>
          
          <div className="embedded-container p-6 flex flex-col h-[400px]">
            <textarea
              className="embedded-textarea flex-1 p-4 rounded-xl text-stone-700 bg-stone-50/50 placeholder-stone-400 resize-none leading-relaxed"
              placeholder="Paste the original content here..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
            />
            <button
              onClick={handleRewrite}
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
                  <Send size={18} />
                  <span>Generate Imitation</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* Right Panel: Output */}
        <section className="flex-1 flex flex-col gap-4">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-sm font-bold uppercase tracking-widest text-stone-400">仿写结果</h2>
            {outputText && !isGenerating && (
              <button 
                onClick={handleCopy}
                className="text-xs text-stone-500 hover:text-stone-800 flex items-center gap-1 transition-colors"
              >
                {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
                {copied ? 'Copied' : 'Copy Text'}
              </button>
            )}
          </div>

          <div className="embedded-container p-6 flex flex-col h-[400px]">
            <div className="embedded-textarea flex-1 p-4 rounded-xl text-stone-800 bg-stone-100/30 overflow-y-auto whitespace-pre-wrap leading-relaxed relative">
              {outputText || <span className="text-stone-400 italic">The imitation will appear here...</span>}
            </div>

            {/* Rating Functionality */}
            {outputText && !isGenerating && (
              <div className="mt-6 flex flex-col items-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-700">
                <span className="text-xs font-bold uppercase tracking-widest text-stone-400">
                  Rate this version {rating > 0 && `(${rating}/5)`}
                </span>
                <div className="flex gap-2 star-rating">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setRating(star)}
                      className="transition-all duration-200 transform hover:scale-125 cursor-pointer"
                    >
                      <Star 
                        size={26} 
                        className={rating >= star ? 'text-amber-500' : 'text-stone-300'}
                        fill={rating >= star ? 'currentColor' : 'none'}
                        strokeWidth={2}
                      />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>

    </div>
  );
};

export default App;
