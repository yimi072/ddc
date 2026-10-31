#!/usr/bin/env python3
"""Build the direct-install release assets for the catalog programs.

These are the artifacts users can install without a package registry account:

    ejfkdev-ddc-<version>.tgz          npm tarball
    ddc-bin-<version>-1-aur.tar.gz     PKGBUILD + .SRCINFO
    ejfkdev.ddc-<version>-winget.zip   local WinGet manifests

Every archive gets a sibling .sha256 file. `scripts/release.sh` uploads the
whole output directory to the GitHub release with --clobber.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "packaging"
sys.path.insert(0, str(PKG))
import sync  # noqa: E402


def die(message: str) -> "NoReturn":
    print(f"packaging/bundle: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksum(path: Path) -> None:
    path.with_name(path.name + ".sha256").write_text(
        f"{sha256(path)}  {path.name}\n", encoding="utf-8"
    )


def tar_file(archive: Path, members: list[tuple[Path, str]]) -> None:
    with tarfile.open(archive, "w:gz") as bundle:
        for source, name in members:
            info = bundle.gettarinfo(str(source), arcname=name)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            with source.open("rb") as handle:
                bundle.addfile(info, handle)


def zip_file(archive: Path, members: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for source, name in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, source.read_bytes())


def build_npm(program: dict, version: str, out: Path) -> Path | None:
    config = program.get("npm")
    if not config:
        return None
    npm = shutil.which("npm")
    if npm is None:
        die("npm is required to build the npm tarball")
    package_name = config["package"]
    package_dir = PKG / "npm" / package_name.split("/")[-1]
    staging = out / ".npm-pack"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    result = subprocess.run(
        [npm, "pack", "--pack-destination", str(staging)],
        cwd=package_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        die(f"npm pack failed: {result.stderr.strip() or result.stdout.strip()}")
    tarballs = sorted(staging.glob("*.tgz"))
    if len(tarballs) != 1:
        die(f"npm pack produced {len(tarballs)} tarballs, expected one")
    tarball = out / tarballs[0].name
    shutil.move(str(tarballs[0]), tarball)
    shutil.rmtree(staging)
    with tarfile.open(tarball, "r:gz") as archive:
        names = set(archive.getnames())
    required = {"package/package.json", "package/install.js"}
    missing = required - names
    if missing:
        die(f"npm tarball is missing {', '.join(sorted(missing))}")
    command = config.get("bin", program["name"])
    if f"package/bin/{command}.js" not in names:
        die(f"npm tarball is missing package/bin/{command}.js")
    if f"package/bin/{command}" in names or f"package/bin/{command}.exe" in names:
        die("npm tarball contains a downloaded binary; refusing to publish it")
    write_checksum(tarball)
    return tarball


def build_aur(program: dict, version: str, out: Path) -> Path | None:
    config = program.get("aur")
    if not config:
        return None
    pkgname = config["pkgname"]
    pkgrel = int(config.get("pkgrel", 1))
    source = PKG / "aur" / pkgname
    archive = out / f"{pkgname}-{version}-{pkgrel}-aur.tar.gz"
    members = []
    for name in ("PKGBUILD", ".SRCINFO"):
        path = source / name
        if not path.is_file():
            die(f"missing AUR file: {path}")
        members.append((path, f"{pkgname}/{name}"))
    tar_file(archive, members)
    with tarfile.open(archive, "r:gz") as bundle:
        names = bundle.getnames()
    if f"{pkgname}/PKGBUILD" not in names or f"{pkgname}/.SRCINFO" not in names:
        die("AUR bundle is missing PKGBUILD or .SRCINFO")
    write_checksum(archive)
    return archive


def build_winget(program: dict, version: str, out: Path) -> Path | None:
    config = program.get("winget")
    if not config:
        return None
    identifier = config["id"]
    source = sync.winget_dir(program, version)
    if not source.is_dir():
        die(f"missing WinGet manifest directory: {source}")
    archive = out / f"{identifier}-{version}-winget.zip"
    prefix = f"{identifier}-{version}"
    members = [
        (path, f"{prefix}/{path.name}")
        for path in sorted(source.glob("*.yaml"))
    ]
    if len(members) != 3:
        die(f"expected 3 WinGet YAML files in {source}, found {len(members)}")
    zip_file(archive, members)
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
    if len(names) != 3:
        die(f"WinGet bundle has {len(names)} entries, expected 3")
    write_checksum(archive)
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", default="ddc", help="catalog program name")
    parser.add_argument("--version", help="catalog version (default: resolved)")
    parser.add_argument(
        "--out",
        default=str(PKG / "dist"),
        help="output directory (default: packaging/dist)",
    )
    args = parser.parse_args()

    program = next(
        (item for item in sync.load_catalog() if item["name"] == args.program),
        None,
    )
    if program is None:
        die(f"unknown program: {args.program}")
    version = args.version or sync.resolve_version(program)
    record = sync.check_checksums(
        program, version, sync.load_checksums().get(args.program)
    )
    if record["version"] != version:
        die(f"checksums are for {record['version']}, asked for {version}")

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    made = [
        path
        for path in (
            build_npm(program, version, out),
            build_aur(program, version, out),
            build_winget(program, version, out),
        )
        if path is not None
    ]
    if not made:
        die(f"{args.program} has no package channel config")
    for path in made:
        print(f"{path.relative_to(out.parent)}  {path.stat().st_size} bytes")
        print(f"{path.relative_to(out.parent)}.sha256")


if __name__ == "__main__":
    main()