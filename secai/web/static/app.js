// SecAI Production-Grade Workspace (Linear / Raycast / Claude Architecture)
import React, { useEffect, useRef, useState, useMemo } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);
const TOKEN = window.SECAI_TOKEN;

function api(path, opts = {}) {
  return fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", "X-SecAI-Token": TOKEN, ...(opts.headers || {}) },
  });
}

// --- Icons (Handcrafted crisp SVG icons mirroring Lucide React) ---
const Icon = {
  Terminal: () => html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>`,
  Plus: () => html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`,
  MessageSquare: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`,
  Brain: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z"></path><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z"></path></svg>`,
  BookOpen: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>`,
  ShieldCheck: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>`,
  Trash: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`,
  Copy: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`,
  Check: () => html`<svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
  ArrowUp: () => html`<svg class="w-4 h-4 stroke-[2.5]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>`,
  ChevronDown: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"></polyline></svg>`,
  Search: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`,
  Mic: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`,
  Paperclip: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>`,
  Sidebar: () => html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line></svg>`,
};

// --- Secure Markdown Renderer with Copyable Code Blocks ---
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const HIDDEN = /```(?:save-note|update-note|delete-note|export-note|web-search|intel-lookup|secops-action|remember|forget)\s*\n[\s\S]*?(?:```|$)/gi;

function inline(s) {
  return s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function parseBlocks(src) {
  const text = src.replace(HIDDEN, "").trim();
  const blocks = [];
  const lines = text.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("```")) {
      const lang = line.slice(3).trim() || "bash";
      const buf = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        buf.push(lines[i++]);
      }
      i++;
      blocks.push({ type: "code", lang, code: buf.join("\n") });
      continue;
    }

    if (line.trim().startsWith("|")) {
      const buf = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        buf.push(lines[i].trim());
        i++;
      }
      blocks.push({ type: "table", raw: buf });
      continue;
    }

    if (/^\s*[-*] /.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*] /.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*] /, ""));
        i++;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      blocks.push({ type: "heading", level: h[1].length, text: h[2] });
      i++;
      continue;
    }

    if (line.trim() && line.trim() !== "---") {
      blocks.push({ type: "paragraph", text: line });
    }
    i++;
  }
  return blocks;
}

function CodeBlock({ lang, code }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return html`
    <div class="my-3 rounded-lg border border-zinc-800 bg-[#0d0d10] overflow-hidden text-xs">
      <div class="flex items-center justify-between px-3.5 py-1.5 border-b border-zinc-800/80 bg-zinc-900/60 font-mono text-[11px] text-zinc-400">
        <span class="lowercase text-zinc-500 font-medium">${lang}</span>
        <button onClick=${copy} class="flex items-center gap-1.5 hover:text-zinc-200 transition-colors">
          ${copied ? html`<${Icon.Check} /> <span class="text-emerald-400 font-sans">Kopyalandı</span>` : html`<${Icon.Copy} /> <span class="font-sans">Kopyala</span>`}
        </button>
      </div>
      <div class="p-3.5 overflow-x-auto font-mono text-zinc-300 leading-relaxed selection:bg-zinc-800">
        <pre><code>${code}</code></pre>
      </div>
    </div>`;
}

function MarkdownRenderer({ content }) {
  const blocks = useMemo(() => parseBlocks(content), [content]);

  return html`
    <div class="markdown-body">
      ${blocks.map((b, i) => {
        if (b.type === "code") {
          return html`<${CodeBlock} key=${i} lang=${b.lang} code=${b.code} />`;
        }
        if (b.type === "heading") {
          const Tag = `h${b.level}`;
          return html`<${Tag} key=${i} dangerouslySetInnerHTML=${{ __html: inline(esc(b.text)) }} />`;
        }
        if (b.type === "paragraph") {
          return html`<p key=${i} dangerouslySetInnerHTML=${{ __html: inline(esc(b.text)) }} />`;
        }
        if (b.type === "list") {
          return html`
            <ul key=${i}>
              ${b.items.map((it, idx) => html`<li key=${idx} dangerouslySetInnerHTML=${{ __html: inline(esc(it)) }} />`)}
            </ul>`;
        }
        if (b.type === "table") {
          const rows = b.raw.filter((r) => !/^\|[\s:\-|]+\|$/.test(r)).map((r) => r.split("|").slice(1, -1).map((c) => c.trim()));
          if (!rows.length) return null;
          const [head, ...body] = rows;
          return html`
            <div key=${i} class="overflow-x-auto my-3 rounded-md border border-zinc-800">
              <table>
                <thead>
                  <tr>${head.map((c, idx) => html`<th key=${idx} dangerouslySetInnerHTML=${{ __html: inline(esc(c)) }} />`)}</tr>
                </thead>
                <tbody>
                  ${body.map((r, rIdx) => html`
                    <tr key=${rIdx}>
                      ${r.map((c, cIdx) => html`<td key=${cIdx} dangerouslySetInnerHTML=${{ __html: inline(esc(c)) }} />`)}
                    </tr>`)}
                </tbody>
              </table>
            </div>`;
        }
        return null;
      })}
    </div>`;
}

// --- Main Chat Experience ---
function ChatView({ activeSession, setActiveSession, sessions, setSessions }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const textareaRef = useRef(null);
  const bottomRef = useRef(null);

  const loadHistory = (id) => {
    api(`/api/history?session=${id}`).then((r) => r.json()).then(setMessages).catch(() => {});
  };

  useEffect(() => {
    if (activeSession) loadHistory(activeSession);
  }, [activeSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  // Dynamic textarea auto-grow
  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = async (textToSend) => {
    const text = (textToSend || input).trim();
    if (!text || busy) return;

    if (text === "/clear") {
      await api("/api/clear", { method: "POST", body: JSON.stringify({ session: activeSession }) });
      setMessages([]);
      setInput("");
      return;
    }

    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setBusy(true);

    setMessages((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "" }]);

    try {
      const res = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, session: activeSession }),
      });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let acc = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        acc += dec.decode(value, { stream: true });
        setMessages((prev) => [...prev.slice(0, -1), { role: "assistant", content: acc }]);
      }
      // Refresh session list title
      api("/api/sessions").then((r) => r.json()).then(setSessions);
    } catch {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content: "**Hata:** Servis bağlantısı koptu veya zaman aşımına uğradı." },
      ]);
    }
    setBusy(false);
  };

  const emptyPrompts = [
    { label: "Açık TCP/UDP portlarını denetle", cmd: "Sistemimdeki açık portları ve bağdaştırıcıları analiz et" },
    { label: "CIS Linux güvenlik puanını hesapla", cmd: "Güvenlik sıkılaştırma (CIS hardening) skorumu çıkar" },
    { label: "Son systemd hata loglarını incele", cmd: "Son sistem hatalarını ve ssh yetkilendirme loglarını göster" },
  ];

  return html`
    <div class="flex-1 flex flex-col h-full bg-[#09090b] relative">
      <!-- Chat Flow Messages -->
      <div class="flex-1 overflow-y-auto px-4 md:px-6 py-6">
        <div class="max-w-3xl mx-auto space-y-6">
          ${messages.length === 0 &&
          html`
            <div class="py-20 text-center select-none">
              <div class="inline-flex items-center justify-center w-10 h-10 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300 mb-4 shadow-sm">
                <${Icon.Terminal} />
              </div>
              <h2 class="text-base font-medium text-zinc-200 tracking-tight">SecAI Operasyon Çalışma Alanı</h2>
              <p class="text-xs text-zinc-500 mt-1 max-w-sm mx-auto leading-relaxed">
                Yerel sistem telemetrisi, tehdit istihbaratı ve Linux sıkılaştırma asistanı.
              </p>
              <div class="mt-8 flex flex-wrap gap-2 justify-center max-w-xl mx-auto">
                ${emptyPrompts.map(
                  (p, i) => html`
                    <button
                      key=${i}
                      onClick=${() => handleSubmit(p.cmd)}
                      class="text-xs px-3.5 py-2 rounded-md bg-zinc-900/90 border border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-850 hover:text-zinc-100 transition-all text-left flex items-center gap-2 group shadow-sm"
                    >
                      <span>${p.label}</span>
                      <span class="text-zinc-600 group-hover:text-zinc-400">→</span>
                    </button>`
                )}
              </div>
            </div>`}

          ${messages.map((m, idx) => {
            const isUser = m.role === "user";
            return html`
              <div key=${idx} class="group flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}">
                ${!isUser &&
                html`
                  <div class="w-7 h-7 rounded-md bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-300 flex-shrink-0 mt-0.5 shadow-sm">
                    <span class="font-mono text-[11px] font-semibold">S</span>
                  </div>`}

                <div class="max-w-[85%] md:max-w-[80%] ${isUser ? 'bg-zinc-900 border border-zinc-800 text-zinc-100 px-4 py-2.5 rounded-lg shadow-sm font-sans text-[13.5px]' : 'flex-1 text-zinc-200 pt-0.5'}">
                  ${isUser
                    ? html`<div class="whitespace-pre-wrap leading-relaxed">${m.content}</div>`
                    : html`<${MarkdownRenderer} content=${m.content || "..."} />`}
                </div>

                ${isUser &&
                html`
                  <div class="w-7 h-7 rounded-md bg-zinc-850 border border-zinc-800 flex items-center justify-center text-zinc-400 flex-shrink-0 mt-0.5 text-[11px] font-mono">
                    U
                  </div>`}
              </div>`;
          })}

          <div ref=${bottomRef} class="h-2" />
        </div>
      </div>

      <!-- Input Box (Floating Minimal Linear Style) -->
      <div class="p-4 md:p-6 bg-gradient-to-t from-[#09090b] via-[#09090b]/95 to-transparent">
        <div class="max-w-3xl mx-auto">
          <div class="relative bg-zinc-900/90 border border-zinc-800 rounded-xl shadow-xl focus-within:border-zinc-600 focus-within:ring-1 focus-within:ring-zinc-600 transition-all">
            <textarea
              ref=${textareaRef}
              rows="1"
              value=${input}
              onInput=${handleInputChange}
              onKeyDown=${handleKeyDown}
              placeholder="Bir komut veya soru girin (örn. 'açık portları özetle')..."
              class="w-full bg-transparent text-[13.5px] text-zinc-100 placeholder-zinc-500 px-4 pt-3.5 pb-2 outline-none resize-none min-h-[44px] max-h-[180px] font-sans leading-relaxed"
            />
            
            <div class="flex items-center justify-between px-3.5 pb-2.5 pt-1 border-t border-zinc-850/60 text-zinc-500 text-xs">
              <div class="flex items-center gap-1">
                <button title="Dosya ekle (@)" class="p-1.5 hover:text-zinc-300 hover:bg-zinc-800/60 rounded transition-colors">
                  <${Icon.Paperclip} />
                </button>
                <button title="Canlı Web Araması" class="p-1.5 hover:text-zinc-300 hover:bg-zinc-800/60 rounded transition-colors">
                  <${Icon.Search} />
                </button>
                <button title="Sesli komut (/v)" class="p-1.5 hover:text-zinc-300 hover:bg-zinc-800/60 rounded transition-colors">
                  <${Icon.Mic} />
                </button>
              </div>

              <div class="flex items-center gap-2.5">
                <span class="text-[11px] text-zinc-600 hidden sm:inline-block">Gönder: <kbd class="px-1.5 py-0.5 bg-zinc-850 border border-zinc-800 rounded text-[10px] text-zinc-400 font-mono">Enter</kbd></span>
                <button
                  onClick=${() => handleSubmit()}
                  disabled=${busy || !input.trim()}
                  class="w-7 h-7 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 disabled:bg-zinc-800 disabled:text-zinc-600 flex items-center justify-center transition-all cursor-pointer disabled:cursor-not-allowed"
                >
                  <${Icon.ArrowUp} />
                </button>
              </div>
            </div>
          </div>
          <div class="text-center mt-2">
            <span class="text-[11px] text-zinc-600 tracking-tight">SecAI v0.7.0 · Komut çalıştırmadan önce terminalde doğrulama isteyiniz.</span>
          </div>
        </div>
      </div>
    </div>`;
}

// --- Memory & Profile Workspace ---
function MemoryView() {
  const [memories, setMemories] = useState([]);
  const load = () => api("/api/memories").then((r) => r.json()).then(setMemories);
  useEffect(() => { load(); }, []);

  const del = async (key) => {
    await api("/api/memories/delete", { method: "POST", body: JSON.stringify({ key }) });
    load();
  };

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="border-b border-zinc-800 pb-4">
          <h2 class="text-base font-semibold text-zinc-100">Kalıcı Bellek & Profil Bilgileri</h2>
          <p class="text-xs text-zinc-500 mt-1">Sohbetler arasında bağlam sağlayan ChatGPT Memory benzeri doğrulanmış bilgiler.</p>
        </div>

        ${memories.length === 0 && html`<div class="py-12 text-center text-xs text-zinc-600">Henüz hafızaya alınmış bir profil detayı bulunmuyor.</div>`}

        <div class="divide-y divide-zinc-850 border border-zinc-800 rounded-lg bg-zinc-900/40 overflow-hidden">
          ${memories.map((m) => html`
            <div key=${m.id} class="p-3.5 flex items-center justify-between hover:bg-zinc-850/40 transition-colors text-xs">
              <div>
                <span class="font-mono text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700/60 text-[11px]">${m.key}</span>
                <p class="text-zinc-200 mt-1 font-medium">${m.fact}</p>
                <span class="text-[10px] text-zinc-600">${m.created_at}</span>
              </div>
              <button onClick=${() => del(m.key)} class="text-zinc-500 hover:text-red-400 p-1.5 rounded transition-colors" title="Bellekten Kaldır">
                <${Icon.Trash} />
              </button>
            </div>`)}
        </div>
      </div>
    </div>`;
}

// --- Casebook & Notes View ---
function NotesView() {
  const [notes, setNotes] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api("/api/notes").then((r) => r.json()).then(setNotes);
  }, []);

  if (selected) {
    return html`
      <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
        <div class="max-w-3xl mx-auto space-y-4">
          <button onClick=${() => setSelected(null)} class="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1.5 py-1">
            ← Notlara Dön
          </button>
          <div class="border-b border-zinc-800 pb-3">
            <span class="text-xs font-mono text-zinc-500 uppercase tracking-wider">#${selected.id} · ${selected.category}</span>
            <h1 class="text-lg font-semibold text-zinc-100 mt-1">${selected.title}</h1>
            <span class="text-xs text-zinc-600">${selected.created_at} · ${selected.tags || "etiketsiz"}</span>
          </div>
          <div class="pt-2">
            <${MarkdownRenderer} content=${selected.content} />
          </div>
        </div>
      </div>`;
  }

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="border-b border-zinc-800 pb-4">
          <h2 class="text-base font-semibold text-zinc-100">Vaka & Güvenlik Defteri</h2>
          <p class="text-xs text-zinc-500 mt-1">Sistem denetimleri, zafiyet raporları ve kalıcı inceleme notları.</p>
        </div>

        ${notes.length === 0 && html`<div class="py-12 text-center text-xs text-zinc-600">Henüz kayıtlı rapor veya not bulunmuyor.</div>`}

        <div class="divide-y divide-zinc-850 border border-zinc-800 rounded-lg bg-zinc-900/40 overflow-hidden">
          ${notes.map((n) => html`
            <div key=${n.id} onClick=${() => api(`/api/notes/${n.id}`).then((r) => r.json()).then(setSelected)} class="p-3.5 flex items-center justify-between hover:bg-zinc-850/40 transition-colors text-xs cursor-pointer">
              <div>
                <div class="flex items-center gap-2">
                  <span class="text-zinc-500 font-mono text-[11px]">#${n.id}</span>
                  <span class="text-zinc-200 font-medium hover:underline">${n.title}</span>
                </div>
                <span class="text-[10px] text-zinc-600 mt-0.5 block">${n.created_at}</span>
              </div>
              <span class="text-[11px] font-mono text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700/60">${n.category}</span>
            </div>`)}
        </div>
      </div>
    </div>`;
}

// --- Hardening Scorer View ---
function ScoreView() {
  const [data, setData] = useState(null);
  useEffect(() => {
    api("/api/score").then((r) => r.json()).then(setData);
  }, []);

  if (!data) return html`<div class="flex-1 flex items-center justify-center text-xs text-zinc-500">Denetim puanı hesaplanıyor...</div>`;

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="border border-zinc-800 rounded-xl p-5 bg-zinc-900/50 flex items-center justify-between">
          <div>
            <span class="text-xs font-mono text-zinc-500 uppercase tracking-wider block">CIS Benchmark Linux Skoru</span>
            <div class="text-3xl font-bold font-mono text-zinc-100 mt-1">${data.score} <span class="text-sm font-normal text-zinc-500">/ ${data.max_score}</span></div>
          </div>
          <div class="text-right">
            <span class="text-xs font-mono px-2.5 py-1 rounded border border-zinc-700/60 bg-zinc-800 text-zinc-300 font-medium">${data.grade}</span>
          </div>
        </div>

        <div class="divide-y divide-zinc-850 border border-zinc-800 rounded-lg bg-zinc-900/40 overflow-hidden text-xs">
          ${data.checks.map((c, i) => {
            const isPass = c.status === "PASS";
            const isWarn = c.status === "WARN";
            const badgeColor = isPass ? "text-emerald-400 border-emerald-900/60 bg-emerald-950/20" : isWarn ? "text-amber-400 border-amber-900/60 bg-amber-950/20" : "text-red-400 border-red-900/60 bg-red-950/20";
            return html`
              <div key=${i} class="p-3.5 hover:bg-zinc-850/30 transition-colors">
                <div class="flex items-center justify-between mb-1">
                  <span class="font-medium text-zinc-200">${c.name}</span>
                  <span class="font-mono text-[10px] px-1.5 py-0.5 rounded border ${badgeColor}">${c.status} (${c.points})</span>
                </div>
                <div class="text-zinc-500 text-[11px]">Değer: <span class="font-mono text-zinc-400">${c.current}</span></div>
                ${!isPass && html`<div class="text-[11px] text-zinc-400 mt-1.5 pt-1.5 border-t border-zinc-850 font-mono text-zinc-300">Düzeltme: <code>${c.remediation}</code></div>`}
              </div>`;
          })}
        </div>
      </div>
    </div>`;
}

// --- Main App Root ---
function App() {
  const [tab, setTab] = useState("chat");
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState("web");
  const [status, setStatus] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    api("/api/status").then((r) => r.json()).then(setStatus).catch(() => {});
    api("/api/sessions").then((r) => r.json()).then((d) => {
      setSessions(d);
      if (d.length > 0) setActiveSession(d[0].id);
    }).catch(() => {});
  }, []);

  const handleNewChat = async () => {
    const id = `chat_${Date.now().toString(36)}`;
    await api("/api/sessions/new", { method: "POST", body: JSON.stringify({ id, title: "Yeni Sohbet" }) });
    setActiveSession(id);
    api("/api/sessions").then((r) => r.json()).then(setSessions);
    setTab("chat");
  };

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    await api("/api/sessions/delete", { method: "POST", body: JSON.stringify({ id }) });
    const updated = await api("/api/sessions").then((r) => r.json());
    setSessions(updated);
    if (activeSession === id && updated.length > 0) setActiveSession(updated[0].id);
  };

  return html`
    <div class="flex h-screen w-screen overflow-hidden bg-[#08080a] text-zinc-100 font-sans">
      <!-- Collapsible Minimal Sidebar -->
      <aside class="${sidebarOpen ? 'w-64' : 'w-0'} flex flex-col bg-[#0c0c0e] border-r border-zinc-850 transition-all duration-200 overflow-hidden flex-shrink-0 z-20">
        <div class="h-12 border-b border-zinc-850 flex items-center justify-between px-3.5">
          <div class="flex items-center gap-2 font-mono text-xs font-semibold text-zinc-300 tracking-tight">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>secai</span>
          </div>
          <button onClick=${() => setSidebarOpen(false)} class="p-1 text-zinc-500 hover:text-zinc-300 rounded hover:bg-zinc-800 transition-colors">
            <${Icon.Sidebar} />
          </button>
        </div>

        <div class="p-3">
          <button onClick=${handleNewChat} class="w-full h-8 px-2.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-850 text-xs font-medium text-zinc-200 flex items-center justify-between transition-all group">
            <span class="flex items-center gap-1.5"><${Icon.Plus} /> <span>Yeni Sohbet</span></span>
            <kbd class="text-[10px] text-zinc-500 group-hover:text-zinc-400 font-mono">⌘K</kbd>
          </button>
        </div>

        <!-- Navigation Tabs -->
        <div class="px-3 pb-2 space-y-0.5">
          ${[
            { id: "chat", label: "Sohbet", icon: Icon.MessageSquare },
            { id: "memory", label: "Kalıcı Bellek", icon: Icon.Brain },
            { id: "notes", label: "Vaka Defteri", icon: Icon.BookOpen },
            { id: "score", label: "CIS Güvenlik Skoru", icon: Icon.ShieldCheck },
          ].map((t) => html`
            <button
              key=${t.id}
              onClick=${() => setTab(t.id)}
              class="w-full h-7 px-2.5 rounded text-xs flex items-center gap-2 transition-colors ${tab === t.id ? 'bg-zinc-800/80 text-zinc-100 font-medium' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'}"
            >
              <${t.icon} />
              <span>${t.label}</span>
            </button>`)}
        </div>

        <!-- Grouped Chat Sessions (Linear List) -->
        <div class="flex-1 overflow-y-auto px-3 py-2 space-y-0.5 border-t border-zinc-850/80">
          <div class="text-[10px] font-mono uppercase tracking-wider text-zinc-600 px-2 py-1">Geçmiş Sohbetler</div>
          ${sessions.map((s) => html`
            <div
              key=${s.id}
              onClick=${() => { setActiveSession(s.id); setTab("chat"); }}
              class="group h-7 px-2.5 rounded text-xs flex items-center justify-between cursor-pointer transition-colors ${activeSession === s.id && tab === 'chat' ? 'bg-zinc-850 text-zinc-100 font-medium' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'}"
            >
              <span class="truncate flex-1 pr-1 font-sans">${s.title}</span>
              ${s.id !== "web" && html`
                <button
                  onClick=${(e) => handleDeleteSession(e, s.id)}
                  class="opacity-0 group-hover:opacity-100 p-0.5 text-zinc-500 hover:text-red-400 rounded transition-opacity"
                  title="Sil"
                >
                  <${Icon.Trash} />
                </button>`}
            </div>`)}
        </div>

        <!-- User / Hardware Pill Footer -->
        <div class="h-12 border-t border-zinc-850 p-3 flex items-center justify-between text-xs text-zinc-400 font-mono">
          <div class="flex items-center gap-2 truncate">
            <span class="w-5 h-5 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] text-zinc-300">K</span>
            <span class="truncate text-[11px]">Kayra Divrik</span>
          </div>
          <span class="text-[10px] text-zinc-600">RTX 4050</span>
        </div>
      </aside>

      <!-- Center Main Workspace Container -->
      <div class="flex-1 flex flex-col h-full overflow-hidden bg-[#09090b]">
        <!-- Global Header Bar -->
        <header class="h-12 border-b border-zinc-850 bg-[#09090b] flex items-center justify-between px-4 flex-shrink-0 z-10">
          <div class="flex items-center gap-2.5">
            ${!sidebarOpen && html`
              <button onClick=${() => setSidebarOpen(true)} class="p-1 text-zinc-400 hover:text-zinc-200 rounded hover:bg-zinc-800 transition-colors">
                <${Icon.Sidebar} />
              </button>`}
            <span class="text-xs font-medium text-zinc-300 font-sans">
              ${tab === "chat" ? (sessions.find((s) => s.id === activeSession)?.title || "Sohbet") : tab === "memory" ? "Bellek Yönetimi" : tab === "notes" ? "Vaka Defteri" : "Güvenlik Skoru"}
            </span>
          </div>

          <div class="flex items-center gap-2">
            <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-400">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>${status ? status.model : "yerel"}</span>
            </div>
          </div>
        </header>

        <!-- Dynamic View Router -->
        <div class="flex-1 flex overflow-hidden">
          ${tab === "chat" && html`<${ChatView} activeSession=${activeSession} setActiveSession=${setActiveSession} sessions=${sessions} setSessions=${setSessions} />`}
          ${tab === "memory" && html`<${MemoryView} />`}
          ${tab === "notes" && html`<${NotesView} />`}
          ${tab === "score" && html`<${ScoreView} />`}
        </div>
      </div>
    </div>`;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
