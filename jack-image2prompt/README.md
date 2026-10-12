# jack-image-to-prompt

把一张参考图逆向拆解成结构化字段，再渲染成各家生图模型的 prompt。

## 三条使用路径

### 路径一：可视化工作台（推荐日常用）

```bash
open ~/.claude/skills/jack-image-to-prompt/assets/workbench.html
```

1. 载入参考图（点击 / 拖拽 / Ctrl+V 粘贴）
2. 填接口配置：Base URL、API Key、拆解用模型名
3. 自动请求，左侧显示从原图采样出的真实主色
4. 勾选目标平台，右侧实时出结果，逐个复制

配置和勾选状态会存本机 localStorage，下次打开还在。密钥默认不存，需手动勾选「记住密钥」。

### 路径二：命令行单图分析

```bash
export IMAGE_API_KEY=sk-xxx
export IMAGE_API_BASE=https://proxy.example.com/v1
export IMAGE_API_MODEL=qwen3.8-flash

python3 scripts/analyze.py --image ref.png
python3 scripts/analyze.py --image ref.png --platform mj --platform sd --out result.json
```

### 路径三：批量打标（LoRA 数据集）

```bash
python3 scripts/batch.py --dir ./images --out ./captions.jsonl --workers 4
```

支持断点续跑——已处理的图片会自动跳过，失败的图重跑一次即可。

## 装 Pillow（强烈建议）

没装 Pillow 时脚本仍能跑，但会有两个降级：

| 功能 | 有 Pillow | 无 Pillow |
|---|---|---|
| 色板采样 | 从像素算出真实主色 | 回退用模型描述（**不准，偏亮约 40**） |
| 图片压缩 | 压到长边 768，约 33 KB | 原图直传，**实测 1636 KB** |

装法（macOS 的 python3 是 externally-managed，直接 `pip install` 会被 PEP 668 拦下）：

```bash
# 给 skill 建独立环境
uv venv ~/.claude/skills/jack-image-to-prompt/.venv --python 3.12
uv pip install --python ~/.claude/skills/jack-image-to-prompt/.venv/bin/python Pillow

# 之后用这个解释器跑
~/.claude/skills/jack-image-to-prompt/.venv/bin/python scripts/analyze.py --image ref.png
```

或者干脆用 `uv run`：

```bash
uv run --with Pillow scripts/analyze.py --image ref.png
```

**注意**：装包时如果卡在 SSL 错误或连接重试，是系统代理干的，先 `unset HTTPS_PROXY`。

## 接口要求

任何 OpenAI 兼容的 `POST /v1/chat/completions`，支持 `image_url` 传 base64 即可。

工具本身不绑厂商，也**不存任何密钥**——密钥只在你填的地方和请求头里。

## 常见问题

**报 `Proxy CONNECT aborted` / `EXIT=56`**

系统代理掐断了连接。脚本会自动检查并提示；命令行下：

```bash
unset HTTPS_PROXY
# 或
curl --noproxy '*' ...
```

**浏览器里报 `Failed to fetch`**

接口没带 CORS 头。用工作台的「复制 curl」按钮，把命令拿到本地终端跑。

**色板全是一个颜色**

源图是纯色背景或者大面积单色。这是正常的，采样只反映画面实际构成。

**MJ 输出里 `--ar` 是错的**

长宽比来自 `[技术]` 字段的正则抽取。如果模型没在 `[技术]` 里写长宽比，就不会有 `--ar`。这是设计如此——宁可没有，也不要编一个错的。

## 目录

```
jack-image-to-prompt/
├── SKILL.md               # 给 Claude 看的：流程、契约、禁令、边界
├── README.md              # 给人看的：怎么装、怎么用
├── assets/
│   └── workbench.html     # 可视化工作台
├── scripts/
│   ├── analyze.py         # 单图分析
│   └── batch.py           # 批量打标
└── references/
    ├── platforms.md       # 各平台语法规则
    ├── pitfalls.md        # 实测踩坑清单（最有价值）
    └── security.md        # 密钥处理规范
```

## 边界

- **不承诺 100% 还原**。纯文字通道语义天花板 90~95%。要更高得让生成模型吃参考图，走编辑模式。
- **不承诺精确计数**。模型会诚实标 `unknown`，但不会纠正自己数错。
- **不处理小字号文字**。大字号能读对，画面里的微小文字只能 `unknown`。
- **不做敏感内容**。
