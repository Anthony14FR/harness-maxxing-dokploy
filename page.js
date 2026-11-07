// Dokploy page: connect, then list projects, apps, stacks, databases and domains; deploy only after the user confirms.
const T = {
  en: {
    title: "Dokploy",
    intro: "Your Dokploy projects, apps and domains. Sessions deploy through it with the dokploy skill, asking you first.",
    keyMissing: "Add your Dokploy API key in Settings -> Keys as DOKPLOY_API_KEY, with “Expose to Harness sessions” left off. In Dokploy v0.30: Settings -> Profile (/dashboard/settings/profile), API/CLI Keys, Generate New Key; it is shown only once, copy it right away. Then check it here.",
    skill: { missing: "Claude sessions do not have the dokploy skill yet.", stale: "The dokploy skill of Claude sessions is older than this extension.", broken: "This extension's skill folder is empty: update the extension (git pull)." },
    skillButton: "Install the skill for sessions", skillDone: "Skill installed for Claude sessions.",
    keyChanged: "DOKPLOY_API_KEY changed in Settings -> Keys: check it again before it is used.",
    url: "Dokploy address", check: "Check and connect", disconnect: "Disconnect", refresh: "Refresh",
    connected: "Connected to", projects: "projects", empty: "Nothing in Dokploy yet.",
    deploy: "Deploy", redeploy: "Rebuild", logs: "Last log", close: "Close",
    confirmDeploy: (n) => `Deploy ${n} now?`, confirmRedeploy: (n) => `Rebuild and redeploy ${n} now?`,
    started: (n) => `Deployment of ${n} started.`, noLog: "No deployment yet.",
    cols: ["Last deployment", "Containers", "Kind", "Project", "Name", "Domains", ""],
    health: { ok: "running", partial: "partly down", down: "down", stopped: "stopped", unknown: "unknown" },
    risk: {
      downtime: "Its containers are stopped and started again: the site can be down for a few seconds.",
      no_rebuild: "It has no git source: nothing is rebuilt, the same image starts again.",
      unknown: "Dokploy did not give its details: assume the site can go down.",
      stopped: "The site stays down until you start it again.",
    },
    typeName: (n) => `Type ${n} to confirm`, confirm: "Confirm", cancel: "Cancel",
    stop: "Stop", start: "Start", rollback: "Roll back",
    confirmStop: (n) => `Stop ${n} now?`, confirmStart: (n) => `Start ${n} now?`,
    confirmRollback: (n, d) => `Roll ${n} back to “${d}”?`,
    doneAction: { stop: (n) => `${n} is stopping.`, start: (n) => `${n} is starting.`, rollback: (n) => `Rollback of ${n} started.` },
    protect: "Protect", unprotect: "Unprotect", protectedBadge: "protected",
    protectedHelp: "Protected: read-only here and for sessions. Only you can lift it, on this page.",
  },
  fr: {
    title: "Dokploy",
    intro: "Vos projets, apps et domaines Dokploy. Les sessions déploient avec le skill dokploy, en vous demandant d’abord.",
    keyMissing: "Ajoutez votre clé API Dokploy dans Réglages -> Clés sous le nom DOKPLOY_API_KEY, avec « Fournir aux sessions Harness » désactivé. Dans Dokploy v0.30 : Settings -> Profile (/dashboard/settings/profile), API/CLI Keys, Generate New Key ; elle ne s’affiche qu’une fois, copiez-la tout de suite. Vérifiez-la ensuite ici.",
    skill: { missing: "Les sessions Claude n’ont pas encore le skill dokploy.", stale: "Le skill dokploy des sessions Claude est plus ancien que cette extension.", broken: "Le dossier du skill de cette extension est vide : mettez l’extension à jour (git pull)." },
    skillButton: "Installer le skill pour les sessions", skillDone: "Skill installé pour les sessions Claude.",
    keyChanged: "DOKPLOY_API_KEY a changé dans Réglages -> Clés : vérifiez-la à nouveau avant qu’elle serve.",
    url: "Adresse de Dokploy", check: "Vérifier et connecter", disconnect: "Déconnecter", refresh: "Actualiser",
    connected: "Connecté à", projects: "projets", empty: "Rien dans Dokploy pour l’instant.",
    deploy: "Déployer", redeploy: "Reconstruire", logs: "Dernier log", close: "Fermer",
    confirmDeploy: (n) => `Déployer ${n} maintenant ?`, confirmRedeploy: (n) => `Reconstruire et redéployer ${n} maintenant ?`,
    started: (n) => `Déploiement de ${n} lancé.`, noLog: "Aucun déploiement pour l’instant.",
    cols: ["Dernier déploiement", "Conteneurs", "Type", "Projet", "Nom", "Domaines", ""],
    health: { ok: "en marche", partial: "en partie arrêté", down: "en panne", stopped: "arrêté", unknown: "inconnu" },
    risk: {
      downtime: "Ses conteneurs sont arrêtés puis relancés : le site peut être coupé quelques secondes.",
      no_rebuild: "Il n’a pas de source git : rien n’est reconstruit, la même image redémarre.",
      unknown: "Dokploy n’a pas donné ses détails : considérez que le site peut être coupé.",
      stopped: "Le site reste coupé jusqu’à ce que vous le redémarriez.",
    },
    typeName: (n) => `Tapez ${n} pour confirmer`, confirm: "Confirmer", cancel: "Annuler",
    stop: "Arrêter", start: "Démarrer", rollback: "Revenir en arrière",
    confirmStop: (n) => `Arrêter ${n} maintenant ?`, confirmStart: (n) => `Démarrer ${n} maintenant ?`,
    confirmRollback: (n, d) => `Revenir pour ${n} au déploiement « ${d} » ?`,
    doneAction: { stop: (n) => `${n} s’arrête.`, start: (n) => `${n} démarre.`, rollback: (n) => `Retour arrière de ${n} lancé.` },
    protect: "Protéger", unprotect: "Ne plus protéger", protectedBadge: "protégé",
    protectedHelp: "Protégé : en lecture seule ici et pour les sessions. Vous seul pouvez lever la protection, sur cette page.",
  },
};

const BADGE = { done: "ui-success", running: "ui-success", error: "ui-error", idle: "ui-outline" };
const HEALTH = { ok: "ui-success", partial: "ui-warning", down: "ui-error", stopped: "ui-outline", unknown: "ui-outline" };

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
  const skillBar = h("div", { class: "ui-callout ui-warning ui-row", hidden: true, style: "flex-wrap:wrap;gap:8px" });
  const body = h("div", { class: "ui-stack" });
  el.replaceChildren(h("div", { class: "ui-page", style: "max-width:1100px" },
    h("h1", { class: "ui-h1" }, t.title), h("p", { class: "ui-muted" }, t.intro), notice, skillBar, body));

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

  // Inline confirmation: a possible downtime asks to type the service name, never a single OK.
  function confirmPanel(svc, question, run, close, risks = svc.risks || ["unknown"]) {
    const typed = ["downtime", "unknown", "stopped"].some((r) => risks.includes(r));
    const name = String(svc.name).trim();
    const input = typed ? h("input", { class: "ui-input", placeholder: t.typeName(name), "aria-label": t.typeName(name) }) : null;
    const ok = h("button", { class: "ui-btn ui-danger ui-sm", disabled: typed }, t.confirm);
    const go = async () => {
      if (ok.disabled) return;
      ok.disabled = true;
      await run();
      close();
    };
    if (input) {
      input.addEventListener("input", () => { ok.disabled = input.value.trim() !== name; });
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    }
    ok.addEventListener("click", go);
    const panel = h("div", { class: "ui-card ui-stack" },
      h("b", {}, question),
      risks.map((r) => h("div", { class: "ui-callout ui-warning" }, t.risk[r] || r)),
      input,
      h("div", { class: "ui-row", style: "gap:8px" }, ok, h("button", { class: "ui-btn ui-ghost ui-sm", onclick: close }, t.cancel)));
    queueMicrotask(() => (input || ok).focus());
    return panel;
  }

  function table(services) {
    const slot = h("div");
    const waiting = [];
    let busy = 0;
    const mine = generation;
    const queue = (job) => {  // at most 4 health requests at once, dropped when the table is rebuilt
      waiting.push(job);
      const next = () => {
        if (busy >= 4 || !waiting.length || !alive || mine !== generation) return;
        busy += 1;
        Promise.resolve().then(waiting.shift()).catch(() => {}).finally(() => { busy -= 1; next(); });
      };
      next();
    };
    const close = () => slot.replaceChildren();
    const deploy = (svc, again) => slot.replaceChildren(confirmPanel(svc,
      (again ? t.confirmRedeploy : t.confirmDeploy)(svc.name),
      async () => {
        try {
          await ctx.api("deploy", { method: "POST", body: { id: svc.id, again } });
          say(t.started(svc.name), "ui-success");
        } catch (e) { fail(e); }
      }, close));
    const act = async (svc, action) => {
      let deployment = null;
      const go = async () => {
        try {
          await ctx.api("action", { method: "POST", body: { id: svc.id, action, deployment } });
          say(t.doneAction[action](svc.name), "ui-success");
          setTimeout(() => { if (alive) load(); }, 4000);  // let the containers move before reading them again
        } catch (e) { fail(e); }
      };
      if (action === "stop") return slot.replaceChildren(confirmPanel(svc, t.confirmStop(svc.name), go, close, ["stopped"]));
      if (action === "start") return slot.replaceChildren(confirmPanel(svc, t.confirmStart(svc.name), go, close, []));
      try {  // rollback: say which deployment it goes back to before asking
        const d = await ctx.api(`rollback?id=${encodeURIComponent(svc.id)}`);
        deployment = d.deployment;  // the server refuses if the target moved since
        const risks = (svc.risks || ["unknown"]).filter((r) => r !== "no_rebuild");
        slot.replaceChildren(confirmPanel(svc, t.confirmRollback(svc.name, d.title || d.created || d.deployment), go, close, risks));
      } catch (e) { fail(e); }
    };
    const protect = async (svc, on) => {
      try { await ctx.api("protect", { method: "POST", body: { id: svc.id, on } }); load(); } catch (e) { fail(e); }
    };
    const rows = services.map((s) => {
      const deployable = s.kind === "application" || s.kind === "compose";
      const links = s.domains.map((d) => {
        const href = `${d.https ? "https" : "http"}://${d.host}${d.path !== "/" ? d.path : ""}`;
        return h("a", { class: "ui-link", href, target: "_blank", rel: "noopener noreferrer" }, d.host);
      });
      const writes = deployable && !s.protected ? [
        h("button", { class: "ui-btn ui-sm", onclick: () => deploy(s, false) }, t.deploy), " ",
        h("button", { class: "ui-btn ui-secondary ui-sm", onclick: () => deploy(s, true) }, t.redeploy), " ",
        s.kind === "application" && s.rollback_active ? [h("button", { class: "ui-btn ui-outline ui-sm", onclick: () => act(s, "rollback") }, t.rollback), " "] : null,
        h("button", { class: "ui-btn ui-outline ui-sm", onclick: () => act(s, "stop") }, t.stop), " ",
        h("button", { class: "ui-btn ui-outline ui-sm", onclick: () => act(s, "start") }, t.start), " ",
      ] : [];
      const last = s.last_deployment ?? s.status;
      const boxes = h("td", {}, deployable ? h("span", { class: "ui-skeleton", style: "display:inline-block;width:64px;height:1em" }) : "-");
      if (deployable) {
        queue(() => ctx.api(`health?id=${encodeURIComponent(s.id)}`).then((r) => {
          if (!alive) return;
          const count = r.state === "unknown" || r.expected === 0 ? "" : ` ${r.running}/${r.expected ?? r.containers.length}`;
          boxes.replaceChildren(h("span", {
            class: `ui-badge ${HEALTH[r.state] || "ui-outline"}`,
            title: r.containers.map((b) => `${b.name}: ${b.state}${b.status ? ` (${b.status})` : ""}`).join("\n"),
          }, `${t.health[r.state] || r.state}${count}`));
        }).catch(() => { if (alive) boxes.replaceChildren(h("span", { class: "ui-badge ui-outline" }, t.health.unknown)); }));
      }
      return h("tr", {},
        h("td", {}, h("span", { class: `ui-badge ${BADGE[last] || "ui-outline"}` }, last || "-")),
        boxes,
        h("td", {}, s.kind),
        h("td", {}, s.project + (s.environment ? ` / ${s.environment}` : "")),
        h("td", {}, h("b", {}, s.name), s.protected ? [" ", h("span", { class: "ui-badge ui-primary", title: t.protectedHelp }, t.protectedBadge)] : null),
        h("td", {}, links.length ? links.flatMap((a, i) => (i ? [" ", a] : [a])) : "-"),
        h("td", { style: "white-space:nowrap" }, deployable ? [
          ...writes,
          h("button", { class: "ui-btn ui-ghost ui-sm", onclick: () => slot.replaceChildren(logPanel(s, close)) }, t.logs), " ",
          h("button", { class: "ui-btn ui-outline ui-sm", title: t.protectedHelp, onclick: () => protect(s, !s.protected) },
            s.protected ? t.unprotect : t.protect),
        ] : ""));
    });
    if (!rows.length) return h("p", { class: "ui-empty" }, t.empty);
    return h("div", { class: "ui-stack" }, h("div", { class: "ui-table-wrap" }, h("table", { class: "ui-table" },
      h("thead", {}, h("tr", {}, t.cols.map((c) => h("th", {}, c)))), h("tbody", {}, rows))), slot);
  }

  function showSkill(state) {  // Claude Code reads a copy in the workspace: offer to refresh it
    skillBar.hidden = !t.skill[state];
    if (skillBar.hidden) return;
    const btn = h("button", { class: "ui-btn ui-sm", onclick: async () => {
      btn.disabled = true;
      try {
        const r = await ctx.api("skill", { method: "POST" });
        showSkill(r.skill);
        say(t.skillDone, "ui-success");
      } catch (e) { fail(e); btn.disabled = false; }
    } }, t.skillButton);
    skillBar.replaceChildren(h("span", {}, t.skill[state]), h("span", { class: "ui-spacer" }), state === "broken" ? null : btn);
  }

  let generation = 0;
  async function load() {
    generation += 1;
    body.replaceChildren(h("div", { class: "ui-skeleton", style: "height:120px" }));
    try {
      const st = await ctx.api("status");
      if (!alive) return;
      showSkill(st.skill);
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
