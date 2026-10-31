# ddc — DEX → Java 反编译器（Rust）

[English](README.md) | **简体中文**

[![CI](https://github.com/ejfkdev/ddc/actions/workflows/ci.yml/badge.svg)](https://github.com/ejfkdev/ddc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`ddc` 把 Android DEX 字节码反编译回可读的 Java —— 真实 App 级别的速度、
可以像数据库一样查询，并且**经过 javac 验证**：七个真实 APK 共
909,689 个输出文件全部零语法错误。

## 特性

- **快** —— 226MB/20 dex 的 weibo（9.8 万个类）全量反编译 **~21s**（高质量模式；`--fast` 约 **11s**），
  62MB 的 Telegram **~6.9s**（`--fast` 约 **4.1s**）；病态类跑在带截止期的受控线程上，不会拖死
  整个运行。
- **能编译** —— 七个基准 APK（reqable/Telegram/WhatsApp/weibo/weixin/
  qq/lark，共 91 万文件）的输出全部通过 javac，**零语法错误**；
  大小写仅差一位的类名对（`X/Cua` vs `X/cua`）两个类都各自成文件，
  不再后者覆盖前者。
- **渐进式反编译** —— 15 个查询子命令（字符串、交叉引用、继承谱、
  manifest、资源、方法粒度反编译）毫秒级出答案：先查元数据、按需定点
  反编译，绝大多数分析不必付全量的代价。
- **DEX 035–041 全版本** —— 多 dex APK、XAPK/APKS/APKM 容器、
  invoke-custom；lambda 与字符串拼接折叠回真 Java（`(a) -> …`、
  `Cls::name`、`a + b`）。
- **可读输出** —— jadx 式局部变量名（`str`、`getName() → name`、
  Kotlin `Intrinsics` 参数名）取代 `v12`；IntDef 魔法数字开箱即用
  按常量名渲染（`setVisibility(8)` → `View.GONE`；内置 android-37
  域表，`--symbols` 可覆盖）；Kotlin 空检查噪声消除、synthetic
  `access$NNN` 桥在调用点内联。
- **可复现输出** —— 无时间戳，两次运行 diff 干净。

- **可复现输出** —— 无时间戳，两次运行 diff 干净。
- **默认输出即人写形态**（[cure](https://github.com/ejfkdev/cure)）：每
  个文件经过语义保持的源码级优化 pass——寄存器拷贝链内联、if/else
  赋值折叠为三元、for-each 还原、死存储与编译器产物清除，真实语料
  **输出行数 −15%** 且 javac 门结果不变。优化是精确的，所以花时间：
  weibo（11 万文件）优化后 21 s，`--fast` 跳过简化仅保格式为 10 s。
- **HTTP REST + MCP，开箱内置**（[xyz-rust](https://github.com/ejfkdev/xyz-rust)）：
  `ddc serve` 把每个查询命令暴露为 REST 路由（GET 绑 query 参数，
  POST 亦接受 JSON body）+ `GET /openapi.json` +
  流式 MCP 端点 `/mcp`（MCP 客户端直接指向 `http://地址/mcp`）；
  `ddc http` 是纯 REST 形态（不挂 `/mcp`）；`ddc mcp stdio|http` 把
  同一批命令作为带输入/输出 schema 的 MCP 工具运行。查询子命令支持
  `--format auto|text|table|markdown|md|json|jsonl`（auto：终端表格、
  管道输出稳定文本）。
- **中英双语 CLI** —— 按环境变量自动识别语言（`DDC_LANG=zh|en` 强制
  指定，回退英文）。
- 基于 [`jdc-core`](https://crates.io/crates/jdc-core) —— 与
  [jcdc](https://github.com/ejfkdev/jcdc) 共用的机器无关反编译核心。

## 安装

**macOS**（Homebrew）：

```bash
brew install ejfkdev/tap/ddc
```

**Windows**（Scoop）——先添加 bucket，再按名安装（scoop 不识别
`user/repo/app` 三段式直装——issue #3）：

```powershell
scoop bucket add ejfkdev https://github.com/ejfkdev/scoop-bucket
scoop install ddc

# 或者不添加 bucket，直接用 manifest URL 安装：
scoop install https://raw.githubusercontent.com/ejfkdev/scoop-bucket/main/bucket/ddc.json
```

**cargo-binstall**（全平台——直接下载预编译 release 二进制，不用本地
编译）：

```bash
cargo binstall ddc-cli
```

**二进制**：每个 [release](https://github.com/ejfkdev/ddc/releases) 附带
裸二进制（无压缩包），覆盖 `linux-amd64`、`linux-arm64`、
`windows-amd64`、`windows-arm64`、`macos-amd64`、`macos-arm64`——非
macOS 平台已 UPX 压缩。

**其他包渠道**：Arch（AUR `ddc-bin`）、Windows Package Manager
（`ejfkdev.ddc`）与 npm（`@ejfkdev/ddc`）的清单在
[`packaging/`](packaging/) 中生成；AUR、WinGet、npm 尚待发布（状态与命令
见 [packaging/README.zh-CN.md](packaging/README.zh-CN.md)）。catalog 支持
多个二进制程序，后续程序可复用同一套渠道。

**源码构建**（Rust stable）：

```bash
git clone https://github.com/ejfkdev/ddc && cd ddc
cargo build --release
```

## 用法

```bash
ddc app.apk                          # 全量反编译 → app-out/
ddc app.apk -c com.example.Foo       # 单类输出到 stdout
ddc app.apk -o - | less              # 全部输出到 stdout

ddc info app.apk                      # App 上下文（应用名、包名、版本、
                                      # md5）+ 每镜像计数
ddc listclasses app.apk              # 带类数的包目录树
                                      # （--full：原始全量）
ddc mainactivity app.apk             # 入口：包名 + 启动 Activity
ddc findrefs app.apk string token    # 每个 const-string "token" 引用点
ddc getmethod app.apk Foo.toString   # 单方法，含全部重载
ddc pkg app.apk --app -o own/        # 只反编译 App 自身代码
```

完整选项与示例见 `ddc --help`（按工作流分组的子命令菜单）。更详细的
完整参考 —— 每个选项的语义、每个子命令的输出格式与行为 —— 见
[docs/zh-CN/cli.md](docs/zh-CN/cli.md)（[English](docs/cli.md)）。

## 性能

七个真实 APK，release 构建，冷机后实测（Apple Silicon 6P+12E）。
39 个 APK 的验证语料（408 万个反编译文件，每个 APK 的墙钟 /
峰值 RSS / javac 解析门）见
[docs/zh-CN/validation.md](docs/zh-CN/validation.md)
（[English](docs/validation.md)）。

<details>
<summary>全量反编译 —— 7 个真实 APK</summary>

| APK | 大小 | 全量反编译 | `--fast` | 峰值 RSS |
|---|---|---|---|---|
| reqable | 34 MB | **0.83s** | 0.50s | 280 MB |
| Telegram | 62 MB | **6.91s** | 4.08s | 924 MB |
| WhatsApp | 139 MB | **24.98s** | 11.41s | 1067 MB |
| weibo | 226 MB | **21.03s** | 10.87s | 1380 MB |
| weixin | 268 MB | **40.21s** | 25.29s | 1497 MB |
| lark | 398 MB | **26.29s** | 14.61s | 2406 MB |
| qq | 374 MB | **57.00s** | 31.96s | 2511 MB |


记录于 2026-10-22，v0.1.33：每个单元格一次运行（短暂静置后）；旧表来自更早的版本（cure 之前）；现在“全量”和 `--fast` 分列。峰值 RSS 来自 `/usr/bin/time -l`。
</details>

同一批 APK 上的查询子命令（单元格：耗时 / 峰值 RSS；`strings -f <包名>
--with-locations`，`findrefs` 查包名字符串与方法 `onCreate`，
`hierarchy`/`disasm`/`getclass` 用各 App 启动类）：

<details>
<summary>查询子命令 —— 13 个命令 × 7 个 APK</summary>

| 子命令 | reqable | Telegram | WhatsApp | weibo | weixin | lark | qq |
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

## 文档

| | |
|---|---|
| [架构](docs/zh-CN/architecture.md) | 三个 crate、提升/结构化/输出管线、DEX 版本、invoke-custom（[EN](docs/architecture.md)） |
| [CLI 参考](docs/zh-CN/cli.md) | 全部选项与子命令详解（[EN](docs/cli.md)） |
| [子命令](docs/zh-CN/subcommands.md) | 渐进式分析完整参考（[EN](docs/subcommands.md)） |
| [基准](docs/zh-CN/benchmarks.md) | 耗时/内存、方法论、与 ASC 对比（[EN](docs/benchmarks.md)） |
| [性能工程](docs/zh-CN/optimization.md) | 5 分钟 → 6s：六轮优化与实测排除的捷径（[EN](docs/optimization.md)） |
| [语料验证](docs/zh-CN/validation.md) | 39 个真实 APK、408 万文件全部 javac 解析零错误，含发现并修复的 bug 清单（[EN](docs/validation.md)） |

## 已知限制

擦除类型（DEX 无 Signature）；d8 反糖的 `-$$Lambda$` 类独立成文件；极少数
R8 巨兽方法超时降级（个别被墙钟截止截断的类输出可能随运行浮动）；
pattern-switch 呈现为反糖分发链。上述 javac 门控是**语法**门——语义级
诊断（缺 Android classpath、极少数寄存器密集巨兽方法中的类型混淆局部
变量）仍会存在。量级参考：带完整 Android classpath 的 javac 电池在四
语料上当前约 7,500 个 ddc 侧错误 / 91 万文件（v0.1.19 时为 11,345，
见[基准文档](docs/zh-CN/benchmarks.md)）；jadx 同电池约为其一半，差距
集中在类型恢复。详见[架构文档](docs/zh-CN/architecture.md)。

## 测试

```bash
cargo test    # 74 个测试
```

## 许可

[MIT](LICENSE) © ejfkdev
