#!/usr/bin/env python3
"""No name shows as a raw {placeholder}. Every story text is filled with a fresh captain and with
captains from the other parts, and nothing of a {name} may be left. In the game's code, every
string with a {name} the trilogy's stories know (a character id from any story file, the saga's,
or a placeholder) must be one this game can fill: the port's price board once showed
"{port_broker}", a Cargo 1 name this part never declared. The one exception is an encounter
option that names a crew member and is only offered with that crew member aboard.

    python3 tools/placeholders.py
"""
import ast, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storytest import ROOT, cargo, expect, problems, record, start  # noqa: E402

TOKEN = re.compile(r"\{([a-z][a-z0-9_]*)(?:\.([a-z_]+))?\}")


def texts(node):
    for key in ("text", "title", "say"):
        value = node.get(key)
        for part in ([value] if isinstance(value, str) else value if isinstance(value, list) else []):
            if isinstance(part, str):
                yield part
    for sub in (node.get("variants") or []) + (node.get("choices") or []):
        yield from texts(sub)


# every name the trilogy's stories know, from every story file in the repository
names = set()
for path in glob.glob(os.path.join(ROOT, "story", "**", "*.json"), recursive=True):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except ValueError:
        continue
    if isinstance(data, dict):
        names.update((data.get("characters") or {}).keys())
        names.update((data.get("placeholders") or {}).keys() if isinstance(data.get("placeholders"), dict) else [])
names.update(("origin", "visitor", "player_name", "rank", "money", "place", "turn"))

# 1. every story text, for a fresh captain and for captains from the other parts
story = cargo.story_data()
captains = [None] + [record(part, flags=()) for part in ("cargo1", "cargo2", "cargo3") if part != story.get("game")]
left = {}
for rec in captains:
    game, io, _ = start(rec)
    for nid, node in story["nodes"].items():
        for text in texts(node):
            for head, field in TOKEN.findall(game.story.fill(text)):
                left.setdefault(nid, set()).add(head + ("." + field if field else ""))
expect(not left, "story texts leave names unfilled: %s" % {k: sorted(v) for k, v in left.items()})

# 2. the game's code: a known name must be one this game fills
game, io, _ = start(None)
crew_only = set()           # encounter texts offered only with that crew member aboard
for situation in getattr(cargo, "SITUATIONS", {}).values():
    for option in situation.get("options", []):
        crew = (option.get("needs") or {}).get("crew", [])
        for text in [option.get("say", "")] + [o.get("say", "") for o in (option.get("do"), option.get("do", {}).get("win"),
                                                                          option.get("do", {}).get("lose")) if isinstance(o, dict)]:
            heads = [head for head, _ in TOKEN.findall(text)]
            if heads and all(head in crew for head in heads):
                crew_only.add(text)
code = {}
for path in sorted(glob.glob(os.path.join(ROOT, "game", "*.py"))):
    for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)) or node.value in crew_only:
            continue
        for head, field in TOKEN.findall(node.value):
            token = "{%s%s}" % (head, "." + field if field else "")
            if head in names and game.story.fill(token) == token:
                code.setdefault("%s:%d" % (os.path.relpath(path, ROOT), node.lineno), set()).add(token)
expect(not code, "the code shows names this game cannot fill: %s" % {k: sorted(v) for k, v in code.items()})

print("placeholders: %d story nodes, %d captains, %d crew-only encounter texts; %s" % (
    len(story["nodes"]), len(captains), len(crew_only), "ok" if not problems[0] else "%d problems" % problems[0]))
sys.exit(1 if problems[0] else 0)
