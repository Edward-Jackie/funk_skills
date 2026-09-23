# funk_skills — 个人使用的技能仓库

收集、自研的 agent skills 与全局配置的存档仓库，用于跨设备同步与备份。

## 全局配置存档

| 目录 | 内容 |
|---|---|
| `claude_config/` | Claude Code 的全局配置 `CLAUDE.md` |
| `codex_config/` | Codex 的全局配置 `AGENTS.md`：称呼/语言/对话规范/代码提交规范，以及开发完成度规范（先探后写、完成度对齐现有模块、交付前 DoD 自查） |

## 自研 skills

| 目录 | 用途 |
|---|---|
| `codemap/` | 构建跨 AI 共用的 `.map/`：默认提供任务路由、症状定位和结构化 Graph；高风险领域追加不变量、状态、幂等、补偿与验证边界。触发：/codemap、"梳理代码结构"、"怎么改 X" |
| `show_question/` | 本地 HTML 问卷表单：超过 4 题、含开放文本/滑块/矩阵评分时收集结构化信息，填完一键复制 JSON 回传，全程无网络请求 |
| `goboot/` | Go + Vue 新项目决策与初始化：本地问卷、技术栈取舍、模块化架构、目录基线和验收检查 |
| `weekly_summary/` | 根据会话历史与 git 提交记录生成本周开发周报，支持详细/精简/自定义格式 |
| `base/neko_study/` | 个性化学习教练：触发"我要学 XXX"，制定学习计划、系统掌握新技能，含学习记录模板 |
| `interview/dev-interview-coach/` | 软件工程面试教练：按简历/目标公司/岗位 JD 跑模拟面试、针对性练习、级别化提问与复盘 |

## 官方 skills 副本

| 目录 | 用途 |
|---|---|
| `docx/` | Word 文档创建、编辑、批注与格式处理 |
| `pdf/` | PDF 读取、合并拆分、表单、OCR 等全流程处理 |
| `skill-creator/` | 创建新 skill、优化已有 skill 的描述触发与评测 |

## 收录的第三方 skills（命名：`作者名-技能名`，版权归原作者）

| 目录 | 用途 |
|---|---|
| `0xbigboss-go-best-practices` | Go 类型优先开发最佳实践（自定义类型、接口、函数式选项、错误处理） |
| `92bilal26-prompt-template-designer` | 可复用提示词模板设计，沉淀重复任务的模式 |
| `JuliusBrussee-caveman-commit` | 极压缩式 Conventional Commits 提交信息生成 |
| `Litreily-codex-skill-eastern-beauty-director` | 东方美人系 AI 绘画提示词：古风/图鉴/写真/Cosplay 展会摄影 |
| `asmayaseen-browsing-with-playwright` | Playwright 浏览器自动化：导航、填表、截图、抓取 |
| `autumnsgrove-docker-workflow` | Docker 容器化完整工作流：多阶段构建、compose、镜像优化 |
| `DietrichGebert-ponytail` | 懒人资深开发模式：最少代码（YAGNI/标准库优先/一行赛五十行），含 audit/debt/gain/review 子技能，支持 20+ AI 工具 |
| `autumnsgrove-git-advanced` | Git 高级操作：交互式变基、bisect、reflog 找回、分支策略 |
| `baoyu-format-markdown` | Markdown 排版美化，输出 `*-formatted.md` |
| `codingkaiser-shell-scripting` | Bash/Zsh 脚本编写、调试与命令行自动化 |
| `hmohamed01-powershell-expert` | PowerShell 脚本/模块/GUI 开发 |
| `op7418-nanobanana-ppt-skills` | nanobanana AI 生成 PPT 的完整工作流 |
| `simonlin1212-a-stock-data` | A股数据获取：行情/研报/资金面/龙虎榜/打板/期权等 43 端点，自包含可运行代码 |
| `graphify` | 社区项目：任意输入（代码/文档/论文/图像/视频）转知识图谱并支持问答 |
| `zhanlincui-frontend-design` | 高设计质量的前端界面生成，避免模板化 AI 风格 |

## 说明

- 第三方 skill 均保留原目录结构，版权归原作者所有
- 本仓库整体许可见 [LICENSE](LICENSE)
