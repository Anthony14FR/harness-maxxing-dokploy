// Dokploy page: connect, then list projects, apps, stacks, databases and domains; deploy only after the user confirms.
const T = {
  en: {
    title: "Dokploy",
    intro: "Your Dokploy projects, apps and domains. Sessions deploy through it with the dokploy skill, asking you first.",
    keyMissing: "Add your Dokploy API key in Settings -> Keys as DOKPLOY_API_KEY, with “Expose to Harness sessions” left off. In Dokploy v0.30: Settings -> Profile (/dashboard/settings/profile), API/CLI Keys, Generate New Key; it is shown only once, copy it right away. Then check it here.",
    skill: {
      missing: "Claude sessions do not have the dokploy skill yet.",
      copied: "Claude sessions use a copy of the dokploy skill, which goes stale: link it instead, so it follows every update (the copy keeps working until then).",
      broken: "This extension's skill folder is empty: update the extension (git pull).",
      custom: "Claude sessions use your own dokploy skill folder (it holds your files): it is left as it is.",
      linked: "The dokploy skill of Claude sessions links to another folder: it is left as it is.",
    },
    skillButton: "Link the skill for sessions", skillDone: "Skill linked: Claude sessions now follow every update.",
    keyChanged: "DOKPLOY_API_KEY changed in Settings -> Keys: check it again before it is used.",
    url: "Dokploy address", check: "Check and connect", disconnect: "Disconnect", refresh: "Refresh",
    connected: "Connected to", projects: "projects", empty: "Nothing in Dokploy yet.",
    deploy: "Deploy", redeploy: "Rebuild", logs: "Last log", close: "Close",
    confirmDeploy: (n) => `Deploy ${n} now?`, confirmRedeploy: (n) => `Rebuild and redeploy ${n} now?`,
    started: (n) => `Deployment of ${n} started.`, noLog: "No deployment yet.",
    upd: {
      title: "Updates", check: "Check for updates", checking: "Checking…",
      ext: "This extension", dok: "Dokploy", har: "Harness Maxxing",
      upToDate: (v) => `Up to date (${v}).`, available: (a, b) => `${a} → ${b}`,
      update: "Update", harLink: "Open Settings → Updates",
      harText: "Harness updates itself, with its own checks and rollback, in Settings → Updates.",
      confirmExt: (a, b) => `Update this extension from ${a} to ${b}?`,
      confirmDok: (a, b) => `Update Dokploy from ${a} to ${b}?`,
      doneExt: (v) => `Extension updated to ${v}: the page reloads.`,
      doneDok: (v) => `Dokploy is updating to ${v}: its own page is back in about 2 minutes.`,
      state: {
        not_git: "Installed without git: update it the way it was installed.",
        unreachable: "The extension's repository cannot be reached right now.",
        no_upstream: "Its git folder follows no remote branch.",
        ahead: "Newer than its repository (a development copy): nothing to update.",
        bad_manifest: "Its manifest.json cannot be read.",
        dubious_owner: "git refuses its folder (owned by another user): see the README.",
      },
      blocked: "Not updated automatically:",
      blocker: {
        local_changes: "files of the extension were changed here",
        not_fast_forward: "its history differs from the repository",
        needs_newer_harness: "the new version needs a newer Harness: update Harness first",
        not_this_extension: "the repository now holds another extension",
        ci_failure: "the new version failed its tests",
        ci_pending: "the new version is still being tested: try again in a few minutes",
        ci_unknown: "the new version's tests cannot be checked (GitHub only, public repository)",
        ci_rate_limited: "GitHub limits checks for now: try again in an hour",
        bad_manifest: "the new version's manifest.json is not valid",
      },
    },
    cols: ["Last deployment", "Containers", "Kind", "Project", "Name", "Domains", ""],
    health: { ok: "running", partial: "partly down", down: "down", stopped: "stopped", unknown: "unknown" },
    risk: {
      downtime: "Its containers are stopped and started again: the site can be down for a few seconds.",
      no_rebuild: "It has no git source: nothing is rebuilt, the same image starts again.",
      unknown: "Dokploy did not give its details: assume the site can go down.",
      stopped: "The site stays down until you start it again.",
      dokploy_away: "Your sites stay up: Traefik and the apps keep running. Dokploy's own page and API are away for about 2 minutes.",
    },
    typeName: (n) => `Type ${n} to confirm`, confirm: "Confirm", cancel: "Cancel",
    stop: "Stop", start: "Start", rollback: "Roll back",
    confirmStop: (n) => `Stop ${n} now?`, confirmStart: (n) => `Start ${n} now?`,
    confirmRollback: (n, d) => `Roll ${n} back to “${d}”?`,
    doneAction: { stop: (n) => `${n} is stopping.`, start: (n) => `${n} is starting.`, rollback: (n) => `Rollback of ${n} started.` },
    protect: "Protect", unprotect: "Unprotect", protectedBadge: "protected",
    protectedHelp: "Protected: read-only here and for sessions. Only you can lift it, on this page.",
    routedHelp: "Routed by this compose's own Traefik labels, not a Dokploy domain",
  },
  fr: {
    title: "Dokploy",
    intro: "Vos projets, apps et domaines Dokploy. Les sessions déploient avec le skill dokploy, en vous demandant d’abord.",
    keyMissing: "Ajoutez votre clé API Dokploy dans Réglages -> Clés sous le nom DOKPLOY_API_KEY, avec « Fournir aux sessions Harness » désactivé. Dans Dokploy v0.30 : Settings -> Profile (/dashboard/settings/profile), API/CLI Keys, Generate New Key ; elle ne s’affiche qu’une fois, copiez-la tout de suite. Vérifiez-la ensuite ici.",
    skill: {
      missing: "Les sessions Claude n’ont pas encore le skill dokploy.",
      copied: "Les sessions Claude utilisent une copie du skill dokploy, qui se périme : liez-le plutôt, pour qu’il suive chaque mise à jour (la copie fonctionne d’ici là).",
      broken: "Le dossier du skill de cette extension est vide : mettez l’extension à jour (git pull).",
      custom: "Les sessions Claude utilisent votre propre dossier de skill dokploy (il contient vos fichiers) : il est laissé tel quel.",
      linked: "Le skill dokploy des sessions Claude pointe vers un autre dossier : il est laissé tel quel.",
    },
    skillButton: "Lier le skill pour les sessions", skillDone: "Skill lié : les sessions Claude suivent désormais chaque mise à jour.",
    keyChanged: "DOKPLOY_API_KEY a changé dans Réglages -> Clés : vérifiez-la à nouveau avant qu’elle serve.",
    url: "Adresse de Dokploy", check: "Vérifier et connecter", disconnect: "Déconnecter", refresh: "Actualiser",
    connected: "Connecté à", projects: "projets", empty: "Rien dans Dokploy pour l’instant.",
    deploy: "Déployer", redeploy: "Reconstruire", logs: "Dernier log", close: "Fermer",
    confirmDeploy: (n) => `Déployer ${n} maintenant ?`, confirmRedeploy: (n) => `Reconstruire et redéployer ${n} maintenant ?`,
    started: (n) => `Déploiement de ${n} lancé.`, noLog: "Aucun déploiement pour l’instant.",
    upd: {
      title: "Mises à jour", check: "Vérifier les mises à jour", checking: "Vérification…",
      ext: "Cette extension", dok: "Dokploy", har: "Harness Maxxing",
      upToDate: (v) => `À jour (${v}).`, available: (a, b) => `${a} → ${b}`,
      update: "Mettre à jour", harLink: "Ouvrir Réglages → Mises à jour",
      harText: "Harness se met à jour lui-même, avec ses vérifications et son retour arrière, dans Réglages → Mises à jour.",
      confirmExt: (a, b) => `Mettre à jour cette extension de ${a} vers ${b} ?`,
      confirmDok: (a, b) => `Mettre à jour Dokploy de ${a} vers ${b} ?`,
      doneExt: (v) => `Extension mise à jour en ${v} : la page se recharge.`,
      doneDok: (v) => `Dokploy passe en ${v} : sa propre page revient dans 2 minutes environ.`,
      state: {
        not_git: "Installée sans git : mettez-la à jour comme vous l’avez installée.",
        unreachable: "Le dépôt de l’extension est injoignable pour le moment.",
        no_upstream: "Son dossier git ne suit aucune branche distante.",
        ahead: "Plus récente que son dépôt (une copie de développement) : rien à mettre à jour.",
        bad_manifest: "Son manifest.json est illisible.",
        dubious_owner: "git refuse son dossier (il appartient à un autre utilisateur) : voir le README.",
      },
      blocked: "Pas de mise à jour automatique :",
      blocker: {
        local_changes: "des fichiers de l’extension ont été modifiés ici",
        not_fast_forward: "son historique diffère de celui du dépôt",
        needs_newer_harness: "la nouvelle version demande un Harness plus récent : mettez d’abord Harness à jour",
        not_this_extension: "le dépôt contient maintenant une autre extension",
        ci_failure: "la nouvelle version a échoué à ses tests",
        ci_pending: "la nouvelle version est encore en test : réessayez dans quelques minutes",
        ci_unknown: "les tests de la nouvelle version ne peuvent pas être vérifiés (GitHub uniquement, dépôt public)",
        ci_rate_limited: "GitHub limite les vérifications pour le moment : réessayez dans une heure",
        bad_manifest: "le manifest.json de la nouvelle version n’est pas valide",
      },
    },
    cols: ["Dernier déploiement", "Conteneurs", "Type", "Projet", "Nom", "Domaines", ""],
    health: { ok: "en marche", partial: "en partie arrêté", down: "en panne", stopped: "arrêté", unknown: "inconnu" },
    risk: {
      downtime: "Ses conteneurs sont arrêtés puis relancés : le site peut être coupé quelques secondes.",
      no_rebuild: "Il n’a pas de source git : rien n’est reconstruit, la même image redémarre.",
      unknown: "Dokploy n’a pas donné ses détails : considérez que le site peut être coupé.",
      stopped: "Le site reste coupé jusqu’à ce que vous le redémarriez.",
      dokploy_away: "Vos sites restent en ligne : Traefik et les apps continuent de tourner. La page et l’API de Dokploy sont absentes 2 minutes environ.",
    },
    typeName: (n) => `Tapez ${n} pour confirmer`, confirm: "Confirmer", cancel: "Annuler",
    stop: "Arrêter", start: "Démarrer", rollback: "Revenir en arrière",
    confirmStop: (n) => `Arrêter ${n} maintenant ?`, confirmStart: (n) => `Démarrer ${n} maintenant ?`,
    confirmRollback: (n, d) => `Revenir pour ${n} au déploiement « ${d} » ?`,
    doneAction: { stop: (n) => `${n} s’arrête.`, start: (n) => `${n} démarre.`, rollback: (n) => `Retour arrière de ${n} lancé.` },
    protect: "Protéger", unprotect: "Ne plus protéger", protectedBadge: "protégé",
    protectedHelp: "Protégé : en lecture seule ici et pour les sessions. Vous seul pouvez lever la protection, sur cette page.",
    routedHelp: "Routé par les labels Traefik de ce compose, pas par un domaine Dokploy",
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
  const updates = h("section", { class: "ui-card ui-stack" });
  el.replaceChildren(h("div", { class: "ui-page", style: "max-width:1100px" },
    h("h1", { class: "ui-h1" }, t.title), h("p", { class: "ui-muted" }, t.intro), notice, skillBar, body, updates));

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
    const typed = ["downtime", "unknown", "stopped", "dokploy_away"].some((r) => risks.includes(r));
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
      const link = (d, title) => {
        const href = `${d.https ? "https" : "http"}://${d.host}${d.path !== "/" ? d.path : ""}`;
        return h("a", { class: "ui-link", href, target: "_blank", rel: "noopener noreferrer", ...(title ? { title } : {}) }, d.host);
      };
      const spaced = (as) => (as.length ? as.flatMap((a, i) => (i ? [" ", a] : [a])) : "-");
      const links = s.domains.map((d) => link(d));
      const domains = h("td", {}, spaced(links));
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
          const routed = (r.routed || []).map((d) => link(d, t.routedHelp));  // a compose carrying its own Traefik routes
          if (routed.length) domains.replaceChildren(...[spaced([...links, ...routed])].flat());
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
        domains,
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
    skillBar.replaceChildren(h("span", {}, t.skill[state]), h("span", { class: "ui-spacer" }), ["missing", "copied"].includes(state) ? btn : null);
  }

  // Updates: a check changes nothing; each update runs only the exact version the user confirmed.
  function updatesPanel() {
    const u = t.upd;
    const out = h("div", { class: "ui-stack" });
    const slot = h("div");
    const btn = h("button", { class: "ui-btn ui-outline ui-sm", onclick: check }, u.check);
    updates.replaceChildren(h("div", { class: "ui-row", style: "flex-wrap:wrap;gap:8px" },
      h("h2", { class: "ui-h2" }, u.title), h("span", { class: "ui-spacer" }), btn), out, slot);
    const row = (label, ...rest) => h("div", { class: "ui-stack", style: "gap:4px" }, h("b", {}, label), ...rest);
    const run = (what, to, done) => async () => {
      try {
        const r = await ctx.api("update", { method: "POST", body: { what, to } });
        say(done(r.version), "ui-success");
        if (what === "extension") setTimeout(() => { if (alive) window.location.reload(); }, 2000);
      } catch (e) { fail(e); }
    };
    async function check() {
      btn.disabled = true;
      btn.textContent = u.checking;
      try {
        const r = await ctx.api("updates");
        if (!alive) return;
        const e = r.extension, d = r.dokploy;
        let ext;
        if (e.state === "up_to_date") ext = h("span", { class: "ui-muted" }, u.upToDate(e.current));
        else if (e.state === "available") {
          ext = [h("span", {}, u.available(e.current, e.new)), e.changes ? h("pre", { class: "ui-code", style: "max-height:240px;overflow:auto;white-space:pre-wrap" }, e.changes) : null,
            h("div", {}, h("button", { class: "ui-btn ui-sm", onclick: () => slot.replaceChildren(confirmPanel({ name: "extension" },
              u.confirmExt(e.current, e.new), run("extension", e.commit, u.doneExt), () => slot.replaceChildren(), [])) }, u.update))];
        } else if (e.state === "blocked") {
          ext = [h("span", {}, u.available(e.current, e.new || "?")), h("span", { class: "ui-muted" }, u.blocked),
            h("ul", { class: "ui-list" }, e.blockers.map((b) => h("li", {}, u.blocker[b] || b)))];
        } else ext = h("span", { class: "ui-muted" }, u.state[e.state] || e.state);
        let dok;
        if (d.error) dok = h("span", { class: "ui-muted" }, d.message);
        else if (!d.available) dok = h("span", { class: "ui-muted" }, u.upToDate(d.current || "?"));
        else dok = [h("span", {}, u.available(d.current || "?", d.latest)), h("div", {}, h("button", { class: "ui-btn ui-sm",
          onclick: () => slot.replaceChildren(confirmPanel({ name: "dokploy" }, u.confirmDok(d.current || "?", d.latest),
            run("dokploy", d.latest, u.doneDok), () => slot.replaceChildren(), ["dokploy_away"])) }, u.update))];
        out.replaceChildren(row(u.ext, ext), row(u.dok, dok), row(u.har, h("span", { class: "ui-muted" }, u.harText),
          h("div", {}, h("button", { class: "ui-btn ui-ghost ui-sm", onclick: () => ctx.navigate(r.harness) }, u.harLink))));
      } catch (e) { fail(e); }
      btn.disabled = false;
      btn.textContent = u.check;
    }
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

  updatesPanel();
  load();
  return () => { alive = false; };
}
