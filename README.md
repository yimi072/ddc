# ddc — DEX → Java decompiler in Rust

**English** | [简体中文](README.zh-CN.md)

[![CI](https://github.com/ejfkdev/ddc/actions/workflows/ci.yml/badge.svg)](https://github.com/ejfkdev/ddc/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ejfkdev/ddc)](https://github.com/ejfkdev/ddc/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/ejfkdev/ddc/total?label=downloads)](https://github.com/ejfkdev/ddc/releases)
[![Latest release downloads](https://img.shields.io/github/downloads/ejfkdev/ddc/latest/total?label=latest%20release)](https://github.com/ejfkdev/ddc/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![crates.io](https://img.shields.io/crates/v/ddc-cli)](https://crates.io/crates/ddc-cli)
[![crates.io downloads](https://img.shields.io/crates/d/ddc-cli)](https://crates.io/crates/ddc-cli)
[![npm](https://img.shields.io/npm/v/@ejfkdev/ddc)](https://www.npmjs.com/package/@ejfkdev/ddc)
[![npm downloads](https://img.shields.io/npm/dw/@ejfkdev/ddc)](https://www.npmjs.com/package/@ejfkdev/ddc)
[![Platforms](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20Windows-blue)](#install)
[![WinGet](https://img.shields.io/badge/WinGet-ejfkdev.ddc-0078D4?logo=windows)](https://github.com/microsoft/winget-pkgs/tree/master/manifests/e/ejfkdev/ddc)

`ddc` decompiles Android DEX bytecode back into readable Java — at
real-world app scale, queryable like a database, and **javac-verified**:
every one of the 909,689 files it emits across seven real-world APKs
parses cleanly.

## Highlights

- **Fast** — a 226 MB / 20-dex APK (weibo, 98k classes) fully
  decompiles in **~21s** at high quality (**~11s** with `--fast`), a
  62 MB app (Telegram) in **~6.9s** (**~4.1s** with `--fast`); pathological classes run on deadline-bounded monitored
  threads instead of hanging the run.
- **Compiles** — the full output of all seven benchmark APKs
  (reqable, Telegram, WhatsApp, weibo, weixin, qq, lark — 0.91M
  files) passes `javac` with **zero syntax errors**; every class of
  a case-variant name pair (`X/Cua` vs `X/cua`) is preserved as
  its own file instead of the last one silently overwriting.
- **Progressive decompilation** — 15 query subcommands (strings,
  cross-references, hierarchies, manifest, resources, per-method
  decompiles) answer in milliseconds: query metadata first, decompile
  on demand, skip the full run entirely.
- **DEX 035–041, complete** — multi-dex APKs, XAPK/APKS/APKM
  containers, invoke-custom; lambdas and string concats fold back into
  real Java (`(a) -> …`, `Cls::name`, `a + b`).
- **Readable output** — jadx-style local names (`str`, `getName() →
  name`, Kotlin `Intrinsics` parameter strings) instead of `v12`;
  IntDef literals render as their constants out of the box
  (`setVisibility(8)` → `View.GONE`; a built-in android-37 domain
  table, `--symbols` overrides); Kotlin null-check noise is elided and
  synthetic `access$NNN` bridges inline at their call sites.
- **Reproducible output** — no timestamps; two runs diff cleanly.
- **Human-shaped output, by default** ([cure](https://github.com/ejfkdev/cure)):
  every file goes through a semantic-preserving source-level pass that
  inlines register-copy chains, folds if/else assignments into
  ternaries, recovers for-each, drops dead stores and compiler
  artifacts — −15% output lines on real corpora with identical
  javac-gate results. The pass is exact, so it costs time: weibo
  (110k files) takes 21 s optimized vs 10 s with `--fast` (skip
  the simplification, keep formatting).
- **HTTP REST + MCP, built in** ([xyz-rust](https://github.com/ejfkdev/xyz-rust)):
  `ddc serve` exposes every query as a REST route (GET with query
  params or POST with a JSON body) plus `GET
  /openapi.json` and a streamable MCP endpoint at `/mcp` — point an
  MCP client at `http://addr/mcp`; `ddc http` is REST-only (no
  `/mcp`); `ddc mcp stdio|http` runs the same commands as MCP tools
  with input and output schemas. Query commands take `--format
  auto|text|table|markdown|md|json|jsonl` (auto: table on a terminal,
  the stable text form when piped).
- **Bilingual CLI** — messages localize automatically
  (`DDC_LANG=zh|en` forces; English fallback).
- Built on [`jdc-core`](https://crates.io/crates/jdc-core), the
  machine-neutral core shared with
  [jcdc](https://github.com/ejfkdev/jcdc).

## Install

**macOS** (Homebrew):

```bash
brew install ejfkdev/tap/ddc
```

**Windows** (Scoop) — add the bucket once, then install by name (scoop
does not resolve a bare `user/repo/app` form — issue #3):

```powershell
scoop bucket add ejfkdev https://github.com/ejfkdev/scoop-bucket
scoop install ddc

# or install straight from the manifest URL, no bucket needed:
scoop install https://raw.githubusercontent.com/ejfkdev/scoop-bucket/main/bucket/ddc.json
```

**Windows** (WinGet) — the package is live in `microsoft/winget-pkgs`:

```powershell
winget install --id ejfkdev.ddc -e --source winget
```

**Any platform** (npm) — `@ejfkdev/ddc` is a small wrapper that downloads and
SHA-256-verifies the release binary (Node 18+):

```bash
npm install -g @ejfkdev/ddc
```

If install scripts are disabled, the `ddc` launcher downloads the binary on
first use. GitHub Packages is also available for users with a token that has
`read:packages`:

```bash
npm config set @ejfkdev:registry https://npm.pkg.github.com/
npm config set //npm.pkg.github.com/:_authToken "$GITHUB_TOKEN"
npm install -g @ejfkdev/ddc
```

Without any package registry:

```bash
# replace with the release you want
VERSION=0.1.33
npm install -g "https://github.com/ejfkdev/ddc/releases/download/v$VERSION/ejfkdev-ddc-$VERSION.tgz"
```

**cargo-binstall** (any platform — fetches the prebuilt release binary
instead of compiling):

```bash
cargo binstall ddc-cli
```

**Arch Linux** — the AUR package will be `ddc-bin`, but AUR registration is
currently closed (HTTP 503). Install the release bundle manually in the
meantime (requires `base-devel`):

```bash
# replace with the release you want
VERSION=0.1.33
curl -LO "https://github.com/ejfkdev/ddc/releases/download/v$VERSION/ddc-bin-$VERSION-1-aur.tar.gz"
tar xzf "ddc-bin-$VERSION-1-aur.tar.gz"
cd ddc-bin && makepkg -si
```

Once AUR registration reopens: `yay -S ddc-bin` or `paru -S ddc-bin`.

**Binaries**: every [release](https://github.com/ejfkdev/ddc/releases)
ships raw binaries (no archives) for `linux-amd64`, `linux-arm64`,
`windows-amd64`, `windows-arm64`, `macos-amd64` and `macos-arm64` —
non-macOS builds UPX-compressed.

**From source** (Rust stable):

```bash
cargo install ddc-cli        # from crates.io, compiles locally

# or build the checkout:
git clone https://github.com/ejfkdev/ddc && cd ddc
cargo build --release
```

Package manifests and release bundles are generated from
[`packaging/`](packaging/); see [packaging/README.md](packaging/README.md) for
AUR/WinGet/npm status and multi-program support.

## Usage

```bash
ddc app.apk                          # full decompile → app-out/
ddc app.apk -c com.example.Foo       # one class to stdout
ddc app.apk -o - | less              # everything to stdout

ddc info app.apk                      # app context (label via arsc, package,
                                      # version, md5) + per-dex counts
ddc listclasses app.apk              # package tree with class counts
                                      # (--full: raw names)
ddc mainactivity app.apk             # entry point: package + launcher
ddc findrefs app.apk string token    # every const-string "token" site
ddc getmethod app.apk Foo.toString   # one method, all overloads
ddc pkg app.apk --app -o own/        # the app's own code only
```

Full options and examples: `ddc --help` (subcommand menu grouped by
workflow). The complete reference — every option's semantics, every
subcommand's output format and behavior — lives in
[docs/cli.md](docs/cli.md) ([中文](docs/zh-CN/cli.md)).

## Performance

Seven real-world APKs, release build, measured after a
cooldown (Apple Silicon, 6P+12E). The 39-APK validation corpus (4.08M
decompiled files, per-APK wall time / peak RSS / javac parse gate) is
in [docs/validation.md](docs/validation.md)
([中文](docs/zh-CN/validation.md)).

<details>
<summary>Full decompile — 7 real-world APKs</summary>

| APK | Size | Full decompile | `--fast` | Peak RSS (full) |
|---|---|---|---|---|
| reqable | 34 MB | **0.83s** | 0.50s | 280 MB |
| Telegram | 62 MB | **6.91s** | 4.08s | 924 MB |
| WhatsApp | 139 MB | **24.98s** | 11.41s | 1067 MB |
| weibo | 226 MB | **21.03s** | 10.87s | 1380 MB |
| weixin | 268 MB | **40.21s** | 25.29s | 1497 MB |
| lark | 398 MB | **26.29s** | 14.61s | 2406 MB |
| qq | 374 MB | **57.00s** | 31.96s | 2511 MB |


Recorded 2026-10-22 with v0.1.33: one run per cell after a short settle; the previous table was recorded on an earlier (pre-cure) version; full and `--fast` are now separate columns. Peak RSS is `/usr/bin/time -l`.
</details>

Query subcommands on the same APKs (cells: time / peak RSS;
`strings -f <package> --with-locations`, `findrefs` on the package
string and method `onCreate`, `hierarchy`/`disasm`/`getclass` on each
app's launcher class):

<details>
<summary>Query subcommands — 13 commands × 7 APKs</summary>

| Command | reqable | Telegram | WhatsApp | weibo | weixin | lark | qq |
|---|---|---|---|---|---|---|---|
| `info` | 0.24s / 55MB | 0.41s / 117MB | 0.85s / 316MB | 1.32s / 569MB | 1.61s / 602MB | 2.46s / 969MB | 2.30s / 1145MB |
| `listclasses` | 0.02s / 25MB | 0.03s / 89MB | 0.04s / 96MB | 0.14s / 337MB | 0.16s / 371MB | 0.18s / 251MB | 0.24s / 311MB |
| `manifest` | 0.00s / 12MB | 0.00s / 19MB | 0.00s / 26MB | 0.01s / 48MB | 0.01s / 37MB | 0.01s / 34MB | 0.01s / 54MB |
| `mainactivity` | 0.02s / 20MB | 0.06s / 72MB | 0.08s / 136MB | 0.17s / 199MB | 0.18s / 199MB | 0.22s / 226MB | 0.31s / 300MB |
| `res` | 0.00s / 12MB | 0.00s / 20MB | 0.00s / 27MB | 0.02s / 56MB | 0.01s / 37MB | 0.01s / 36MB | 0.01s / 57MB |
| `largest` | 0.02s / 28MB | 0.05s / 71MB | 0.13s / 195MB | 0.32s / 363MB | 0.30s / 346MB | 0.46s / 519MB | 0.66s / 631MB |
| `strings` | 0.02s / 20MB | 0.04s / 55MB | 0.12s / 117MB | 0.23s / 177MB | 0.28s / 198MB | 0.18s / 192MB | 0.49s / 295MB |
| `findrefs-string` | 0.02s / 31MB | 0.03s / 74MB | 0.04s / 203MB | 0.06s / 397MB | 0.08s / 425MB | 0.04s / 322MB | 0.10s / 849MB |
| `findrefs-method` | 0.02s / 31MB | 0.05s / 81MB | 0.04s / 212MB | 0.06s / 374MB | 0.07s / 448MB | 0.07s / 581MB | 0.11s / 917MB |
| `members` | 0.01s / 19MB | 0.03s / 55MB | 0.05s / 118MB | 0.11s / 174MB | 0.11s / 180MB | 0.14s / 218MB | 0.21s / 285MB |
| `hierarchy` | 0.01s / 20MB | 0.03s / 55MB | 0.05s / 127MB | 0.10s / 174MB | 0.11s / 177MB | 0.15s / 194MB | 0.21s / 294MB |
| `disasm` | 0.01s / 19MB | 0.03s / 58MB | 0.05s / 124MB | 0.10s / 175MB | 0.11s / 182MB | 0.14s / 193MB | 0.20s / 281MB |
| `getclass` | 0.02s / 33MB | 0.21s / 131MB | 0.18s / 256MB | 0.41s / 515MB | 0.50s / 527MB | 0.70s / 830MB | 1.30s / 1200MB |

</details>

## Documentation

| | |
|---|---|
| [Architecture](docs/architecture.md) | crates, the lift/structure/emit pipeline, DEX versions, invoke-custom ([中文](docs/zh-CN/architecture.md)) |
| [CLI reference](docs/cli.md) | every option and subcommand, in detail ([中文](docs/zh-CN/cli.md)) |
| [Subcommands](docs/subcommands.md) | the progressive-analysis reference ([中文](docs/zh-CN/subcommands.md)) |
| [Benchmarks](docs/benchmarks.md) | timings, memory, methodology, ASC comparison ([中文](docs/zh-CN/benchmarks.md)) |
| [Performance engineering](docs/optimization.md) | 5min → 6s: six rounds, measured dead ends ([中文](docs/zh-CN/optimization.md)) |
| [Corpus validation](docs/validation.md) | 39 real APKs, 4.08M files, javac parse-clean, bugs found & fixed ([中文](docs/zh-CN/validation.md)) |

## Known limitations

Erased types (DEX has no Signature); d8-desugared `-$$Lambda$` classes
stay separate files; a few R8 monster methods degrade via timeout (and
a handful of deadline-truncated ones can vary between runs);
pattern-switch renders as desugared dispatch chains. The javac gate
above is a SYNTAX gate — semantic diagnostics (missing Android
classpath, and in rare register-heavy monster methods a type-confused
local) remain in the output. For scale: a full-classpath javac battery
over four corpora currently sits at ~7,500 ddc-attributable errors
across 0.91M files (v0.1.19 measured 11,345 — see
[benchmarks](docs/benchmarks.md)); jadx on the same battery lands at
roughly half that, the gap concentrated in type recovery. Details:
[architecture](docs/architecture.md).

## Testing

```bash
cargo test    # 74 tests
```

## License

[MIT](LICENSE) © ejfkdev

<div align="center">
<sub><a href="README.zh-CN.md"> 简体中文</a> · 友情链接 https://linux.do </sub>
</div>
