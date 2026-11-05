---
name: edj_byte_mv
description: 把图片转成彩色 ASCII，用 terminaltexteffects 的终端特效逐帧驱动，离线渲染成高质量 mp4（可做 macOS 动态屏保 / 桌面壁纸视频）。当用户要把图片/照片做成 ASCII 动画视频、终端特效短片、字符艺术MV，或要替换 macOS 动态屏保视频时使用。
---

# ascii_mv · 图片转 ASCII 特效视频

把静态图片变成「彩色字符 + 终端特效」的动画，离线渲染成 mp4。适合做屏保、壁纸、发布用短片。

## 什么时候用

- 用户给一批图片，要转成 ASCII 风格动画
- 想要 TTE（terminaltexteffects）那些特效（Print / Rain / Smoke / Blackhole…）但产物是**视频文件**而不是终端播放
- 要替换 macOS 动态屏保（Aerial 那套风景视频）

不适用：实时交互的终端动画（直接用 TTE CLI 就行，不必渲染视频）。

## 前置

- `uv`（用 `uv run --with ...` 隔离环境，不污染系统 Python）
- `ffmpeg` 在 PATH
- 系统等宽字体：`/System/Library/Fonts/Menlo.ttc`（Linux 换 DejaVuSansMono）

## 整体链路

```
图片 --缩放--> 亮度量化 --> 字符 + 24bit 颜色 ANSI
     --> terminaltexteffects 特效逐帧驱动
     --> 直接读 TTE 终端对象拿 (字符索引, 颜色)
     --> numpy 图集合成位图
     --> ffmpeg 管道编码 mp4
```

## 四个必须知道的坑

### 1. 不要解析 ANSI 字符串（性能杀手）

TTE 的 `for frame in effect` 返回整屏 ANSI 字符串，`get_formatted_output_string()` 每帧都会重建一次全屏字符串。210×60 的网格上，这会让单帧耗时到秒级。

正确做法：接管迭代器，直接读内部状态，并把字符串构建打空。

```python
it = iter(effect)
term = it.terminal
term.get_formatted_output_string = lambda: ""   # 关键：关掉整屏字符串构建
for _ in it:                                    # 仍然要消费迭代器来推进动画
    idx, col = grab(term, atlas)                # 自己从 _visible_characters 读
```

读取路径：
- `term.visible_top` / `term.visible_right` → 画布行列
- `term._visible_characters`，按 `character.layer` 排序（后写的覆盖先写的）
- `ch.motion.current_coord.row/column` + `term.canvas_row_offset/column_offset`
- `ch.animation.current_character_visual.symbol` 和 `. _fg_color_code`

### 2. TerminalConfig 必须走 `_build_config()`

直接 `TerminalConfig(canvas_width=...)` 会让未传的字段停留在 `ArgSpec` 占位对象上，特效内部用 `terminal_background_color` 做渐变时就会炸：

```
AttributeError: 'ArgSpec' object has no attribute 'rgb_ints'
```

正确写法：

```python
from dataclasses import replace
cfg = replace(
    TerminalConfig._build_config(),
    canvas_width=cols, canvas_height=rows,
    ignore_terminal_dimensions=True,   # 不受真实终端尺寸限制
    frame_rate=0,                      # 关掉内部 sleep
    existing_color_handling="always",  # 保留我们输入的图片颜色
)
```

### 3. 坐标系原点在左下，必须自己翻转行

TTE 内部 `terminal_state` 是**自底向上**存的，`get_formatted_output_string()` 最后用 `terminal_state[::-1]` 反转成从上到下。直接读 `_visible_characters` 时如果漏了这一步，整幅画面上下颠倒——而且动画看起来完全"正常"，只是图是倒的，极易漏检。

```python
r = rows - 1 - (ch.motion.current_coord.row + canvas_row_offset - 1)
c = ch.motion.current_coord.column + canvas_column_offset - 1
```

### 4. 每段时长要重采样，不能直接截断

TTE 每个特效的自然帧数差别极大（Print 在 213×60 上能跑三千多帧）。按目标时长均匀抽帧：

```python
if n >= target:  picks = np.linspace(0, n-1, target).round().astype(int)
else:            picks = list(range(n)) + [n-1] * (target - n)   # 补尾帧停留
```

抽帧=加速。如果加速后节奏太赶，减少每段字符量或换特效，不要硬压。

## 核心代码骨架

```python
# 图片 -> 彩色 ASCII
im = Image.open(path).convert("RGB").resize((cols, rows), Image.LANCZOS)
a = np.asarray(im, np.float32) / 255
lum = 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]
idx = (np.clip(lum,0,1)**0.72 * (len(CHARS)-1)).astype(int)
line = "".join(f"\x1b[38;2;{r};{g};{b}m{CHARS[idx[r,c]]}" for ...)

# 抓帧
idx_map = np.zeros((rows, cols), np.int16)
col_map = np.zeros((rows, cols, 3), np.uint8)
# ... 遍历 term._visible_characters 填充

# 合成（字符图集 + 颜色广播）
g = atlas[idx_map]                                    # (R,C,ch,cw)
img = g[...,None] * col_map[:,:,None,None,:]          # (R,C,ch,cw,3)
img = img.transpose(0,2,1,3,4).reshape(R*ch, C*cw, 3)
```

## 参数速查

| 参数 | 建议 | 说明 |
|---|---|---|
| `cols` × `rows` | 1080p：160×45 / **200×56（推荐）** / 240×67；4K：320×90 | 字符网格 |
| `cw` × `ch` | 1080p：12×24 / 9×19 / 8×16；4K：12×24 | 单字符像素尺寸，比约 1:2 |
| 字号 | `ch × 0.82` | 超过这个值字符会互相裁切 |
| fps | 30 | 屏保足够；60 需要成倍渲染时间 |
| CRF | 18–20 | 字符边缘多，太低会浪费码率 |

网格与输出尺寸的关系：`宽 = cols × cw`，`高 = rows × ch`。凑不整就 ffmpeg `pad` 居中补黑边。

**密度怎么选（1080p）**：字符宽 18px 视觉偏粗，12px 明显改善，**9px 是甜点**，8px 以下开始糊成噪点、失去 ASCII 味道。密度每提一档，TTE 字符数按平方涨，渲染时间随之上浮。

## 特效选择

| 特效 | 观感 | 适合 |
|---|---|---|
| Print | 逐字打印，键盘节奏 | 开场、文字类素材 |
| Rain | 字符雨落下汇聚 | 风景、大面积色块 |
| RandomSequence | 随机闪现拼合 | 高对比图 |
| Smoke | 烟雾弥散 | 暗调、氛围图 |
| Spray | 喷溅扩散 | 动感题材 |
| SynthGrid | 网格扫描 + 渐变 | 赛博/科技风 |
| Thunderstorm | 闪电照亮 | 夜景、强对比 |
| Blackhole | 黑洞吸入/吐出 | 收尾、循环 |

多图串联时每段换一个特效，段间硬切（TTE 从空白重建，天然有呼吸感）。

## macOS 屏保替换

前提：**SIP 已关**（`csrutil status` 显示 Filesystem Protections: disabled），否则改不了系统目录。

```bash
# 1. 备份（必做）
mkdir -p ~/Documents/wallpaper/screensaver_backup
cp -p "/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS/"*.mov \
      ~/Documents/wallpaper/screensaver_backup/
cp -p "/Library/Application Support/com.apple.idleassetsd/Customer/entries.json" \
      ~/Documents/wallpaper/screensaver_backup/

# 2. 看现有视频规格
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt \
  -of default=nw=1 "/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS/XXX.mov"

# 3. 替换（同名覆盖，保持 UUID 文件名）
cp new.mp4 "/Library/Application Support/com.apple.idleassetsd/Customer/4KSDR240FPS/XXX.mov"

# 4. 刷新屏保服务
killall WallpaperAgent 2>/dev/null; killall idleassetsd 2>/dev/null
```

回滚：把备份目录里的 .mov 拷回原位，再 killall 一次。

SIP 没关的方案：装 Aerial（自定义视频）或 WebViewScreenSaver（网页当屏保），不要动系统文件。

## 参考

- terminaltexteffects：https://github.com/ChrisBuilds/terminaltexteffects
- 特效展厅：https://chrisbuilds.github.io/terminaltexteffects/showroom/
- 本次实现脚本：`~/dev/work/ascii_wallpaper/`
