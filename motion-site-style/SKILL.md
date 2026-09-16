---
name: motion-site-style
description: 按用户（大哥）定档的"动态交互网站/落地页"审美与实现规范。当任务涉及：做带 3D/滚动叙事/微交互/氛围光的高级感 landing page、hero 首屏、作品集站、品牌营销页；或要把"炫酷动效网站"想法生成成可运行项目；或提到 motionsites 那种风格、"安静+局部炸点"、"暗底单强调色"、three.js/r3f/tresjs、GSAP ScrollTrigger、Lenis 平滑滚动、framer-motion 入场动画时，加载本 skill。它锁定风格档、动效强度阈值、配色系统、Vue(默认)/React 技术栈映射、设计流程 SOP、可复用组件模板与反模式，保证产出"安静为底、流畅缓动、最多一个高光炸点"的统一质感。
---

# Motion Site Style

把"做这种高级感动态网站"从每次从零手搓，收敛成 **定档风格 + 填空流程**。以下规则均来自 7 个真实参考案例的像素量化分析，非主观臆测。

## 0. 一句话画像

> **「单色相 value scale × 安静为底 × 流畅缓动 × 每页 ≤1 个高光炸点 × 首屏叙事」**
> 暗色/亮色两套档共享同一骨架；色相随项目走，但"一个主角色、靠光不靠堆、大留白、缓动优雅、重开场轻堆料"锁死。

## 1. 何时用 / 不用

- **用**：landing page / hero 首屏 / 个人作品集 / 品牌营销页 / SaaS·AI 产品官网，要求有质感动效或 3D。
- **不用**：后台管理系统、表格/表单密集型、纯内容型强 SEO 站、要求"信息密度最大化"的页面——那些用普通栈，别硬套动效。

## 2. 风格档（两套，共享骨架）

### dark 档（主，默认）
- 背景 L∈[15,90]/255（近黑到深灰），1 深中性 base。
- 锚点组合（综合，非单一）：**开场爆发→归于安静的极克制**(b3/a72) 为基调 + **three.js 红光式高光**(b2) 为可选炸点模块 + **冷色发光**(a33) / **暖色浓烈**(mezzanine) 作强调色变体。
- 氛围靠光：径向光晕、极光底色、玻璃拟态 backdrop-blur、渐变描边、轻噪点。

### light 档
- **主锚点 = b1**：白/浅底 + 单一强调色（如深绿）value scale + 持续微动（运动量 <4）。
- 关键：亮≠廉价。靠**大留白 + 低饱和 + 一个记忆点色 + 极缓动效**保持高级感；避免满屏彩色。

### 共享骨架
单一主导色相的明度阶 + ≤1 对比点缀 + 低-中饱和 + 高留白 + 安静动效 + 首屏 Hero 绝对主角。

## 3. 配色系统（锁死）

- **1 主色相的 value scale**：用 HSL 生成同色相 5~7 档明度做画面主体（案例几乎所有主色都是"一个色相的深浅"）。
- **1 强调色 accent**：仅用于发光/描边/关键文本/CTA，占比 **≤10%**。色相不锁（冷/暖/中性皆可），锁"只此一个主角"。
- **中性 base**：暗档近黑、亮档近白。
- 饱和度：整体 **低到中**（案例 sat 0.26~0.72）；炸点区允许局部高彩高发光。
- ❌ 反模式：彩虹多色、≥2 个强色争主角、通体高饱和。

## 4. 动效三档（量化阈值，核心）

| 档 | 帧间运动量 | 何时用 | 手法 |
|---|---|---|---|
| 安静（基调） | **< 4** | 全站默认 | 一次性 reveal、hover 微光微位移、低幅呼吸循环 |
| 流畅（手段） | 4 ~ 12 | Hero + 1~2 叙事段 | GSAP 视差 / scrub / 叠字轮换 / 图文交替入场 |
| 炸点（高光） | **> 12** | **每页 ≤1（至多 2）** | three.js 3D 运镜 / 全屏 shader 流体 / 重粒子 |

**时间曲线规则（高级感关键，别漏）**：
- 主体走"**开场爆发 → 归于安静**"：入场 0.4~1.0s 内一次性 reveal 到位，之后只做低幅循环（呼吸、缓转、微视差）。
- 禁止持续高频抖动；禁止无缓动的 linear 位移。

**统一缓动令牌**：ease `cubic-bezier(0.22,1,0.36,1)` / expo-out；时长阶梯 `0.4 / 0.7 / 1.0s`；stagger `0.06~0.08s`。

## 5. 技术栈（Vue 默认；React 映射）

跨框架通用的：**GSAP(ScrollTrigger) · Lenis · three.js · Tailwind** —— 直接复用。
框架绑定的替换：

| 能力 | Vue（默认） | React（映射） |
|---|---|---|
| 构建 | Vite + @vitejs/plugin-vue | Vite + @vitejs/plugin-react |
| 组件 | `<script setup lang="ts">` | TSX / hooks |
| 平滑滚动 | Lenis composable | Lenis hook |
| 滚动时间轴 | GSAP ScrollTrigger（onMounted/onBeforeUnmount + gsap.context） | GSAP（useGSAP）|
| 入场动画 | 自研 `v-reveal` 指令(IntersectionObserver) | framer `whileInView` |
| 鼠标跟随/hover | @vueuse/core(useMouse/useMouseInElement/useRafFn)+CSS | framer-motion |
| 3D | **three 命令式封装**；重场景用 @tresjs/core(Vue版r3f)+cientos | @react-three/fiber + drei |
| 减弱动效 | usePreferredReducedMotion(归一布尔) | matchMedia hook |

## 6. 区块库（作品集 + 品牌营销取子集）

`Nav → Hero(叠字/光背景/一次性入场) → Marquee(信任或技术栈条) → 精选作品网格(hover tilt) → 品牌叙事段(scroll 视差·图文交替) → 能力/服务列表 → Quote/数据 → CTA → Footer`。
**一屏一个主角效果**，其余用安静 reveal 托场。

## 7. 设计流程 SOP（10 步）

1. 定调：受众/品牌/选 dark 或 light 档 + 一个 accent 色相。
2. 定栈：Vue 默认；按 §5 选库，锁兼容版本。
3. 搭骨架：脚手架 + Tailwind + Lenis + GSAP + `config` 分层先跑通（见 §9 starter）。
4. 背景层先行：定整页氛围（光晕/极光/shader）。
5. 叙事层：按滚动排区块，每段配"一个主效果"并定档（安静/流畅/炸点）。
6. 微交互层：hover、cursor、按钮反馈、错峰 stagger。
7. 炸点：只在 Hero 或 1 个关键节点放 ≤1 个 three.js/shader 高光，懒加载、可降级。
8. 降级与性能：reduced-motion、LCP 保 Hero、掉帧排查。
9. 内容替换：文案/图/模型接进 `config`，框架不动。
10. 交付：build + 类型检查绿、真机/触屏验证。

## 8. 落地：`config/motion.ts` 收敛模板

内容/主题/动效参数集中在一个文件，换站=改配置：

```ts
export const theme = { bg:"#05060a", base:"#0a0c12", accent:"#7cf5d4", neutral:"#8b90a0" } as const;
export const content = {
  brand:"…", nav:["Works","Studio","Contact"],
  hero:{ eyebrow:"…", lead:"…", rotating:["变快","变美","变立体"], interval:2400, sub:"…", ctaPrimary:"…", ctaSecondary:"…" },
  marquee:["REACT","THREE.JS","GSAP","LENIS","TAILWIND"],
  features:[{ title:"…", body:"…", tag:"…" }],
  closing:{ title:"…", body:"…", cta:"…" },
  footer:"…",
};
export const motion = {
  petals:96, petalRadius:2.6,
  camera:{ startZ:7.2, endZ:3.4, orbit:0.9 },   // 滚动进度→相机
  reveal:{ y:24, duration:0.7, stagger:0.06 },   // 安静档默认
  easing:"cubic-bezier(0.22,1,0.36,1)",
  blast:false,                                    // 是否启用 three.js 炸点（每页≤1）
} as const;
```

## 9. 可复用单元清单（直接抄）

starter 参考（本地已存在）：`~/dev/demo/motion-lab-vue`（Vue）、`~/dev/demo/motion-lab`（React）。核心单元：
- `lib/motionStore.ts` —— 模块级滚动进度 store（高频值不进响应式 state，供 WebGL/rAF 读取）。
- `lib/useLenis.ts` —— Lenis + GSAP ticker + ScrollTrigger 联动。
- `directives/reveal.ts` —— `v-reveal="delay"` 声明式入场（Vue）。
- `three/createFloraScene.ts` —— 命令式 three 场景：`InstancedMesh` 合批 + 滚动映射相机 + `dispose()`。
- 组件：`CursorGlow`(useRafFn lerp)、`ScrollProgress`(scaleX)、`Hero`(叠字 `<Transition>`)、`Marquee`(CSS translateX -50%)、`FeatureCard`(useMouseInElement tilt)、`Closing`(GSAP scrub)。

## 10. 性能 & 无障碍硬线（必守）

- 动画**只动 `transform`/`opacity`**（GPU 合成层），绝不在动画里改 `width/top/left`。
- 高频值走 **rAF / Lenis 回调 + motionStore**，不进响应式 state。
- 事件 `passive:true`；3D 用 `InstancedMesh` 合批、离屏暂停、GLTF 走 DRACO/KTX2 + lazy。
- WebGL 客户端挂载，SSR 不渲染。
- **全程尊重 `prefers-reduced-motion`**：炸点降级为静帧/淡入、跑马灯停、相机锁死、reveal 到位。
- 触屏隐藏 cursor glow。**LCP 优先保 Hero**，炸点资源懒加载。

## 11. 反模式（skill 级"禁止"）

通体亮底配花哨动效 · 彩虹多色/双主角色 · DOM 堆粒子 · 动画改布局属性 · 每屏重 3D · 持续高频抖动 · linear 无缓动 · 亮色档堆彩色显得廉价 · 满屏动效没有留白。

## 12. 给 AI 的生成 prompt 模板（复制改）

```
用 Vue3 + Vite + TS + Tailwind + Lenis + GSAP(ScrollTrigger) + @vueuse/core + three.js(命令式) 做一个 {dark|light} 动态落地页。
风格：单主色相的明度阶 + 1 个强调色 {accent，占比≤10%}，{暗场氛围/白底留白}，靠光(光晕/玻璃/渐变描边)不靠堆元素，大留白。
动效：安静为底(全站运动量低、一次性 reveal、缓动 cubic-bezier(.22,1,.36,1))，
仅在 {Hero / 某叙事段} 放 ≤1 个高光炸点（three.js 3D 运镜 / shader），其余克制。
区块：{Nav,Hero(叠字),Marquee,作品网格 hover tilt,品牌叙事 scroll 视差,CTA,Footer 取子集}。
工程：内容/主题/动效参数集中在 config/motion.ts；v-reveal 指令做入场；motionStore 传滚动进度；
全程只动 transform/opacity；尊重 prefers-reduced-motion。
```

## 13. 案例锚点附录（7 案例量化，回归校验用）

| 案例 | 档 | 亮度L | 暗底% | 主色 | 饱和 | 运动 | 时间形态 | 定性 |
|---|---|---|---|---|---|---|---|---|
| a33 | dark | 33 | 高 | 黑+冷紫蓝发光 | .62 | 10.5 | 持续 | 流畅·冷发光 |
| a72 | dark | 55 | 高 | 墨绿单色 | .40 | 1.9 | 持续微 | 安静·克制 |
| mezzanine | dark | 85 | 中 | 高饱和红+大地棕 | .72 | 11.8 | 持续 | 流畅·暖浓烈 |
| b1 | **light** | 182 | 0 | 白+深绿 | .26 | 1.1 | 持续微 | 安静·亮极简（**亮档锚点**）|
| b2 flowerthree | dark | 59 | 49% | 黑+红/品红发光 | .59 | **21.7** | 持续 | **炸点·three.js 3D** |
| b3 | dark | 40 | 60% | 黑+暗绿 | .50 | 1.6 | **开场爆发→静** | 安静·暗档基调（**暗档锚点**）|
| b4 | light | 111 | 7% | 天蓝+墨绿 | .40 | 3.8 | 渐入递增 | 安静偏亮·图文 |

> 规律印证：安静档运动 <4（a72/b1/b3/b4），炸点档 >12（b2/mezzanine）；主色皆"单色相 value scale"；高级感来自"开场爆发→归于安静"的时间曲线。
