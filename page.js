// Dokploy page: connect, then list projects, apps, stacks, databases and domains; deploy only after the user confirms.
const T = {
  en: {
    title: "Dokploy",
    intro: "Your Dokploy projects, apps and domains. Sessions deploy through it with the dokploy skill, asking you first.",
    keyMissing: "Add your Dokploy API key in Settings -> Keys as DOKPLOY_API_KEY (Dokploy -> Profile -> API keys), and keep it out of the environment of sessions. Then check it here.",
    keyChanged: "DOKPLOY_API_KEY changed in Settings -> Keys: check it again before it is used.",
    url: "Dokploy address", check: "Check and connect", disconnect: "Disconnect", refresh: "Refresh",
    connected: "Connected to", projects: "projects", empty: "Nothing in Dokploy yet.",
    deploy: "Deploy", redeploy: "Rebuild", logs: "Last log", close: "Close",
    confirmDeploy: (n) => `Deploy ${n} now?`, confirmRedeploy: (n) => `Rebuild and redeploy ${n} now?`,
    started: (n) => `Deployment of ${n} started.`, noLog: "No deployment yet.",
    cols: ["State", "Kind", "Project", "Name", "Domains", ""],
  },
  fr: {
    title: "Dokploy",
    intro: "Vos projets, apps et domaines Dokploy. Les sessions déploient avec le skill dokploy, en vous demandant d’abord.",
    keyMissing: "Ajoutez votre clé API Dokploy dans Réglages -> Clés sous le nom DOKPLOY_API_KEY (Dokploy -> Profile -> API keys), sans l’exposer aux sessions. Vérifiez-la ensuite ici.",
    keyChanged: "DOKPLOY_API_KEY a changé dans Réglages -> Clés : vérifiez-la à nouveau avant qu’elle serve.",
    url: "Adresse de Dokploy", check: "Vérifier et connecter", disconnect: "Déconnecter", refresh: "Actualiser",
    connected: "Connecté à", projects: "projets", empty: "Rien dans Dokploy pour l’instant.",
    deploy: "Déployer", redeploy: "Reconstruire", logs: "Dernier log", close: "Fermer",
    confirmDeploy: (n) => `Déployer ${n} maintenant ?`, confirmRedeploy: (n) => `Reconstruire et redéployer ${n} maintenant ?`,
    started: (n) => `Déploiement de ${n} lancé.`, noLog: "Aucun déploiement pour l’instant.",
    cols: ["État", "Type", "Projet", "Nom", "Domaines", ""],
  },
};

const BADGE = { done: "ui-success", running: "ui-success", error: "ui-error", idle: "ui-outline" };

function h(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null) e.append(c);   // text nodes only: data is never parsed as HTML
  return e;
}

export function mount(el, ctx) {
  const t = T[ctx.lang] || T.en;
  let alive = true;
  const notice = h("div", { class: "ui-callout", hidden: true });
  const body = h("div", { class: "ui-stack" });
  el.replaceChildren(h("div", { class: "ui-page", style: "max-width:1100px" },
    h("h1", { class: "ui-h1" }, t.title), h("p", { class: "ui-muted" }, t.intro), notice, body));

  const say = (text, kind = "ui-info") => {
    notice.className = `ui-callout ${kind}`;
    notice.textContent = text;
    notice.hidden = !text;
  };
  const fail = (e) => say(e && e.message ? e.message : String(e), "ui-error");

  function connectForm(st) {
    const input = h("input", { class: "ui-input", name: "url", value: st.url || "http://127.0.0.1:3000", style: "flex:1" });
    const btn = h("button", { class: "ui-btn", type: "submit", disabled: !st.key_present }, t.check);
    const form = h("form", { class: "ui-card ui-stack", onsubmit: async (ev) => {
      ev.preventDefault();
      btn.disabled = true;
      try {
        const r = await ctx.api("connect", { method: "POST", body: { url: input.value.trim() } });
        say(`${t.connected} ${r.url} (${r.projects} ${t.projects})`, "ui-success");
        load();
      } catch (e) { fail(e); btn.disabled = false; }
    } }, h("label", { class: "ui-label" }, t.url), h("div", { class: "ui-row" }, input, btn));
    return form;
  }

  function logPanel(svc, close) {
    const pre = h("pre", { class: "ui-code", style: "max-height:420px;overflow:auto;white-space:pre-wrap" }, "…");
    ctx.api(`log?id=${encodeURIComponent(svc.id)}`).then((r) => { if (alive) pre.textContent = r.log || t.noLog; })
      .catch((e) => { if (alive) pre.textContent = e.code === "not_found" ? t.noLog : e.message; });
    return h("div", { class: "ui-card ui-stack" },
      h("div", { class: "ui-row" }, h("b", {}, `${svc.project} / ${svc.name}`), h("span", { class: "ui-spacer" }),
        h("button", { class: "ui-btn ui-ghost ui-sm", onclick: close }, t.close)), pre);
  }

  function table(services) {
    const slot = h("div");
    const deploy = async (svc, again) => {
      if (!window.confirm((again ? t.confirmRedeploy : t.confirmDeploy)(svc.name))) return;
      try {
        await ctx.api("deploy", { method: "POST", body: { id: svc.id, again } });
        say(t.started(svc.name), "ui-success");
      } catch (e) { fail(e); }
    };
    const rows = services.map((s) => {
      const deployable = s.kind === "application" || s.kind === "compose";
      const links = s.domains.map((d) => {
        const href = `${d.https ? "https" : "http"}://${d.host}${d.path !== "/" ? d.path : ""}`;
        return h("a", { class: "ui-link", href, target: "_blank", rel: "noopener noreferrer" }, d.host);
      });
      return h("tr", {},
        h("td", {}, h("span", { class: `ui-badge ${BADGE[s.status] || "ui-outline"}` }, s.status || "-")),
        h("td", {}, s.kind),
        h("td", {}, s.project + (s.environment ? ` / ${s.environment}` : "")),
        h("td", {}, h("b", {}, s.name)),
        h("td", {}, links.length ? links.flatMap((a, i) => (i ? [" ", a] : [a])) : "-"),
        h("td", { style: "white-space:nowrap" }, deployable ? [
          h("button", { class: "ui-btn ui-sm", onclick: () => deploy(s, false) }, t.deploy), " ",
          h("button", { class: "ui-btn ui-secondary ui-sm", onclick: () => deploy(s, true) }, t.redeploy), " ",
          h("button", { class: "ui-btn ui-ghost ui-sm", onclick: () => slot.replaceChildren(logPanel(s, () => slot.replaceChildren())) }, t.logs),
        ] : ""));
    });
    if (!rows.length) return h("p", { class: "ui-empty" }, t.empty);
    return h("div", { class: "ui-stack" }, h("div", { class: "ui-table-wrap" }, h("table", { class: "ui-table" },
      h("thead", {}, h("tr", {}, t.cols.map((c) => h("th", {}, c)))), h("tbody", {}, rows))), slot);
  }

  async function load() {
    body.replaceChildren(h("div", { class: "ui-skeleton", style: "height:120px" }));
    try {
      const st = await ctx.api("status");
      if (!alive) return;
      if (!st.connected) {
        if (!st.key_present) say(t.keyMissing, "ui-warning");
        else if (st.key_changed) say(t.keyChanged, "ui-warning");
        body.replaceChildren(connectForm(st));
        return;
      }
      const { services } = await ctx.api("services");
      if (!alive) return;
      const bar = h("div", { class: "ui-row", style: "flex-wrap:wrap;gap:8px" }, h("span", { class: "ui-muted" }, `${t.connected} ${st.url}`),
        h("span", { class: "ui-spacer" }),
        h("button", { class: "ui-btn ui-outline ui-sm", onclick: load }, t.refresh),
        h("button", { class: "ui-btn ui-ghost ui-sm", onclick: async () => {
          try { await ctx.api("disconnect", { method: "POST" }); say(""); load(); } catch (e) { fail(e); }
        } }, t.disconnect));
      body.replaceChildren(bar, table(services));
    } catch (e) {
      if (alive) { body.replaceChildren(); fail(e); }
    }
  }

  load();
  return () => { alive = false; };
}
