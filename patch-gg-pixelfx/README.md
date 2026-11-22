# patch-gg-pixelfx

像素风游戏特效（VFX）技能：用 [pixelfx](https://github.com/patch-gg/pixelfx) 库以"代码即特效"的方式找、用、改、导出
244 个现成像素特效（火焰/爆炸/水系/冰/闪电/近战/命中/弹道/奥术/神圣/暗影/状态/自然/天气/UI/拾取/转场/小生物/连招），
带角色前后摇 + 命中顿帧 + 震屏的 `act` 时序，可实时播放在 canvas/Phaser/PixiJS/three.js，或烘成 sprite sheet 给
Godot/Unity/GameMaker/Defold/LÖVE/Bevy 用。

## 来源

- 上游仓库：<https://github.com/patch-gg/pixelfx>（Patch 出品，MIT，Copyright (c) 2026 Patch / Hugo Duprez）
- 本 skill 正文 = 上游官方 Claude Code 插件里的 `skills/pixelfx/SKILL.md`（v0.3.1，2026-11 取）
- 上游同时提供插件安装方式：`/plugin marketplace add patch-gg/pixelfx` → `/plugin install pixelfx@pixelfx`
  （仓库根带 `.claude-plugin/marketplace.json` 与 `plugin.json`）

## 本地改动（相对上游原文）

1. frontmatter `name` 改为 `patch-gg-pixelfx`，与目录名一致（Claude 规范要求）。
2. `description` 末尾追加中文触发词：像素特效、游戏特效、VFX、打击感、顿帧、震屏、sprite sheet 导出等。
3. 新增「本地环境（先读这一节）」：写死本机 clone 路径 `/Users/edj/dev/ai_dev/pixelfx`、零安装（只需 Node ≥18）、
   自检命令、重新 clone / 跟进上游的命令、库不在 npm 的引入方式（`npm i github:patch-gg/pixelfx` 或拷 `src/core` +
   所需 `src/fx/**`）、许可例外（`gallery/fonts` 的 Patch Pixel 字体不在 MIT 内）、Godot 社区移植地址。
4. 「Before anything」补一句：本机直接用那个 clone，不要在业务项目目录里跑 `tools/*.mjs`。
5. 「5. Publish it on Patch」标注**本地默认跳过**——那是上游平台推广，除非明确要发布。

## 依赖与验证

- 依赖一个 pixelfx checkout（见上），以及 Node ≥ 18；`ffmpeg` 可选（`--gif` / `--mp4` 预览）。
- 2026-11-23 在本机 Node 24 验证通过：
  - `node tools/list.mjs` → `244 effects`
  - `node tools/render.mjs ice/frost-nova` → `records/ice/frost-nova/contact.png`（103 帧）
  - `node tools/serve.mjs 8080` → 本地画廊 <http://localhost:8080/gallery/>
- 安装方式（与库内其他第三方 skill 一致）：目录放进本仓库 + `~/.claude/skills/patch-gg-pixelfx` 软链到本目录。
