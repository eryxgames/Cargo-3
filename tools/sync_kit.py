#!/usr/bin/env python3
"""CLIo's screen and sound layer, copied into kit/.

Cargo 3 draws its screens and plays its sound with CLIo's engine modules (terminal, frames
and menus, themes, ASCII art and sprites, the synthesizer). They only import each other and
the standard library, so they are copied in as they are, not linked: a player who clones
Cargo 3 gets everything. kit/KIT.json records which CLIo they came from and a checksum of
every file.

    python3 tools/sync_kit.py ../CLIo        # copy from a CLIo checkout, write KIT.json
    python3 tools/sync_kit.py --check        # fail if a copied file was changed by hand

Change these files in CLIo, then copy them again; never edit them here.
"""
import hashlib, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(os.path.dirname(HERE), "kit")
MANIFEST = os.path.join(KIT, "KIT.json")
# what is taken from CLIo's engine/ (folders are taken whole)
PARTS = ["term.py", "ui.py", "theme.py", "art.py", "sprite.py", "pixels.py", "fx.py", "banner.py", "style", "audio"]
FROM_ROOT = ["LICENSE", "NOTICE"]
INIT = '''# SPDX-License-Identifier: Apache-2.0
"""CLIo's screen and sound layer, copied from CLIo %s (%s) by tools/sync_kit.py.
Do not edit these files here: change them in CLIo and copy them again."""
CLIO_VERSION = "%s"
CLIO_COMMIT = "%s"
'''


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def kit_files():
    found = []
    for where, dirs, names in os.walk(KIT):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            if name != "KIT.json" and not name.endswith((".pyc", ".pyo")):
                found.append(os.path.relpath(os.path.join(where, name), KIT).replace(os.sep, "/"))
    return found


def copy(clio):
    engine = os.path.join(clio, "engine")
    version = re.search(r'__version__ = "(.+?)"', open(os.path.join(engine, "__init__.py")).read()).group(1)
    try:
        commit = subprocess.run(["git", "-C", clio, "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    if os.path.isdir(KIT):
        shutil.rmtree(KIT)
    os.makedirs(KIT)
    for part in PARTS:
        source = os.path.join(engine, part)
        if os.path.isdir(source):
            shutil.copytree(source, os.path.join(KIT, part), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(source, os.path.join(KIT, part))
    for name in FROM_ROOT:
        shutil.copy2(os.path.join(clio, name), os.path.join(KIT, name))
    with open(os.path.join(KIT, "__init__.py"), "w", encoding="utf-8") as handle:
        handle.write(INIT % (version, commit, version, commit))
    manifest = {"clio_version": version, "clio_commit": commit,
                "files": {name: digest(os.path.join(KIT, name)) for name in kit_files()}}
    with open(MANIFEST, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print("kit: CLIo %s (%s), %d files" % (version, commit, len(manifest["files"])))


def check():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    present = set(kit_files())
    expected = set(manifest["files"])
    problems = ["changed by hand: %s" % name for name in sorted(present & expected)
                if digest(os.path.join(KIT, name)) != manifest["files"][name]]
    problems += ["missing: %s" % name for name in sorted(expected - present)]
    problems += ["not from CLIo: %s" % name for name in sorted(present - expected)]
    for problem in problems:
        print("FAIL kit", problem)
    print("kit: CLIo %s (%s), %d files, %s" % (manifest["clio_version"], manifest["clio_commit"],
                                               len(expected), "unchanged" if not problems else "%d problems" % len(problems)))
    return not problems


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    copy(sys.argv[1])
