// SecAI Web UI — Modern ChatGPT / Claude Tarzi React Arayuzu
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

// Markdown ayrıştırma
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

// --- Sohbet Bileseni ---
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

  useEffect(() => { loadSessions(); }, []);

  useEffect(() => {
    if (currentSession) {
      loadHistory(currentSession);
    }
  }, [currentSession]);

  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }), [msgs]);

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
      <!-- SIDEBAR -->
      <div class="sidebar">
        <div class="sidebar-header">
          <button class="new-btn" onClick=${newChat}>
            <span style=${{ fontSize: "16px" }}>+</span> Yeni Sohbet
          </button>
        </div>
        <div class="session-list">
          ${sessions.map(
            (s) => html`
              <div
                key=${s.id}
                class=${"session-item " + (s.id === currentSession ? "active" : "")}
                onClick=${() => setCurrentSession(s.id)}
              >
                <span class="title">${s.title}</span>
                ${s.id !== "web" &&
                html`<button class="del" title="Sil" onClick=${(e) => deleteSession(e, s.id)}>×</button>`}
              </div>`
          )}
        </div>
      </div>

      <!-- CHAT MAIN -->
      <div class="chat-area">
        <main class="chat-messages">
          <div class="chat-container">
            ${msgs.length === 0 &&
            html`
              <div class="empty-state">
                <div style=${{ fontSize: "28px", marginBottom: "12px" }}>🛡️</div>
                <h3 style=${{ color: "#fff", marginBottom: "8px" }}>SecAI ile nasıl yardımcı olabilirim?</h3>
                <p>Güvenlik denetimleri yapabilir, portları inceleyebilir, dosya okutabilir veya genel sohbet edebilirsin.</p>
              </div>`}
            ${msgs.map(
              (m, i) => html`
                <div class=${"msg " + m.role} key=${i} style=${{ marginBottom: "24px" }}>
                  <div class="avatar">${m.role === "user" ? "K" : "S"}</div>
                  <div class="msg-body">
                    <div class="who">${m.role === "user" ? "Sen" : "SecAI"}</div>
                    ${m.role === "user"
                      ? html`<div class="content">${m.content}</div>`
                      : html`<${Md} text=${m.content || "Düşünüyor..."} />`}
                  </div>
                </div>`
            )}
            <div ref=${endRef} />
          </div>
        </main>

        <div class="input-wrapper">
          <form onSubmit=${send} class="input-box">
            <input
              value=${input}
              onInput=${(e) => setInput(e.target.value)}
              placeholder=${busy ? "SecAI düşünüyor..." : "Mesajınızı yazın..."}
              autofocus
            />
            <button class="send-btn" type="submit" disabled=${busy || !input.trim()}>
              ↑
            </button>
          </form>
        </div>
      </div>
    </div>`;
}

// --- Bellek Bileseni ---
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
    <div class="view-container">
      <h2 style=${{ color: "#fff", marginBottom: "6px" }}>Kişisel Profil & Kalıcı Bellek</h2>
      <p style=${{ color: "var(--text-muted)", marginBottom: "24px" }}>
        ChatGPT Memory tarzı: Senin donanımını, sistemini veya paylaştığın tercihleri hatırlar; tüm sohbetlerde arka planda bağlam kurar.
      </p>
      ${mems.length === 0 && html`<div class="empty-state">Henüz hafızaya kaydedilmiş bir bilgi yok. Sohbette 'benim adım...' veya 'aklında tut...' dersen otomatik kaydeder.</div>`}
      ${mems.map(
        (m) => html`
          <div class="card" key=${m.id} style=${{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style=${{ color: "var(--accent)", fontWeight: "600", fontSize: "13px", marginBottom: "4px" }}>${m.key}</div>
              <div style=${{ color: "#f8fafc", fontSize: "14.5px" }}>${m.fact}</div>
              <small style=${{ color: "var(--text-dim)", marginTop: "4px", display: "block" }}>${m.created_at}</small>
            </div>
            <button class="session-item del" style=${{ display: "block", fontSize: "18px" }} title="Sil" onClick=${() => del(m.key)}>×</button>
          </div>`
      )}
    </div>`;
}

// --- Defter Bileseni ---
function Notes() {
  const [notes, setNotes] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api("/api/notes").then((r) => r.json()).then(setNotes).catch(() => {});
  }, []);

  if (open) {
    return html`
      <div class="view-container">
        <button class="new-btn" style=${{ width: "auto", display: "inline-flex", marginBottom: "20px" }} onClick=${() => setOpen(null)}>
          ← Notlara Dön
        </button>
        <h2 style=${{ color: "#fff", marginBottom: "8px" }}>#${open.id} ${open.title}</h2>
        <div style=${{ color: "var(--text-dim)", marginBottom: "20px", fontSize: "13px" }}>
          ${open.category} · ${open.tags || "etiketsiz"} · ${open.created_at}
        </div>
        <div class="card">
          <${Md} text=${open.content} />
        </div>
      </div>`;
  }

  return html`
    <div class="view-container">
      <h2 style=${{ color: "#fff", marginBottom: "6px" }}>Vaka & Proje Defteri</h2>
      <p style=${{ color: "var(--text-muted)", marginBottom: "24px" }}>
        Kaydettiğin raporlar, güvenlik analizleri ve proje notları.
      </p>
      ${notes.length === 0 && html`<div class="empty-state">Defter henüz boş.</div>`}
      ${notes.map(
        (n) => html`
          <div class="card" key=${n.id} style=${{ cursor: "pointer" }} onClick=${() => api(`/api/notes/${n.id}`).then((r) => r.json()).then(setOpen)}>
            <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style=${{ fontWeight: "600", color: "#f1f5f9" }}>#${n.id} ${n.title}</span>
              <span class="model-tag">${n.category}</span>
            </div>
            <div style=${{ color: "var(--text-dim)", fontSize: "12px", marginTop: "6px" }}>${n.created_at}</div>
          </div>`
      )}
    </div>`;
}

// --- Skor Bileseni ---
function Score() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api("/api/score").then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data) return html`<div class="view-container"><div class="empty-state">Güvenlik skoru hesaplanıyor...</div></div>`;

  return html`
    <div class="view-container">
      <div class="score-banner">
        <div style=${{ color: "var(--accent)", fontSize: "13px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "1px" }}>
          CIS Linux Güvenlik Skoru
        </div>
        <div class="score-num">${data.score} <span style=${{ fontSize: "20px", color: "var(--text-dim)", fontWeight: "400" }}>/ ${data.max_score}</span></div>
        <div style=${{ color: "var(--text-muted)", marginTop: "6px" }}>Seviye: <b>${data.grade}</b></div>
      </div>

      <h3 style=${{ color: "#fff", marginBottom: "14px" }}>Denetim Kalemleri</h3>
      ${data.checks.map(
        (c, i) => html`
          <div class="card" key=${i}>
            <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <span style=${{ fontWeight: "600" }}>${c.name}</span>
              <span class=${c.status.toLowerCase()}>${c.status} (${c.points})</span>
            </div>
            <div style=${{ color: "var(--text-dim)", fontSize: "13px" }}>Mevcut Değer: <code style=${{ color: "#cbd5e1" }}>${c.current}</code></div>
            ${c.status !== "PASS" && html`
              <div style=${{ marginTop: "8px", fontSize: "13px", color: "var(--text-muted)" }}>
                Öneri / Komut: <code>${c.remediation}</code>
              </div>`}
          </div>`
      )}
    </div>`;
}

// --- Ana Uygulama ---
function App() {
  const [tab, setTab] = useState("chat");
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api("/api/status").then((r) => r.json()).then(setStatus).catch(() => {});
  }, []);

  const tabs = [
    ["chat", "Sohbet"],
    ["memory", "Bellek"],
    ["notes", "Defter"],
    ["score", "Güvenlik Skoru"],
  ];

  return html`
    <div class="app">
      <header>
        <div class="brand">
          <div class="logo-badge">S</div>
          <span class="brand-title">secai</span>
          <span class="model-tag">${status ? `${status.model}` : "bağlanıyor..."}</span>
        </div>
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
