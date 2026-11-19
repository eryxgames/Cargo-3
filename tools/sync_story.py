#!/usr/bin/env python3
"""The trilogy's story tools and saga file, copied from the Cargo (1) repository.

storykit/ (the story format, validator, map) and the saga file (story/saga.json: characters
who span the trilogy, promises between the parts) live in the Cargo repository, the trilogy's
home. Cargo 3 copies them, with Cargo 1's story (story/cargo1.story.json and story/cargo1/), so that its
own story can be checked against the saga: names come from the saga, and the promises Cargo 1
made are paid here. story/STORYKIT.json records where they came from and a checksum of each.

    python3 tools/sync_story.py ../Cargo       # copy from a Cargo checkout
    python3 tools/sync_story.py --check        # fail if a copied file was changed here

storykit/record.py (the captain record's history: ledger, lines, errands) is also copied into the
game package as game/record.py, which the game imports.

Change these files in the Cargo repository, then copy them again; never edit them here.
"""
import hashlib, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(ROOT, "story", "STORYKIT.json")
FILES = ["storykit/story.py", "storykit/validate.py", "storykit/storymap.py", "storykit/replay.py",
         "storykit/record.py", "storykit/map_template.html", "storykit/FORMAT.md", "storykit/README.md",
         "story/saga.json", "story/cargo1.story.json"]
COPIES = {"game/record.py": "storykit/record.py"}     # copied file here -> its source in the kit


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def files_in(cargo):
    """The files to copy: the fixed list, and every source file of Cargo 1's story (its
    story file includes them)."""
    folder = os.path.join(cargo, "story", "cargo1")
    return FILES + sorted("story/cargo1/" + f for f in os.listdir(folder) if f.endswith(".json"))


def copy(cargo):
    try:
        commit = subprocess.run(["git", "-C", cargo, "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    names = files_in(cargo)
    for name in names:
        target = os.path.join(ROOT, name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(os.path.join(cargo, name), target)
    for target, source in COPIES.items():
        shutil.copy2(os.path.join(cargo, source), os.path.join(ROOT, target))
    names = names + sorted(COPIES)
    manifest = {"from": "eryxgames/Cargo", "commit": commit,
                "files": {name: digest(os.path.join(ROOT, name)) for name in names}}
    with open(MANIFEST, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print("story kit: from Cargo %s, %d files" % (commit, len(names)))


def check():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    problems = []
    for name, want in manifest["files"].items():
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            problems.append("missing: %s" % name)
        elif digest(path) != want:
            problems.append("changed here: %s (change it in the Cargo repository)" % name)
    for problem in problems:
        print("FAIL story kit", problem)
    print("story kit: from Cargo %s, %d files, %s" % (manifest["commit"], len(manifest["files"]),
                                                      "unchanged" if not problems else "%d problems" % len(problems)))
    return not problems


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    copy(sys.argv[1])
