// SecAI Production-Grade Workspace (Linear / Raycast / Claude Architecture)
import React, { useEffect, useRef, useState, useMemo, useCallback } from "https://esm.sh/react@18.3.1";
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

// --- Crisp SVG Icons (Developer-Grade Utilitarian Minimalism) ---
const Icon = {
  Terminal: () => html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>`,
  Plus: () => html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`,
  MessageSquare: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`,
  Brain: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z"></path><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z"></path></svg>`,
  BookOpen: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>`,
  ShieldCheck: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>`,
  Globe: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`,
  Activity: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
  Trash: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`,
  Copy: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`,
  Check: () => html`<svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
  ArrowUp: () => html`<svg class="w-4 h-4 stroke-[2.5]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>`,
  ChevronDown: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"></polyline></svg>`,
  Search: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`,
  Mic: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`,
  MicOff: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="1" y1="1" x2="23" y2="23"></line><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`,
  Volume2: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>`,
  VolumeX: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>`,
  Square: () => html`<svg class="w-3 h-3 fill-current" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"></rect></svg>`,
  Paperclip: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>`,
  Sidebar: () => html`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line></svg>`,
  Refresh: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>`,
  Sparkles: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"></path></svg>`,
  Layers: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>`,
  Bot: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>`,
  Image: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`,
  Edit: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>`,
  Cpu: () => html`<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>`,
};

// --- Audio Player Manager (Edge Neural TTS) ---
let globalAudio = null;

function stopCurrentAudio() {
  if (globalAudio) {
    try {
      globalAudio.pause();
      globalAudio.currentTime = 0;
    } catch (_) {}
    globalAudio = null;
  }
}

// --- Secure Markdown Renderer ---
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const HIDDEN = /```(?:save-note|update-note|delete-note|export-note|web-search|intel-lookup|secops-action|remember|forget)\s*\n[\s\S]*?(?:```|$)/gi;

function inline(s) {
  return s
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<div class="my-3 rounded-lg overflow-hidden border border-zinc-800 bg-zinc-900/60 p-2 max-w-lg mx-auto"><img src="$2" alt="$1" class="rounded max-h-[480px] w-auto object-contain mx-auto shadow-2xl" loading="lazy" /><div class="mt-2 text-center text-xs text-zinc-400 font-mono flex items-center justify-center gap-3"><span>$1</span><a href="$2" download="secai_image" class="text-emerald-400 hover:text-emerald-300 font-sans text-[11px] underline">İndir 📥</a></div></div>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-emerald-400 hover:underline">$1</a>')
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
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

// --- Main Chat Experience with Full Voice & TTS Integration ---
function ChatView({ activeSession, setActiveSession, sessions, setSessions, activeSkill, autoSpeak, setAutoSpeak, onStatusUpdate }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [playingMsgIdx, setPlayingMsgIdx] = useState(null);
  const [ttsLoadingIdx, setTtsLoadingIdx] = useState(null);

  const textareaRef = useRef(null);
  const bottomRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recognitionRef = useRef(null);

  const loadHistory = (id) => {
    api(`/api/history?session=${id}`).then((r) => r.json()).then(setMessages).catch(() => {});
  };

  useEffect(() => {
    if (activeSession) loadHistory(activeSession);
  }, [activeSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  // Read message out loud using Edge Neural TTS
  const speakMessage = async (text, idx) => {
    if (playingMsgIdx === idx) {
      stopCurrentAudio();
      setPlayingMsgIdx(null);
      return;
    }

    stopCurrentAudio();
    setTtsLoadingIdx(idx);

    try {
      const res = await api("/api/tts", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error("TTS Hatasi");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      globalAudio = audio;

      audio.onended = () => {
        setPlayingMsgIdx(null);
        globalAudio = null;
      };
      audio.onerror = () => {
        setPlayingMsgIdx(null);
        globalAudio = null;
      };

      setTtsLoadingIdx(null);
      setPlayingMsgIdx(idx);
      await audio.play();
    } catch {
      setTtsLoadingIdx(null);
      setPlayingMsgIdx(null);
    }
  };

  // Start / Stop Microphone Recording (Web Speech API + MediaRecorder Fallback)
  const toggleRecording = async () => {
    if (recording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      setRecording(false);
      return;
    }

    // Try SpeechRecognition first
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recog = new SpeechRecognition();
        recog.lang = "tr-TR";
        recog.continuous = false;
        recog.interimResults = true;

        recog.onstart = () => setRecording(true);
        recog.onresult = (e) => {
          const transcript = Array.from(e.results)
            .map((r) => r[0].transcript)
            .join("");
          setInput((prev) => (prev ? prev + " " + transcript : transcript));
        };
        recog.onerror = (e) => {
          console.warn("SpeechRec error, falling back to MediaRecorder", e);
          recog.stop();
          fallbackMediaRecorder();
        };
        recog.onend = () => setRecording(false);
        recognitionRef.current = recog;
        recog.start();
        return;
      } catch (_) {}
    }

    fallbackMediaRecorder();
  };

  const fallbackMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Audio = reader.result;
          try {
            const res = await api("/api/stt", {
              method: "POST",
              body: JSON.stringify({ audio: base64Audio, mime_type: "audio/webm" }),
            });
            const data = await res.json();
            if (data.transcript) {
              setInput((prev) => (prev ? prev + " " + data.transcript : data.transcript));
            }
          } catch (err) {
            console.error("STT Hatasi:", err);
          }
        };
      };

      mediaRecorder.start();
      setRecording(true);
    } catch (err) {
      alert("Mikrofona erişilemedi: " + err.message);
      setRecording(false);
    }
  };

  // Textarea Auto-grow
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

    const newIndex = messages.length + 1;
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
      // If Auto-Speak (Sesli Sohbet Modu) is enabled, speak out loud!
      if (autoSpeak && acc.trim()) {
        speakMessage(acc, newIndex);
      }
      api("/api/sessions").then((r) => r.json()).then(setSessions);
      if (onStatusUpdate) onStatusUpdate();
    } catch {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content: "**Hata:** Sunucu bağlantısı kesildi veya model yanıt veremedi." },
      ]);
    }
    setBusy(false);
  };

  const emptyPrompts = [
    { label: "Görsel Oluştur (/image)", cmd: "/image cyberpunk hacker terminal neon matrix dijital sanat" },
    { label: "Beni Tanı & Kimlik Yaz (/infomy)", cmd: "/infomy" },
    { label: "SecOps Ajanını Değiştir (/agent)", cmd: "/agent" },
    { label: "Açık TCP/UDP portlarını denetle", cmd: "Sistemimdeki açık portları ve dinleyen servisleri analiz et" },
    { label: "CIS Linux güvenlik puanını hesapla", cmd: "Sistem güvenlik (CIS hardening) skorumu çıkar" },
    { label: "Sistem baseline sapmalarını kontrol et", cmd: "Son referans noktasına göre sistemde bir sapma veya yeni port var mı?" },
    { label: "Son auth ve systemd loglarını tara", cmd: "Son sistem hatalarını ve ssh yetkilendirme loglarını incele" },
  ];

  return html`
    <div class="flex-1 flex flex-col h-full bg-[#09090b] relative">
      <!-- Chat Flow Messages -->
      <div class="flex-1 overflow-y-auto px-4 md:px-6 py-6">
        <div class="max-w-3xl mx-auto space-y-6">
          ${messages.length === 0 &&
          html`
            <div class="py-16 text-center select-none">
              <div class="inline-flex items-center justify-center w-10 h-10 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300 mb-4 shadow-sm">
                <${Icon.Terminal} />
              </div>
              <h2 class="text-base font-medium text-zinc-200 tracking-tight">SecAI Operasyon Çalışma Alanı</h2>
              <p class="text-xs text-zinc-500 mt-1 max-w-sm mx-auto leading-relaxed">
                Yerel sistem telemetrisi, tehdit istihbaratı, sesli asistan ve Linux sıkılaştırma motoru.
              </p>
              ${activeSkill && html`
                <div class="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950/30 border border-emerald-800/50 text-[11px] font-mono text-emerald-400">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>Aktif Ajan: ${activeSkill}</span>
                </div>
              `}
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
            const isPlaying = playingMsgIdx === idx;
            const isTtsLoading = ttsLoadingIdx === idx;

            return html`
              <div key=${idx} class="group flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}">
                ${!isUser &&
                html`
                  <div class="w-7 h-7 rounded-md bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-300 flex-shrink-0 mt-0.5 shadow-sm">
                    <span class="font-mono text-[11px] font-semibold">S</span>
                  </div>`}

                <div class="max-w-[85%] md:max-w-[80%] ${isUser ? 'bg-zinc-900 border border-zinc-800 text-zinc-100 px-4 py-2.5 rounded-lg shadow-sm font-sans text-[13.5px]' : 'flex-1 text-zinc-200 pt-0.5'}">
                  ${isUser
                    ? html`<div class="whitespace-pre-wrap leading-relaxed">${m.content}</div>`
                    : html`
                      <div>
                        <${MarkdownRenderer} content=${m.content || "..."} />
                        <!-- Assistant Micro Actions Bar: Read Aloud TTS & Copy -->
                        ${m.content && html`
                          <div class="mt-3 flex items-center gap-2 pt-2 border-t border-zinc-850/60 text-zinc-500 text-xs">
                            <button
                              onClick=${() => speakMessage(m.content, idx)}
                              class="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-zinc-800 hover:text-zinc-200 transition-colors ${isPlaying ? 'text-emerald-400 bg-emerald-950/20 border border-emerald-900/40' : ''}"
                              title="${isPlaying ? 'Durdur' : 'Sesli Dinle (Edge Neural TTS)'}"
                            >
                              ${isTtsLoading
                                ? html`<span class="w-3.5 h-3.5 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin"></span>`
                                : isPlaying
                                ? html`
                                  <div class="flex items-center gap-1">
                                    <span class="wave-bar"></span>
                                    <span class="wave-bar"></span>
                                    <span class="wave-bar"></span>
                                    <span class="wave-bar"></span>
                                    <span class="text-[11px] text-emerald-400 font-mono ml-1">Okunuyor</span>
                                    <${Icon.Square} />
                                  </div>`
                                : html`<${Icon.Volume2} /> <span class="text-[11px] font-sans">Dinle</span>`}
                            </button>

                            <button
                              onClick=${() => { navigator.clipboard.writeText(m.content); }}
                              class="flex items-center gap-1 px-2 py-1 rounded hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                              title="Metni Kopyala"
                            >
                              <${Icon.Copy} /> <span class="text-[11px] font-sans">Kopyala</span>
                            </button>
                          </div>
                        `}
                      </div>`}
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

      <!-- Floating Minimal Linear Input Box -->
      <div class="p-4 md:p-6 bg-gradient-to-t from-[#09090b] via-[#09090b]/95 to-transparent">
        <div class="max-w-3xl mx-auto">
          <div class="relative bg-zinc-900/90 border border-zinc-800 rounded-xl shadow-xl focus-within:border-zinc-600 focus-within:ring-1 focus-within:ring-zinc-600 transition-all">
            <textarea
              ref=${textareaRef}
              rows="1"
              value=${input}
              onInput=${handleInputChange}
              onKeyDown=${handleKeyDown}
              placeholder="${recording ? 'Sesiniz dinleniyor, konuşun...' : 'Bir komut veya soru girin (örn. \'açık portları özetle\')...'}"
              class="w-full bg-transparent text-[13.5px] text-zinc-100 placeholder-zinc-500 px-4 pt-3.5 pb-2 outline-none resize-none min-h-[44px] max-h-[180px] font-sans leading-relaxed"
            />

            <!-- Recording live banner -->
            ${recording && html`
              <div class="flex items-center gap-2 px-4 py-1.5 bg-red-950/20 border-t border-red-900/30 text-xs text-red-400">
                <span class="w-2 h-2 rounded-full bg-red-500 mic-recording-pulse"></span>
                <span>Mikrofon dinleniyor... Tamamlamak için mikrofona tekrar tıklayın.</span>
              </div>
            `}

            <div class="flex items-center justify-between px-3.5 pb-2.5 pt-1 border-t border-zinc-850/60 text-zinc-500 text-xs">
              <div class="flex items-center gap-1">
                <!-- Voice Recording Button -->
                <button
                  onClick=${toggleRecording}
                  title="${recording ? 'Kaydı Durdur' : 'Sesli Konuş (Mikrofon STT)'}"
                  class="p-1.5 rounded transition-all ${recording ? 'bg-red-500 text-white mic-recording-pulse' : 'hover:text-zinc-200 hover:bg-zinc-800/80 text-zinc-400'}"
                >
                  ${recording ? html`<${Icon.MicOff} />` : html`<${Icon.Mic} />`}
                </button>

                <!-- Auto-speak Handsfree Toggle Button -->
                <button
                  onClick=${() => setAutoSpeak(!autoSpeak)}
                  title="${autoSpeak ? 'Sesli Sohbet Modu Aktif (Yanıtlar seslendiriliyor)' : 'Sesli Sohbet Modu Kapalı'}"
                  class="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-mono transition-colors ${autoSpeak ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/60' : 'hover:text-zinc-300 hover:bg-zinc-800/60 text-zinc-500'}"
                >
                  <${Icon.Volume2} />
                  <span>${autoSpeak ? "Sesli Mod: Açık" : "Ses"}</span>
                </button>

                <!-- Image Generation Quick Action -->
                <button
                  onClick=${() => {
                    const current = input.trim();
                    if (!current.startsWith('/image')) {
                      setInput('/image ' + current);
                    }
                    textareaRef.current?.focus();
                  }}
                  title="Yapay zeka ile görsel üret (/image)"
                  class="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-mono hover:text-zinc-200 hover:bg-zinc-800/60 text-zinc-400 transition-colors"
                >
                  <${Icon.Image} />
                  <span class="hidden md:inline">Görsel</span>
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
            <span class="text-[11px] text-zinc-600 tracking-tight">SecAI v0.9.0 · AI Image Studio & Çift Yönlü Ses Motoru</span>
          </div>
        </div>
      </div>
    </div>`;
}

// --- Threat Intel (Shodan InternetDB & GeoIP) Workspace ---
function IntelView({ onSendToChat }) {
  const [query, setQuery] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const lookup = async (target) => {
    const q = (target || query).trim();
    if (!q) return;
    setLoading(true);
    setReport(null);
    try {
      const res = await api("/api/intel", {
        method: "POST",
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();
      setReport(data.report || "Sonuç bulunamadı.");
    } catch {
      setReport("İstihbarat servisine bağlanılamadı.");
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") lookup();
  };

  const quickSamples = ["1.1.1.1", "8.8.8.8", "9.9.9.9", "185.199.108.153"];

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="border-b border-zinc-800 pb-4">
          <div class="flex items-center gap-2">
            <${Icon.Globe} />
            <h2 class="text-base font-semibold text-zinc-100">Tehdit İstihbaratı & Shodan Analizi</h2>
          </div>
          <p class="text-xs text-zinc-500 mt-1">
            IP adresleri, log satırları ve alan adları için Shodan InternetDB açık port, zafiyet (CVE) ve GeoIP sorgulaması.
          </p>
        </div>

        <!-- Query Search Bar -->
        <div class="flex gap-2">
          <input
            type="text"
            value=${query}
            onChange=${(e) => setQuery(e.target.value)}
            onKeyDown=${handleKeyDown}
            placeholder="IP adresi veya host girin (örn. 8.8.8.8)..."
            class="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3.5 py-2 text-xs font-mono text-zinc-100 placeholder-zinc-500 outline-none focus:border-zinc-600 transition-colors"
          />
          <button
            onClick=${() => lookup()}
            disabled=${loading || !query.trim()}
            class="px-4 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs disabled:bg-zinc-800 disabled:text-zinc-600 flex items-center gap-1.5 transition-colors"
          >
            ${loading ? html`<span class="w-3.5 h-3.5 border-2 border-zinc-900 border-t-transparent rounded-full animate-spin"></span>` : html`<${Icon.Search} />`}
            <span>Sorgula</span>
          </button>
        </div>

        <div class="flex items-center gap-2 text-xs text-zinc-500">
          <span>Örnekler:</span>
          ${quickSamples.map(
            (s) => html`
              <button
                key=${s}
                onClick=${() => { setQuery(s); lookup(s); }}
                class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 font-mono text-[11px] transition-colors"
              >
                ${s}
              </button>`
          )}
        </div>

        <!-- Intel Result Report -->
        ${report && html`
          <div class="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-4">
            <div class="flex items-center justify-between border-b border-zinc-800 pb-3">
              <span class="text-xs font-mono text-zinc-400 uppercase tracking-wider">İstihbarat Raporu</span>
              <button
                onClick=${() => onSendToChat(`Aşağıdaki tehdit istihbaratı raporunu analiz et ve risk seviyesini değerlendir:\n\n${report}`)}
                class="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-medium transition-colors"
              >
                <${Icon.Sparkles} />
                <span>Asistanla Zafiyet Analizi Yap →</span>
              </button>
            </div>
            <div class="pt-1">
              <${MarkdownRenderer} content=${report} />
            </div>
          </div>
        `}
      </div>
    </div>`;
}

// --- Baseline & Drift Detection Workspace ---
function BaselineView({ onSendToChat }) {
  const [diff, setDiff] = useState(null);
  const [loading, setLoading] = useState(false);
  const [snapshotting, setSnapshotting] = useState(false);

  const loadDiff = async () => {
    setLoading(true);
    try {
      const res = await api("/api/baseline/diff");
      const data = await res.json();
      setDiff(data);
    } catch {
      setDiff(null);
    }
    setLoading(false);
  };

  useEffect(() => { loadDiff(); }, []);

  const takeSnapshot = async () => {
    setSnapshotting(true);
    try {
      await api("/api/baseline/take", {
        method: "POST",
        body: JSON.stringify({ label: `web-${Date.now().toString(36)}` }),
      });
      await loadDiff();
    } catch (e) {
      alert("Snapshot hatası: " + e.message);
    }
    setSnapshotting(false);
  };

  const hasDrift = diff && (
    (diff.ports && (diff.ports.added.length > 0 || diff.ports.removed.length > 0)) ||
    (diff.services && (diff.services.added.length > 0 || diff.services.removed.length > 0)) ||
    (diff.users && (diff.users.added.length > 0 || diff.users.removed.length > 0)) ||
    (diff.crontabs && diff.crontabs.changed)
  );

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div>
            <div class="flex items-center gap-2">
              <${Icon.Activity} />
              <h2 class="text-base font-semibold text-zinc-100">Sistem Baseline & Sapma Tespiti</h2>
            </div>
            <p class="text-xs text-zinc-500 mt-1">
              Referans noktasına kıyasla dinlenen portlar, systemd servisleri ve yetkili hesaplardaki izinsiz sapmalar.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              onClick=${loadDiff}
              class="h-8 px-3 rounded-md bg-zinc-900 border border-zinc-800 hover:bg-zinc-850 text-xs text-zinc-300 flex items-center gap-1.5 transition-colors"
            >
              <${Icon.Refresh} />
              <span>Yenile</span>
            </button>
            <button
              onClick=${takeSnapshot}
              disabled=${snapshotting}
              class="h-8 px-3 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <${Icon.Plus} />
              <span>${snapshotting ? "Alınıyor..." : "Yeni Referans Al"}</span>
            </button>
          </div>
        </div>

        ${!diff ? html`<div class="py-12 text-center text-xs text-zinc-500">Baseline verisi kontrol ediliyor...</div>` : html`
          <div class="space-y-4">
            <!-- Drift Status Card -->
            <div class="p-4 rounded-xl border ${hasDrift ? 'border-amber-900/60 bg-amber-950/10' : 'border-emerald-900/60 bg-emerald-950/10'} flex items-center justify-between">
              <div>
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full ${hasDrift ? 'bg-amber-400' : 'bg-emerald-400'}"></span>
                  <span class="text-xs font-mono uppercase tracking-wider ${hasDrift ? 'text-amber-300' : 'text-emerald-300'} font-semibold">
                    ${hasDrift ? "Sapma Tespit Edildi (Drift Detected)" : "Sistem Temiz: Sapma Yok"}
                  </span>
                </div>
                <p class="text-xs text-zinc-400 mt-1">
                  Son referans: <span class="font-mono text-zinc-300">${diff.baseline_time || "Mevcut Değil"}</span> (${diff.baseline_label || "etiketsiz"})
                </p>
              </div>

              ${hasDrift && html`
                <button
                  onClick=${() => onSendToChat(`Baseline kontrolünde sistemde sapma tespit edildi:\n- Portlar: ${JSON.stringify(diff.ports)}\n- Servisler: ${JSON.stringify(diff.services)}\nBu sapmaları güvenlik açısından incele.`)}
                  class="text-xs px-3 py-1.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-200 hover:bg-amber-500/30 transition-colors flex items-center gap-1 font-medium"
                >
                  <${Icon.Sparkles} />
                  <span>Sapmayı Asistanla Analiz Et</span>
                </button>
              `}
            </div>

            <!-- Ports Diff Section -->
            <div class="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
              <span class="text-xs font-mono uppercase tracking-wider text-zinc-400 font-semibold block">Dinlenen Ağ Portları</span>
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div class="p-3 rounded-lg border border-zinc-855 bg-zinc-900/60">
                  <span class="text-zinc-500 text-[11px] block mb-1">Yeni Açılan Portlar (+)</span>
                  ${diff.ports.added.length === 0
                    ? html`<span class="text-zinc-600 font-mono text-[11px]">Yok</span>`
                    : diff.ports.added.map((p) => html`<span key=${p} class="inline-block mr-1.5 mb-1 px-2 py-0.5 rounded bg-red-950/40 border border-red-800 text-red-300 font-mono text-[11px]">+${p}</span>`)}
                </div>
                <div class="p-3 rounded-lg border border-zinc-855 bg-zinc-900/60">
                  <span class="text-zinc-500 text-[11px] block mb-1">Kapanan Portlar (-)</span>
                  ${diff.ports.removed.length === 0
                    ? html`<span class="text-zinc-600 font-mono text-[11px]">Yok</span>`
                    : diff.ports.removed.map((p) => html`<span key=${p} class="inline-block mr-1.5 mb-1 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono text-[11px]">-${p}</span>`)}
                </div>
              </div>
            </div>

            <!-- Services Diff Section -->
            <div class="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-3">
              <span class="text-xs font-mono uppercase tracking-wider text-zinc-400 font-semibold block">Systemd Servisleri</span>
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div class="p-3 rounded-lg border border-zinc-855 bg-zinc-900/60">
                  <span class="text-zinc-500 text-[11px] block mb-1">Yeni Başlatılan Servisler (+)</span>
                  ${diff.services.added.length === 0
                    ? html`<span class="text-zinc-600 font-mono text-[11px]">Yok</span>`
                    : diff.services.added.map((s) => html`<span key=${s} class="inline-block mr-1.5 mb-1 px-2 py-0.5 rounded bg-amber-950/40 border border-amber-800 text-amber-300 font-mono text-[11px]">+${s}</span>`)}
                </div>
                <div class="p-3 rounded-lg border border-zinc-855 bg-zinc-900/60">
                  <span class="text-zinc-500 text-[11px] block mb-1">Durdurulan Servisler (-)</span>
                  ${diff.services.removed.length === 0
                    ? html`<span class="text-zinc-600 font-mono text-[11px]">Yok</span>`
                    : diff.services.removed.map((s) => html`<span key=${s} class="inline-block mr-1.5 mb-1 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono text-[11px]">-${s}</span>`)}
                </div>
              </div>
            </div>
          </div>
        `}
      </div>
    </div>`;
}

// --- Memory & Profile Workspace ---
function MemoryView() {
  const [memories, setMemories] = useState([]);
  const [profile, setProfile] = useState("");
  const [editingProfile, setEditingProfile] = useState(false);
  const [profileInput, setProfileInput] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    api("/api/memories").then((r) => r.json()).then(setMemories);
    api("/api/profile").then((r) => r.json()).then((d) => {
      setProfile(d.profile || "");
      setProfileInput(d.profile || "");
    });
  };

  useEffect(() => { load(); }, []);

  const saveProfile = async () => {
    if (!profileInput.trim()) return;
    setSaving(true);
    await api("/api/profile", {
      method: "POST",
      body: JSON.stringify({ profile: profileInput.trim() }),
    });
    setSaving(false);
    setEditingProfile(false);
    load();
  };

  const del = async (key) => {
    await api("/api/memories/delete", { method: "POST", body: JSON.stringify({ key }) });
    load();
  };

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="border-b border-zinc-800 pb-4">
          <div class="flex items-center gap-2">
            <${Icon.Brain} />
            <h2 class="text-base font-semibold text-zinc-100">Kalıcı Bellek & Profil Bilgileri (/infomy)</h2>
          </div>
          <p class="text-xs text-zinc-500 mt-1">Sohbetler arasında bağlam sağlayan, AI'ın sizin kim olduğunuzu daima hatırlamasını sağlayan kimlik hafızası.</p>
        </div>

        <!-- /infomy User Identity Card -->
        <div class="rounded-xl border border-emerald-900/60 bg-emerald-950/15 p-4 space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-base">👤</span>
              <span class="text-xs font-mono uppercase tracking-wider text-emerald-400 font-semibold">Kullanıcı Kimlik Tanımı (/infomy)</span>
            </div>
            ${!editingProfile && html`
              <button
                onClick=${() => setEditingProfile(true)}
                class="text-xs px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 text-zinc-300 font-medium transition-colors"
              >
                ${profile ? "Düzenle" : "+ Bilgi Ekle"}
              </button>
            `}
          </div>

          ${editingProfile
            ? html`
              <div class="space-y-2.5 pt-1">
                <textarea
                  rows="3"
                  value=${profileInput}
                  onInput=${(e) => setProfileInput(e.target.value)}
                  placeholder="Kendinizi tanıtın (örn: 'Adım Kayra, siber güvenlik araştırmacısıyım, Arch Linux ve Python kullanıyorum, hedefim OSCP almak')..."
                  class="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs text-zinc-100 outline-none focus:border-emerald-500 transition-colors font-sans leading-relaxed resize-none"
                />
                <div class="flex items-center justify-end gap-2">
                  <button
                    onClick=${() => { setEditingProfile(false); setProfileInput(profile); }}
                    class="px-3 py-1.5 rounded text-xs text-zinc-400 hover:text-zinc-200"
                  >
                    İptal
                  </button>
                  <button
                    onClick=${saveProfile}
                    disabled=${saving || !profileInput.trim()}
                    class="px-3.5 py-1.5 rounded bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium text-xs transition-colors"
                  >
                    ${saving ? "Kaydediliyor..." : "Kaydet"}
                  </button>
                </div>
              </div>`
            : html`
              <div class="text-xs text-zinc-300 leading-relaxed font-sans pt-0.5">
                ${profile
                  ? html`<p class="bg-zinc-900/60 border border-zinc-850 p-3 rounded-lg text-zinc-200">${profile}</p>`
                  : html`<span class="text-zinc-500 italic">Henüz bir profil tanımlanmadı. Chat'e <code>/infomy Adım...</code> yazarak veya buradan ekleyebilirsiniz.</span>`}
              </div>`
          }
        </div>

        <div class="border-t border-zinc-850 pt-2">
          <span class="text-xs font-mono uppercase tracking-wider text-zinc-500 block mb-3">Otomatik Öğrenilen Diğer Bellek Detayları</span>
          ${memories.length === 0 && html`<div class="py-6 text-center text-xs text-zinc-600">Henüz hafızaya alınmış ek bir detay bulunmuyor.</div>`}

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
          <div class="border-b border-zinc-800 pb-3 flex items-start justify-between">
            <div>
              <span class="text-xs font-mono text-zinc-500 uppercase tracking-wider">#${selected.id} · ${selected.category}</span>
              <h1 class="text-lg font-semibold text-zinc-100 mt-1">${selected.title}</h1>
              <span class="text-xs text-zinc-600">${selected.created_at} · ${selected.tags || "etiketsiz"}</span>
            </div>
            <a
              href="/api/notes/${selected.id}/pdf"
              target="_blank"
              download="secai_report_${selected.id}.pdf"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition-colors shadow-sm"
              title="Kurumsal Siber Güvenlik Raporu (PDF)"
            >
              <span>Kurumsal PDF İndir</span>
              <span>📄</span>
            </a>
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
              <div class="flex items-center gap-2">
                <a
                  href="/api/notes/${n.id}/pdf"
                  target="_blank"
                  download="secai_report_${n.id}.pdf"
                  onClick=${(e) => e.stopPropagation()}
                  class="px-2 py-0.5 rounded text-[11px] font-mono text-emerald-400 hover:text-emerald-300 hover:bg-emerald-950/40 border border-emerald-800/40 transition-colors"
                  title="Kurumsal PDF İndir"
                >
                  PDF 📄
                </a>
                <span class="text-[11px] font-mono text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700/60">${n.category}</span>
              </div>
            </div>`)}
        </div>
      </div>
    </div>`;
}

// --- Dedicated Agents (SecOps Ajanları) Hub ---
function AgentsView({ activeSkill, onSelectAgent, onSendToChat }) {
  const agentProfiles = [
    {
      id: null,
      name: "Genel SecOps Ajanı",
      tag: "STANDART",
      desc: "Genel Linux sistem güvenliği, terminal komutları, log okuma ve genel siber asistanlık.",
      focus: "Temel Linux, Bash Komutları, Sistem Analizi",
      icon: "🎯",
    },
    {
      id: "recon",
      name: "Recon Ajanı",
      tag: "AĞ & KEŞİF",
      desc: "Ağ ve port keşfi, servis versiyon tespiti, nmap, ss, ip, dig araçları ve yerel ağ haritalama.",
      focus: "Nmap, Açık Portlar, Ağ Topolojisi, Servis Tespiti",
      icon: "🔍",
    },
    {
      id: "hardening",
      name: "Hardening Ajanı",
      tag: "CIS SIKILAŞTIRMA",
      desc: "CIS Benchmark standartlarına göre Linux sıkılaştırma, SSH, firewall, sysctl çekirdek parametreleri ve yetki kısıtlamaları.",
      focus: "Kernel Parametreleri, UFW/iptables, SSH Güvenliği, SUID",
      icon: "🛡️",
    },
    {
      id: "detection",
      name: "Detection Ajanı",
      tag: "KURAL & TESPİT",
      desc: "Tehdit ve saldırı tespiti, Sigma kuralı yazımı, YARA kuralları, Fail2ban ve brute-force engelleme.",
      focus: "YARA, Sigma, Fail2ban, Log Anomali Tespiti",
      icon: "⚡",
    },
    {
      id: "ctf",
      name: "CTF & PrivEsc Ajanı",
      tag: "OFANSİF ANALİZ",
      desc: "CTF çözümleri, Linux yerel yetki yükseltme (Privilege Escalation), GTFOBins, SUID ve cron zafiyetleri incelemesi.",
      focus: "PrivEsc, GTFOBins, SUID Exploit, Yetki Yükseltme",
      icon: "🚩",
    },
  ];

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-4xl mx-auto space-y-6">
        <div class="border-b border-zinc-800 pb-4">
          <div class="flex items-center gap-2">
            <${Icon.Bot} />
            <h2 class="text-base font-semibold text-zinc-100">SecAI Ajanları (SecOps Agent Hub)</h2>
          </div>
          <p class="text-xs text-zinc-500 mt-1">
            Görevinize uygun uzman siber güvenlik ajanını seçin. Seçtiğiniz ajan tüm promptlara kendi uzmanlık talimatlarıyla yanıt verir.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          ${agentProfiles.map((ag) => {
            const isActive = (!ag.id && !activeSkill) || (ag.id && activeSkill === ag.id);
            return html`
              <div
                key=${ag.name}
                class="rounded-xl border p-5 flex flex-col justify-between transition-all ${isActive ? 'bg-emerald-950/15 border-emerald-800/80 shadow-lg ring-1 ring-emerald-500/20' : 'bg-zinc-900/40 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900/70'}"
              >
                <div>
                  <div class="flex items-center justify-between mb-2.5">
                    <div class="flex items-center gap-2">
                      <span class="text-lg">${ag.icon}</span>
                      <span class="text-sm font-semibold text-zinc-100 font-sans">${ag.name}</span>
                    </div>
                    <span class="text-[10px] font-mono px-2 py-0.5 rounded border ${isActive ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800' : 'bg-zinc-800 text-zinc-400 border-zinc-700'}">
                      ${ag.tag}
                    </span>
                  </div>

                  <p class="text-xs text-zinc-400 leading-relaxed mb-3">
                    ${ag.desc}
                  </p>

                  <div class="pt-2 border-t border-zinc-850/80 text-[11px] text-zinc-500">
                    <span class="font-mono text-zinc-400">Odak:</span> ${ag.focus}
                  </div>
                </div>

                <div class="mt-4 pt-3 flex items-center justify-between border-t border-zinc-850">
                  ${isActive
                    ? html`
                      <span class="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-medium font-mono">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        Aktif Ajan
                      </span>`
                    : html`
                      <button
                        onClick=${() => onSelectAgent(ag.id)}
                        class="text-xs px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 font-medium transition-colors"
                      >
                        Bu Ajanı Seç
                      </button>`}

                  <button
                    onClick=${() => {
                      if (!isActive) onSelectAgent(ag.id);
                      onSendToChat(`Merhaba ${ag.name}, bu alanda bana nasıl yardımcı olabilirsin?`);
                    }}
                    class="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors"
                  >
                    <span>Sohbet Başlat</span>
                    <span>→</span>
                  </button>
                </div>
              </div>`;
          })}
        </div>
      </div>
    </div>`;
}

// --- Hardening Scorer View ---
function ScoreView({ onSendToChat }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    api("/api/score").then((r) => r.json()).then((d) => {
      setData(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (!data) return html`<div class="flex-1 flex items-center justify-center text-xs text-zinc-500">Denetim puanı hesaplanıyor...</div>`;

  return html`
    <div class="flex-1 overflow-y-auto p-6 md:p-8 bg-[#09090b]">
      <div class="max-w-3xl mx-auto space-y-6">
        <div class="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div>
            <h2 class="text-base font-semibold text-zinc-100">CIS Benchmark Linux Güvenlik Skoru</h2>
            <p class="text-xs text-zinc-500 mt-1">Sistem çekirdeği, ağ parametreleri ve yetki kısıtlamaları denetimi.</p>
          </div>
          <button onClick=${load} class="h-8 px-3 rounded-md bg-zinc-900 border border-zinc-800 hover:bg-zinc-850 text-xs text-zinc-300 flex items-center gap-1.5 transition-colors">
            <${Icon.Refresh} />
            <span>${loading ? "Taranıyor..." : "Yeniden Tara"}</span>
          </button>
        </div>

        <div class="border border-zinc-800 rounded-xl p-5 bg-zinc-900/50 flex items-center justify-between">
          <div>
            <span class="text-xs font-mono text-zinc-500 uppercase tracking-wider block">Toplam CIS Skoru</span>
            <div class="text-3xl font-bold font-mono text-zinc-100 mt-1">${data.score} <span class="text-sm font-normal text-zinc-500">/ ${data.max_score}</span></div>
          </div>
          <div class="text-right">
            <span class="text-xs font-mono px-3 py-1.5 rounded border border-zinc-700/60 bg-zinc-800 text-zinc-200 font-medium">${data.grade}</span>
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
                ${!isPass && html`
                  <div class="mt-2 pt-2 border-t border-zinc-850 flex items-center justify-between">
                    <span class="font-mono text-zinc-300 text-[11px]">Çözüm: <code>${c.remediation}</code></span>
                    <button
                      onClick=${() => onSendToChat(`CIS Denetiminde başarısız olan "${c.name}" kuralını düzeltmek için adımları anlat. Önerilen komut: ${c.remediation}`)}
                      class="text-[11px] text-emerald-400 hover:text-emerald-300 font-medium ml-2"
                    >
                      Asistana Sor →
                    </button>
                  </div>
                `}
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
  const [skills, setSkills] = useState([]);
  const [activeSkill, setActiveSkill] = useState(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [skillMenuOpen, setSkillMenuOpen] = useState(false);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [modelsData, setModelsData] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");

  const handleStartRename = (e, s) => {
    if (e) e.stopPropagation();
    setEditingSessionId(s.id);
    setEditingTitle(s.title);
  };

  const handleSaveRename = async (e, id) => {
    if (e) e.stopPropagation();
    const clean = editingTitle.trim();
    if (clean) {
      await api("/api/sessions/rename", {
        method: "POST",
        body: JSON.stringify({ id, title: clean }),
      });
      const updated = await api("/api/sessions").then((r) => r.json());
      setSessions(updated);
    }
    setEditingSessionId(null);
  };

  const loadStatus = () => {
    api("/api/status").then((r) => r.json()).then((s) => {
      setStatus(s);
      setActiveSkill(s.active_skill);
      setAutoSpeak(Boolean(s.tts_enabled));
    }).catch(() => {});
  };

  const loadModels = () => {
    api("/api/models").then((r) => r.json()).then(setModelsData).catch(() => {});
  };

  useEffect(() => {
    loadStatus();
    loadModels();
    api("/api/skills").then((r) => r.json()).then(setSkills).catch(() => {});

    api("/api/sessions").then((r) => r.json()).then((d) => {
      setSessions(d);
      if (d.length > 0) setActiveSession(d[0].id);
    }).catch(() => {});

    const handleOutsideClick = (e) => {
      if (!e.target.closest(".dropdown-container")) {
        setSkillMenuOpen(false);
        setModelMenuOpen(false);
      }
    };
    window.addEventListener("click", handleOutsideClick);
    return () => window.removeEventListener("click", handleOutsideClick);
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

  const switchSkill = async (skillName) => {
    const res = await api("/api/skill/set", { method: "POST", body: JSON.stringify({ name: skillName }) });
    const data = await res.json();
    setActiveSkill(data.active);
    setSkillMenuOpen(false);
    loadStatus();
  };

  const switchModel = async (provider, model) => {
    await api("/api/model/set", { method: "POST", body: JSON.stringify({ provider, model }) });
    setModelMenuOpen(false);
    loadStatus();
    loadModels();
  };

  const handleSendToChat = async (promptText) => {
    setTab("chat");
    setTimeout(async () => {
      await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: promptText, session: activeSession }),
      });
      api("/api/history?session=" + activeSession);
    }, 100);
  };

  return html`
    <div class="flex h-screen w-screen overflow-hidden bg-[#08080a] text-zinc-100 font-sans">
      <!-- Collapsible Minimal Sidebar -->
      <aside class="${sidebarOpen ? 'w-64' : 'w-0'} flex flex-col bg-[#0c0c0e] border-r border-zinc-850 transition-all duration-200 overflow-hidden flex-shrink-0 z-20">
        <div class="h-12 border-b border-zinc-850 flex items-center justify-between px-3.5">
          <div class="flex items-center gap-2 font-mono text-xs font-semibold text-zinc-300 tracking-tight">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>secai</span>
            <span class="text-[10px] text-zinc-500 font-normal">v0.9.0</span>
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
            { id: "chat", label: "Sohbet & Ses", icon: Icon.MessageSquare },
            { id: "agents", label: "Ajanlar (Agents)", icon: Icon.Bot },
            { id: "intel", label: "Tehdit İstihbaratı", icon: Icon.Globe },
            { id: "baseline", label: "Baseline & Sapma", icon: Icon.Activity },
            { id: "score", label: "CIS Güvenlik Skoru", icon: Icon.ShieldCheck },
            { id: "notes", label: "Vaka Defteri", icon: Icon.BookOpen },
            { id: "memory", label: "Kalıcı Bellek", icon: Icon.Brain },
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
          ${sessions.map((s) => {
            const isEditing = editingSessionId === s.id;
            return html`
              <div
                key=${s.id}
                onClick=${() => { if (!isEditing) { setActiveSession(s.id); setTab("chat"); } }}
                class="group h-7 px-2.5 rounded text-xs flex items-center justify-between cursor-pointer transition-colors ${activeSession === s.id && tab === 'chat' ? 'bg-zinc-850 text-zinc-100 font-medium' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'}"
              >
                ${isEditing
                  ? html`
                    <div class="flex items-center gap-1 w-full" onClick=${(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value=${editingTitle}
                        onInput=${(e) => setEditingTitle(e.target.value)}
                        onKeyDown=${(e) => {
                          if (e.key === "Enter") handleSaveRename(e, s.id);
                          if (e.key === "Escape") setEditingSessionId(null);
                        }}
                        autoFocus
                        class="flex-1 h-5 px-1.5 bg-zinc-950 border border-emerald-500 rounded text-[11px] text-zinc-100 focus:outline-none"
                      />
                      <button
                        onClick=${(e) => handleSaveRename(e, s.id)}
                        class="p-0.5 text-emerald-400 hover:text-emerald-300"
                        title="Kaydet"
                      >
                        <${Icon.Check} />
                      </button>
                    </div>`
                  : html`
                    <span
                      class="truncate flex-1 pr-1 font-sans"
                      onDoubleClick=${(e) => handleStartRename(e, s)}
                      title="${s.title} (Çift tıklayarak yeniden adlandır)"
                    >
                      ${s.title}
                    </span>
                    <div class="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                      <button
                        onClick=${(e) => handleStartRename(e, s)}
                        class="p-0.5 text-zinc-500 hover:text-zinc-200 rounded transition-colors"
                        title="Yeniden Adlandır"
                      >
                        <${Icon.Edit} />
                      </button>
                      ${s.id !== "web" && html`
                        <button
                          onClick=${(e) => handleDeleteSession(e, s.id)}
                          class="p-0.5 text-zinc-500 hover:text-red-400 rounded transition-colors"
                          title="Sil"
                        >
                          <${Icon.Trash} />
                        </button>`}
                    </div>`
                }
              </div>`;
          })}
        </div>

        <!-- User / Hardware Pill Footer -->
        <div class="h-12 border-t border-zinc-850 p-3 flex items-center justify-between text-xs text-zinc-400 font-mono">
          <div class="flex items-center gap-2 truncate">
            <span class="w-5 h-5 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] text-zinc-300">${(status?.user || "U")[0].toUpperCase()}</span>
            <span class="truncate text-[11px]">${status?.user || "SecAI Workspace"}</span>
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
            ${tab === "chat" ? html`
              <div class="flex items-center gap-1.5 group/hdr">
                <span class="text-xs font-medium text-zinc-200 font-sans">
                  ${sessions.find((s) => s.id === activeSession)?.title || "Sohbet"}
                </span>
                <button
                  onClick=${(e) => {
                    const currentSess = sessions.find((s) => s.id === activeSession);
                    if (currentSess) handleStartRename(e, currentSess);
                  }}
                  class="opacity-0 group-hover/hdr:opacity-100 p-0.5 text-zinc-500 hover:text-zinc-200 rounded transition-all"
                  title="Sohbet Başlığını Değiştir"
                >
                  <${Icon.Edit} />
                </button>
              </div>
            ` : html`
              <span class="text-xs font-medium text-zinc-300 font-sans">
                ${tab === "agents" ? "SecAI Ajanları" : tab === "intel" ? "Tehdit İstihbaratı" : tab === "baseline" ? "Sistem Baseline & Sapma" : tab === "score" ? "Güvenlik Skoru" : tab === "notes" ? "Vaka Defteri" : "Kalıcı Bellek"}
              </span>
            `}
          </div>

          <div class="flex items-center gap-2">
            <!-- Ajan (Agent / Skill) Selector Dropdown -->
            <div class="relative dropdown-container">
              <button
                onClick=${() => { setSkillMenuOpen(!skillMenuOpen); setModelMenuOpen(false); }}
                class="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-300 hover:border-zinc-700 transition-colors"
                title="Aktif Ajanı Değiştir"
              >
                <${Icon.Bot} />
                <span class="text-emerald-400 font-sans font-medium text-[11px]">Ajan:</span>
                <span class="capitalize">${activeSkill ? activeSkill : "Standart"}</span>
                <${Icon.ChevronDown} />
              </button>

              ${skillMenuOpen && html`
                <div class="absolute right-0 mt-1.5 w-64 rounded-lg bg-zinc-900 border border-zinc-800 shadow-2xl py-1 z-50 text-xs">
                  <div class="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800">SecOps Ajanı Seç</div>
                  <button
                    onClick=${() => switchSkill(null)}
                    class="w-full text-left px-3 py-2 hover:bg-zinc-800 flex items-center justify-between ${!activeSkill ? 'text-emerald-400 font-semibold bg-zinc-850/50' : 'text-zinc-300'}"
                  >
                    <div>
                      <div class="font-medium text-zinc-200">🎯 Genel / Standart Ajan</div>
                      <div class="text-[10px] text-zinc-500">Genel Linux & siber güvenlik danışmanı</div>
                    </div>
                    ${!activeSkill && html`<${Icon.Check} />`}
                  </button>
                  ${skills.map((sk) => html`
                    <button
                      key=${sk.name}
                      onClick=${() => switchSkill(sk.name)}
                      class="w-full text-left px-3 py-2 hover:bg-zinc-800 flex items-center justify-between ${activeSkill === sk.name ? 'text-emerald-400 font-semibold bg-zinc-850/50' : 'text-zinc-300'}"
                    >
                      <div>
                        <div class="font-medium text-zinc-200 capitalize">${sk.name === "recon" ? "🔍 Recon Ajanı" : sk.name === "hardening" ? "🛡️ Hardening Ajanı" : sk.name === "detection" ? "⚡ Detection Ajanı" : "🚩 CTF Ajanı"}</div>
                        <div class="text-[10px] text-zinc-500 truncate max-w-[190px]">${sk.description}</div>
                      </div>
                      ${activeSkill === sk.name && html`<${Icon.Check} />`}
                    </button>
                  `)}
                  <div class="pt-1 border-t border-zinc-800 px-3 py-1">
                    <button onClick=${() => { setSkillMenuOpen(false); setTab("agents"); }} class="text-[11px] text-emerald-400 hover:underline">Tüm Ajan Detaylarını Gör →</button>
                  </div>
                </div>
              `}
            </div>

            <!-- Active LLM Model Selector Dropdown -->
            <div class="relative dropdown-container">
              <button
                onClick=${() => { setModelMenuOpen(!modelMenuOpen); setSkillMenuOpen(false); }}
                class="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-300 hover:border-zinc-700 transition-colors"
                title="Modeli Değiştir"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>${status ? status.model : "yerel"}</span>
                <${Icon.ChevronDown} />
              </button>

              ${modelMenuOpen && html`
                <div class="absolute right-0 mt-1.5 w-60 rounded-lg bg-zinc-900 border border-zinc-800 shadow-2xl py-1 z-50 text-xs">
                  <div class="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-b border-zinc-800">Yerel Ollama Modelleri</div>
                  ${(modelsData?.ollama_models || ["gemma3:4b", "qwen2.5-coder:7b"]).map((m) => html`
                    <button
                      key=${m}
                      onClick=${() => switchModel("ollama", m)}
                      class="w-full text-left px-3 py-2 hover:bg-zinc-800 flex items-center justify-between ${status?.model === m ? 'text-emerald-400 font-semibold' : 'text-zinc-300'}"
                    >
                      <span class="font-mono text-xs">${m}</span>
                      ${status?.model === m && html`<${Icon.Check} />`}
                    </button>
                  `)}

                  <div class="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-zinc-500 border-t border-b border-zinc-800 mt-1">Google Gemini API</div>
                  ${["gemini-2.5-flash", "gemini-3-flash-preview"].map((m) => html`
                    <button
                      key=${m}
                      onClick=${() => switchModel("gemini", m)}
                      class="w-full text-left px-3 py-2 hover:bg-zinc-800 flex items-center justify-between ${status?.model === m ? 'text-emerald-400 font-semibold' : 'text-zinc-300'}"
                    >
                      <span class="font-mono text-xs">${m}</span>
                      ${status?.model === m && html`<${Icon.Check} />`}
                    </button>
                  `)}
                </div>
              `}
            </div>
          </div>
        </header>

        <!-- Dynamic View Router -->
        <div class="flex-1 flex overflow-hidden">
          ${tab === "chat" && html`<${ChatView} activeSession=${activeSession} setActiveSession=${setActiveSession} sessions=${sessions} setSessions=${setSessions} activeSkill=${activeSkill} autoSpeak=${autoSpeak} setAutoSpeak=${setAutoSpeak} onStatusUpdate=${loadStatus} />`}
          ${tab === "agents" && html`<${AgentsView} activeSkill=${activeSkill} onSelectAgent=${switchSkill} onSendToChat=${handleSendToChat} />`}
          ${tab === "intel" && html`<${IntelView} onSendToChat=${handleSendToChat} />`}
          ${tab === "baseline" && html`<${BaselineView} onSendToChat=${handleSendToChat} />`}
          ${tab === "score" && html`<${ScoreView} onSendToChat=${handleSendToChat} />`}
          ${tab === "notes" && html`<${NotesView} />`}
          ${tab === "memory" && html`<${MemoryView} />`}
        </div>
      </div>
    </div>`;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
