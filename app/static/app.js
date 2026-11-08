/* NetConfig Assistant UI: plain JavaScript, no build step. */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const api = async (path, body) => {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j;
};

const ICONS = { "cisco-ios": "🛜", "cisco-asa": "🧱", "cisco-nxos": "🗄️", fortigate: "🛡️", paloalto: "🔥", juniper: "🌿",
  mikrotik: "📡", checkpoint: "✅", huawei: "🔷", aruba: "🔀", arista: "⚡", linux: "🐧", cloud: "☁️", other: "🧩", unknown: "❓" };
const TASK_INFO = {
  new: { ico: "✨", desc: "First-time setup, a new feature, or a lab", ex: ["Set up a basic internet connection with NAT", "Create a guest Wi-Fi VLAN that can't reach the office network", "Build a site-to-site VPN to our branch office"] },
  change: { ico: "🛠️", desc: "Safely change a device that people are using", ex: ["Allow my web server 192.168.1.20 to be reached from the internet on HTTPS", "Only let the IT PC 10.0.0.5 manage the firewall", "Add a new VLAN 30 for cameras"] },
  fix: { ico: "🩺", desc: "Something doesn't work and you need to find out why", ex: ["The VPN to the branch is down", "Users can't reach the internet but the firewall can", "One VLAN can't talk to the printer"] },
  review: { ico: "🔍", desc: "Find security problems and bad practice", ex: ["Check this config for security problems", "Is my remote access set up safely?", "What should I clean up first?"] },
  migrate: { ico: "🔁", desc: "Translate a config from one brand to another", ex: ["Convert this Cisco ASA config to FortiGate", "Move these firewall rules from pfSense to MikroTik"] },
  question: { ico: "💬", desc: "Learn a concept or find the right command", ex: ["What is the difference between NAT and PAT?", "How do I see which interfaces are up?", "How do I save the configuration?"] },
};

const state = { meta: null, vendors: [], vendor2: null, task: null, live: null, conn: null, messages: [], busy: false, ctrl: null, chatCtx: {} };

/* ---------------------------------------------------------------- theme */
const savedTheme = (() => { try { return localStorage.getItem("theme"); } catch { return null; } })();
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
$("#btn-theme").onclick = () => {
  const dark = matchMedia("(prefers-color-scheme: dark)").matches;
  const cur = document.documentElement.dataset.theme || (dark ? "dark" : "light");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch {}
};

/* ---------------------------------------------------------------- startup */
async function init() {
  state.meta = await api("/api/status");
  $("#versions").textContent = `App ${state.meta.app_version} · skill v${state.meta.skill_version}`;
  buildVendorGrid($("#vendor-grid"), (id) => { state.vendors = [id]; markSelected("#vendor-grid", id); if (!$("#second-vendor-toggle").checked) go(2); });
  buildVendorGrid($("#vendor-grid-2"), (id) => { state.vendor2 = id; markSelected("#vendor-grid-2", id); go(2); }, ["unknown"]);
  buildTaskGrid();
  refreshAiStatus();
}

function buildVendorGrid(el, onPick, skip = []) {
  el.innerHTML = "";
  for (const [id, v] of Object.entries(state.meta.vendors)) {
    if (skip.includes(id)) continue;
    const b = document.createElement("button");
    b.className = "card"; b.dataset.id = id;
    b.innerHTML = `<span class="ico"></span><b></b><span></span>`;
    b.children[0].textContent = ICONS[id] || "🔧"; b.children[1].textContent = v.label; b.children[2].textContent = v.hint;
    b.onclick = () => onPick(id);
    el.appendChild(b);
  }
}
const markSelected = (grid, id) => $$(".card", $(grid)).forEach((c) => c.classList.toggle("selected", c.dataset.id === id));

$("#second-vendor-toggle").onchange = (e) => {
  $("#vendor2-wrap").hidden = !e.target.checked;
  if (!e.target.checked) state.vendor2 = null;
};

function buildTaskGrid() {
  const el = $("#task-grid"); el.innerHTML = "";
  for (const [id, t] of Object.entries(state.meta.tasks)) {
    const info = TASK_INFO[id] || {};
    const b = document.createElement("button");
    b.className = "card"; b.dataset.id = id;
    b.innerHTML = `<span class="ico"></span><b></b><span></span>`;
    b.children[0].textContent = info.ico || "•"; b.children[1].textContent = t.label; b.children[2].textContent = info.desc || "";
    b.onclick = () => { state.task = id; markSelected("#task-grid", id); prepareStep3(); go(3); };
    el.appendChild(b);
  }
}

function go(n) {
  [1, 2, 3].forEach((i) => { $(`#step-${i}`).hidden = i !== n; });
  $$(".steps li").forEach((li) => {
    const i = +li.dataset.step;
    li.classList.toggle("active", i === n); li.classList.toggle("done", i < n);
    li.onclick = i < n ? () => go(i) : null;
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}
$$("[data-back]").forEach((b) => (b.onclick = () => go(+b.dataset.back)));

function vendorLabel(id) { return state.meta.vendors[id]?.label || id; }
function allVendors() { return [...state.vendors, ...(state.vendor2 ? [state.vendor2] : [])]; }

function prepareStep3() {
  const t = state.task;
  const names = allVendors().map(vendorLabel).join(" + ");
  $("#step3-summary").textContent = `${names} · ${state.meta.tasks[t].label}`;
  const ex = $("#examples"); ex.innerHTML = "";
  for (const s of TASK_INFO[t]?.ex || []) {
    const c = document.createElement("button"); c.className = "chip"; c.type = "button"; c.textContent = s;
    c.onclick = () => { $("#request").value = s; $("#request").focus(); };
    ex.appendChild(c);
  }
  // live/connection questions matter for changes and fixes
  $("#live-block").hidden = t === "question" || t === "migrate";
  if (t === "change") setSeg("live", "yes");
  if (t === "new") setSeg("live", "no");
  const cmds = allVendors().map((v) => state.meta.vendors[v]?.version).filter(Boolean);
  $("#version-hint").textContent = cmds.length ? `To find it, run: ${[...new Set(cmds)].join("   or   ")}` : "";
  $("#paste-box").open = t === "review" || t === "migrate" || t === "change";
}

function setSeg(name, v) {
  state[name] = v;
  $$(`#${name} button`).forEach((b) => b.classList.toggle("on", b.dataset.v === v));
}
["live", "conn"].forEach((name) => $$(`#${name} button`).forEach((b) => (b.onclick = () => setSeg(name, b.dataset.v))));

/* ---------------------------------------------------------------- secret removal */
let sanitized = { text: "", findings: [], source: null };
async function sanitizeConfig() {
  const raw = $("#config").value;
  const mask = $("#mask-ips").checked;
  if (!raw.trim()) { $("#redact-report").hidden = true; sanitized = { text: "", findings: [], source: raw }; return sanitized; }
  if (sanitized.source === raw && sanitized.mask === mask) return sanitized;
  const r = await api("/api/sanitize", { text: raw, mask_public_ips: mask });
  sanitized = { text: r.text, findings: r.findings, source: raw, mask };
  showRedactReport(r.findings);
  return sanitized;
}
function showRedactReport(findings) {
  const box = $("#redact-report"); box.hidden = false; box.innerHTML = "";
  const secrets = findings.filter((f) => !f.original_hint);
  const ips = findings.filter((f) => f.original_hint);
  const head = document.createElement("div");
  head.innerHTML = secrets.length
    ? `🛡 <b>${secrets.length} secret${secrets.length > 1 ? "s" : ""} removed</b> before sending. They will appear as <code>&lt;REDACTED-n&gt;</code> in the answer: put your real value back when you paste.`
    : "🛡 No passwords or keys were found. Check the text yourself before sending if you're unsure.";
  box.appendChild(head);
  if (findings.length) {
    const ul = document.createElement("ul");
    for (const f of secrets) { const li = document.createElement("li"); li.textContent = `${f.token}: ${f.label}${f.count > 1 ? ` (×${f.count})` : ""}`; ul.appendChild(li); }
    for (const f of ips) { const li = document.createElement("li"); li.textContent = `${f.original_hint} → ${f.token} (public IP)`; ul.appendChild(li); }
    box.appendChild(ul);
  }
}
let sanTimer;
$("#config").addEventListener("input", () => { clearTimeout(sanTimer); sanTimer = setTimeout(sanitizeConfig, 500); });
$("#mask-ips").onchange = sanitizeConfig;

$("#btn-redact-followup").onclick = async () => {
  const ta = $("#followup-text");
  if (!ta.value.trim()) return;
  const r = await api("/api/sanitize", { text: ta.value, mask_public_ips: $("#mask-ips").checked });
  ta.value = r.text;
  const n = r.findings.filter((f) => !f.original_hint).length;
  toast(n ? `Removed ${n} secret${n > 1 ? "s" : ""}.` : "No secrets found.");
};

/* ---------------------------------------------------------------- ask */
$("#btn-ask").onclick = async () => {
  const req = $("#request").value.trim();
  const cfg = await sanitizeConfig();
  if (!req && !cfg.text) { $("#request").focus(); toast("Please describe what you need first."); return; }
  const t = state.task, lines = [];
  lines.push(`Device: ${allVendors().map(vendorLabel).join(" and ")}`);
  lines.push(`What I want to do: ${state.meta.tasks[t].label}`);
  if (!$("#live-block").hidden) {
    const live = { yes: "yes, it is in use on a real network", no: "no, it is new or a lab", unsure: "not sure" }[state.live];
    const conn = { console: "console cable / direct", remote: "remotely (SSH or web), so a mistake could cut me off", unsure: "not sure" }[state.conn];
    if (live) lines.push(`Live device: ${live}`);
    if (conn) lines.push(`Connected: ${conn}`);
    const ver = $("#version").value.trim();
    lines.push(`Software version: ${ver || "unknown"}`);
  }
  if ($("#ipv6").checked) lines.push("The network uses IPv6 as well as IPv4.");
  lines.push("", req || "Please review the configuration below.");
  if (cfg.text) lines.push("", "Current configuration (secrets removed by the app):", "```text", cfg.text, "```");
  state.chatCtx = { vendors: allVendors(), task: t, ipv6: $("#ipv6").checked, has_config: !!cfg.text };
  state.messages = [];
  $("#messages").innerHTML = "";
  $("#wizard").hidden = true; $("#chat").hidden = false;
  $("#chat-context").textContent = $("#step3-summary").textContent;
  send(lines.join("\n"));
};

$("#followup").onsubmit = (e) => {
  e.preventDefault();
  const v = $("#followup-text").value.trim();
  if (!v || state.busy) return;
  $("#followup-text").value = "";
  send(v);
};
$("#followup-text").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) $("#followup").requestSubmit();
});

function addMessage(role, text) {
  const m = document.createElement("div");
  m.className = `msg ${role}`;
  const who = document.createElement("div"); who.className = "who"; who.textContent = role === "user" ? "You" : "NetConfig Assistant";
  m.appendChild(who);
  if (role === "user") { m.appendChild(document.createTextNode(text)); m.dir = "auto"; }
  $("#messages").appendChild(m);
  return m;
}

/* Split Qwen/DeepSeek style <think>…</think> out of the visible text. */
function splitThinking(text) {
  let think = "", out = text;
  const open = out.indexOf("<think>");
  if (open !== -1) {
    const close = out.indexOf("</think>", open);
    if (close === -1) { think = out.slice(open + 7); out = out.slice(0, open); }
    else { think = out.slice(open + 7, close); out = out.slice(0, open) + out.slice(close + 8); }
  } else if (out.includes("</think>")) {
    const close = out.indexOf("</think>"); think = out.slice(0, close); out = out.slice(close + 8);
  }
  return { think: think.trim(), out: out.replace(/^\s+/, "") };
}

function render(el, text, thinking, streaming) {
  const s = splitThinking(text);
  const think = (thinking + "\n" + s.think).trim();
  let body = el.querySelector(".body");
  if (!body) {
    const th = document.createElement("details"); th.className = "thinking"; th.hidden = true;
    th.innerHTML = "<summary>Show the AI's reasoning</summary><pre></pre>";
    body = document.createElement("div"); body.className = "body"; body.dir = "auto";
    el.append(th, body);
  }
  const th = el.querySelector(".thinking");
  th.hidden = !think; th.querySelector("pre").textContent = think;
  if (!s.out) {
    body.innerHTML = `<p class="waiting">${think ? "Thinking…" : "Working on it… (local models can take a little while to start)"}</p>`;
    return;
  }
  body.innerHTML = DOMPurify.sanitize(marked.parse(escapePlaceholders(s.out)));
  body.classList.toggle("cursor", streaming);
  for (const pre of body.querySelectorAll("pre")) {
    const wrap = document.createElement("div"); wrap.className = "codewrap";
    pre.replaceWith(wrap); wrap.appendChild(pre);
    const btn = document.createElement("button"); btn.className = "copy"; btn.type = "button"; btn.textContent = "Copy";
    btn.onclick = async () => {
      const code = pre.innerText.replace(/\n$/, "");
      try { await navigator.clipboard.writeText(code); } catch { fallbackCopy(code); }
      btn.textContent = "Copied ✓"; btn.classList.add("done");
      setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("done"); }, 1500);
    };
    wrap.appendChild(btn);
  }
  for (const a of body.querySelectorAll("a")) { a.target = "_blank"; a.rel = "noopener"; }
}
/* Keep <REDACTED-n> visible: outside code, escape it so it isn't treated as an HTML tag. */
function escapePlaceholders(md) {
  return md.split(/(```[\s\S]*?(?:```|$)|`[^`\n]*`)/).map((part, i) =>
    i % 2 ? part : part.replace(/<((?:REDACTED|PUBLIC-IP)-\d+|[A-Z][A-Z0-9_-]{2,})>/g, "&lt;$1&gt;")).join("");
}
function fallbackCopy(t) {
  const ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select();
  document.execCommand("copy"); ta.remove();
}

async function send(text) {
  state.messages.push({ role: "user", content: text });
  addMessage("user", text);
  const el = addMessage("assistant");
  let out = "", thinking = "", meta = null;
  render(el, "", "", true);
  setBusy(true);
  state.ctrl = new AbortController();
  let raf = 0;
  const paint = () => { raf = 0; render(el, out, thinking, true); };
  try {
    const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, signal: state.ctrl.signal,
      body: JSON.stringify({ ...state.chatCtx, messages: state.messages }) });
    const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = "";
    let follow = true;
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) !== -1) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        if (!chunk.startsWith("data:")) continue;
        const ev = JSON.parse(chunk.slice(5));
        if (ev.type === "delta") out += ev.text;
        else if (ev.type === "thinking") thinking += ev.text;
        else if (ev.type === "meta") meta = JSON.parse(ev.text);
        else if (ev.type === "error") throw new Error(ev.text);
      }
      follow = window.innerHeight + window.scrollY >= document.body.scrollHeight - 160;
      if (!raf) raf = requestAnimationFrame(() => { paint(); if (follow) window.scrollTo(0, document.body.scrollHeight); });
    }
  } catch (e) {
    if (e.name !== "AbortError") {
      el.classList.add("error");
      const p = document.createElement("p"); p.textContent = "⚠ " + e.message; el.appendChild(p);
      if (/model|reach|Settings|refused/i.test(e.message)) {
        const b = document.createElement("button"); b.textContent = "Open Settings"; b.onclick = openSettings; el.appendChild(b);
      }
    }
  } finally {
    cancelAnimationFrame(raf);
    const clean = splitThinking(out).out;
    if (clean) { render(el, out, thinking, false); state.messages.push({ role: "assistant", content: clean }); }
    else if (!el.classList.contains("error")) { state.messages.pop(); el.remove(); }
    if (meta) $("#chat-context").textContent = `${$("#step3-summary").textContent} · ${meta.provider || ""} ${meta.model || ""}`;
    setBusy(false);
  }
}

function setBusy(b) {
  state.busy = b;
  $("#btn-send").disabled = b; $("#btn-stop").hidden = !b;
}
$("#btn-stop").onclick = () => state.ctrl?.abort();

$("#btn-new").onclick = () => {
  if (state.busy) state.ctrl?.abort();
  $("#chat").hidden = true; $("#wizard").hidden = false; go(1);
};

$("#btn-export").onclick = () => {
  const md = [`# NetConfig Assistant — ${$("#chat-context").textContent}`, `_Saved ${new Date().toLocaleString()}_`, ""];
  for (const m of state.messages) md.push(m.role === "user" ? "## You" : "## Assistant", "", m.content, "");
  const blob = new Blob([md.join("\n")], { type: "text/markdown" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = `netconfig-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-")}.md`; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};

/* ---------------------------------------------------------------- settings */
async function refreshAiStatus() {
  const s = state.meta.settings, pill = $("#ai-status"), banner = $("#setup-banner");
  const presetLabel = state.meta.presets[s.preset]?.label || "AI";
  if (!s.model) {
    pill.textContent = "AI not set up"; pill.className = "pill bad";
    banner.hidden = false;
    banner.innerHTML = "<b>One-time setup:</b> choose which AI to use. A model on this computer keeps your configs private.";
    const b = document.createElement("button"); b.className = "primary"; b.textContent = "Set up AI"; b.onclick = openSettings;
    banner.appendChild(b);
    return;
  }
  pill.textContent = `${presetLabel}: ${s.model}`; pill.className = "pill";
  try { await api("/api/models", {}); pill.classList.add("ok"); banner.hidden = true; }
  catch (e) {
    pill.classList.add("bad"); banner.hidden = false;
    banner.textContent = "⚠ " + e.message + " ";
    const b = document.createElement("button"); b.textContent = "Settings"; b.onclick = openSettings; banner.appendChild(b);
  }
}

function fillPresetSelect() {
  const sel = $("#s-preset"); sel.innerHTML = "";
  for (const [id, p] of Object.entries(state.meta.presets)) { const o = new Option(p.label, id); sel.add(o); }
}
function presetChanged(keepBase) {
  const p = state.meta.presets[$("#s-preset").value];
  if (!keepBase || !$("#s-base").value) $("#s-base").value = p.base_url;
  $("#s-key-wrap").hidden = !p.needs_key && $("#s-preset").value !== "custom";
}
$("#s-preset").onchange = () => { presetChanged(false); $("#s-model").innerHTML = ""; loadModels(); };

function formSettings() {
  return { preset: $("#s-preset").value, base_url: $("#s-base").value.trim(), api_key: $("#s-key").value.trim(),
    model: $("#s-model-manual").value.trim() || $("#s-model").value, temperature: +$("#s-temp").value || 0.2, max_tokens: +$("#s-max").value || 8192 };
}

async function loadModels(selectId) {
  const res = $("#s-result"); res.className = "small"; res.textContent = "Looking for models…";
  const f = formSettings();
  try {
    const { models } = await api("/api/models", { preset: f.preset, base_url: f.base_url, api_key: f.api_key });
    const sel = $("#s-model"); sel.innerHTML = "";
    models.forEach((m) => sel.add(new Option(m, m)));
    const want = selectId || state.meta.settings.model;
    if (models.includes(want)) { sel.value = want; $("#s-model-manual").value = ""; }
    res.className = "small ok"; res.textContent = models.length ? `✓ Connected. ${models.length} model${models.length > 1 ? "s" : ""} available.` : "✓ Connected, but no models were listed. Type the model name.";
    return true;
  } catch (e) { res.className = "small bad"; res.textContent = "✗ " + e.message; return false; }
}
$("#s-refresh").onclick = () => loadModels();
$("#s-test").onclick = () => loadModels($("#s-model").value);

async function openSettings() {
  fillPresetSelect();
  const s = state.meta.settings;
  $("#s-preset").value = s.preset; $("#s-base").value = s.base_url; $("#s-key").value = s.api_key || "";
  $("#s-temp").value = s.temperature; $("#s-max").value = s.max_tokens;
  $("#s-model").innerHTML = ""; if (s.model) $("#s-model").add(new Option(s.model, s.model));
  $("#s-model-manual").value = ""; $("#s-result").textContent = "";
  presetChanged(true);
  $("#settings").showModal();
  // look for AI servers running on this computer
  const det = $("#detected"); det.innerHTML = '<span class="small muted">Looking for AI on this computer…</span>';
  try {
    const { local } = await api("/api/detect");
    det.innerHTML = "";
    if (!local.length) { det.innerHTML = '<span class="small muted">No local AI server found (llama.cpp, Ollama or LM Studio). Start one, or use a cloud service below.</span>'; return; }
    for (const l of local) {
      const b = document.createElement("button"); b.type = "button";
      b.textContent = `✓ Use ${l.label}${l.models[0] ? ` · ${l.models[0]}` : ""}`;
      b.onclick = () => { $("#s-preset").value = l.preset; presetChanged(false); loadModels(l.models[0]); };
      det.appendChild(b);
    }
  } catch { det.innerHTML = ""; }
}
$("#btn-settings").onclick = openSettings;

$("#s-save").onclick = async () => {
  const f = formSettings();
  if (!f.model) { $("#s-result").className = "small bad"; $("#s-result").textContent = "Choose or type a model first (press ↻ Load models)."; return; }
  let settings;
  try { ({ settings } = await api("/api/settings", f)); }
  catch (e) { $("#s-result").className = "small bad"; $("#s-result").textContent = "✗ Couldn't save: " + e.message; return; }
  state.meta.settings = settings;
  $("#settings").close();
  refreshAiStatus();
  toast("Settings saved.");
};

/* ---------------------------------------------------------------- toast */
function toast(msg) {
  let t = $("#toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; document.body.appendChild(t);
    Object.assign(t.style, { position: "fixed", bottom: "24px", left: "50%", transform: "translateX(-50%)", background: "var(--text)", color: "var(--bg)",
      padding: "8px 16px", borderRadius: "10px", zIndex: 50, fontSize: ".9rem", transition: "opacity .2s" }); }
  t.textContent = msg; t.style.opacity = 1;
  clearTimeout(t._h); t._h = setTimeout(() => (t.style.opacity = 0), 2200);
}

marked.setOptions({ gfm: true, breaks: false });
init().catch((e) => { document.body.innerHTML = `<p style="padding:24px">Couldn't start: ${String(e.message).replace(/</g, "&lt;")}</p>`; });
