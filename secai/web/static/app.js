// SecAI — sade React arayuzu (derleme gerektirmez: React + htm, ESM)
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

// --- Guvenli, minimal Markdown (HTML once kacislanir, model ciktisi asla ham HTML olarak basilmaz) ---
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const HIDDEN = /```(?:save-note|update-note|delete-note|export-note|web-search|intel-lookup|secops-action)\s*\n[\s\S]*?(?:```|$)/gi;

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

// --- Sohbet ---
function Chat() {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    api("/api/history").then((r) => r.json()).then(setMsgs).catch(() => {});
  }, []);

  useEffect(() => endRef.current?.scrollIntoView({ block: "end" }), [msgs]);

  async function send(e) {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;

    if (message === "/clear") {
      await api("/api/clear", { method: "POST" });
      setMsgs([]);
      setInput("");
      return;
    }

    setInput("");
    setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: message }, { role: "assistant", content: "" }]);

    try {
      const res = await api("/api/chat", { method: "POST", body: JSON.stringify({ message }) });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let acc = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        acc += dec.decode(value, { stream: true });
        setMsgs((m) => [...m.slice(0, -1), { role: "assistant", content: acc }]);
      }
    } catch {
      setMsgs((m) => [...m.slice(0, -1), { role: "assistant", content: "**Hata:** sunucuya ulasilamadi." }]);
    }
    setBusy(false);
  }

  return html`
    <main>
      ${msgs.length === 0 && html`<p class="empty">Bir sey sor. Ornek: "acik portlar neyi ifade eder?" — temizlemek icin /clear</p>`}
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
        placeholder=${busy ? "dusunuyor..." : "> mesaj yaz"}
        autofocus
      />
    </form>`;
}

// --- Defter ---
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

// --- Guvenlik skoru ---
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

// --- Uygulama ---
function App() {
  const [tab, setTab] = useState("chat");
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api("/api/status").then((r) => r.json()).then(setStatus).catch(() => {});
  }, []);

  const tabs = [["chat", "sohbet"], ["notes", "defter"], ["score", "skor"]];

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
      ${tab === "notes" && html`<${Notes} />`}
      ${tab === "score" && html`<${Score} />`}
    </div>`;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);

