#!/usr/bin/env bash
# Publish generated package manifests.
#
#   packaging/publish.sh aur   [--program NAME] [--yes]
#   packaging/publish.sh npm   [--program NAME] [--yes]
#   packaging/publish.sh winget [--program NAME]
#
# Without --yes this is a dry run. AUR and npm need credentials on the machine
# (an AUR SSH key and `npm login`); WinGet is a pull request to
# microsoft/winget-pkgs and prints the exact wingetcreate command instead of
# opening one automatically.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PKG="$ROOT/packaging"
channel=${1:-}

usage() {
  cat >&2 <<'EOF'
usage: packaging/publish.sh <aur|npm|winget> [--program NAME] [--yes]

  aur      push PKGBUILD/.SRCINFO to ssh://aur@aur.archlinux.org/<pkg>.git
  npm      npm publish the wrapper package
  winget   print the wingetcreate command / fork instructions

  --yes    actually publish (aur, npm); default is a dry run
EOF
}

case "$channel" in
  aur|npm|winget) ;;
  -h|--help|help) usage; exit 0 ;;
  *) usage; exit 2 ;;
esac
shift

program=ddc
confirm=0
while (($#)); do
  case "$1" in
    --program)
      program=${2:?--program needs a value}
      shift 2
      ;;
    --program=*)
      program=${1#*=}
      shift
      ;;
    --yes)
      confirm=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "publish: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

echo "publish: checking packaging/$program"
python3 "$PKG/sync.py" --check --program "$program"

meta=$(
  python3 - "$PKG" "$program" <<'PY'
import shlex
import sys
from pathlib import Path

pkg = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(pkg))
import sync  # noqa: E402

wanted = sys.argv[2]
program = next((p for p in sync.load_catalog() if p["name"] == wanted), None)
if program is None:
    print(f"publish: unknown program: {wanted}", file=sys.stderr)
    raise SystemExit(1)

version = sync.resolve_version(program)
record = sync.check_checksums(program, version, sync.load_checksums().get(wanted))

def emit(key: str, value: str) -> None:
    print(f"{key}={shlex.quote(str(value))}")

emit("NAME", wanted)
emit("VERSION", version)
if program.get("aur"):
    emit("AUR_PKG", program["aur"]["pkgname"])
if program.get("npm"):
    emit("NPM_PKG", program["npm"]["package"])
if program.get("winget"):
    emit("WINGET_ID", program["winget"]["id"])
    urls = []
    hash_lines = []
    for arch, target in program["winget"].get("arch", {}).items():
        urls.append(sync.asset_url(program, version, target))
        hash_lines.append(f"  {arch}: {record['targets'][target]['sha256']}")
    print("WINGET_URL_ARGS=(" + " ".join(shlex.quote(url) for url in urls) + ")")
    emit("WINGET_HASH_LINES", "\n".join(hash_lines))
PY
)
eval "$meta"

case "$channel" in
  aur)
    if [[ -z ${AUR_PKG:-} ]]; then
      echo "publish: $NAME has no [program.aur] config" >&2
      exit 1
    fi
    aur_src="$PKG/aur/$AUR_PKG"
    if (( ! confirm )); then
      echo "publish: dry run — would push $AUR_PKG $VERSION to AUR"
      echo "  files: $aur_src/PKGBUILD"
      echo "         $aur_src/.SRCINFO"
      echo "  rerun with --yes to publish"
      exit 0
    fi
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    repo="$tmp/repo"
    echo "publish: cloning ssh://aur@aur.archlinux.org/$AUR_PKG.git"
    if ! git clone --quiet "ssh://aur@aur.archlinux.org/$AUR_PKG.git" "$repo" 2>/dev/null; then
      echo "publish: clone failed; initializing a first-push repository"
      mkdir -p "$repo"
      git -C "$repo" init -q -b master
      git -C "$repo" remote add origin "ssh://aur@aur.archlinux.org/$AUR_PKG.git"
    fi
    install -m 644 "$aur_src/PKGBUILD" "$repo/PKGBUILD"
    install -m 644 "$aur_src/.SRCINFO" "$repo/.SRCINFO"
    git -C "$repo" add PKGBUILD .SRCINFO
    if git -C "$repo" diff --cached --quiet; then
      echo "publish: AUR package is already at $VERSION"
      exit 0
    fi
    git -C "$repo" \
      -c user.name="${GIT_AUTHOR_NAME:-ejfkdev}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-ejfkdev@users.noreply.github.com}" \
      commit -q -m "$AUR_PKG $VERSION"
    git -C "$repo" push -q origin master
    echo "publish: pushed $AUR_PKG $VERSION to AUR"
    ;;

  npm)
    if [[ -z ${NPM_PKG:-} ]]; then
      echo "publish: $NAME has no [program.npm] config" >&2
      exit 1
    fi
    npm_dir="$PKG/npm/${NPM_PKG##*/}"
    if (( ! confirm )); then
      echo "publish: dry run — would publish $NPM_PKG $VERSION to npmjs"
      (cd "$npm_dir" && npm pack --dry-run)
      echo "  rerun with --yes to publish"
      exit 0
    fi
    if ! npm whoami --registry=https://registry.npmjs.org/ >/dev/null 2>&1; then
      echo "publish: not logged in to npmjs; run 'npm login --registry=https://registry.npmjs.org/'" >&2
      exit 1
    fi
    (cd "$npm_dir" && npm publish --access public --registry=https://registry.npmjs.org/)
    ;;

  winget)
    if [[ -z ${WINGET_ID:-} ]]; then
      echo "publish: $NAME has no [program.winget] config" >&2
      exit 1
    fi
    cat <<EOF
publish: WinGet needs a pull request to microsoft/winget-pkgs.

Option A — wingetcreate on Windows:
  wingetcreate update $WINGET_ID --version $VERSION \\
    --urls ${WINGET_URL_ARGS[*]} \\
    --submit

Option B — copy the manifests into a fork:
  $PKG/winget/manifests/${WINGET_ID:0:1}/${WINGET_ID%%.*}/${WINGET_ID#*.}/$VERSION/

  Then open a pull request against microsoft/winget-pkgs.

Pinned hashes:
$WINGET_HASH_LINES
EOF
    ;;
esac