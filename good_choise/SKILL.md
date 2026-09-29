---
name: good_choise
license: MIT
description: >
  Build AI-powered software with TypeSafe: small units of AI intelligence you
  can use like programming primitives. Its System One models, including Jev,
  turn natural language and application state into typed judgments and
  probabilities that code can combine. Use when a feature needs programmable
  common sense, when brainstorming what AI could make possible in an app, or
  when an LLM prompt-and-parse step could become a structured decision.
  Applications include routing, ranking, extraction, verification, and
  interactive experiences; these are starting points, not the limits.
  Read live docs and cookbooks to find useful patterns and discover new combinations.
  在本机环境中该能力默认通过阿里云百炼（Model Studio / DashScope）的 `decision-model-preview`
  决策模型接入，而非 api.typesafe.ai；涉及百炼、Model Studio、DashScope、decision-model-preview、
  systemone、决策模型、结构化判定/分流/置信度路由时同样适用本技能。
---

# Build with TypeSafe

TypeSafe makes units of AI intelligence usable like programming primitives: small
judgments you can compose into larger capabilities. Its **System One models** return
fast, focused judgments that software can consume directly. **Jev** is TypeSafe's
flagship and first System One model. It understands natural language and returns
typed answers and probabilities rather
than generating text or reasoning explanations. Code owns the workflow; the model
supplies programmable common sense where ordinary code needs semantic understanding.

## 本地默认接入：阿里云百炼（决策模型）

> 本节是本地改造，**是本环境唯一的调用口径**，覆盖下方官方文档给出的默认 transport。协议、问题设计、patterns、cookbooks 照用，只有"打到哪里、叫什么名、哪些参数能传"按本节改写。**硬约束：本 skill 一律只调用阿里云百炼；禁止生成或执行任何指向 `api.typesafe.ai`、`dashscope.aliyuncs.com`、Packy 或其它中转的 curl / SDK / Go 代码，也禁止使用 `jev-*` 模型名。** 概念与方法论可以读 TypeSafe 文档，但落地调用只认百炼。

**环境变量（base_url / model / api_key 的唯一来源）**

| 变量 | 含义 | 示例 |
| --- | --- | --- |
| `BAILIAN_BASE_URL` | compatible-mode 根地址（业务空间专属域名，**不含** `/v1/systemone`） | `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode` |
| `BAILIAN_DECISION_MODEL` | 决策模型名 | `decision-model-preview` |
| `BAILIAN_API_KEY` | 该业务空间的 API Key | `sk-…`（仅存本地，绝不出现在代码/仓库/日志） |

- 本机配置位置：`~/.config/bailian.env`（权限 600，不在任何 git 仓），由 `~/.zshrc` 与 `~/.zprofile` source；从终端启动的 Claude Code / Codex / opencode 均自动继承这三个变量。
- 生成代码时**一律引用变量名**（`$BAILIAN_BASE_URL` / `${BAILIAN_DECISION_MODEL}` / `$BAILIAN_API_KEY`），不得写死真实域名或 key；拿不到变量时先报错提示用户配置，不要回退到任何官方/中转域名。
- 注意兼容旧名：若只见 `DASHSCOPE_API_KEY` 而无 `BAILIAN_API_KEY`，可临时用 `${BAILIAN_API_KEY:-$DASHSCOPE_API_KEY}`。

**端点（唯一入口，实测有效）**

```
POST ${BAILIAN_BASE_URL}/v1/systemone
```

- 必须用**业务空间专属域名**（已含在 `BAILIAN_BASE_URL` 里）。`dashscope.aliyuncs.com/compatible-mode/v1/systemone` 会返回 **404**（该 path 没挂在通用域名上）；`/v1/chat/completions` 也不行，此模型只支持 `systemone` 一个端点。
- `{WorkspaceId}` 取百炼控制台左上角业务空间 ID，且 API Key 必须属于**同一个业务空间**（跨空间调用报 401/404）。
- 鉴权：`Authorization: Bearer $BAILIAN_API_KEY`。Key 只从环境变量读，**禁止写进源码、配置示例、提交历史或日志**。

**模型名**：从 `${BAILIAN_DECISION_MODEL}` 读取，当前值为 `decision-model-preview`。`jev-latest`、`jev-preview`、`jev-1.13.0` 这些官方别名在百炼无效。响应里的 `model` 字段会回显 `decision-model-preview`，无版本可比对。

**请求体只有三个字段**：`model`、`state`、`questions`。没有 temperature/top_p/response_format 之类，也不生成文本。

| 项 | 百炼口径 | 与官方 Jev 的差异 |
| --- | --- | --- |
| `state` | String / Object / Array，**纯文本**（图片、音频、视频需先转文本） | 一致 |
| `questions.<id>.type` | `choice` / `noul` / `score` | 一致 |
| `questions.<id>.instructions` | **只接 String** | ⚠️ 官方支持的 `{question, focus, inspect, compare}` 对象式写法在百炼**不能用**，必须压成一句话 |
| `criteria`（choice） | 选项名 → 描述 的 Object，1–255 项 | 官方允许的 `{what, not_for, examples}` 嵌套描述在百炼同样降为字符串 |
| `criteria`（score） | 由低到高的描述 Array，2–255 级（建议 3–7） | 同上 |
| `criteria`（noul） | 可选 `{"true": …, "false": …}` | 一致 |
| 路径引用 | 反引号点路径照样有效，例如 `` `candidates[0].exertion` `` | 一致，是提准数的首选手段 |
| 上下文 | 65536 token；`state` + 最长问题 ≤ 32k | 一致 |
| 问题数 | 接口不设上限，**建议 ≤ 16**，延迟随问题数近线性增长 | 一致 |

**响应**：`answers.<id>`（`choice` / `noul` / `score` / `probabilities` / `confidence` / `legend`）、`usage.input_tokens`、`latency_ms`、`request_id`、`model`。`confidence` 只在 `choice` 与 `score` 上返回，`noul` 只有 P(yes)。`request_id` 记得落日志，工单排查要用。

**配额与价格**：当前**限时免费**；华北2（北京）默认 RPM 1200 / TPM 2,000,000。实测单请求延迟约 58 ms。计费与限流以百炼模型页实时数据为准，别照抄本节数字。

**语言**：上游 Jev 以英文为主训练语言，中文可用但判断更易挤在 0.5 附近。**默认把 `instructions` 和 `criteria` 写成英文**，业务原文留在 `state`。

**SDK 写法（已验证可跑）**：官方 `typesafe-sdk` 直接把 `base_url` 指向 compatible-mode 即可，SDK 自己拼 `/v1/systemone`。

```python
import os
from typesafe_sdk import TypeSafeClient

client = TypeSafeClient(
    api_key=os.environ["BAILIAN_API_KEY"],
    base_url=os.environ["BAILIAN_BASE_URL"],
)
result = client.system_one(
    model=os.environ["BAILIAN_DECISION_MODEL"],
    state={"content": "Order paid, service still down after 24 hours."},
    questions={"escalate": {"type": "noul", "instructions": "Should we page on-call now?"}},
)
print(result.answers)
```

**curl 最小可用样例**

```bash
test -n "$BAILIAN_BASE_URL" && test -n "$BAILIAN_API_KEY" || { echo "缺少 BAILIAN_* 环境变量，请先配置 ~/.config/bailian.env"; exit 1; }
curl -sS -X POST "${BAILIAN_BASE_URL}/v1/systemone" \
  -H "Authorization: Bearer ${BAILIAN_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d @- <<EOF
{"model":"${BAILIAN_DECISION_MODEL:-decision-model-preview}","state":{"content":"Order paid, service still down after 24 hours."},"questions":{"escalate":{"type":"noul","instructions":"Should we page on-call now?"}}}
EOF
```

**通路唯一性**：本 skill 在本机只经 `BAILIAN_BASE_URL` 指向的阿里云百炼空间调用该模型。不要生成任何指向 TypeSafe 官方（`api.typesafe.ai`）、Packy（`cf.api.fan`）或其它中转的代码；上方 SDK 示例里的 `typesafe-sdk` 之所以可用，只是因为把 `base_url` 指到了百炼 compatible-mode，SDK 只是客户端、不代表走官方接口。

## Read the live docs

**The live TypeSafe docs are the source of truth. Read them as part of the task.**
This skill gives direction; the docs carry current concepts, prompting guidance,
API contracts, SDK usage, models, limits, and worked examples.

> 读官方文档时只取**概念、问题设计、patterns、cookbooks**；文档里出现的 endpoint、模型名、
> `instructions` 对象式写法等 transport 细节，一律以顶部「本地默认接入：阿里云百炼」为准改写。

- Start with the [documentation index](https://docs.typesafe.ai/llms.txt) to discover
  relevant pages and cookbooks. Use targeted reads rather than loading the entire site.
- Mintlify serves Markdown by appending `.md` to a page path, for example
  [how to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md).
  Follow links from the index; convert extensionless documentation page links to
  `.md` when useful. Resolve relative links against `https://docs.typesafe.ai`.
- Before writing an integration, read the current API or chosen SDK page and the
  question guidance relevant to the design. For a new workflow, also inspect the
  closest cookbook: it often shows a better decomposition than a generic classifier.
- If the index is unavailable, use the direct links below or the site's navigation.
  If Markdown fetching fails, try the normal page. If live access is unavailable,
  use available local docs or installed SDK types, state that limitation, and avoid
  inventing version-dependent details.

| Task | Start here; follow the relevant details |
| --- | --- |
| Understand the programming model | [System One](https://docs.typesafe.ai/concepts/system-one.md), [building guide](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md) |
| Explore what to build | [Use-case map](https://docs.typesafe.ai/concepts/use-case-map.md), then relevant cookbooks from the index |
| Prepare inputs and questions | [State](https://docs.typesafe.ai/concepts/state.md), [primitives](https://docs.typesafe.ai/primitives.md), then the chosen primitive's page |
| Decide how to handle uncertainty | [Confidence](https://docs.typesafe.ai/confidence.md) |
| Write API code | [HTTP API](https://docs.typesafe.ai/api.md), [Python SDK](https://docs.typesafe.ai/sdk/python.md), or [JavaScript SDK](https://docs.typesafe.ai/sdk/javascript.md) |
| Update an older integration | [Migration guide](https://docs.typesafe.ai/migrating-to-v1.md) and the installed SDK's current reference |

## Find the useful shape

Start from the behavior the user wants: what will the application show, select,
change, or hand off? Work backward to the judgments it needs. Keep known rules,
calculations, exact lookups, and execution in code. Preserve the user's chosen stack
and scope; add TypeSafe where semantic understanding helps.

When brainstorming or choosing an architecture, consider more than classification.
The patterns below are starting points: combine primitives around the user's goal,
including ideas that do not fit an established recipe.

- **Route and fill known arguments.** A request can select a handler and its typed
  parameters. Ask useful branch-specific questions up front and consume only the
  relevant answers. Explore [function calling](https://docs.typesafe.ai/cookbooks/function_calling.md)
  and [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out.md).
- **Select instead of generate.** Find candidate values or source spans in code,
  use a judgment to select the intended one, then copy or normalize it. Code can
  also assemble source text into a formatted document or reading guide. Explore
  [value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md)
  and [structure recovery](https://docs.typesafe.ai/cookbooks/autoformat.md).
- **Find and judge evidence.** Retrieve candidates, compare their relevance to a
  query, and select useful context. Explore [reranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md)
  and [hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification.md).
- **Turn judgments into reusable data.** Score dimensions once, then let code or
  user controls change weights, thresholds, rankings, and views. With labeled
  outcomes, those signals can become classical ML features. Explore
  [composite scoring](https://docs.typesafe.ai/patterns/composite-scoring.md) and
  [feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md).
- **Verify and escalate.** Check specific claims or fields against their evidence;
  send uncertain or failing cases to a person or reasoning model. Explore
  [citation checks](https://docs.typesafe.ai/cookbooks/citation_check.md) and
  [extraction cascades](https://docs.typesafe.ai/cookbooks/sde_cascade.md).
- **Respond to changing state.** Code can retain goals and observations while fresh
  judgments guide the next bounded step. Keep inferred state distinct from observed
  facts, and check freshness before applying a result to a changed situation.

For open-ended requests, offer the few directions that best serve the user's goal
and recommend a starting point. For a concrete request, choose the relevant pattern
and build; a brainstorm is not a mandatory detour.

## Design the judgments

Choose by what the answer means, then read the relevant primitive page:

| Need | Primitive | Important distinction |
| --- | --- | --- |
| One of a defined set | [Choice](https://docs.typesafe.ai/primitives/choice.md) | Picks one option; its distribution compares competing options |
| Whether a condition holds | [Noul](https://docs.typesafe.ai/primitives/noul.md) | Probability of yes; no separate confidence; use one per label when several may apply |
| Degree along a described dimension | [Score](https://docs.typesafe.ai/primitives/score.md) | Probability-weighted position on ordered levels; use comparable per-item Scores for graded ranking |

Give each question enough relevant **state** to answer: source text, identities,
relationships, policies, and current facts. Prefer named JSON fields when context
has several parts. Put the judgment in **instructions** and define its possible
answers in **criteria**. Question IDs are for code and are not sent to the model;
include complete meaning in the question. Reference nested state with backticked
paths such as `ticket.messages[0].text`.

Ask one narrow, coherent judgment per question. Split independently useful dimensions,
without destroying the relationship being judged. A bounded action selection or
contextual interpretation is valid; atomic does not mean literal fact extraction
or a one-sentence limit. Strings work for simple questions. Use structured objects
or arrays when definitions, contrasts, exclusions, or examples clarify instructions
or criteria. Score levels must describe concrete situations and stand on their own.
（百炼侧例外：`instructions` 只接 String，`criteria` 里每个选项/等级的描述也必须是字符串；
上方「本地默认接入」已说明，结构化对象写法仅在 api.typesafe.ai 直连时可用。）

Keep the needed answers available. Include a no-match outcome when nothing may fit;
use a separate presence judgment when it is independently useful. For source-value
selection, check candidate coverage: the model cannot choose an omitted value.

## Compose and verify

**Ask independent questions over the same state together**, including useful
speculative questions. They run in parallel and cannot see one another's answers.
State each speculative premise explicitly; code consumes the applicable answers.
A second request is warranted when an earlier answer is needed to fetch evidence,
construct new state, or determine the next options. Extra questions still use tokens;
measure actual request budgets, cost, and end-to-end latency.

Use probabilities and confidence to guide behavior, with thresholds evaluated on
the user's data and consequences. Choice/Score confidence summarizes distribution
concentration, not overall workflow correctness or permission to act. A Noul near
0.5 means similar probability for yes and no, not medium intensity. Several
acceptable alternatives can also spread probability; low confidence need not
invalidate a harmless preference choice. Ignore uncertainty on unused branches.

Keep policy explicit and raw judgments reusable. Weighted scores suit compensating
preferences; an “any serious violation” rule needs separate conditions. Changing a
weight or display filter need not rerun inference when evidence and question meanings
are unchanged. Typed output guarantees the interface, not truth. System One models
are trained for calibrated decisions; validate their performance in the target domain.

Test representative cases and the resulting application behavior. For failures,
inspect the exact state, questions, candidates, answers, composition, and observed
outcome. Separate missing evidence, model errors, code errors, and service failures.
Treat cookbook thresholds and demo results as examples to evaluate, not universal
rules or permanent model limitations. Keep API credentials server-side in web apps.
