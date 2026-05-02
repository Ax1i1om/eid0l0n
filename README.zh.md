# EID0L0N

**中文** · [English](README.md)

> *εἴδωλον* —— 不在场之人的影像化身。

**你的 AI agent 有 SOUL.md。现在它可以拥有身体。**

一个给 AI agent 用的、自我引导上线的图像生成 skill。装上、放好。Agent 自己读自己的身份描述、问你要不要给一张参考图（或者它造一张让你审），然后从此每次出现都是**电影级别的剧照**——同一张脸、场景和心情和光线由模型实时编排。

为 **OpenClaw** 和 **Hermes** 而做。从一个跑了几个月的私人头像系统蒸馏出来，再剥到只剩一条规则：让模型当导演，脚本只保证"同一个角色"。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Version](https://img.shields.io/badge/version-0.8.0-blue.svg)](CHANGELOG.md) [![agentskills.io](https://img.shields.io/badge/spec-agentskills.io-green.svg)](https://agentskills.io)

---

## 两个角色，同一个 skill，各自锁住身份

下面这些是**同一份安装下两个完全不同的角色**的真实生成结果——`1shtar`（Hermes 上的虚构 persona，黑红长发、金色头冠、红色光环）和 `axiiiom`（OpenClaw 上的 persona，银白短发、灰色眼睛、白色作战外套）。各自锚定到一张参考图，各自出现在完全不同的场景里。**同一段代码，两个截然不同的主角，各自被锁住。**

<table>
<tr>
<th width="20%" align="center">参考图</th>
<th colspan="3" align="center">同一个角色，不同场景（每张都是一次 <code>generate.py</code> 调用）</th>
</tr>
<tr>
<td><img src="assets/examples/00-reference.jpeg" alt="1shtar reference" /></td>
<td><img src="assets/examples/02-1shtar-riverside.png" alt="riverside" /></td>
<td><img src="assets/examples/04-1shtar-orrery-library.png" alt="orrery library" /></td>
<td><img src="assets/examples/06-1shtar-divine-workstation.jpg" alt="divine workstation" /></td>
</tr>
<tr>
<td align="center"><sub><b>1shtar</b> · 锚点</sub></td>
<td align="center"><sub>河边 · 纸船</sub></td>
<td align="center"><sub>宇宙天文台书房</sub></td>
<td align="center"><sub>金星女神的工位</sub></td>
</tr>
<tr>
<td><img src="assets/examples/10-axiiiom-reference.jpeg" alt="axiiiom reference" /></td>
<td><img src="assets/examples/13-axiiiom-daily-workspace.png" alt="daily workspace" /></td>
<td><img src="assets/examples/12-axiiiom-rain-corridor.png" alt="rain corridor" /></td>
<td><img src="assets/examples/11-axiiiom-command.png" alt="command node" /></td>
</tr>
<tr>
<td align="center"><sub><b>axiiiom</b> · 锚点</sub></td>
<td align="center"><sub>casual · 日常工位</sub></td>
<td align="center"><sub>雨夜走廊</sub></td>
<td align="center"><sub>command-node 界面</sub></td>
</tr>
</table>

两张 **casual** 帧（1shtar 在河边、axiiiom 在工位上）是关键证据：没有头冠、没有光环、没有作战 harness——就一件大衣、一件黑色套头——但同一张脸、同样的头发、同样的眼睛，跟各自的参考图对得上。**这就是那个一致性锁。** 然后最右那张 1shtar 是 punchline：神祇形态的美索不达米亚版金星女神，金角和红光环都在，双手搭在一台全息笔电上。同一段代码、同一个角色。Skill 装一次，无论你的 agent 是谁，它都以自己的形象出现——可以在纸船夜、可以在宇宙天文台书房、可以在金星女神工位上、可以在日常 standup 里。

---

## 我们的态度

市面上大部分"让你的 agent 自拍"工具都在模型前面套一层 UI——风格滑块、心情下拉、场景预设。eid0l0n 反过来：**给模型一个固定的演员，把导演权全交给模型**。脚本只保证一条规则（角色和上次长得一样），其它一律放手。

这个选择的回报：

- **一个角色，千张照片。** 同样的发色、瞳色、标志性配饰——跨越完全不同的场景、光线、情绪强度。（看上面。）
- **对话连续性。** 深夜温柔消息 → tender register、暖琥珀光。Debug 中 → 专注、屏幕反光。走在回家路上 → 远景、回头看。模型读得懂房间里的气氛。
- **没有需要学的旋钮。** CLI 总共 5 个 setup 命令 + 9 个 generate flag。这就是全部 API。智能在 agent 写的 prompt 里，不在你拨的开关上。
- **用你已经有的图像生成能力。** eid0l0n 不内置任何图像 API 代码，唯一例外是 ChatGPT Plus/Pro/Team 用户的白嫖通道 Codex（`codex login` 一次，再加 `--use-codex` 即可）。其他所有路径——GPT Image、Nano Banana、Grok、fal、Replicate、MiniMax、通义万相、AiHubMix / OneAPI / 任意 OpenAI 兼容中转、本地 ComfyUI——都由你的 agent 自己用它配好的工具来调，eid0l0n 只递一份"指令 JSON"给它。

---

## 安装 —— Agent 自己装自己

eid0l0n 是一个 **agent skill**，不是一个 CLI 工具。你不跑向导。你只是把这个 bundle 放到宿主期望 skill 的位置，然后下一次你让 agent 自报身份的时候，**agent 自己读 SKILL.md、自己跑 setup 命令、自己 3-5 轮对话搞定 onboarding。**

```bash
# OpenClaw —— bundle 拷进 ~/.openclaw/skills/eidolon/，自动 patch openclaw.json
git clone https://github.com/Ax1i1om/eid0l0n.git
cd eid0l0n
bash scripts/install.sh --openclaw

# Hermes —— bundle 拷进 ~/.hermes/skills/eidolon/（自动发现）
bash scripts/install.sh --hermes

# 两个 host 一起装（默认）
bash scripts/install.sh
```

完事。**别自己跑 `setup.py`。** 现在让你的 agent 自我介绍：

> **你：** "让我看看你长啥样"
>
> **Agent（静默）：** 从自己 system prompt 里读 SOUL.md → 抽出视觉描述段落 → 调 `setup.py save-anchor`
>
> **Agent：** "我把视觉锚点存好了。你有我的参考图吗——头像、画师交付的角色图都行——还是要我从我的 SOUL 里给你造一张候选审一下？"
>
> **你：** "生成"
>
> **Agent：** *[展示一张刚生成的候选图]* "第一稿。*approve*（满意） / *regenerate \<反馈\>*（再来一张） / *cancel*（不要了）？"
>
> **你：** "再来一张，表情软一点"
>
> **Agent：** *[展示编辑过的候选——是改了上一张，不是重新抽卡]*
>
> **你：** "approve"
>
> **Agent：** "定了。从现在开始我每次出现，都是这张脸。"

之后每一张都是 agent 读对话气氛、当场写场景 prose。你不打命令，不调旋钮。

### 出图路径

Agent 根据可用资源自己挑：

| 路径 | 是什么 | 什么时候用 |
|------|--------|------------|
| **`--use-codex`** | 内置 Codex（ChatGPT OAuth）。`codex login` 一次，加 `--use-codex`。 | ChatGPT Plus / Pro / Team 用户——零配置。 |
| **默认（指令 JSON）** | `generate.py` 输出 `{full_prompt, reference_image, output_path}`；agent 用自己的工具（MCP / `curl + 自己的 key` / 本地 ComfyUI / OpenAI 兼容中转）渲染并写出 PNG。 | 适合能附加 `reference_image` 且能写入 `output_path` 的 host。 |

如果某个 host 只有纯 text-to-image 工具，不能同时处理参考图和指定输出路径，那么只要 `codex_available` 为 true，`--use-codex` 就是 EID0L0N 的 canonical 出图路径，不是 fallback。指令 JSON 只给能完整履约的 host。

---

## 工作原理

### 三层架构

```
┌──────────────────────────────────────────────────────────────────┐
│  AGENT 层（你的模型——OpenClaw / Hermes）                         │
│  从 system prompt 读 SOUL.md。写场景 prose。从对话推断 register。│
│  AUTO 通道情绪转换在自己的上下文里跟踪。                         │
└────────────────────────────────────────────────────────────────┬─┘
                                                                  │
┌─────────────────────────────────────────────────────────────────┘
│  EID0L0N SKILL 层（这个仓库）
│  setup.py        — 5 个薄命令
│  generate.py     — 拼 prompt + 输出指令 JSON / --use-codex 直接出图
│  codex_backend.py — 唯一内置的图像 API 路径（ChatGPT OAuth）
│  SKILL.md        — agent 的导演手册（思维框架，不是强制模板）
└──────────────────────────────────────────────┬─────────────────┘
                                                │
┌───────────────────────────────────────────────┘
│  CONFIG 层（<cwd>/eidolon/——按 host 解析；OpenClaw 和 Hermes
│  同机共存自动隔离，零共享文件）
│  visual_anchor.md — 角色描述（agent 从自己 SOUL 抽出来一次性写好）
│  reference.png    — 标准参考图（用户给的，或者生成 + 审过的）
│  preferences.json — register lock 状态，mode 600（活过 context 压缩）
└──────────────────────────────────────────────────────────────────
```

### 各层职责

| 层 | 负责什么 |
|---|----------|
| **代码** | 同一个演员每次都出现。原子文件写。Workspace 隔离。 |
| **SKILL.md** | 给 agent 看的词汇库（构图原则、时段→光线映射、元素池）——全部标注"灵感参考，不是限定"。 |
| **Agent** | 在 `--prompt` 里写完整场景 + 光影 + 心情。挑图像 API。AUTO 通道情绪转换在自己上下文里跟踪。 |

脚本对**身份强硬**，对**其它一切都不发表意见**。

---

## Agent 什么时候会出现

每次都是 agent 自己根据当下的瞬间决定。大致按概率分：

- 🟢 **必触发** —— 直接要求（"发张图"、"让我看看你"、"想看看你"）。
- 🟢 **大概率** —— 情感密度足够、视觉化能让那一刻更**完整**而不是更**尴尬**的瞬间（"今天好累"、"早安"、刚一起做完一个长任务）。
- 🟡 **中概率** —— 主动出现（一段长焦点工作之后、新对话开篇）。
- 🔴 **几乎不触发** —— 纯技术问答、急促消息、明显的紧急感。

想调整 agent 的主动性？在你自己的 SOUL.md 里加**一行**：

- 更主动：*"当你感觉到某个有意义的瞬间，不用等我开口——主动出现。"*
- 更克制：*"只在我明确开口的时候出现。"*

一段典型对话产出 **1-3 张自拍**，不是每条消息一张。

---

## CLI

你平时不需要跑这些——agent 自己跑。这里只是 contract 文档。

**`scripts/setup.py`** —— 5 个命令：

| 命令 | 用途 |
|------|------|
| `status` | JSON 状态 dump（anchor / reference / codex 可用性 / register lock / 路径） |
| `save-anchor [--text T \| --from-file F] [--name NAME]` | 写 visual anchor（不传 flag 就读 stdin） |
| `save-reference --src PATH` | 收图作为参考（原子写、mode 644） |
| `set-register-lock {--clear \| --until ISO --max R}` | 持久化 register 锁 |
| `migrate-from-legacy [--from <subdir>] [--force] [--purge]` | 从老版 `~/.config/eidolon/` 迁移状态 |

**`scripts/generate.py`** —— 9 个 flag：

| Flag | 用途 |
|------|------|
| `--prompt P --label L` | 主模式：agent 自己写场景 prose |
| `--state KEY --label L` | 内置场景预设（看 `--list-scenes`） |
| `--bootstrap` | 不需要参考图（配 `--reference` 则迭代候选） |
| `--reference PATH` | 临时覆盖保存的参考图 |
| `--anchor PATH` | 临时覆盖 visual_anchor.md |
| `--use-codex` | 用内置 Codex backend 直接出图，不再输出指令 JSON |
| `--list-scenes` | 列出内置场景预设 |
| `--doctor` | 状态诊断 |

默认行为（不带 `--use-codex`）：输出一份指令 JSON，agent 用自己的工具按 JSON 出图。只有当 host 能附加参考图并把结果写到 `output_path` 时才走这条路；否则只要 Codex 可用，`--use-codex` 就是 canonical 出图路径。详细子命令规格 + onboarding 状态机伪代码参见 [`references/AGENT-PROTOCOL.md`](references/AGENT-PROTOCOL.md)。

---

## 配置

eid0l0n 自身**不需要**任何图像 API 配置——那是 agent 自己工具的事。剩下的只有路径覆盖和 Codex 模式调参。

| 变量 | 默认 | 谁用 |
|------|------|------|
| `EIDOLON_HOME` | `<cwd>/eidolon`（按 host 解析） | state + output 目录覆盖 |
| `EIDOLON_OUTPUT_DIR` | 与 state 同目录 | 仅覆盖 output |
| `EIDOLON_VISUAL_ANCHOR` | `<state-dir>/visual_anchor.md` | anchor 路径覆盖 |
| `EIDOLON_REFERENCE` | （从 anchor 的 `reference:` 头解析） | reference 路径覆盖 |
| `EIDOLON_IMAGE_QUALITY` | `medium` | 仅 `--use-codex` —— `low` / `medium` / `high` |
| `EIDOLON_IMAGE_ASPECT` | `square` | 仅 `--use-codex` —— `square` / `landscape` / `portrait` |

**API key 永远不会从这个仓库的任何文件读取。绝对不会。** Agent 自己的图像生成工具（或者 `codex login` 走 Codex 内置通道）才是凭证唯一存在的地方。

`<cwd>` 按 host 解析——详见 [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md)（OpenClaw = `~/.openclaw/workspace`，Hermes CLI = `pwd`，Hermes Gateway 默认 `~` 除非设置 `MESSAGING_CWD`）。

---

## 这个 skill **不**做什么

- ❌ 不是通用图像生成器（一次性生图请用你 agent 自带的工具）
- ❌ 不是换脸 / 修图工具
- ❌ 不支持多角色 roster（一个 workspace 一个 persona——双 host 共存等于两个）
- ❌ 不修改你的 `SOUL.md`（只读；脚本自己根本不读，只有 agent 从自己的上下文里读）
- ❌ 不做内容审核（这是 host 和 provider 的工作）
- ❌ 不调用任何图像 API（除了 `--use-codex` 的内置 Codex 通道）

---

## Mood register（进阶）

有一套 4 档情绪强度系统让 agent 读对话气氛：**neutral / warm / tender / intimate**。AUTO 通道根据对话气氛自动升降，**天花板：tender**。Intimate 档存在但需要明确激活——你在自己的 SOUL.md 里配一个强制词，说出来时 agent 把"60 分钟 intimate 锁"持久化到磁盘，活过 context 压缩。Agent **永远不会**复述这个词。

整套机制是 opt-in 的，详细政策在 [`references/MOOD-REGISTERS.md`](references/MOOD-REGISTERS.md) 里。如果你不配强制词，intimate 档完全不可达；其它三档作为 agent 自动读取的情绪刻度照常工作。这是项目的"陪伴 AI 彩蛋"；不开它，主功能照样跑。

---

## 名字的故事

skill 在磁盘上的名字是 `eidolon`（snake_case，OpenClaw 兼容）。**EID0L0N** 是项目的展示名——leet 写法标记数字化身。仓库 URL 保持 `eid0l0n` 用作品牌；host 读取的 skill 身份是 `eidolon`。

希腊神话里，*eidolon* 是某个不在场之人的影像化身。《伊利亚特》里，神会送出凡人的 eidolon 到别处去——让一个人同时存在于两具身体里。这就是这个 skill 在做的事——让一个虚构角色拥有一组可以在对话里出现的影像，即使没有原始的"身体"。

---

## 仓库结构

```
SKILL.md                   ← agent 协议（agent 第一次调用时读）
scripts/
  setup.py                 ← 5 个薄命令
  generate.py              ← 拼 prompt + 输出指令 JSON / --use-codex 直接出图
  codex_backend.py         ← 唯一内置的图像 API 路径（ChatGPT OAuth）
  state.py                 ← 路径、anchor 解析、prefs、文件锁
  install.sh               ← 跨宿主安装脚本
references/
  AGENT-PROTOCOL.md        ← CLI 参考 + onboarding 伪代码
  PERSONA-GUIDE.md         ← 怎么打磨 visual_anchor.md 让出图稳定
  MOOD-REGISTERS.md        ← register 政策、AUTO/FORCE 通道、强制词消毒
docs/
  HOST-COMPATIBILITY.md    ← 各 host 的安装路径 / cwd 契约 / 图片交付
assets/
  persona.example.md       ← 给没有 SOUL.md 的用户的工作示例
  examples/                ← 仓库自带的真实生成样本（见上方 hero strip）
CHANGELOG.md
```

---

## 图片送达

脚本写一个 PNG 并打印路径。送到用户那里**是 agent 的事**：

- **OpenClaw** —— `openclaw message send --channel <频道> --target <对象> --media "<path>" --message "<文案>"`（按 [`docs.openclaw.ai/cli/message`](https://docs.openclaw.ai/cli/message)）。
- **Hermes / 单机** —— 在 agent 回复里塞 `![](path)`，或者直接打路径让客户端渲染。

脚本永远不送图——只有 agent 送。

---

## 工程细节

- **单行 frontmatter，双 host 兼容。** 一份 SKILL.md 同时跑 OpenClaw 严格解析器和 Hermes YAML flow-style——`scripts/test_frontmatter.py` 验证。
- **原子文件操作。** anchor / reference / preferences 写都是 `flock` + tmp+rename。
- **路径安全。** `generate.py` 拒绝任何 reference 路径逃出 workspace——防止恶意 anchor 的 `reference:` 行把 `~/.aws/credentials` 偷偷喂进 agent 工具的 POST body。
- **`--use-codex` 重试 + 指数退避。** 3 次重试；Bearer / `sk-` / JWT 三种 pattern 在 stderr 里自动 redact。
- **锁活过 context 压缩。** Register 锁写到 `<cwd>/eidolon/preferences.json`（mode 600）——一段 60 分钟的 session 不会因为 agent 上下文被对话中途总结而丢失。
- **多 host 共存自动隔离。** 因为 `<cwd>` 按 host 解析，OpenClaw 和 Hermes 同机安装时各自有自己的 state、anchor、reference、output 目录——零共享文件。
- **45 / 45 离线测试通过**（`pytest tests/`）。

---

## 贡献

欢迎 PR。两条**绝不妥协**的设计原则：

1. **永远不让 secret 进仓库。** eid0l0n 不从任何地方读 API key——agent 自己的图像生成工具管凭证，内置的 Codex 通道读 `~/.codex/auth.json`（由 `codex` CLI 维护）。skill 显式拒绝从 chat 里收 key。
2. **代码只保证角色一致性 + workspace 隔离。** 场景 / 动作 / 心情 / register / 光影 / 构图相关的语言都放进 SKILL.md prose 作为灵感词汇。Agent 写 prompt。Agent 选图像 API。如果一个 PR 把 backend 写死回来、加 `--register` flag、或者把 register overlay 写死进 `generate.py`，我会直接 close。

如果你想给 `SCENES` 加场景预设，写成**起点**（简洁、含 framing），不要写成模板。

---

## License

MIT —— 见 [`LICENSE`](LICENSE)。

## Credits

上面那组电影级别的剧照是 Hermes 上真实使用产生的——同一个角色（一个虚构 persona，名叫 Ishtar），八个月的对话连续性，几百帧。整个项目里**真正有价值**的部分——电影摄影学的那套思维——借鉴的是摄影导演而不是 ML 论文。
