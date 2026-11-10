// Dokploy page: a dashboard of the whole Dokploy (updates on top, then tabs); every write asks the user first.
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
      title: "Updates", lead: "This extension, Dokploy and Harness: see what is new, update after you confirm.", check: "Check for updates", checkShort: "Check", checking: "Checking…",
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
    health: { ok: "Running", partial: "Partly down", down: "Down", stopped: "Stopped", unknown: "Unknown" },
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
    protect: "Protect", unprotect: "Unprotect", protectedBadge: "Protected",
    protectedHelp: "Protected: read-only here and for sessions. Only you can lift it, on this page.",
    routedHelp: "Routed by this compose's own Traefik labels, not a Dokploy domain",
    d: {
      tabs: { overview: "Overview", services: "Services", domains: "Domains", databases: "Databases", deployments: "Deployments", server: "Server" },
      tabsLabel: "Dokploy sections",
      subtitle: (url) => `Connected to ${url}`,
      unavailable: "Not available on this Dokploy version.",
      allGood: "Everything is running.",
      attention: "Needs your attention",
      issue: {
        svcError: (n) => `${n}: its last deployment failed.`,
        failed24: (n) => `${n} failed deployment${n > 1 ? "s" : ""} in the last 24 hours.`,
        infra: (k, s) => `${k}: ${s}.`,
        disk: (p) => `Disk ${p}% full.`,
        mem: (p) => `Memory ${p}% used.`,
        http: (n) => `${n} domain${n > 1 ? "s" : ""} served without HTTPS.`,
        queue: (n) => `${n} deployment${n > 1 ? "s" : ""} waiting in the queue.`,
      },
      stat: { services: "Services", projects: "Projects", domains: "Domains", deploys: "Deployments (24 h)", containers: "Containers" },
      statSub: {
        services: (r, e, i) => `${r} running · ${e} failed · ${i} idle`,
        projects: (n) => `${n} environment${n > 1 ? "s" : ""}`,
        domains: (h) => `${h} with HTTPS`,
        deploys: (ok, ko) => `${ok} done · ${ko} failed`,
        containers: (n) => `${n} running`,
      },
      res: { title: "Server resources", cpu: "CPU", cpus: (n, r) => `${n} cores${r ? ` · ${r} reserved` : ""}`, mem: "Memory", disk: "Disk", of: (a, b) => `${a} of ${b}` },
      recent: "Recent deployments", seeAll: "See all",
      search: "Search", searchSvc: "Service, project or domain", searchDom: "Domain or service",
      filter: { all: "All", problems: "Problems", failed: "Failed", running: "In progress" },
      noMatch: "Nothing matches.",
      more: "More", logsOf: (n) => `Logs of ${n}`,
      dom: { cols: ["Domain", "Service", "Project", "HTTPS", "Certificate", "Source"], dokploy: "Dokploy", labels: "Traefik labels", off: "off", disabled: "Disabled", none: "No domain yet." },
      db: { title: "Databases", backups: "Backups", none: "No database in Dokploy.", noBackup: "No backup scheduled: add one in Dokploy (a destination is needed).",
        cols: ["Database", "Engine", "Project", "Containers"], bcols: ["Service", "Database", "Schedule", "Keeps", "Last run", "Active"],
        keep: (n) => (n ? `${n} latest` : "all"), never: "never run" },
      dep: { cols: ["Service", "Status", "Deployment", "When", "Duration", ""], log: "Log", none: "No deployment yet.", backup: "backup", schedule: "scheduled job",
        queue: (n) => `${n} in the queue` },
      srv: { infra: "Infrastructure", postgres: "Dokploy database", traefik: "Traefik", ip: "Public IP", cleanup: "Log cleanup", cleanupOn: (c) => `On (${c})`, off: "Off",
        traefikVer: (v, r) => (r && r !== v ? `${v} · ${r} recommended` : v), docker: "Docker disk usage",
        dcols: ["Type", "Count", "Active", "Size", "Reclaimable"], servers: "Remote servers", noServers: "Only this server.",
        services: (n) => `${n} swarm services`, checked: (w) => `Checked ${w}`, healthy: "Healthy", outdated: "Update available", on: "On" },
      dashFailed: "The dashboard could not be read, only the services are shown:",
      st: { done: "Done", error: "Failed", running: "In progress", idle: "Idle", queued: "Queued", cancelled: "Cancelled" },
      kind: { application: "app", compose: "compose", postgres: "PostgreSQL", mysql: "MySQL", mariadb: "MariaDB", mongo: "MongoDB", redis: "Redis", libsql: "libSQL" },
    },
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
      title: "Mises à jour", lead: "Cette extension, Dokploy et Harness : voyez les nouveautés, mettez à jour après confirmation.", check: "Vérifier les mises à jour", checkShort: "Vérifier", checking: "Vérification…",
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
    health: { ok: "En marche", partial: "En partie arrêté", down: "En panne", stopped: "Arrêté", unknown: "Inconnu" },
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
    protect: "Protéger", unprotect: "Ne plus protéger", protectedBadge: "Protégé",
    protectedHelp: "Protégé : en lecture seule ici et pour les sessions. Vous seul pouvez lever la protection, sur cette page.",
    routedHelp: "Routé par les labels Traefik de ce compose, pas par un domaine Dokploy",
    d: {
      tabs: { overview: "Aperçu", services: "Services", domains: "Domaines", databases: "Bases", deployments: "Déploiements", server: "Serveur" },
      tabsLabel: "Sections Dokploy",
      subtitle: (url) => `Connecté à ${url}`,
      unavailable: "Indisponible sur cette version de Dokploy.",
      allGood: "Tout fonctionne.",
      attention: "À regarder",
      issue: {
        svcError: (n) => `${n} : son dernier déploiement a échoué.`,
        failed24: (n) => `${n} déploiement${n > 1 ? "s" : ""} en échec ces dernières 24 h.`,
        infra: (k, s) => `${k} : ${s}.`,
        disk: (p) => `Disque plein à ${p} %.`,
        mem: (p) => `Mémoire utilisée à ${p} %.`,
        http: (n) => `${n} domaine${n > 1 ? "s" : ""} servi${n > 1 ? "s" : ""} sans HTTPS.`,
        queue: (n) => `${n} déploiement${n > 1 ? "s" : ""} en attente.`,
      },
      stat: { services: "Services", projects: "Projets", domains: "Domaines", deploys: "Déploiements (24 h)", containers: "Conteneurs" },
      statSub: {
        services: (r, e, i) => `${r} en marche · ${e} en échec · ${i} inactif${i > 1 ? "s" : ""}`,
        projects: (n) => `${n} environnement${n > 1 ? "s" : ""}`,
        domains: (h) => `${h} en HTTPS`,
        deploys: (ok, ko) => `${ok} réussi${ok > 1 ? "s" : ""} · ${ko} en échec`,
        containers: (n) => `${n} en marche`,
      },
      res: { title: "Ressources du serveur", cpu: "Processeur", cpus: (n, r) => `${n} cœurs${r ? ` · ${r} réservés` : ""}`, mem: "Mémoire", disk: "Disque", of: (a, b) => `${a} sur ${b}` },
      recent: "Derniers déploiements", seeAll: "Tout voir",
      search: "Rechercher", searchSvc: "Service, projet ou domaine", searchDom: "Domaine ou service",
      filter: { all: "Tous", problems: "Problèmes", failed: "En échec", running: "En cours" },
      noMatch: "Aucun résultat.",
      more: "Plus", logsOf: (n) => `Logs de ${n}`,
      dom: { cols: ["Domaine", "Service", "Projet", "HTTPS", "Certificat", "Source"], dokploy: "Dokploy", labels: "Labels Traefik", off: "non", disabled: "Désactivé", none: "Aucun domaine pour l’instant." },
      db: { title: "Bases de données", backups: "Sauvegardes", none: "Aucune base de données dans Dokploy.", noBackup: "Aucune sauvegarde planifiée : ajoutez-en une dans Dokploy (il faut une destination).",
        cols: ["Base", "Moteur", "Projet", "Conteneurs"], bcols: ["Service", "Base", "Planification", "Conserve", "Dernière exécution", "Active"],
        keep: (n) => (n ? `${n} dernières` : "toutes"), never: "jamais exécutée" },
      dep: { cols: ["Service", "Statut", "Déploiement", "Quand", "Durée", ""], log: "Log", none: "Aucun déploiement pour l’instant.", backup: "sauvegarde", schedule: "tâche planifiée",
        queue: (n) => `${n} en attente` },
      srv: { infra: "Infrastructure", postgres: "Base de Dokploy", traefik: "Traefik", ip: "IP publique", cleanup: "Nettoyage des logs", cleanupOn: (c) => `Activé (${c})`, off: "Désactivé",
        traefikVer: (v, r) => (r && r !== v ? `${v} · ${r} recommandée` : v), docker: "Espace disque Docker",
        dcols: ["Type", "Nombre", "Actifs", "Taille", "Récupérable"], servers: "Serveurs distants", noServers: "Uniquement ce serveur.",
        services: (n) => `${n} services swarm`, checked: (w) => `Vérifié ${w}`, healthy: "Sain", outdated: "Mise à jour disponible", on: "Activée" },
      dashFailed: "Le tableau de bord n’a pas pu être lu, seuls les services sont affichés :",
      st: { done: "Réussi", error: "En échec", running: "En cours", idle: "Inactif", queued: "En attente", cancelled: "Annulé" },
      kind: { application: "app", compose: "compose", postgres: "PostgreSQL", mysql: "MySQL", mariadb: "MariaDB", mongo: "MongoDB", redis: "Redis", libsql: "libSQL" },
    },
  },
};

const BADGE = { done: "ui-success", running: "ui-warning", error: "ui-error", idle: "ui-outline", queued: "ui-outline", cancelled: "ui-outline" };
const HEALTH = { ok: "ui-success", partial: "ui-warning", down: "ui-error", stopped: "ui-outline", unknown: "ui-outline" };
const DB_KINDS = ["postgres", "mysql", "mariadb", "mongo", "redis", "libsql"];
const TABS = [
  ["overview", "layout-dashboard"], ["services", "app-window"], ["domains", "globe"],
  ["databases", "database"], ["deployments", "rocket"], ["server", "server"],
];
const DAY = 864e5;

// Scoped to .dk: the kit's tokens only (no new colors, no gradients); tables turn into cards on phones.
const CSS = `
.dk .dk-head{display:flex;flex-wrap:wrap;align-items:center;gap:12px}
.dk .dk-head-text{flex:1;min-width:200px}
.dk .dk-head-text p{margin:2px 0 0}
.dk .dk-tabs{display:flex;gap:2px;border-bottom:1px solid var(--border);overflow-x:auto;scrollbar-width:none;margin-top:4px}
.dk .dk-tabs::-webkit-scrollbar{display:none}
.dk .dk-tab{flex:none;display:inline-flex;align-items:center;gap:8px;padding:10px 12px;min-height:40px;border:0;background:none;color:var(--muted-foreground);
  font:inherit;font-size:14px;font-weight:500;white-space:nowrap;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;border-radius:6px 6px 0 0}
.dk .dk-tab:hover{color:var(--foreground)}
.dk .dk-tab{scroll-margin-top:72px}
.dk .dk-tab[aria-selected="true"]{color:var(--foreground);border-bottom-color:var(--primary)}
.dk .dk-tab:focus-visible{outline:2px solid var(--primary);outline-offset:-2px}
.dk .dk-tab svg,.dk .dk-ico svg{width:16px;height:16px;flex:none}
.dk .dk-count{font-size:12px;color:var(--muted-foreground);font-variant-numeric:tabular-nums}
.dk .dk-stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(130px,100%),1fr));gap:12px}
.dk .dk-stat{display:flex;flex-direction:column;gap:4px;padding:14px 16px}
.dk .dk-go{font:inherit;color:inherit;text-align:left;cursor:pointer;transition:border-color .15s}
.dk .dk-go:hover{border-color:color-mix(in oklab,var(--primary) 45%,var(--border))}
.dk .dk-go:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
.dk .dk-stat-top{display:flex;flex-wrap:wrap;align-items:flex-start;gap:4px 8px;color:var(--muted-foreground);font-size:13px;line-height:1.3;min-width:0}
.dk .dk-stat-top svg{margin-top:1px}
.dk .dk-stat-value{font-size:26px;font-weight:600;line-height:1.1;font-variant-numeric:tabular-nums}
.dk .dk-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr));gap:12px;align-items:start}
.dk .dk-cols>*{min-width:0}
.dk .dk-meter{display:grid;gap:6px}
.dk .dk-meter-row{display:flex;align-items:baseline;gap:8px;font-size:14px}
.dk .dk-meter-row b{font-weight:500}
.dk .dk-bar{height:8px;border-radius:999px;background:var(--muted);overflow:hidden}
.dk .dk-bar>span{display:block;height:100%;border-radius:inherit;background:var(--primary)}
.dk .dk-bar.dk-warn>span{background:var(--warning)}
.dk .dk-bar.dk-bad>span{background:var(--destructive)}
.dk .dk-kv{display:grid;grid-template-columns:minmax(120px,auto) 1fr;gap:8px 16px;margin:0;font-size:14px}
.dk .dk-kv dt{color:var(--muted-foreground)}
.dk .dk-kv dd{margin:0;min-width:0;overflow-wrap:anywhere}
.dk .dk-tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.dk .dk-tools .ui-input{flex:1;min-width:200px}
.dk .dk-chips{display:inline-flex;gap:4px;padding:3px;border:1px solid var(--border);border-radius:8px}
.dk .dk-chip{border:0;background:none;color:var(--muted-foreground);font:inherit;font-size:13px;padding:5px 10px;border-radius:6px;cursor:pointer;min-height:30px}
.dk .dk-chip[aria-pressed="true"]{background:var(--muted);color:var(--foreground)}
.dk .dk-chip:focus-visible,.dk summary:focus-visible{outline:2px solid var(--primary);outline-offset:1px}
.dk .dk-list{display:grid;gap:0;margin:0;padding:0;list-style:none}
.dk .dk-list li{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--border);min-width:0}
.dk .dk-list li:first-child{border-top:0}
.dk .dk-grow{flex:1;min-width:0}
.dk .dk-trunc{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dk .dk-sub{display:block;font-size:12px;color:var(--muted-foreground)}
.dk .dk-issues{margin:6px 0 0;padding-left:18px}
.dk .dk-actions{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
@media (min-width:721px){.dk .dk-svc .dk-actions{flex-wrap:nowrap;justify-content:flex-end}}
.dk .dk-actions .ui-btn svg{width:14px;height:14px}
.dk details.dk-more{position:relative}
.dk details.dk-more>summary{list-style:none}
.dk details.dk-more>summary::-webkit-details-marker{display:none}
.dk .dk-menu{position:absolute;right:0;top:calc(100% + 4px);z-index:20;display:grid;gap:2px;min-width:180px;padding:6px;
  background:var(--card);border:1px solid var(--border);border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.18)}
.dk .dk-menu .ui-btn{justify-content:flex-start;width:100%}
.dk .dk-upd{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.dk .dk-upd .dk-grow{flex:1 1 260px}
.dk .dk-short{display:none}
.dk .dk-md{max-height:260px;overflow:auto;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--muted);font-size:13px;line-height:1.5}
.dk .dk-md>:first-child{margin-top:0}
.dk .dk-md-h{margin:12px 0 4px;font-size:13px;font-weight:600}
.dk .dk-md-ul{margin:0 0 4px;padding-left:18px;list-style:disc}
.dk .dk-md-ul li{margin:3px 0}
.dk .dk-md p{margin:4px 0}
.dk .dk-md-code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;padding:0 4px;border-radius:4px;background:var(--background)}
@media (max-width:720px){.dk .dk-upd .dk-grow{order:3;flex-basis:100%}.dk .dk-upd>.ui-btn{order:4}.dk .dk-stat-value{font-size:22px}}
.dk .ui-table td{vertical-align:middle}
.dk .ui-num{white-space:nowrap}
@media (max-width:720px){
  .dk .dk-rt thead{display:none}
  .dk .dk-rt,.dk .dk-rt tbody,.dk .dk-rt tr,.dk .dk-rt td{display:block;width:100%}
  .dk .dk-rt tr{border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:10px}
  .dk .dk-rt td{border:0;padding:4px 0;display:flex;gap:4px 12px;align-items:center;flex-wrap:wrap;overflow-wrap:anywhere;min-width:0}
  .dk .dk-rt td>*{min-width:0}
  .dk .dk-rt .dk-actions{width:100%}
  .dk .dk-rt .dk-actions>*{flex:1 1 84px;justify-content:center}
  .dk .dk-rt .dk-actions>details>summary{width:100%;justify-content:center}
  .dk .dk-list li{flex-wrap:wrap}
  .dk .dk-list li>time{margin-left:auto}
  .dk .dk-tools .ui-input{min-width:0;flex-basis:100%}
  .dk .dk-rt td[data-label]::before{content:attr(data-label);color:var(--muted-foreground);font-size:12px;min-width:96px}
  .dk .dk-rt td.dk-name{font-size:15px}
  .dk .ui-table-wrap{overflow:visible}
  .dk .dk-kv{grid-template-columns:1fr}
  .dk .dk-kv dd{margin-bottom:6px}
}
@media (pointer:coarse){.dk .dk-rt a.ui-link,.dk .dk-list a.ui-link{display:inline-flex;align-items:center;min-height:44px}.dk .ui-btn,.dk .dk-chip,.dk .dk-tab,.dk summary.ui-btn{min-height:44px}.dk .dk-tab{min-width:44px;justify-content:center}}
@media (max-width:520px){
  .dk .dk-tabs{gap:0}
  .dk .dk-tab{padding:10px 8px}
  .dk .dk-tab[aria-selected="false"] .dk-tab-label,.dk .dk-tab[aria-selected="false"] .dk-count{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
  .dk .dk-head .ui-row{width:100%;justify-content:flex-end}
  .dk .dk-chips{width:100%}.dk .dk-chip{flex:1}
  .dk .dk-upd .dk-grow{display:none}.dk .dk-upd>.ui-btn{order:0;margin-left:auto}
  .dk .dk-upd .dk-long{display:none}.dk .dk-upd .dk-short{display:inline}
}
@media (prefers-reduced-motion:no-preference){.dk .dk-bar>span{transition:width .4s ease}}
`;

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

// **bold**, `code` and [text](https://…) of a changelog line, as nodes; any other link target stays plain text.
function inline(text) {
  const out = [];
  const rx = /\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)/g;
  let last = 0;
  for (const m of text.matchAll(rx)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1] != null) out.push(h("strong", {}, m[1]));
    else if (m[2] != null) out.push(h("code", { class: "dk-md-code" }, m[2]));
    else if (/^https?:\/\//i.test(m[4])) out.push(h("a", { class: "ui-link", href: m[4], target: "_blank", rel: "noopener noreferrer" }, m[3]));
    else out.push(m[3]);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

// The CHANGELOG sections of an update: "## 1.4.1 - date" headings, "- " bullets whose wrapped lines continue them.
function markdown(text) {
  const root = h("div", { class: "dk-md" });
  let list = null, item = null, para = null;
  for (const raw of String(text).split("\n")) {
    const line = raw.replace(/\s+$/, "");
    const head = line.match(/^#{1,6}\s+(.*)$/);
    const bullet = line.match(/^(\s*)[-*]\s+(.*)$/);
    if (!line.trim()) { list = item = para = null; continue; }
    if (head) {
      list = item = para = null;
      root.append(h("h4", { class: "dk-md-h" }, inline(head[1])));
    } else if (bullet) {
      para = null;
      if (!list) root.append(list = h("ul", { class: "dk-md-ul" }));
      list.append(item = h("li", {}, inline(bullet[2])));
    } else if (item && /^\s/.test(line)) {
      item.append(" ", ...inline(line.trim()));
    } else if (para) {
      para.append(" ", ...inline(line.trim()));
    } else {
      list = item = null;
      root.append(para = h("p", {}, inline(line.trim())));
    }
  }
  return root;
}

export function mount(el, ctx) {
  const t = T[ctx.lang] || T.en;
  const d = t.d;
  const loc = ctx.lang === "fr" ? "fr-FR" : "en-US";
  let alive = true;
  const icon = (name) => {  // ctx.icon exists since the UI kit; older Harness simply shows no icon
    try { const s = ctx.icon ? ctx.icon(name) : null; if (s) s.setAttribute("aria-hidden", "true"); return s; } catch { return null; }
  };
  const store = {  // remembers the tab in this browser only; private windows simply start on Overview
    get: (k) => { try { return sessionStorage.getItem(`dokploy.${k}`); } catch { return null; } },
    set: (k, v) => { try { sessionStorage.setItem(`dokploy.${k}`, v); } catch { /* ignored */ } },
  };

  // ---- formatting
  const nf = new Intl.NumberFormat(loc, { maximumFractionDigits: 1 });
  const bytes = (n) => {
    if (n == null) return "–";
    const u = ctx.lang === "fr" ? ["o", "Ko", "Mo", "Go", "To"] : ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i += 1; }
    return `${nf.format(n)} ${u[i]}`;
  };
  const rtf = new Intl.RelativeTimeFormat(loc, { numeric: "auto" });
  const date = (s) => { const x = s ? new Date(s) : null; return x && !Number.isNaN(+x) ? x : null; };
  const ago = (s) => {
    const x = date(s);
    if (!x) return "–";
    const sec = (x - Date.now()) / 1000;
    for (const [u, n] of [["day", 86400], ["hour", 3600], ["minute", 60]]) if (Math.abs(sec) >= n) return rtf.format(Math.round(sec / n), u);
    return rtf.format(Math.round(sec), "second");
  };
  const full = (s) => { const x = date(s); return x ? x.toLocaleString(loc) : ""; };
  const dur = (a, b) => {
    const x = date(a), y = date(b);
    if (!x || !y || y < x) return "–";
    const s = Math.round((y - x) / 1000);
    return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")} s`;
  };
  const pct = (a, b) => (a != null && b ? Math.round((a / b) * 100) : null);
  const status = (s) => h("span", { class: `ui-badge ${BADGE[s] || "ui-outline"}` }, d.st[s] || s || "–");

  // ---- shell
  const style = h("style", {}, CSS);
  const notice = h("div", { class: "ui-callout", hidden: true, role: "status" });
  const skillBar = h("div", { class: "ui-callout ui-warning ui-row", hidden: true, style: "flex-wrap:wrap;gap:8px" });
  const headBtns = h("div", { class: "ui-row", style: "gap:8px" });
  const subtitle = h("p", { class: "ui-muted ui-small" }, t.intro);
  const updates = h("section", { class: "ui-card ui-stack", "aria-labelledby": "dk-upd-title" });
  const body = h("div", { class: "ui-stack" });
  el.replaceChildren(style, h("div", { class: "ui-page dk ui-stack", style: "max-width:1200px" },
    h("header", { class: "dk-head" },
      h("span", { class: "ui-icon-box ui-lg" }, icon("rocket")),
      h("div", { class: "dk-head-text" }, h("h1", { class: "ui-h1" }, t.title), subtitle),
      headBtns),
    notice, skillBar, updates, body));

  const say = (text, kind = "ui-info") => {
    notice.className = `ui-callout ${kind}`;
    notice.setAttribute("role", kind === "ui-error" ? "alert" : "status");
    notice.textContent = text;
    notice.hidden = !text;
  };
  const fail = (e) => say(e && e.message ? e.message : String(e), "ui-error");
  const card = (title, iconName, ...content) => h("section", { class: "ui-card ui-stack" },
    title ? h("div", { class: "ui-row", style: "gap:8px;align-items:center" }, iconName ? h("span", { class: "dk-ico ui-muted" }, icon(iconName)) : null,
      h("h2", { class: "ui-h3" }, title)) : null, ...content);
  const empty = (text, iconName = "info") => h("div", { class: "ui-empty" }, icon(iconName), h("p", {}, text));
  const missing = () => h("p", { class: "ui-muted ui-small" }, d.unavailable);
  const btn = (label, iconName, onclick, cls = "ui-btn ui-outline ui-sm", extra = {}) =>
    h("button", { class: cls, type: "button", onclick, ...extra }, iconName ? icon(iconName) : null, label);
  const table = (cols, rows, cls = "") => h("div", { class: "ui-table-wrap" }, h("table", { class: `ui-table dk-rt ${cls}` },
    h("thead", {}, h("tr", {}, cols.map((c) => h("th", { scope: "col" }, c)))), h("tbody", {}, rows)));
  const td = (label, ...content) => h("td", label ? { "data-label": label } : {}, ...content);
  const meter = (label, used, total, text) => {
    const p = pct(used, total);
    const cls = p == null ? "" : p >= 90 ? "dk-bad" : p >= 80 ? "dk-warn" : "";
    return h("div", { class: "dk-meter" },
      h("div", { class: "dk-meter-row" }, h("b", {}, label), h("span", { class: "ui-spacer" }),
        h("span", { class: "ui-muted ui-num" }, text || (p == null ? "–" : `${d.res.of(bytes(used), bytes(total))} · ${p} %`))),
      p == null ? null : h("div", { class: `dk-bar ${cls}`, role: "progressbar", "aria-label": label, "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(p) },
        h("span", { style: `width:${Math.min(100, p)}%` })));
  };
  const link = (dm, title) => {  // a host that is not a plain DNS name stays text: no user@host or odd URL from data
    const host = String(dm.host || "");
    if (!/^[a-z0-9*]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$/i.test(host) || host.includes("*")) return h("span", {}, host);
    const path = typeof dm.path === "string" && dm.path.startsWith("/") && dm.path !== "/" ? dm.path : "";
    const href = `${dm.https ? "https" : "http"}://${host}${path}`;
    return h("a", { class: "ui-link", href, target: "_blank", rel: "noopener noreferrer", ...(title ? { title } : {}) }, host);
  };
  const spaced = (as) => (as.length ? as.flatMap((a, i) => (i ? [" ", a] : [a])) : "-");

  // ---- skill, connect, logs, confirmations (unchanged behavior)
  function connectForm(st) {
    const input = h("input", { class: "ui-input", name: "url", value: st.url || "http://127.0.0.1:3000", style: "flex:1", "aria-label": t.url });
    const b = h("button", { class: "ui-btn", type: "submit", disabled: !st.key_present }, t.check);
    return h("form", { class: "ui-card ui-stack", onsubmit: async (ev) => {
      ev.preventDefault();
      b.disabled = true;
      try {
        const r = await ctx.api("connect", { method: "POST", body: { url: input.value.trim() } });
        say(`${t.connected} ${r.url} (${r.projects} ${t.projects})`, "ui-success");
        load();
      } catch (e) { fail(e); b.disabled = false; }
    } }, h("label", { class: "ui-label" }, t.url), h("div", { class: "ui-row" }, input, b));
  }

  function logPanel(title, path, close) {
    const pre = h("pre", { class: "ui-code", style: "max-height:420px;overflow:auto;white-space:pre-wrap", tabindex: "0", "aria-label": title }, "…");
    ctx.api(path).then((r) => { if (alive) pre.textContent = r.log || t.noLog; })
      .catch((e) => { if (alive) pre.textContent = e.code === "not_found" ? t.noLog : e.message; });
    const closeBtn = btn(t.close, "x", close, "ui-btn ui-ghost ui-sm");
    queueMicrotask(() => closeBtn.focus());
    return h("div", { class: "ui-card ui-stack" }, h("div", { class: "ui-row" }, h("b", {}, title), h("span", { class: "ui-spacer" }), closeBtn), pre);
  }

  // Inline confirmation: a possible downtime asks to type the service name, never a single OK.
  function confirmPanel(svc, question, run, close, risks = svc.risks || ["unknown"]) {
    const typed = ["downtime", "unknown", "stopped", "dokploy_away"].some((r) => risks.includes(r));
    const name = String(svc.name).trim();
    const input = typed ? h("input", { class: "ui-input", placeholder: t.typeName(name), "aria-label": t.typeName(name) }) : null;
    const ok = h("button", { class: "ui-btn ui-danger ui-sm", type: "button", disabled: typed }, t.confirm);
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
    const panel = h("div", { class: "ui-card ui-stack", role: "group", "aria-label": question },
      h("b", {}, question),
      risks.map((r) => h("div", { class: "ui-callout ui-warning" }, t.risk[r] || r)),
      input,
      h("div", { class: "ui-row", style: "gap:8px" }, ok, h("button", { class: "ui-btn ui-ghost ui-sm", type: "button", onclick: close }, t.cancel)));
    queueMicrotask(() => (input || ok).focus());
    return panel;
  }

  function showSkill(state) {  // Claude Code reads the skill from the workspace: offer to link it
    skillBar.hidden = !t.skill[state];
    if (skillBar.hidden) return;
    const b = h("button", { class: "ui-btn ui-sm", type: "button", onclick: async () => {
      b.disabled = true;
      try {
        const r = await ctx.api("skill", { method: "POST" });
        showSkill(r.skill);
        say(t.skillDone, "ui-success");
      } catch (e) { fail(e); b.disabled = false; }
    } }, t.skillButton);
    skillBar.replaceChildren(h("span", {}, t.skill[state]), h("span", { class: "ui-spacer" }), ["missing", "copied"].includes(state) ? b : null);
  }

  // Updates, on top: a check changes nothing; each update runs only the exact version the user confirmed.
  function updatesPanel() {
    const u = t.upd;
    const out = h("div", { class: "ui-stack", hidden: true });
    const slot = h("div");
    const label = (long, short) => [h("span", { class: "dk-long" }, long), h("span", { class: "dk-short", "aria-hidden": "true" }, short)];
    const b = h("button", { class: "ui-btn ui-outline ui-sm", type: "button", onclick: check, "aria-label": u.check }, icon("refresh-cw"), label(u.check, u.checkShort));
    const setLabel = (long, short) => { b.replaceChildren(icon("refresh-cw"), label(long, short)); b.setAttribute("aria-label", long); };
    const line = h("span", { class: "ui-muted ui-small dk-grow" }, u.lead);
    updates.replaceChildren(h("div", { class: "dk-upd" },
      h("span", { class: "ui-icon-box ui-neutral" }, icon("download")),
      h("h2", { class: "ui-h3", id: "dk-upd-title" }, u.title), line, b), out, slot);
    const row = (label, ...rest) => h("div", { class: "ui-stack", style: "gap:4px" }, h("b", {}, label), ...rest);
    const run = (what, to, done) => async () => {
      try {
        const r = await ctx.api("update", { method: "POST", body: { what, to } });
        say(done(r.version), "ui-success");
        if (what === "extension") setTimeout(() => { if (alive) window.location.reload(); }, 2000);
      } catch (e) { fail(e); }
    };
    async function check() {
      b.disabled = true;
      setLabel(u.checking, u.checking);
      b.setAttribute("aria-busy", "true");
      try {
        const r = await ctx.api("updates");
        if (!alive) return;
        const e = r.extension, dk = r.dokploy;
        let ext;
        if (e.state === "up_to_date") ext = h("span", { class: "ui-muted" }, u.upToDate(e.current));
        else if (e.state === "available") {
          ext = [h("span", {}, u.available(e.current, e.new)), e.changes ? markdown(e.changes) : null,
            h("div", {}, btn(u.update, "download", () => slot.replaceChildren(confirmPanel({ name: "extension" },
              u.confirmExt(e.current, e.new), run("extension", e.commit, u.doneExt), () => slot.replaceChildren(), [])), "ui-btn ui-sm"))];
        } else if (e.state === "blocked") {
          ext = [h("span", {}, u.available(e.current, e.new || "?")), h("span", { class: "ui-muted" }, u.blocked),
            h("ul", { class: "ui-list" }, e.blockers.map((x) => h("li", {}, u.blocker[x] || x)))];
        } else ext = h("span", { class: "ui-muted" }, u.state[e.state] || e.state);
        let dok;
        if (dk.error) dok = h("span", { class: "ui-muted" }, dk.message);
        else if (!dk.available) dok = h("span", { class: "ui-muted" }, u.upToDate(dk.current || "?"));
        else dok = [h("span", {}, u.available(dk.current || "?", dk.latest)), h("div", {}, btn(u.update, "download",
          () => slot.replaceChildren(confirmPanel({ name: "dokploy" }, u.confirmDok(dk.current || "?", dk.latest),
            run("dokploy", dk.latest, u.doneDok), () => slot.replaceChildren(), ["dokploy_away"])), "ui-btn ui-sm"))];
        out.hidden = false;
        out.replaceChildren(h("div", { class: "dk-cols" }, row(u.ext, ext), row(u.dok, dok),
          row(u.har, h("div", {}, btn(u.harLink, "settings", () => ctx.navigate(r.harness), "ui-btn ui-ghost ui-sm")))));
      } catch (err) { fail(err); }
      b.disabled = false;
      b.removeAttribute("aria-busy");
      setLabel(u.check, u.checkShort);
    }
  }

  // ---- data
  let generation = 0;
  let services = [];   // project.all completed (the actions need it)
  let dash = null;     // the whole Dokploy at once (dashboard route)
  const healthCache = new Map();
  let tab = TABS.some(([k]) => k === store.get("tab")) ? store.get("tab") : "overview";
  const panels = new Map();
  const tabBtns = new Map();

  function tabsBar() {
    const bar = h("div", { class: "dk-tabs", role: "tablist", "aria-label": d.tabsLabel });
    const keys = TABS.map(([k]) => k);
    for (const [k, ic] of TABS) {
      const count = h("span", { class: "dk-count" });
      const b = h("button", {
        class: "dk-tab", role: "tab", type: "button", id: `dk-tab-${k}`, "aria-controls": `dk-panel-${k}`,
        "aria-selected": String(k === tab), tabindex: k === tab ? "0" : "-1",
        onclick: () => select(k),
        onkeydown: (e) => {  // arrows move between tabs, as in any tab list
          const i = keys.indexOf(k);
          const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: keys.length - 1 }[e.key];
          if (next == null) return;
          e.preventDefault();
          const to = keys[(next + keys.length) % keys.length];
          select(to);
          tabBtns.get(to).focus();
        },
      }, icon(ic), h("span", { class: "dk-tab-label" }, d.tabs[k]), " ", count);
      b.count = count;
      tabBtns.set(k, b);
      bar.append(b);
    }
    return bar;
  }

  function select(k) {
    tab = k;
    store.set("tab", k);
    for (const [key, b] of tabBtns) {
      b.setAttribute("aria-selected", String(key === k));
      b.tabIndex = key === k ? 0 : -1;
    }
    for (const [key, p] of panels) p.hidden = key !== k;
    tabBtns.get(k)?.scrollIntoView({ block: "nearest", inline: "nearest" });  // a phone shows the chosen tab whole
    render(k);
  }

  const rendered = new Set();
  function render(k, force = false) {
    if (!force && rendered.has(k)) return;
    rendered.add(k);
    const p = panels.get(k);
    const view = { overview, services: servicesView, domains, databases, deployments, server }[k];
    try { p.replaceChildren(view()); } catch (e) { p.replaceChildren(h("div", { class: "ui-callout ui-error" }, String(e.message || e))); }
  }

  function counts() {
    const set = (k, n) => { const b = tabBtns.get(k); if (b) b.count.textContent = n == null ? "" : String(n); };
    set("services", services.length);
    set("domains", dash?.domains?.length);
    set("databases", services.filter((s) => DB_KINDS.includes(s.kind)).length);
    set("deployments", dash?.deployments?.length);
  }

  // ---- Overview
  function issues() {
    const out = [];
    for (const s of services) if (s.last_deployment === "error") out.push(d.issue.svcError(s.name));
    const since = Date.now() - DAY;
    const failed = (dash?.deployments || []).filter((x) => x.status === "error" && (date(x.created) || 0) > since).length;
    if (failed) out.push(d.issue.failed24(failed));
    for (const [k, s] of Object.entries(dash?.infra || {})) if (s && !["healthy", "running", "ok"].includes(String(s).toLowerCase())) out.push(d.issue.infra(k === "postgres" ? d.srv.postgres : k === "traefik" ? d.srv.traefik : k, s));
    const r = dash?.resources;
    const dp = pct(r?.disk_used, r?.disk_total), mp = pct(r?.mem_used, r?.mem_total);
    if (dp >= 85) out.push(d.issue.disk(dp));
    if (mp >= 90) out.push(d.issue.mem(mp));
    const http = (dash?.domains || []).filter((x) => !x.https && x.enabled !== false).length;
    if (http) out.push(d.issue.http(http));
    if (dash?.queue) out.push(d.issue.queue(dash.queue));
    return out;
  }

  function stat(iconName, label, value, sub, to) {
    const inner = [h("span", { class: "dk-stat-top" }, icon(iconName), label), h("span", { class: "dk-stat-value" }, value == null ? "–" : String(value)),
      sub ? h("span", { class: "ui-muted ui-small" }, sub) : null];
    return to ? h("button", { class: "ui-card dk-stat dk-go", type: "button", onclick: () => select(to) }, inner)
      : h("div", { class: "ui-card dk-stat" }, inner);
  }

  function overview() {
    const st = dash?.stats, r = dash?.resources;
    const list = issues();
    const since = Date.now() - DAY;
    const deps24 = (dash?.deployments || []).filter((x) => (date(x.created) || 0) > since);
    const doms = dash?.domains || [];
    const running = (dash?.containers || []).filter((c) => c.state === "running").length;
    const health = list.length
      ? h("div", { class: "ui-callout ui-warning", role: "status" }, h("div", {}, h("b", {}, d.attention), h("ul", { class: "dk-issues" }, list.map((x) => h("li", {}, x)))))
      : h("div", { class: "ui-callout ui-success", role: "status" }, d.allGood);
    const stats = h("div", { class: "dk-stats" },
      stat("app-window", d.stat.services, st?.services ?? services.filter((s) => !DB_KINDS.includes(s.kind)).length,
        st ? d.statSub.services(st.status?.running ?? 0, st.status?.error ?? 0, st.status?.idle ?? 0) : null, "services"),
      stat("layers", d.stat.projects, st?.projects, st ? d.statSub.projects(st.environments ?? 0) : null),
      stat("globe", d.stat.domains, dash?.domains ? doms.length : null, dash?.domains ? d.statSub.domains(doms.filter((x) => x.https).length) : null, "domains"),
      stat("rocket", d.stat.deploys, dash?.deployments ? deps24.length : null,
        dash?.deployments ? d.statSub.deploys(deps24.filter((x) => x.status === "done").length, deps24.filter((x) => x.status === "error").length) : null, "deployments"),
      stat("package", d.stat.containers, dash?.containers ? dash.containers.length : null, dash?.containers ? d.statSub.containers(running) : null, "server"));
    const res = r ? card(d.res.title, "gauge",
      meter(d.res.cpu, null, null, r.cpus != null ? d.res.cpus(r.cpus, r.cpu_reserved) : "–"),
      meter(d.res.mem, r.mem_used, r.mem_total), meter(d.res.disk, r.disk_used, r.disk_total)) : card(d.res.title, "gauge", missing());
    const recent = card(d.recent, "rocket",
      dash?.deployments ? (dash.deployments.length ? h("ul", { class: "dk-list" }, dash.deployments.slice(0, 6).map(depItem)) : empty(d.dep.none))
        : missing(),
      dash?.deployments?.length ? h("div", {}, btn(d.seeAll, "arrow-right", () => select("deployments"), "ui-btn ui-ghost ui-sm")) : null);
    return h("div", { class: "ui-stack" }, health, stats, h("div", { class: "dk-cols" }, res, recent));
  }

  function depItem(x) {
    return h("li", {}, status(x.status),
      h("span", { class: "dk-grow" }, h("span", { class: "dk-trunc", style: "display:block" }, h("b", {}, x.service || d.dep[x.kind] || "–"), x.title ? ` · ${x.title}` : ""),
        x.error ? h("span", { class: "dk-sub dk-trunc" }, x.error) : null),
      h("time", { class: "ui-muted ui-small", datetime: x.created || "", title: full(x.created) }, ago(x.created)));
  }

  // ---- Services (the table of 1.x, searchable, cards on phones)
  function servicesView() {
    const slot = h("div");
    const close = () => slot.replaceChildren();
    let q = "", only = "all";
    const listSlot = h("div");
    const search = h("input", { class: "ui-input", type: "search", placeholder: d.searchSvc, "aria-label": d.search,
      oninput: () => { q = search.value.trim().toLowerCase(); draw(); } });
    const chips = chipGroup([["all", d.filter.all], ["problems", d.filter.problems]], (v) => { only = v; draw(); });
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
        const r = await ctx.api(`rollback?id=${encodeURIComponent(svc.id)}`);
        deployment = r.deployment;  // the server refuses if the target moved since
        const risks = (svc.risks || ["unknown"]).filter((x) => x !== "no_rebuild");
        slot.replaceChildren(confirmPanel(svc, t.confirmRollback(svc.name, r.title || r.created || r.deployment), go, close, risks));
      } catch (e) { fail(e); }
    };
    const protect = async (svc, on) => {
      try { await ctx.api("protect", { method: "POST", body: { id: svc.id, on } }); load(); } catch (e) { fail(e); }
    };
    const healthOf = (s) => {  // one request per service, cached for the page's life (Refresh clears it)
      if (!healthCache.has(s.id)) healthCache.set(s.id, ctx.api(`health?id=${encodeURIComponent(s.id)}`));
      return healthCache.get(s.id);
    };
    const queue = [];
    let busy = 0;
    const mine = generation;
    const next = () => {  // at most 4 health requests at once
      if (busy >= 4 || !queue.length || !alive || mine !== generation) return;
      busy += 1;
      Promise.resolve().then(queue.shift()).catch(() => {}).finally(() => { busy -= 1; next(); });
    };
    const row = (s) => {
      const deployable = s.kind === "application" || s.kind === "compose";
      const links = (s.domains || []).map((x) => link(x));
      const domCell = td(t.cols[5], spaced(links));
      const boxes = td(t.cols[1], deployable ? h("span", { class: "ui-skeleton", style: "display:inline-block;width:64px;height:1em" }) : dbBoxes(s));
      if (deployable) {
        queue.push(() => healthOf(s).then((r) => {
          if (!alive) return;
          if (only !== "all") queueMicrotask(draw);  // the Problems filter needs the states that just arrived
          const routed = (r.routed || []).map((x) => link(x, t.routedHelp));
          if (routed.length) domCell.replaceChildren(...[spaced([...links, ...routed])].flat());
          const count = r.state === "unknown" || r.expected === 0 ? "" : ` ${r.running}/${r.expected ?? r.containers.length}`;
          boxes.replaceChildren(h("span", {
            class: `ui-badge ${HEALTH[r.state] || "ui-outline"}`,
            "data-state": r.state,  // the Problems filter reads it, not the translated text
            title: r.containers.map((b) => `${b.name}: ${b.state}${b.status ? ` (${b.status})` : ""}`).join("\n"),
          }, `${t.health[r.state] || r.state}${count}`));
        }).catch(() => { if (alive) boxes.replaceChildren(h("span", { class: "ui-badge ui-outline" }, t.health.unknown)); }));
      }
      const last = s.last_deployment ?? s.status;
      const more = deployable ? h("details", { class: "dk-more" },
        h("summary", { class: "ui-btn ui-ghost ui-sm", "aria-label": `${d.more}: ${s.name}` }, d.more),
        h("div", { class: "dk-menu", role: "group", "aria-label": s.name },
          !s.protected ? [
            btn(t.redeploy, "hammer", () => deploy(s, true), "ui-btn ui-ghost ui-sm"),
            s.kind === "application" && s.rollback_active ? btn(t.rollback, "refresh-cw", () => act(s, "rollback"), "ui-btn ui-ghost ui-sm") : null,
            btn(t.stop, "x", () => act(s, "stop"), "ui-btn ui-ghost ui-sm"),
            btn(t.start, "check", () => act(s, "start"), "ui-btn ui-ghost ui-sm"),
          ] : null,
          btn(s.protected ? t.unprotect : t.protect, "shield", () => protect(s, !s.protected), "ui-btn ui-ghost ui-sm", { title: t.protectedHelp }))) : null;
      if (more) {
        more.addEventListener("click", (e) => { if (e.target.closest(".dk-menu button")) more.open = false; });
        more.place = () => {  // fixed, so the table's scroll box never clips it; flips up near the bottom
          const menu = more.querySelector(".dk-menu");
          const r = more.firstChild.getBoundingClientRect();
          const below = window.innerHeight - r.bottom > menu.offsetHeight + 12;
          Object.assign(menu.style, { position: "fixed", right: `${Math.max(8, window.innerWidth - r.right)}px`,
            top: below ? `${r.bottom + 4}px` : "auto", bottom: below ? "auto" : `${window.innerHeight - r.top + 4}px` });
        };
        more.addEventListener("toggle", () => {
          if (!more.open) return;
          more.place();
          more.querySelector(".dk-menu button")?.focus({ preventScroll: true });
        });
      }
      return h("tr", {},
        td(null, h("span", { class: "dk-name" }, h("b", {}, s.name), s.protected ? [" ", h("span", { class: "ui-badge ui-primary", title: t.protectedHelp }, icon("lock"), " ", t.protectedBadge)] : null),
          h("span", { class: "dk-sub" }, `${s.project}${s.environment ? ` / ${s.environment}` : ""} · ${d.kind[s.kind] || s.kind}`)),
        td(t.cols[0], status(last)),
        boxes,
        domCell,
        td(null, deployable ? h("div", { class: "dk-actions" },
          !s.protected ? btn(t.deploy, "rocket", () => deploy(s, false), "ui-btn ui-sm") : null,
          btn(t.logs, "file-text", () => slot.replaceChildren(logPanel(d.logsOf(s.name), `log?id=${encodeURIComponent(s.id)}`, close)), "ui-btn ui-outline ui-sm"),
          more) : null));
    };
    const rows = services.map((s) => [s, row(s)]);
    next(); next(); next(); next();
    const problem = (s, tr) => s.last_deployment === "error" || ["down", "partial"].includes(tr.children[2].querySelector("[data-state]")?.dataset.state);
    function draw() {
      const shown = rows.filter(([s, tr]) => {
        const text = `${s.name} ${s.project} ${s.environment || ""} ${(s.domains || []).map((x) => x.host).join(" ")} ${tr.children[3].textContent}`.toLowerCase();
        return (!q || text.includes(q)) && (only === "all" || problem(s, tr));
      });
      listSlot.replaceChildren(shown.length
        ? table([`${t.cols[4]}`, t.cols[0], t.cols[1], t.cols[5], ""], shown.map(([, tr]) => tr), "dk-svc")
        : empty(rows.length ? d.noMatch : t.empty));
    }
    draw();
    return h("div", { class: "ui-stack" }, h("div", { class: "dk-tools" }, search, chips), listSlot, slot);
  }

  function dbBoxes(s) {  // a database's swarm task containers (<appName>.<slot>.<task>), from the dashboard's list
    if (!dash?.containers || !s.app_name) return "–";
    const mine = dash.containers.filter((b) => String(b.name || "").startsWith(`${s.app_name}.`));
    const up = mine.filter((b) => b.state === "running").length;
    const state = !mine.length ? "unknown" : up ? "ok" : "down";
    return h("span", { class: `ui-badge ${HEALTH[state]}`, "data-state": state }, `${t.health[state]}${mine.length ? ` ${up}/${mine.length}` : ""}`);
  }

  function chipGroup(items, onPick) {
    const g = h("div", { class: "dk-chips", role: "group" });
    for (const [v, label] of items) {
      g.append(h("button", { class: "dk-chip", type: "button", "aria-pressed": String(v === items[0][0]), onclick: (e) => {
        for (const b of g.children) b.setAttribute("aria-pressed", String(b === e.currentTarget));
        onPick(v);
      } }, label));
    }
    return g;
  }

  // ---- Domains
  function domains() {
    if (!dash?.domains) return card(null, null, missing());
    if (!dash.domains.length) return empty(d.dom.none, "globe");
    const c = d.dom.cols;
    let q = "";
    const listSlot = h("div");
    const search = h("input", { class: "ui-input", type: "search", placeholder: d.searchDom, "aria-label": d.search,
      oninput: () => { q = search.value.trim().toLowerCase(); draw(); } });
    const rows = [...dash.domains].sort((a, b) => String(a.host).localeCompare(String(b.host))).map((x) => [x, h("tr", {},
      td(null, h("span", {}, link(x, x.routed ? t.routedHelp : null), x.path && x.path !== "/" ? h("span", { class: "ui-muted" }, x.path) : null,
        x.enabled === false ? [" ", h("span", { class: "ui-badge ui-outline" }, d.dom.disabled)] : null)),
      td(c[1], x.service || "–"),
      td(c[2], `${x.project || "–"}${x.environment ? ` / ${x.environment}` : ""}`),
      td(c[3], x.https ? h("span", { class: "ui-badge ui-success" }, icon("lock"), " HTTPS") : h("span", { class: "ui-badge ui-warning" }, "HTTP")),
      td(c[4], x.cert && x.cert !== "none" ? x.cert : "–"),
      td(c[5], h("span", { class: "ui-badge ui-outline", title: x.routed ? t.routedHelp : null }, x.routed ? d.dom.labels : d.dom.dokploy)))]);
    function draw() {
      const shown = rows.filter(([x]) => !q || [x.host, x.service, x.project].filter(Boolean).join(" ").toLowerCase().includes(q));
      listSlot.replaceChildren(shown.length ? table(c, shown.map(([, tr]) => tr)) : empty(d.noMatch));
    }
    draw();
    return h("div", { class: "ui-stack" }, h("div", { class: "dk-tools" }, search), listSlot);
  }

  // ---- Databases and their backups
  function databases() {
    const dbs = services.filter((s) => DB_KINDS.includes(s.kind));
    const c = d.db.cols;
    const list = dbs.length ? table(c, dbs.map((s) => h("tr", {},
      td(null, h("b", {}, s.name)),
      td(c[1], d.kind[s.kind] || s.kind),
      td(c[2], `${s.project}${s.environment ? ` / ${s.environment}` : ""}`),
      td(c[3], dbBoxes(s))))) : empty(d.db.none, "database");
    const bc = d.db.bcols;
    const backups = !dash?.backups ? missing() : !dash.backups.length ? h("p", { class: "ui-muted" }, d.db.noBackup) : table(bc, dash.backups.map((b) => h("tr", {},
      td(null, h("b", {}, b.service || b.name || b.app_name || "–")),
      td(bc[1], b.database || "–"),
      td(bc[2], b.schedule ? h("code", { class: "ui-code", style: "padding:1px 6px;font-size:13px" }, b.schedule) : "–"),
      td(bc[3], d.db.keep(b.keep)),
      td(bc[4], b.last_run ? [status(b.last_run.status), " ", h("time", { class: "ui-muted ui-small", title: full(b.last_run.at) }, ago(b.last_run.at))] : h("span", { class: "ui-muted" }, d.db.never)),
      td(bc[5], b.enabled === false ? h("span", { class: "ui-badge ui-outline" }, d.srv.off) : h("span", { class: "ui-badge ui-success" }, icon("check"), " ", d.srv.on)))));
    return h("div", { class: "ui-stack" }, card(d.db.title, "database", list), card(d.db.backups, "database-backup", backups));
  }

  // ---- Deployments
  function deployments() {
    if (!dash?.deployments) return card(null, null, missing());
    if (!dash.deployments.length) return empty(d.dep.none, "rocket");
    const slot = h("div");
    const close = () => slot.replaceChildren();
    const c = d.dep.cols;
    let only = "all";
    const listSlot = h("div");
    const chips = chipGroup([["all", d.filter.all], ["error", d.filter.failed], ["running", d.filter.running]], (v) => { only = v; draw(); });
    function draw() {
      const shown = dash.deployments.filter((x) => only === "all" || x.status === only);
      listSlot.replaceChildren(shown.length ? table(c, shown.map((x) => h("tr", {},
        td(null, h("span", {}, h("b", {}, x.service || d.dep[x.kind] || "–"), x.project ? h("span", { class: "dk-sub" }, x.project) : null)),
        td(c[1], status(x.status)),
        td(c[2], h("span", { style: "min-width:0" }, x.title || "–", x.error ? h("span", { class: "dk-sub", style: "color:var(--destructive)" }, x.error) : null)),
        td(c[3], h("time", { datetime: x.created || "", title: full(x.created) }, ago(x.created))),
        td(c[4], h("span", { class: "ui-num" }, dur(x.started || x.created, x.finished))),
        td(null, x.has_log ? btn(d.dep.log, "file-text", () => slot.replaceChildren(
          logPanel(`${x.service || d.dep[x.kind] || ""} · ${x.title || ""}`, `deployment-log?id=${encodeURIComponent(x.id)}`, close)), "ui-btn ui-ghost ui-sm") : null)))) : empty(d.noMatch));
    }
    draw();
    return h("div", { class: "ui-stack" },
      h("div", { class: "dk-tools" }, chips, dash.queue ? h("span", { class: "ui-badge ui-warning" }, d.dep.queue(dash.queue)) : null), slot, listSlot);
  }

  // ---- Server
  function server() {
    const r = dash?.resources, tr = dash?.traefik, infra = dash?.infra;
    const kv = (pairs) => h("dl", { class: "dk-kv" }, pairs.filter(Boolean).flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)]));
    const okBadge = (s) => {
      const good = ["healthy", "running", "ok"].includes(String(s || "").toLowerCase());
      return h("span", { class: `ui-badge ${good ? "ui-success" : s ? "ui-error" : "ui-outline"}` }, good ? d.srv.healthy : s || "–");
    };
    const res = r ? card(d.res.title, "gauge",
      meter(d.res.cpu, null, null, r.cpus != null ? d.res.cpus(r.cpus, r.cpu_reserved) : "–"),
      meter(d.res.mem, r.mem_used, r.mem_total), meter(d.res.disk, r.disk_used, r.disk_total),
      kv([[d.stat.containers, String(r.containers ?? "–")]]),
      [r.services ? d.srv.services(r.services) : null, r.checked ? d.srv.checked(ago(r.checked)) : null].some(Boolean)
        ? h("p", { class: "ui-muted ui-small" }, [r.services ? d.srv.services(r.services) : null, r.checked ? d.srv.checked(ago(r.checked)) : null].filter(Boolean).join(" · "))
        : null) : card(d.res.title, "gauge", missing());
    const inf = card(d.srv.infra, "shield", kv([
      [d.srv.postgres, infra ? okBadge(infra.postgres) : "–"],
      [d.srv.traefik, tr ? h("span", {}, okBadge(tr.state), " ", h("span", { class: "ui-muted" }, d.srv.traefikVer(tr.version || "?", tr.recommended)),
        tr.version_status === "outdated" ? [" ", h("span", { class: "ui-badge ui-warning" }, d.srv.outdated)] : null) : infra ? okBadge(infra.traefik) : "–"],
      [d.srv.ip, dash?.ip ? h("code", { class: "ui-code", style: "padding:1px 6px;font-size:13px" }, dash.ip) : "–"],
      [d.srv.cleanup, dash?.log_cleanup ? (dash.log_cleanup.enabled ? d.srv.cleanupOn(dash.log_cleanup.cron || "") : d.srv.off) : "–"],
    ]));
    const dc = d.srv.dcols;
    const docker = card(d.srv.docker, "hard-drive", !dash?.disk_usage ? missing() : table(dc, dash.disk_usage.map((x) => h("tr", {},
      td(null, x.type || "–"), td(dc[1], h("span", { class: "ui-num" }, String(x.total ?? "–"))),
      td(dc[2], h("span", { class: "ui-num" }, String(x.active ?? "–"))), td(dc[3], h("span", { class: "ui-num" }, x.bytes != null ? bytes(x.bytes) : x.size || "–")),
      td(dc[4], h("span", { class: "ui-num" }, x.reclaimable || "–"))))));
    const srv = card(d.srv.servers, "network", !dash?.servers ? missing() : !dash.servers.length ? h("p", { class: "ui-muted" }, d.srv.noServers)
      : h("ul", { class: "dk-list" }, dash.servers.map((s) => h("li", {}, h("span", { class: "dk-ico" }, icon("server")),
        h("span", { class: "dk-grow" }, h("b", {}, s.name || "–"), h("span", { class: "dk-sub" }, [s.ip, s.type].filter(Boolean).join(" · "))),
        s.status ? h("span", { class: `ui-badge ${s.status === "active" ? "ui-success" : "ui-outline"}` }, s.status) : null))));
    return h("div", { class: "dk-cols" }, res, inf, docker, srv);
  }

  // ---- load
  function skeleton() {
    return h("div", { class: "ui-stack", "aria-busy": "true" }, h("div", { class: "dk-stats" },
      [1, 2, 3, 4].map(() => h("div", { class: "ui-skeleton", style: "height:92px;border-radius:12px" }))),
      h("div", { class: "ui-skeleton", style: "height:220px;border-radius:12px" }));
  }

  async function load() {
    generation += 1;
    const mine = generation;
    healthCache.clear();
    rendered.clear();
    body.replaceChildren(skeleton());
    try {
      const st = await ctx.api("status");
      if (!alive || mine !== generation) return;
      showSkill(st.skill);
      if (!st.connected) {
        headBtns.replaceChildren();
        subtitle.textContent = t.intro;
        if (!st.key_present) say(t.keyMissing, "ui-warning");
        else if (st.key_changed) say(t.keyChanged, "ui-warning");
        body.replaceChildren(connectForm(st));
        return;
      }
      subtitle.textContent = d.subtitle(st.url);
      headBtns.replaceChildren(btn(t.refresh, "refresh-cw", load),
        btn(t.disconnect, null, async () => {
          try { await ctx.api("disconnect", { method: "POST" }); say(""); load(); } catch (e) { fail(e); }
        }, "ui-btn ui-ghost ui-sm"));
      let dashError = null;  // the services table still works when the dashboard read fails: say why, do not hide it
      const [svc, db] = await Promise.all([ctx.api("services"), ctx.api("dashboard").catch((e) => { dashError = e; return null; })]);
      if (!alive || mine !== generation) return;
      services = svc.services;
      dash = db;
      if (dashError) say(`${d.dashFailed} ${dashError.message || dashError}`, "ui-warning");
      panels.clear();
      tabBtns.clear();
      const bar = tabsBar();
      const wrap = h("div", {});
      for (const [k] of TABS) {
        const p = h("div", { role: "tabpanel", id: `dk-panel-${k}`, "aria-labelledby": `dk-tab-${k}`, tabindex: "0", hidden: k !== tab, style: "padding-top:16px" });
        panels.set(k, p);
        wrap.append(p);
      }
      body.replaceChildren(bar, wrap);
      counts();
      render(tab);
    } catch (e) {
      if (alive && mine === generation) { body.replaceChildren(); fail(e); }
    }
  }

  const closeMenus = (e) => {  // one "More" menu open at a time; a click elsewhere closes it
    for (const m of el.querySelectorAll("details.dk-more[open]")) if (!m.contains(e.target)) m.open = false;
  };
  const onKey = (e) => { if (e.key === "Escape") for (const m of el.querySelectorAll("details.dk-more[open]")) { m.open = false; m.querySelector("summary").focus(); } };
  const onScroll = () => {  // a fixed menu follows its button; it closes once the button leaves the screen
    for (const m of el.querySelectorAll("details.dk-more[open]")) {
      const r = m.firstChild.getBoundingClientRect();
      if (r.bottom < 0 || r.top > window.innerHeight) m.open = false;
      else m.place?.();
    }
  };
  document.addEventListener("click", closeMenus);
  document.addEventListener("keydown", onKey);
  document.addEventListener("scroll", onScroll, true);
  window.addEventListener("resize", onScroll);
  updatesPanel();
  load();
  return () => {
    alive = false;
    document.removeEventListener("click", closeMenus);
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("scroll", onScroll, true);
    window.removeEventListener("resize", onScroll);
  };
}
