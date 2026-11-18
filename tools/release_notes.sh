#!/bin/sh
# The GitHub release's description for a version: .github/release-intro.md with {version} filled
# in, then that version's section of CHANGELOG.md under "New in <version>".
# Usage: sh tools/release_notes.sh 2.2.0 > notes.md   (the release workflow runs it)
set -e
version=${1:?usage: release_notes.sh VERSION}
cd "$(dirname "$0")/.."
notes=$(awk -v v="## $version" '$0==v {on=1; next} /^## / {on=0} on' CHANGELOG.md)
[ -n "$notes" ] || { echo "CHANGELOG.md has no '## $version' section" >&2; exit 1; }
if [ -f .github/release-intro.md ]; then
    sed "s/{version}/$version/g" .github/release-intro.md
    printf '\n**New in %s**\n' "$version"
fi
printf '%s\n' "$notes"
