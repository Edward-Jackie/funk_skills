# 实测踩坑清单

> 这份清单来自一轮真实测试（模型 `qwen3.8-flash`，测试图：仙侠人像 1024×1536、macOS 图标 1024×1024）。
> 每条都附了实测数据，不是推测。

## 一、色值必须采样，不能问模型

**现象**：同一张仙侠人像，模型报的色板和从原图像素采样的实际结果对不上。

| 模型报的 | 最接近的实际色 | RGB 距离 | 亮度差 |
|---|---|---|---|
| `#A8C0E0` | `#A8B8E8` | 11.3 | +5 |
| `#E8F0F8` | `#B8C8E8` | 64.5 | **+40** |
| `#B8A8D0` | `#A8B8E8` | 33.0 | -10 |

图标那张图同样：模型报 `#7FA8E0`，实际 `#A8C8E8`。

**结论**：模型给的是**高光受光面**的颜色，不是画面主色；整体偏亮，越亮的色偏差越大。

**做法**：主色板一律从原图直接采样。

```js
// 浏览器：canvas 量化到 16 级分桶，取 TOP-N，并合并肉眼难分的近色
// 关键参数：忽略 alpha < 200 的像素；近色阈值 L1 距离 42
```

```python
# 脚本：Pillow 缩到 96×96 后分桶，同样的量化与近色合并逻辑
```

**脚本实测验证**（仙侠人像，采样 6 色）：

```
采样结果: #8AA3DB #A5BAE6 #C6D4F1 #E4E8F6 #8699B6 #7688A7
模型曾报: #A8C0E0 #E8F0F8 #B8A8D0
```

采样首色 `#8AA3DB` 与手工采样得到的 `#88A8D8` 几乎一致；模型的 `#E8F0F8` 亮度明显偏高。

---

## 一之补充：透明通道会被压成黑色

**现象**：源图带 alpha 通道时，直接转 RGB 会把透明区变成纯黑，污染整个色板统计。

验证方式——造一张上半透明、下半红色的测试图：

```
做了 alpha 合成:    ['#FEFEFE', '#C73B3B']        ← 正确
不做 alpha 合成:    [(0,0,0), (13,4,4), (187,56,56), ...]  ← 黑色混进来了
```

**做法**：转 RGB 前先合成到白底。

```python
bg = Image.new("RGB", img.size, (255, 255, 255))
img = img.convert("RGBA")
bg.paste(img, mask=img.split()[-1])
img = bg
```

图标类 PNG 尤其常见——macOS 的应用图标基本都是带透明边的 RGBA。

---

## 二、双语必须由模型生成

**现象**：初版让模型用中文答，代码事后按 `[一-龥]` 正则过滤字段——英文模板被整个滤空，SD 和 Midjourney 只输出了个色板。

**结论**：按语种过滤是错的。模型用什么语言回答不可控，不能让代码猜。

**做法**：模板里明确要求 `[字段名] 中文 | English`，双语由模型原生生成。

附带问题：用 `|` 分隔后，`[文字]` 字段会被误拆。模型答 `PNG / unknown | PNG / unknown`，原文被切碎。

**做法**：`[文字]` 字段**单独处理，整段照抄，不拆竖线、不翻译**。

---

## 三、系统代理会掐断请求

**现象**：`curl` 全部报 `EXIT=56`，看起来像接口挂了。

```
HTTPS_PROXY=http://d1-99bbd5:***@45.78.64.196:20004
* Establish HTTP proxy tunnel to proxy.droiclaw.com:443
* Proxy CONNECT aborted
curl: (56) Proxy CONNECT aborted
```

**做法**：加 `--noproxy '*'` 绕过。加完立刻 `HTTP=200`。

工具生成 curl 时默认带上这个参数，否则换台机器还会再踩一次。

---

## 四、大文件请求体撑爆命令行

**现象**：1024×1536 的 PNG 转 base64 后单是 JSON 就 **1.6MB**。

**做法**：不要把 base64 塞进 `curl -d`。用 Python 落文件走 `--data-binary @file`：

```python
import base64, json
with open('/tmp/ref.png','rb') as f:
    b64 = base64.b64encode(f.read()).decode()
payload = {...}
json.dump(payload, open('/tmp/req.json','w'), ensure_ascii=False)
```

```bash
curl -s --noproxy '*' --max-time 180 \
  --request POST "$BASE/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KEY" \
  --data-binary @/tmp/req.json
```

浏览器场景下同样要注意：原图压缩到长边 768、JPEG 质量 70，约 50KB 即可保持识别质量。

---

## 五、模型会诚实标 unknown（好消息）

图标那张图，模型主动写了：

```
[主体] ... 黑色瓶盖材质 unknown
[文字] PNG / unknown
```

**没有编造**。模板里"不确定就写 unknown"的约束是生效的。

对照它读对的部分：画面里最大的字 `PNG` 读对了，**镜头环上那圈极小的白字诚实标了 unknown**。

**结论**：大字号没问题，小字号别指望。这条印证了"精确计数和微小文字是共同弱项"。

---

## 六、模型的推理会吃掉输出预算

图标那张图，第二次调用时 `reasoning_tokens` 达到 **3370**，占总输出 3781 的 89%。

**做法**：`max_tokens` 至少给 1500，否则可能被推理过程挤掉正文。如果要批量跑，注意这个成本。

---

## 七、浏览器直连的 CORS 问题

很多厂商接口不带 CORS 头，浏览器里 `fetch` 会被直接拦。

**做法**：
- 工具里做错误识别——`Failed to fetch` / `NetworkError` / `Load failed` 统一提示"改用 curl"
- 提供「复制 curl」按钮作为逃生口，curl 不走同源策略

---

## 八、canvas 采样的静默降级

跨域图片或隐私模式下，`getImageData` 会抛异常。

**做法**：`try/catch` 包住，失败返回空数组，色板区块整体隐藏，**不能让页面崩**。
