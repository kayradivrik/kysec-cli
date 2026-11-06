// SecAI — ChatGPT/Gemini Tarzi Coklu Oturum & Kalici Bellek React Arayuzu
import React, { useEffect, useRef, useState } from "https://esm.sh/react@18.3.1";
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

// --- Guvenli Minimal Markdown ---
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const HIDDEN = /```(?:save-note|update-note|delete-note|export-note|web-search|intel-lookup|secops-action|remember|forget)\s*\n[\s\S]*?(?:```|$)/gi;

function inline(s) {
  return s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
}

function renderMarkdown(src) {
  const text = esc(src.replace(HIDDEN, "").trim());
  const out = [];
  const lines = text.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("```")) {
      const buf = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) buf.push(lines[i++]);
      i++;
      out.push(`<pre><code>${buf.join("\n")}</code></pre>`);
      continue;
    }

    if (line.trim().startsWith("|")) {
      const buf = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        if (!/^\|[\s:\-|]+\|$/.test(lines[i].trim())) buf.push(lines[i].trim());
        i++;
      }
      out.push(`<pre class="table">${buf.map(inline).join("\n")}</pre>`);
      continue;
    }

    if (/^\s*[-*] /.test(line)) {
      const buf = [];
      while (i < lines.length && /^\s*[-*] /.test(lines[i])) {
        buf.push(`<li>${inline(lines[i].replace(/^\s*[-*] /, ""))}</li>`);
        i++;
      }
      out.push(`<ul>${buf.join("")}</ul>`);
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`);
    else if (line.trim() && line.trim() !== "---") out.push(`<p>${inline(line)}</p>`);
    i++;
  }
  return out.join("");
}

const Md = ({ text }) => html`<div class="md" dangerouslySetInnerHTML=${{ __html: renderMarkdown(text) }} />`;

// --- ChatGPT Tarzi Coklu Oturumlu Sohbet ---
function Chat() {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState("web");
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  const loadSessions = () => {
    api("/api/sessions")
      .then((r) => r.json())
      .then((data) => {
        setSessions(data);
        if (data.length > 0 && !data.some((s) => s.id === currentSession)) {
          setCurrentSession(data[0].id);
        }
      })
      .catch(() => {});
  };

  const loadHistory = (sessId) => {
    api(`/api/history?session=${sessId}`)
      .then((r) => r.json())
      .then(setMsgs)
      .catch(() => {});
  };

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (currentSession) {
      loadHistory(currentSession);
    }
  }, [currentSession]);

  useEffect(() => endRef.current?.scrollIntoView({ block: "end" }), [msgs]);

  const newChat = async () => {
    const newId = `chat_${Date.now().toString(36)}`;
    await api("/api/sessions/new", {
      method: "POST",
      body: JSON.stringify({ id: newId, title: "Yeni Sohbet" }),
    });
    setCurrentSession(newId);
    setMsgs([]);
    loadSessions();
  };

  const deleteSession = async (e, id) => {
    e.stopPropagation();
    await api("/api/sessions/delete", {
      method: "POST",
      body: JSON.stringify({ id }),
    });
    loadSessions();
    if (currentSession === id) {
      setCurrentSession("web");
    }
  };

  async function send(e) {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;

    if (message === "/clear") {
      await api("/api/clear", { method: "POST", body: JSON.stringify({ session: currentSession }) });
      setMsgs([]);
      setInput("");
      loadSessions();
      return;
    }

    setInput("");
    setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: message }, { role: "assistant", content: "" }]);

    try {
      const res = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message, session: currentSession }),
      });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let acc = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        acc += dec.decode(value, { stream: true });
        setMsgs((m) => [...m.slice(0, -1), { role: "assistant", content: acc }]);
      }
      loadSessions();
    } catch {
      setMsgs((m) => [...m.slice(0, -1), { role: "assistant", content: "**Hata:** sunucuya ulasilamadi." }]);
    }
    setBusy(false);
  }

  return html`
    <div class="chat-layout">
      <div class="sidebar">
        <button class="new-btn" onClick=${newChat}>+ Yeni Sohbet</button>
        <div class="session-list">
          ${sessions.map(
            (s) => html`
              <div
                key=${s.id}
                class=${"session-item " + (s.id === currentSession ? "active" : "")}
                onClick=${() => setCurrentSession(s.id)}
              >
                <span style=${{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  ${s.title}
                </span>
                ${s.id !== "web" &&
                html`<button class="del" title="Sil" onClick=${(e) => deleteSession(e, s.id)}>×</button>`}
              </div>`
          )}
        </div>
      </div>

      <div class="chat-area">
        <main>
          ${msgs.length === 0 &&
          html`<p class="empty">Bu sohbet yeni basladi. ChatGPT gibi konusabilir, soru sorabilir veya sistem durumunu analiz ettirebilirsin.</p>`}
          ${msgs.map(
            (m, i) => html`
              <div class=${"msg " + m.role} key=${i}>
                <div class="who">${m.role === "user" ? "sen" : "secai"}</div>
                ${m.role === "user" ? html`<div>${m.content}</div>` : html`<${Md} text=${m.content || "..."} />`}
              </div>`
          )}
          <div ref=${endRef} />
        </main>
        <form onSubmit=${send}>
          <input
            value=${input}
            onInput=${(e) => setInput(e.target.value)}
            placeholder=${busy ? "dusunuyor..." : "> mesaj yaz (ornek: 'adim Kayra', 'acik portlari analiz et')"}
            autofocus
          />
        </form>
      </div>
    </div>`;
}

// --- Kalici Profil & Bellek Sekmesi (ChatGPT Memory) ---
function Memories() {
  const [mems, setMems] = useState([]);

  const load = () => {
    api("/api/memories").then((r) => r.json()).then(setMems).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const del = async (key) => {
    await api("/api/memories/delete", { method: "POST", body: JSON.stringify({ key }) });
    load();
  };

  return html`
    <main>
      <h3 style=${{ marginBottom: "8px" }}>SecAI Kalici Profil Bellekleri (ChatGPT Memory)</h3>
      <p class="empty" style=${{ marginBottom: "16px" }}>
        Sohbet sirasinda paylastigin bilgiler (donanimin, adin, projelerin vb.) burada saklanir ve her sohbette dogal olarak hatirlanir.
      </p>
      ${mems.length === 0 && html`<p class="empty">Henuz kaydedilmis kisisel bir bellek yok. Sohbette 'adim Kayra' veya 'bunu aklinda tut' dersen otomatik kaydeder.</p>`}
      ${mems.map(
        (m) => html`
          <div class="mem-card" key=${m.id}>
            <div>
              <b>${m.key}</b>
              <div style=${{ marginTop: "4px" }}>${m.fact}</div>
              <small class="empty">${m.created_at}</small>
            </div>
            <button class="del-btn" title="Bellekten Sil" onClick=${() => del(m.key)}>×</button>
          </div>`
      )}
    </main>`;
}

// --- Defter Sekmesi ---
function Notes() {
  const [notes, setNotes] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api("/api/notes").then((r) => r.json()).then(setNotes).catch(() => {});
  }, []);

  if (open) {
    return html`
      <main>
        <button class="back" onClick=${() => setOpen(null)}>← geri</button>
        <h3>#${open.id} ${open.title}</h3>
        <p class="empty">${open.category} · ${open.tags || "-"} · ${open.created_at}</p>
        <${Md} text=${open.content} />
      </main>`;
  }

  return html`
    <main>
      ${notes.length === 0 && html`<p class="empty">Defter bos.</p>`}
      ${notes.map(
        (n) => html`
          <div class="row" key=${n.id} onClick=${() => api(`/api/notes/${n.id}`).then((r) => r.json()).then(setOpen)}>
            <span>#${n.id} ${n.title}</span>
            <small>${n.category} · ${n.created_at}</small>
          </div>`
      )}
    </main>`;
}

// --- Guvenlik Skoru Sekmesi ---
function Score() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api("/api/score").then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data) return html`<main><p class="empty">hesaplaniyor...</p></main>`;

  return html`
    <main>
      <div class="score">${data.score} / ${data.max_score}</div>
      <p class="empty" style=${{ marginBottom: "16px" }}>${data.grade}</p>
      ${data.checks.map(
        (c, i) => html`
          <div class="row" key=${i} style=${{ cursor: "default" }}>
            <span><span class=${c.status.toLowerCase()}>${c.status}</span> ${c.name}</span>
            <small>${c.points}</small>
          </div>`
      )}
    </main>`;
}

// --- Ana Uygulama ---
function App() {
  const [tab, setTab] = useState("chat");
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api("/api/status").then((r) => r.json()).then(setStatus).catch(() => {});
  }, []);

  const tabs = [
    ["chat", "sohbet"],
    ["memory", "bellek (memory)"],
    ["notes", "defter"],
    ["score", "skor"],
  ];

  return html`
    <div class="app">
      <header>
        <div><b>secai</b> <span>${status ? `${status.version} · ${status.model}` : ""}</span></div>
        <nav>
          ${tabs.map(([k, label]) => html`
            <button key=${k} class=${tab === k ? "on" : ""} onClick=${() => setTab(k)}>${label}</button>`)}
        </nav>
      </header>
      ${tab === "chat" && html`<${Chat} />`}
      ${tab === "memory" && html`<${Memories} />`}
      ${tab === "notes" && html`<${Notes} />`}
      ${tab === "score" && html`<${Score} />`}
    </div>`;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
