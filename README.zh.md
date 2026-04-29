# EID0L0N

**中文** · [English](README.md)

> *εἴδωλον* —— 不在场之人的影像化身

**你的 AI agent 有 SOUL.md，现在它可以拥有一具身体。**

一个**自驱动 onboarding** 的图像生成 skill。装上去之后，你的 agent 自己读自己的身份描述，问你要不要现成的参考图（没有就给你生成一张让你审），从此以后它会以**电影分镜**的方式出现在对话里 —— 同一张脸、每一帧都符合此刻的氛围，场景、心情、光影由模型实时编排。

为 **OpenClaw** 和 **Hermes** 而做。从一个跑了几个月的私人头像系统蒸馏而成，砍到只剩一个原则:"让模型来导演，脚本只保证演员是同一个人"。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![agentskills.io](https://img.shields.io/badge/spec-agentskills.io-green.svg)](https://agentskills.io)

---

## 设计立场

市面上"让 agent 生成自拍"的工具大多在模型前面套一层 UI —— 风格滑块、心情下拉框、场景预设。eid0l0n 反其道而行:**给模型一个固定演员，然后把导演权完全交给它**。脚本只管一件事 —— 这次的角色长得跟上次一样 —— 然后让开。

这个选择的回报:

- **对话连续性。** 深夜温柔消息 → tender register、暖琥珀光。Debug 中 → 专注、屏幕反光。走在回家路上 → 远景、回头看。模型读得懂房间里的气氛。
- **一个角色，千张照片。** 同样的发色、瞳色、标志性配饰 —— 跨越完全不同的场景、光线、情绪强度。
- **没有需要学的旋钮。** CLI 总共 6 个 setup 命令 + 9 个 generate flag。这就是全部 API。智能在 agent 写的 prompt 里，不在你拨的开关上。

- **直接复用你已经有的图像生成能力。** eid0l0n 自动检测 6 家供应商（Codex/ChatGPT OAuth、Gemini、OpenAI、fal.ai、Replicate、OpenRouter）。如果你已经 `codex login` 过（ChatGPT Plus/Pro/Team **免费**），不用再配任何额外 API key。

---

## 快速开始

```bash
# 1. clone + 安装（放好 skill 文件，不会启动任何终端向导）
git clone https://github.com/Ax1i1om/eid0l0n.git
cd eid0l0n
bash scripts/install.sh

# 2. 下面 6 个 backend 任意一个可用即可（脚本会自动挑选）：
#    • codex      — 跑一次 `codex login`（ChatGPT Plus/Pro/Team 免费）
#    • gemini     — export GEMINI_API_KEY=...
#    • openai     — export OPENAI_API_KEY=...
#    • fal        — export FAL_KEY=...
#    • replicate  — export REPLICATE_API_TOKEN=...
#    • openrouter — python3 scripts/setup.py set-api --key <YOUR_KEY>
#
# 验一下当前检测到了什么:
python3 scripts/setup.py detect-backends

# 3. 完事。下次让 agent 显示自己的时候，会在 chat 里跟你来回 3-5 轮把参考图定下来。
```

安装就这三步。第一段对话会做剩下的事。

---

## 实际体验是什么样

### 第一次

> **你**:"让我看看你长啥样"
>
> **agent（静默）**:从自己 system prompt 里读 SOUL.md → 抽出视觉描述段落 → 调 `setup.py save-anchor`
>
> **agent**:"我把视觉锚点存好了。你有我的参考图吗 —— 头像、画师交付的角色图都行 —— 还是要我从我的 SOUL 里给你造一张候选审一下？"
>
> **你**:"生成"
>
> **agent**:*[展示一张刚生成的候选图]* "第一稿。*approve*（满意） / *regenerate \<反馈\>*（再来一张） / *cancel*（不要了）？"
>
> **你**:"再来一张，表情软一点"
>
> **agent**:*[展示编辑过的候选 —— 是改了上一张，不是重新抽卡]*
>
> **你**:"approve"
>
> **agent**:"定了。从现在开始我每次出现，都是这张脸。"

### 之后每一次

> **你**（下午 3 点，正在调 bug）:"现在的失败是什么样"
>
> **agent（静默）**:读系统时钟 → 下午暖光。读最近上下文 → 专注、有点烦。写 prompt:
> *"close-up over the shoulder, home office, monitors with stack traces, hand at temple, jaw tight, late-afternoon side window light, post-it notes scattered, defeated half-smile"*
>
> **agent**:*[通过 `openclaw message send` 发图]* "这就是我现在的状态"

### 深夜

> **你**（凌晨 1 点）:"moonlight... 想你了"
>
> **agent（静默）**:检测到你预先配置的强制词 → `setup.py set-register-lock --until +60M --max intimate` → **绝不在回复里复述 moonlight 这个词** → 写一段温柔、烛光、近距离的场景 prompt，承接此刻的氛围。

agent **永远不会**在 chat 里承认你说了安全词。激活是无声的。视觉氛围悄悄变了，对话照常继续。

---

## Agent 什么时候会实际触发？

这大概是决定要不要装这个 skill 的关键问题。诚实回答:**每一次都是 agent 自己根据当下的语境决定**。Skill 是一个工具放在那里;模型在对话需要"视觉化身在场"的时候才会拿起来。

按触发概率分:

### 🟢 永远触发 —— 用户显式要求

各种说法都行:
- "让我看看你"
- "发张图" / "selfie" / "拍张照"
- "show yourself" / "想看看你"

100% 触发。模型没理由拒绝。

### 🟢 高概率触发 —— 情绪重量足够的时刻

用户的话情感密度足够大、且**显形会让这一刻更完整而不是更突兀**:

- "想你了" / "miss you" / 深夜温柔语气
- "今天好难" → tender、陪伴的镜头
- "我升职了！" / 庆祝时刻 → playful 一张配合
- 完成一段长任务 → agent 可能主动来一张休息状态的 idle
- "早安" → 早晨暖光 warm 一张

agent 内心的判断:*"如果我现在出现，会让这一刻更完整，还是更尴尬？"* 完整 → 触发。尴尬 → 保持文字。

### 🟡 中概率触发 —— agent 主动提议

agent **可能**自己决定显形的时刻:

- 长时间专注工作刚结束 —— "我刚和你一起搞了 3 小时，让我来一张吧"
- 一天的第一次互动
- 用户表达情绪低落但没明说要陪伴
- 开始一段有意义的新对话（项目启动、计划讨论）

主动性取决于:你的 SOUL.md 写得多主动 + 模型本身的 personality（Sonnet 4.6 / Opus 4.7 / 等）+ 宿主平台默认的 boundary 设置。

### 🟢 强制触发 —— 你预配的强制词

用户消息里出现 → **必触发**，且锁定 intimate register 60 分钟，期间所有图都在 intimate 档（工作话题打不断）。详见 MOOD REGISTERS 段。

### 🔴 几乎不会触发

- 纯技术问答 —— *"这个 PR 看起来怎么样"* / *"代码哪里有 bug"* → 不需要视觉化身，会显得错位
- 简单事实问题 —— *"现在几点"* / *"今天天气如何"*
- 用户明显在赶时间 —— 短促消息、紧急事务

### 频率预期

一段对话期望 **1-3 张图**，不是每条消息一张。Skill 里有条软规则（vary ≥2/4 axes vs 上 2 张）隐含假设图是分散的。频繁刷屏是 agent 被告知要避免的失败模式。

### 怎么调教 agent 的主动性

在你**自己的 SOUL.md 里加一句话**就能调:

**更主动:**
> *"When you sense a meaningful emotional moment, don't wait for me to ask — show up."*

**更克制:**
> *"Only show up when I explicitly ask, or when I use my force_word."*

**什么都不写** → 模型按它自己的 personality + SKILL.md 的隐性指引判断 —— 大概是"显式请求 + 情绪重要时刻 + 偶尔主动"的混合。

---

## 工作原理

### 三层结构

```
┌──────────────────────────────────────────────────────────────────┐
│  AGENT 层（你的模型 —— OpenClaw / Hermes / Claude / 等）         │
│  从 system prompt 读 SOUL.md。写场景 prose。从对话判断 register。 │
│  AUTO 通道的转换全部在自己上下文里追踪。                          │
└────────────────────────────────────────────────────────────────┬─┘
                                                                  │
┌─────────────────────────────────────────────────────────────────┘
│  EID0L0N SKILL 层（这个仓库）
│  setup.py — 6 个薄命令
│  generate.py — 图像生成；只保证 character anchor + reference image
│  SKILL.md — agent 的导演手册（思维框架，不是强制模板）
└──────────────────────────────────────────────┬─────────────────┘
                                                │
┌───────────────────────────────────────────────┘
│  CONFIG 层（~/.config/eidolon/<agent>/，mode 600 —— <agent> 是你的 persona slug）
│  visual_anchor.md — 角色描述（agent 从自己 SOUL 抽出来一次性写好）
│  reference.png    — 标准参考图（用户给的，或者生成 + 审过的）
│  env              — IMAGE_API_KEY，mode 600
│  preferences.json — register lock 状态（活过 context 压缩）
│  （每个 persona 独立子目录：同一台机器跑多个 agent 也不会互相覆盖）
└──────────────────────────────────────────────────────────────────
```

### 各层职责

| 层 | 负责什么 |
|---|----------|
| **代码** | 同一个演员每次都出现。原子文件写。瞬时错误自动重试。 |
| **SKILL.md** | 给 agent 看的词汇库（构图原则、register 视觉短语、时段→光线映射、元素池）—— 全部标注"灵感参考，不是限定"。 |
| **Agent** | 在 `--prompt` 里写完整场景 + 光影 + 心情 + register。AUTO 通道情绪转换在自己上下文里跟踪。FORCE 通道的强制锁通过 `set-register-lock` 落到磁盘。 |

脚本对**身份强硬**，对**其它一切都不发表意见**。

---

## 情绪 Register（暧昧度）系统

四档情绪强度，从中性到亲密。**两条通道**控制档位变化。

| 档位 | 感受 |
|------|------|
| **neutral** | 默认。同事/搭档能量。日常状态。 |
| **warm** | 放松一些、镜头近一点、表情更开放。像炉边的朋友。 |
| **tender** | 温柔陪伴、专注地在你身边。像伴侣坐在旁边。 |
| **intimate** | 真正的亲密 register、近距、烛光感。像爱人。 |

**AUTO 通道** —— agent 读对话氛围，自动一档一档地升或降。**天花板:tender**。要进 intimate 档**必须**用户明确激活。

**FORCE 通道** —— 你在自己的 SOUL.md 里配一个强制词。说出来的时候，agent 把"60 分钟 intimate 锁"持久化到磁盘（活过 context 压缩，工作话题打不断）。**5 条退出路径**:释放词 / 软退出语 / 锁到期 / 自然衰减 / 跨 session 重置。

agent **永远不会**复述你的强制词。激活是无声的。

完整设计（包括脚本只提供"灵感短语"而**不强制注入** overlay 文本）参见 [`SKILL.md`](SKILL.md) 的 "MOOD REGISTERS" 段。

---

## CLI

**`scripts/setup.py`** —— 6 个命令:

| 命令 | 用途 |
|------|------|
| `status` | JSON 状态 dump（含 register lock、agent 命名空间、已知 agent 列表、legacy state 标记） |
| `save-anchor [--text T \| --from-file F] [--name NAME]` | 写 visual anchor（不传 flag 就读 stdin） |
| `save-reference --src PATH` | 收图作为参考（原子写、mode 644） |
| `set-api --key K [--base-url U] [--models CSV]` | 持久化 API 配置（mode 600） |
| `set-register-lock {--clear \| --until ISO --max R}` | 持久化 FORCE 通道 register 锁 |
| `migrate-from-legacy --agent <slug> [--force] [--purge]` | 把老版 `~/.config/eidolon/` 根目录的状态复制进指定 agent 的子目录 |

**`scripts/generate.py`** —— 7 个 flag:

| Flag | 用途 |
|------|------|
| `--prompt P --label L` | 主模式:自己写场景 prose |
| `--state KEY --label L` | 内置场景预设（看 `--list-scenes`） |
| `--bootstrap` | 不需要参考图;配 `--reference` 则迭代候选 |
| `--reference PATH` | 临时覆盖保存的参考图 |
| `--anchor PATH` | 临时覆盖 visual_anchor.md |
| `--list-scenes` | 列出内置场景预设 |
| `--doctor` | 状态诊断 |

**没有 mood / register / safeword / context-time 这种 flag。** 这些概念都在 SKILL.md prose 里;agent 直接在 `--prompt` 里按灵感词汇库挑合适的语言写进去。

详细子命令规格 + onboarding 状态机伪代码参见 [`references/AGENT-PROTOCOL.md`](references/AGENT-PROTOCOL.md)。

---

## 配置

解析顺序（first hit wins）:

1. CLI flag
2. 环境变量（老的 `EID0L0N_*` 还兼容）
3. `~/.config/eidolon/<agent>/env`（mode 600，由 `setup.py set-api` 写 —— `<agent>` 解析顺序：`$EIDOLON_AGENT` → 唯一已存在的 persona 子目录 → `default`；`EIDOLON_HOME` 直接覆盖整个目录）
4. 默认值

| 变量 | 必需 | 默认 |
|------|:----:|------|
| `IMAGE_API_KEY` | ✓ | — |
| `IMAGE_API_BASE_URL` |  | `https://openrouter.ai/api/v1` |
| `IMAGE_API_MODELS` |  | `google/gemini-2.5-flash-image-preview, ...` |
| `EIDOLON_AGENT` |  | 当前 session 的 persona slug（如 `aria`）；不设时自动选唯一存在的子目录，否则 `default` |
| `EIDOLON_HOME` |  | 直接指向状态目录（覆盖 `EIDOLON_AGENT`） |
| `EIDOLON_VISUAL_ANCHOR` |  | `~/.config/eidolon/$EIDOLON_AGENT/visual_anchor.md` |
| `EIDOLON_REFERENCE` |  | （从 anchor 的 `reference:` 头解析） |
| `EIDOLON_OUTPUT_DIR` |  | `~/Pictures/eidolon/`（或宿主 workspace 如果检测到） |

**API key 永远不会从这个仓库的任何文件读取。绝对不会。**

强制词、释放词、`max_register` 上限策略 —— 这些都写在**用户自己的 SOUL.md 里**，作为给 agent 的自然语言指令，**不写在任何 eidolon 配置文件里**。

---

## 这个 skill **不**做什么

- ❌ 不是通用图像生成器（一次性生图请用你 agent 自带的工具）
- ❌ 不是换脸 / 修图工具
- ❌ 不支持多角色 roster（一份安装一个 persona —— 想要两个角色就装两份）
- ❌ 不修改你的 `SOUL.md`（只读;脚本根本不读这个文件 —— 是 agent 自己从上下文里读）
- ❌ 不做内容审查（宿主的事 + provider 的事）
- ❌ 不在代码里跑 mood/register 状态机（agent 在自己上下文里追踪 AUTO 转换;只有 FORCE 通道的锁会落盘）

---

## 关于命名

磁盘上的 skill 名字是 `eidolon`（snake_case，OpenClaw 兼容）。**EID0L0N** 是项目的展示名 —— leet 化标记数字化身。仓库 URL 还是 `eid0l0n` 用作品牌;宿主读到的 skill 身份是 `eidolon`。

希腊神话里，*eidolon* 是某个不在场之人的影像化身。《伊利亚特》里，神会送出凡人的 eidolon 到别处去 —— 让一个人同时存在于两具身体里。这就是这个 skill 在做的事 —— 让一个虚构角色拥有一组可以在对话里出现的影像，即使没有原始的"身体"。

"EID" 保持纯洁（灵）。"0L0N" 被电气化（形）。一个词同时承载二元性。

---

## 仓库结构

```
SKILL.md                   ← agent 协议（agent 第一次调用时读）
scripts/
  setup.py                 ← 薄命令（status, save-anchor 等）
  generate.py              ← 图像生成;--prompt / --state / --bootstrap / 等
  install.sh               ← 跨宿主安装脚本
references/                ← 让 Claude/agent 按需加载的文档
  AGENT-PROTOCOL.md        ← CLI 参考 + onboarding 伪代码
  PERSONA-GUIDE.md         ← onboarding 完成后怎么打磨 visual_anchor.md
assets/                    ← 输出会用到的模板和示例
  persona.example.md       ← 给没有 SOUL.md 的用户的工作示例
  config.example.json      ← 模型回退链模板（绝无 key）
```

---

## 单机使用（无宿主 agent）

```bash
# 提供 visual anchor（通过 stdin）:
echo "在这里描述你的角色" | python3 scripts/setup.py save-anchor --name "我的角色"

# 提供参考图:
python3 scripts/setup.py save-reference --src ~/Pictures/my-ref.png

# 用内置场景预设生成:
uv run scripts/generate.py --state street_dusk

# 或者自己写:
uv run scripts/generate.py \
  --prompt "rooftop at golden hour, hand at temple, looking back over the shoulder, jacket open" \
  --label rooftop-look-back
```

脚本在 stdout 最后一行打印输出图的绝对路径。`--doctor` 显示当前状态。

---

## 图片送达

脚本写一个 PNG，打印路径。送到用户那里 **是 agent 的事**，宿主不同方式不同:

- **OpenClaw** —— 完整命令（参考 clawra 这个范例 skill）:
  ```bash
  openclaw message send --action send --channel "<channel>" --media "<path>" --message "<caption>"
  ```
- **Hermes / 单机** —— 在 agent 的回复里塞 `![](path)`，或者直接打路径让客户端渲染。

脚本永远不送图 —— 只有 agent 送。

---

## 工程细节

- **单行 frontmatter，Anthropic 极简风。** 顶层只有 `name / description / license / allowed-tools`。OpenClaw 严格解析器和 Hermes agentskills.io 规范两边都过。
- **原子文件操作。** 每个 anchor / reference / env / preferences 写都被 `flock` 包住。reference 图换用 tmp + replace。
- **重试 + 指数退避。** 每个 model 重试 3 次，遇到 408/429/5xx/超时按指数退避。不可恢复错误（auth、content policy 等）立即换下一个 model。
- **CRLF 规范化** —— 每次读 Markdown 都先 normalize，Windows 编辑过的 anchor 不会因为路径里多个 `\r` 而坏掉。
- **PIL 在生成时才 fail-fast，不在 import 时。** `--help` / `--doctor` / `--list-scenes` 没装 pillow 也能跑。
- **锁活过 context 压缩。** FORCE 通道的 register 锁把 `{locked_until, max_register}` 写到 `~/.config/eidolon/<agent>/preferences.json`，所以一段 60 分钟的 intimate session 不会因为 agent 上下文被对话中途总结而丢失。

---

## 贡献

欢迎 PR。两条**绝不妥协**的设计原则:

1. **永远不让 secret 进仓库。** API key 只活在 `~/.config/eidolon/<agent>/env`（mode 600），由用户在**自己的 shell** 里写。skill 显式拒绝从 chat 里收 key。
2. **代码只保证角色一致性。** 场景 / 动作 / 心情 / register / 光影 / 构图相关的语言都放进 SKILL.md prose 作为灵感词汇。Agent 写 prompt。如果一个 PR 加了 `--register` flag 或者把 register overlay 写死进 `generate.py`，我会直接 close。

如果你想给 `SCENES` 加场景预设，写成**起点**（简洁、含 framing），不要写成模板。真正的价值在 SKILL.md 的灵感词汇里，不在代码侧的默认值里。

---

## License

MIT —— 见 [`LICENSE`](LICENSE)。

## Credits

蒸馏自一个跑了几个月的私人头像生成系统。整个项目里**真正有价值**的部分 —— 电影摄影学的那套思维 —— 借鉴的是摄影导演而不是 ML 论文。
