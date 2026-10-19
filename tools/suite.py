#!/usr/bin/env python3
"""Shared "suite" shell for Skyler's apps: Kitchen, Grocery, Lift, DishLog, Protocol.

One top bar, one set of app colors, one set of layout tokens. This script writes
the identical block into every app between <!-- suite:css --> ... <!-- /suite:css -->
and <!-- suite:bar --> ... <!-- /suite:bar --> markers, so a change made here lands
everywhere at once.

    python3 tools/suite.py ../kitchen ../daily_schedule

The first run places the markers (replacing each app's old .applinks nav); later
runs only replace what sits between them.
"""
import io, re, sys, os

SUITE_VERSION = "1"

APPS = [  # key, label, kitchen-repo file, svg body
    ("kitchen", "Kitchen", "index.html",
     '<path d="M4 11h13v4a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/><path d="M17 12.5h3M8 4.5c0 1.5 1.5 1.5 1.5 3M12 4.5c0 1.5 1.5 1.5 1.5 3"/>'),
    ("grocery", "Grocery", "grocery.html",
     '<path d="M3 4h2.2l2.2 11h10.4l2-7.5H6.4"/><circle cx="9.5" cy="19.5" r="1.4"/><circle cx="16.5" cy="19.5" r="1.4"/>'),
    ("lift", "Lift", "workout.html",
     '<path d="M6.5 7v10M17.5 7v10M4 9.5v5M20 9.5v5M6.5 12h11"/>'),
    ("dishlog", "DishLog", "dishlog.html",
     '<path d="M5 3v5a2 2 0 0 0 4 0V3M7 10v11M17 21V3c-2 0-3.5 2.5-3.5 6s1.5 4 3.5 4"/>'),
    ("protocol", "Protocol", None,
     '<rect x="4.5" y="3.5" width="15" height="17" rx="2.5"/><path d="M8 9l1.5 1.5L12 8M8 15l1.5 1.5L12 14M14.5 9.5H16M14.5 15.5H16"/>'),
]
KITCHEN_BASE = "https://frostie4life9.github.io/kitchen/"
PROTOCOL_URL = "https://frostie4life9.github.io/daily_schedule/"

CSS = """<!-- suite:css vVERSION · shared by Kitchen, Grocery, Lift, DishLog, Protocol — edit tools/suite.py in the kitchen repo, not here -->
<style id="suite-css">
/* App colors come from each app's home-screen icon, so the bar, the icon and
   the page all agree. The tab for every app carries its own color, so the
   whole set reads as one color-coded system wherever you are in it. */
.sx-bar{
  --sx-kitchen:#7A2E1E; --sx-grocery:#2D5840; --sx-lift:#A8522B; --sx-dishlog:#6A2347; --sx-protocol:#1E3550;
  --sx-on:#FFF8EF;
  --sx-paper:#FAF6F0; --sx-ink:#1F1A14; --sx-dim:#7D7262; --sx-line:#DDD3C2; --sx-hover:#EFE7DA;
}
@media (prefers-color-scheme:dark){ .sx-bar:not(.sx-light){
  --sx-kitchen:#E8987C; --sx-grocery:#7CC39A; --sx-lift:#EE9C66; --sx-dishlog:#DD8DB2; --sx-protocol:#5FE6B0;
  --sx-on:#15120E;
  --sx-paper:#17140F; --sx-ink:#F1EADF; --sx-dim:#A0947F; --sx-line:#3B342B; --sx-hover:#2A251E;
}}
.sx-bar.sx-dark{
  --sx-kitchen:#E8987C; --sx-grocery:#7CC39A; --sx-lift:#EE9C66; --sx-dishlog:#DD8DB2; --sx-protocol:#5FE6B0;
  --sx-on:#15120E;
}
/* layout tokens every app's own layout lines up with */
:root{ --sx-max:1280px; --sx-gut:clamp(16px,2.4vw,32px); --sx-barh:56px; }

.sx-bar{position:relative;z-index:40;background:var(--sx-paper);border-bottom:1px solid var(--sx-line);
  font-family:'Manrope',system-ui,-apple-system,'Segoe UI',sans-serif;-webkit-font-smoothing:antialiased;color:var(--sx-ink)}
.sx-in{max-width:var(--sx-max);margin:0 auto;box-sizing:border-box;min-height:var(--sx-barh);
  padding:calc(8px + env(safe-area-inset-top,0px)) var(--sx-gut) 8px;display:flex;align-items:center;gap:18px}
.sx-id{display:none;align-items:center;gap:10px;flex:0 0 auto;min-width:0}
.sx-tile{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:var(--app);color:var(--sx-on);flex:0 0 auto}
.sx-tile svg{width:17px;height:17px}
.sx-name{font-family:'Fraunces',Georgia,serif;font-style:italic;font-weight:600;font-size:21px;letter-spacing:-.01em;line-height:1;color:var(--sx-ink);white-space:nowrap}
.sx-tabs{display:flex;gap:6px;flex:1 1 auto;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;margin:0 calc(var(--sx-gut) * -1);padding:0 var(--sx-gut)}
.sx-tabs::-webkit-scrollbar{display:none}
.sx-t{flex:0 0 auto;display:inline-flex;align-items:center;gap:7px;height:36px;padding:0 14px 0 11px;box-sizing:border-box;
  border-radius:999px;border:1px solid var(--sx-line);background:transparent;color:var(--sx-dim);text-decoration:none;
  font:700 12.5px/1 'Manrope',system-ui,sans-serif;letter-spacing:.02em;white-space:nowrap;transition:background .15s,color .15s,border-color .15s}
.sx-t svg,.sx-tile svg{fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.sx-t svg{width:16px;height:16px;color:var(--c);flex:0 0 auto}
.sx-t:hover{background:var(--sx-hover);color:var(--sx-ink)}
.sx-t:focus-visible{outline:2px solid var(--c);outline-offset:2px}
.sx-t[aria-current="page"]{background:var(--c);border-color:var(--c);color:var(--sx-on)}
.sx-t[aria-current="page"] svg{color:inherit}
@media (min-width:900px){
  .sx-bar{position:sticky;top:0;z-index:70;background:color-mix(in srgb,var(--sx-paper) 88%,transparent);
    -webkit-backdrop-filter:saturate(1.4) blur(14px);backdrop-filter:saturate(1.4) blur(14px)}
  .sx-id{display:flex}
  .sx-tabs{flex:0 1 auto;margin:0 0 0 auto;padding:0}
  .sx-t{border-color:transparent}
  .sx-t[aria-current="page"]{border-color:var(--c)}
}
@media print{.sx-bar{display:none}}
</style>
<!-- /suite:css -->"""


def bar(here, repo):
    tabs = []
    cur = None
    for key, label, fname, svg in APPS:
        if key == "protocol":
            href = "./" if repo == "daily_schedule" else PROTOCOL_URL
        else:
            href = fname if repo == "kitchen" else KITCHEN_BASE + fname
        attr = ' aria-current="page"' if key == here else ""
        if key == here:
            cur = (label, svg)
        tabs.append('<a class="sx-t" style="--c:var(--sx-%s)" href="%s"%s><svg viewBox="0 0 24 24" aria-hidden="true">%s</svg>%s</a>'
                    % (key, href, attr, svg, label))
    extra = " sx-dark" if here == "protocol" else ""
    return ('<!-- suite:bar -->\n<nav class="sx-bar%s" style="--app:var(--sx-%s)" aria-label="Your apps"><div class="sx-in">\n'
            '  <div class="sx-id" aria-hidden="true"><span class="sx-tile"><svg viewBox="0 0 24 24">%s</svg></span><span class="sx-name">%s</span></div>\n'
            '  <div class="sx-tabs">\n    %s\n  </div>\n</div></nav>\n<!-- /suite:bar -->'
            % (extra, here, cur[1], cur[0], "\n    ".join(tabs)))


TARGETS = {  # (repo, file) -> app key
    ("kitchen", "index.html"): "kitchen",
    ("kitchen", "grocery.html"): "grocery",
    ("kitchen", "workout.html"): "lift",
    ("kitchen", "dishlog.html"): "dishlog",
    ("daily_schedule", "index.html"): "protocol",
}


def apply(path, repo, here):
    with io.open(path, encoding="utf-8") as f:
        s = f.read()
    css = CSS.replace("VERSION", SUITE_VERSION)
    b = bar(here, repo)
    # CSS: replace between markers, or insert just before </head>
    if "<!-- suite:css" in s:
        s = re.sub(r"<!-- suite:css.*?<!-- /suite:css -->", lambda m: css, s, flags=re.S)
    else:
        i = s.index("</head>")
        s = s[:i] + css + "\n" + s[i:]
    # bar: replace between markers, or place as the first thing in <body>
    if "<!-- suite:bar -->" in s:
        s = re.sub(r"<!-- suite:bar -->.*?<!-- /suite:bar -->", lambda m: b, s, flags=re.S)
    else:
        s = re.sub(r'\s*<nav class="applinks"[^>]*>.*?</nav>\n?', "\n", s, count=1, flags=re.S)
        m = re.search(r"<body[^>]*>", s)
        s = s[:m.end()] + "\n" + b + "\n" + s[m.end():]
    # the old per-app switcher styles are dead once the bar is in
    s = re.sub(r"[ \t]*\.applinks[^{}]*\{[^{}]*\}[ \t]*\n?", "", s)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(s)


if __name__ == "__main__":
    roots = sys.argv[1:] or ["."]
    for root in roots:
        repo = os.path.basename(os.path.abspath(root))
        for (r, fn), key in TARGETS.items():
            if r == repo and os.path.exists(os.path.join(root, fn)):
                apply(os.path.join(root, fn), repo, key)
                print("suite v%s ->" % SUITE_VERSION, repo + "/" + fn)
