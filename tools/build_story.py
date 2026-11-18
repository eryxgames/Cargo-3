#!/usr/bin/env python3
"""Build Cargo 3's story for the game, or check that the built file is current.

    python3 tools/build_story.py            write story/cargo3.game.json
    python3 tools/build_story.py --check    fail if it is out of date, or if the story's stats
                                            and the game's snapshot disagree

The story is written in story/cargo3.story.json and the files it includes (story/cargo3/);
the names of characters who span the trilogy come from story/saga.json (copied from the Cargo
repository by tools/sync_story.py). The game reads the built file, one node per line.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "storykit"))
import story as kit  # noqa: E402

SOURCE = os.path.join(ROOT, "story", "cargo3.story.json")
BUILT = os.path.join(ROOT, "story", "cargo3.game.json")

NODE_FIELDS = ("kind", "arc", "act", "title", "text", "variants", "requires", "effects", "choices", "next",
               "choose", "in", "who", "where", "chance", "repeat", "status", "handled_by", "sound", "secret")
CHARACTER_FIELDS = ("name", "short", "full", "title", "kind", "generated", "route")
PLACE_FIELDS = ("kind", "type", "system", "ly", "made", "open", "about")


def build():
    story = kit.load(SOURCE)
    nodes = {}
    repaired = []
    for nid, node in story["nodes"].items():
        nodes[nid] = {k: node[k] for k in NODE_FIELDS if k in node}
        # Cargo 3 writes its own main story: a chapter, milestone or ending that states a
        # condition replaces the one in game/chapters.py (Cargo 1's), as an amended one does
        frame = node.get("kind") in ("chapter", "milestone", "ending") and "requires" in node
        if frame or any("requires" in a.get("fields", []) for a in node.get("amended", [])):
            repaired.append(nid)
    return {
        "game": story["game"]["id"],
        "characters": {cid: {k: c[k] for k in CHARACTER_FIELDS if k in c}
                       for cid, c in sorted(story["characters"].items())},
        "flags": {fid: {k: f[k] for k in ("about", "carries_to") if k in f}
                  for fid, f in sorted(story["flags"].items())},
        "places": {pid: {k: p[k] for k in PLACE_FIELDS if k in p}
                   for pid, p in story["places"].items() if p.get("kind") == "location"},
        "repaired": sorted(repaired),
        "order": list(nodes),
        "nodes": nodes,
    }


def as_text(data):
    """The built story as JSON, one node per line (readable diffs)."""
    head = {k: v for k, v in data.items() if k != "nodes"}
    lines = [json.dumps(head, ensure_ascii=False, separators=(",", ":"))[:-1] + ',"nodes":{']
    items = list(data["nodes"].items())
    for i, (nid, node) in enumerate(items):
        lines.append(json.dumps(nid) + ":" + json.dumps(node, ensure_ascii=False, separators=(",", ":"))
                     + ("," if i < len(items) - 1 else ""))
    lines.append("}}")
    return "\n".join(lines) + "\n"


def snapshot_keys():
    """The stats and sets a running game gives the story, to compare with the declared ones."""
    sys.path.insert(0, HERE)
    import headless
    cargo = headless.load(os.path.join(ROOT, "game", "world.py"))
    game, _ = headless.new_game(cargo)
    snap = game.story_snapshot()
    return set(snap["stats"]), set(snap["sets"])


def main(argv):
    text = as_text(build())
    if "--check" not in argv:
        with open(BUILT, "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s: %d nodes" % (os.path.relpath(BUILT, ROOT), text.count("\n") - 2))
        return 0
    problems = []
    try:
        current = open(BUILT, encoding="utf-8").read()
    except OSError:
        current = ""
    if current != text:
        problems.append("story/cargo3.game.json is out of date: run python3 tools/build_story.py")
    story = kit.load(SOURCE)
    stats, sets = snapshot_keys()
    declared = set(story["stats"])
    problems += ["the game gives the story a stat it does not declare: %s" % s for s in sorted(stats - declared)]
    problems += ["the story declares a stat the game never gives: %s" % s for s in sorted(declared - stats)]
    problems += ["the game gives the story a set it does not declare: %s" % s for s in sorted(sets - set(story["sets"]))]
    for problem in problems:
        print("FAIL", problem)
    print("story build: %s" % ("current, stats agree with the game" if not problems else "%d problems" % len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
