#!/usr/bin/env python3
"""Each of the game's modules imports on its own, in a fresh Python, whichever is loaded first;
and none imports game/world.py while it loads (world.py imports all of them, so only code
inside functions may fetch Game from it).

    python3 tools/modules.py
"""
import ast, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")
problems = []
names = sorted(f[:-3] for f in os.listdir(GAME) if f.endswith(".py") and f != "__init__.py")
for name in names:
    tree = ast.parse(open(os.path.join(GAME, name + ".py"), encoding="utf-8").read())
    for node in tree.body:          # module level only: imports inside functions are fine
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module == "world" and name != "world":
            problems.append("%s imports world.py at module level (line %d)" % (name, node.lineno))
    run = subprocess.run([sys.executable, "-c", "import game.%s" % name], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if run.returncode:
        problems.append("game.%s does not import on its own:\n%s" % (name, run.stdout.strip()[-400:]))
for problem in problems:
    print("FAIL", problem)
print("modules: %d, %s" % (len(names), "each imports on its own" if not problems else "%d problems" % len(problems)))
sys.exit(1 if problems else 0)
