# 01 — KDE architecture map

Before you ask a model questions about KDE you have to know what KDE is. This chapter is the lab's working map of the platform. It is not exhaustive — KDE is enormous — and it is biased toward the layers that show up in the ontology and the eval suite. If your goal is to make the model answer *"why is Dolphin slow when I open this folder?"*, this is where you start.

## Layered desktop platform

A practical mental model has five horizontal tiers and a handful of vertical concerns that cut across them.

```
+--------------------------------------------------------------+
|  User applications  (Dolphin, Kate, Konsole, Okular, ...)    |
+--------------------------------------------------------------+
|  Plasma shell + Plasmoids + KRunner + System Settings        |
+--------------------------------------------------------------+
|  KDE Frameworks (KIO, KConfig, KCoreAddons, KService, KIO    |
|                  workers, KItemModels, Solid, Baloo client)  |
+--------------------------------------------------------------+
|  Window manager (KWin) + display server glue (Wayland / X11) |
+--------------------------------------------------------------+
|  Qt 6 (Core, GUI, Quick/QML, DBus, Network, Concurrent)      |
+--------------------------------------------------------------+

Cross-cutting:  D-Bus session bus  |  KConfig + .kcfg files  |
                QLoggingCategory   |  desktop files / .service files
                .so plugins        |  systemd user units
```

A user-visible action almost always lights up at least three of those layers plus one or two cross-cutting concerns. That is what makes pure-code search insufficient and an ontology useful.

## The Frameworks tier system

KDE Frameworks classify each library into tiers based on dependency depth:

- **Tier 1** depends only on Qt. Examples: KConfig, KCoreAddons, KArchive.
- **Tier 2** depends on Qt and Tier 1. Examples: KAuth, KCompletion, KCrash.
- **Tier 3** depends on Qt, Tier 1, and Tier 2. Examples: KIO, KParts, KService, KWindowSystem.
- **Tier 4** mostly integrations on top of the rest. Examples: KDELibs4Support, Plasma framework.

The tiering matters for ontology design because higher-tier code can call lower-tier code but not the other way around. When you add a `CALLS` or `RELATED_TO` edge between two `CppClass` entities, the direction has to respect this order or you have an evidence bug. Chapter [03_kde_ontology_design.md](03_kde_ontology_design.md) revisits this.

## Plasma shell, KWin, KIO

These three components show up in nearly every real KDE bug report.

- **Plasma shell** is the desktop process you actually see — panels, taskbar, system tray, the wallpaper. It is written mostly in QML over a C++ backend. The QML lives in `/usr/share/plasma/...`. It uses D-Bus for nearly all cross-component coordination.
- **KWin** is the window manager and compositor. Effects are plugins. On Wayland it doubles as the compositor; on X11 it talks to the X server. KWin scripts and effect packages are loaded at runtime, which means the static call graph misses most of the behaviour. The ontology has `Plugin` and `LOADS_PLUGIN` to handle this.
- **KIO** is the I/O abstraction. Whenever an application opens `smb://host/share/file.txt` or `trash:/`, KIO routes the request to a worker (formerly called a slave). Workers are separate processes; that means errors travel back as D-Bus or local-socket messages, and any "slow folder open" question almost always involves at least one KIO worker.

Other heavy hitters: **Baloo** (file indexer), **Solid** (hardware abstraction), **KRunner** (search bar), **KDED** (daemon host), **KGlobalAccel** (global shortcuts), **kded6** (the daemon binary on KF6).

## Configuration: KConfig and KCM modules

User-visible settings are stored as KConfig files under `~/.config`. A schema-defined family of settings is described by a `.kcfg` file like the mini repo's [../examples/mini_kde_repo/kconfig/minisearch.kcfg](../examples/mini_kde_repo/kconfig/minisearch.kcfg). The XML names a `kcfgfile` (e.g. `minisearchrc`), groups (here `Search` and `Ui`), and per-entry type, default, label.

The runtime reads values with `KSharedConfig::openConfig("minisearchrc")` and then `KConfigGroup` lookups. The mini repo's `KFileSearcher::KFileSearcher` constructor does exactly this with `MaxResults`. Our regex-based extractor in [../src/repo_ingest/cpp_reader.py](../src/repo_ingest/cpp_reader.py) catches the `readEntry("MaxResults", ...)` pattern and produces a `READS_CONFIG` edge from `KFileSearcher` to the `ConfigKey` named `MaxResults`.

System Settings modules (KCMs) are plugins that surface those keys in the UI. When a user changes a setting, a KConfig write fires `KConfigWatcher`, which fires QObject signals, which fire QML bindings — observability all the way through.

## D-Bus services

A KDE session is awash in D-Bus. The session bus carries:

- `org.kde.plasmashell` for the shell,
- `org.kde.KWin` for the window manager,
- `org.kde.kded6` for the daemon,
- `org.kde.minisearch` (in our fixture) for MiniSearch,
- plus dozens of per-application names registered on demand.

Any service can be introspected by `qdbus`. The XML in [../examples/mini_kde_repo/dbus/org.kde.minisearch.xml](../examples/mini_kde_repo/dbus/org.kde.minisearch.xml) is the same shape a real introspection dump produces, which is why [../src/repo_ingest/dbus_reader.py](../src/repo_ingest/dbus_reader.py) can chew on either. D-Bus is the cleanest way to discover what a running KDE process can do; for the lab it provides the spine of the `DbusInterface` / `DbusMethod` / `EXPOSES_DBUS` slice of the ontology.

## QML UI and C++ backend

Plasma and most modern KDE apps split presentation from logic. QML lives at the top, declarative and reactive. C++ lives underneath, exposing properties, signals, and methods that QML binds to.

The bridge is `qmlRegisterType<C>("namespace", major, minor, "Name")`. In the mini repo, `SearchView.qml` says `import org.kde.minisearch 1.0` and instantiates a `KFileSearcher { id: searcher; ... }`. The ontology models this with a `QmlComponent` node connected to a `CppClass` node via `CONNECTS_TO` carrying a `via=qmlRegisterType` property. Look at [../src/ontology/extractor.py](../src/ontology/extractor.py)'s `from_qml` to see how the edge is created even when the C++ class entity has not been seen yet — the id is deterministic, so the edge resolves once the class is added.

## Sessions, startup, and `.desktop` files

`.desktop` files are how applications appear in menus, get launched by the session, and (with `DBusActivatable=true`) get auto-started over D-Bus. The mini repo has [../examples/mini_kde_repo/desktop/minisearch.desktop](../examples/mini_kde_repo/desktop/minisearch.desktop). The desktop entry is the only file the user has to know exists to launch the app — every other piece (binary, QML, D-Bus connection, config) is implicit.

For the ontology, a `DesktopFile` entity carries the `exec`, `icon`, `dbus_activatable`, and `categories` properties. When `DBusActivatable=true`, the lab adds a `REGISTERS_SERVICE` self-relation so we can trace from a desktop launch back to a D-Bus service name.

## Logs: `QLoggingCategory`

KDE's logging story is `QLoggingCategory`. Each module declares a category like `Q_LOGGING_CATEGORY(MINISEARCH_BACKEND, "minisearch.backend")`. At runtime, the operator turns categories on with `QT_LOGGING_RULES='minisearch.backend.debug=true'` or via `qdbus6 org.kde.KDebugSettings`. The mini repo log file at [../examples/mini_kde_repo/logs/minisearch.log](../examples/mini_kde_repo/logs/minisearch.log) carries lines like `2026-05-13T10:07:55.402 DEBUG minisearch.backend scan complete processed= 312044 hits= 100`.

In ontology terms, each `LogCategory` has many `LogEvent` children connected by `OBSERVED_IN`. Both endpoints are queryable. When a symptom hits the traceability path, log categories light up first because their names usually overlap with the symptom's vocabulary ("minisearch", "scan", "thumbnail", "search").

## A worked symptom: "Dolphin slow on folder open"

Pretend a user reports that Dolphin lags for several seconds when opening a folder full of photos. The traceability path:

```
symptom   : "Dolphin slow on folder open"
  |
  v
Dolphin UI            (Qt + KParts + KIO model)
  |
  v
KIO worker            (file:// worker, the right one for local paths)
  |
  v
filesystem metadata   (stat, getxattr, readdir)
  |
  v
Baloo indexer         (if active, possibly stalling on a huge db)
  |
  v
thumbnailer plugin    (KFileItemActions, ThumbnailJob, image decoders)
  |
  v
KConfig key           (Dolphin's "PreviewSettings" group, thumbnail enabled?)
  |
  v
log categories        ("kf.kio.workers.file", "kf.baloo", "dolphin")
```

Every arrow in that chain is an ontology relation, and every node is an entity. If the trained model can name even half of them when prompted, it has already beaten generic code search. Chapter [08_debug_reasoning_eval.md](08_debug_reasoning_eval.md) shows the exact passing criteria.

## What this lab covers vs. what real KDE has

The mini repo is a microcosm:

| Real KDE                                       | Mini repo                       |
|------------------------------------------------|---------------------------------|
| KIO + KFileItemModel + KDirLister              | `KFileSearcher` + backend        |
| `org.kde.plasmashell`, `org.kde.KWin`, ...     | `org.kde.minisearch`             |
| Hundreds of `.kcfg` files                      | `minisearch.kcfg`                |
| `kf.kio.workers.file`, `kf.baloo`, ...         | `minisearch.backend`             |
| `dolphin.desktop`, `org.kde.dolphin.desktop`   | `minisearch.desktop`             |
| Many many QML components                       | `SearchView.qml`                 |

The pipeline does not know it is small. The same readers, the same ontology, the same graph, and the same evaluator run identically on a real KDE clone configured in `configs/repos.yaml`.

## Exercises

1. Pick one component you actually use (Dolphin, KRunner, KWin, Plasma) and sketch its layered slice in the format above. Mark the layers the v0 ontology already covers.
2. Run `qdbus6 | grep org.kde` on a live KDE session. Pick three services and list their methods with `qdbus6 <service> /`. Decide which ones you would want to expose as `DbusInterface` entities for a debugging model.
3. Open [../examples/mini_kde_repo/kconfig/minisearch.kcfg](../examples/mini_kde_repo/kconfig/minisearch.kcfg) and add a new entry `RecentSearches` of type `StringList`. Re-run the pipeline. What changes in `artifacts/graphs/mini_repo.json`?
4. Read the log file at [../examples/mini_kde_repo/logs/minisearch.log](../examples/mini_kde_repo/logs/minisearch.log) line by line. For each line, identify the layer it belongs to in the diagram above.
5. Write a 3-step traceability scenario for "KWin scripts stop working after upgrade" using the layered map and the cross-cutting concerns. Identify the entity types you would need (some already exist; some you would have to add to [../src/ontology/schema.py](../src/ontology/schema.py)).

## Further reading

- `develop.kde.org/docs/` — KDE Frameworks tier overview, KIO worker tutorial, KConfig howto.
- `community.kde.org` — Plasma architecture pages; search for "Plasma 6 architecture".
- The `freedesktop.org` desktop entry specification.
- The `freedesktop.org` D-Bus specification (introspection format, well-known names, activation).
- Qt's `QLoggingCategory` and `QObject` documentation at `doc.qt.io`.
- *Foundations of Qt Development* by Johan Thelin for the C++/QML bridge in depth.
- The "Plasma overview" talk from Akademy each year is usually a recorded YouTube session; search the year you care about.
