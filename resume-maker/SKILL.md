---
name: resume-builder
description: |
  技术岗位简历生成与优化工具。支持两种模式：1) 从零写简历 - 通过引导式问答采集信息并生成结构化简历；2) 简历优化 - 解析现有简历，针对目标 JD 进行内容优化和排版升级。当用户提到"写简历"、"优化简历"、"改简历"、"投简历"、"求职"、"面试准备"、"更新简历"、"简历模板"时触发此技能。即使用户只是说"帮我看看这个简历"或"我要找工作"，也应该触发此技能。
---

# Resume Builder - 技术岗位简历生成器

面向技术岗位的简历生成与优化 skill，支持从零创建和基于现有简历优化两种模式。

## 工作模式

根据用户的输入判断使用哪种模式：

- **模式 A：从零写简历** - 用户说"我要写简历"、"帮我创建简历"、"我没有简历"
- **模式 B：简历优化** - 用户提供了现有简历文件，或说"优化我的简历"、"帮我改简历"

---

## 模式 A：从零写简历

### 步骤 1：信息采集

通过引导式问答收集以下信息。不要一次性问完，分 2-3 轮自然地询问。

**第一轮：目标定位**
- 目标岗位名称（如：高级前端工程师、Java 后端开发）
- 目标行业（如：互联网、金融科技、AI）
- 工作年限级别（应届 / 1-3年 / 3-5年 / 5年+）

**第二轮：硬实力**
- 教育背景（学校、专业、学历、毕业时间）
- 技术栈（按类别：前端/后端/数据库/DevOps/其他）
- 掌握程度（精通 / 熟练 / 掌握 / 了解）
- 证书资质（可选）

**第三轮：经历挖掘**（最关键，用 STAR 法则引导）
- 工作/实习经历（公司、职位、时间、主要职责）
- 项目经历（项目名、技术栈、你的角色、具体做了什么、成果是什么）
- 每段经历引导用户说出**量化成果**（如：提升了 30% 性能、服务 10 万用户）

**可选：软性差异化**
- GitHub / 技术博客 / 开源贡献
- 技术社区参与 / 演讲经历
- 获奖情况

### 步骤 2：生成 base_info

将采集的信息整理成结构化数据，保存到 `resume_base_info.md`：

```markdown
# 基本信息
- 姓名：
- 电话：
- 邮箱：
- GitHub：
- 博客：

# 求职意向
- 目标岗位：
- 目标行业：
- 工作年限：

# 技术能力
## 前端
- React：熟练（3年）
- TypeScript：熟练（2年）

## 后端
- Node.js：掌握（1年）

# 工作经历
## 公司名称 | 职位 | 2022.06 - 至今
- 负责 XX 系统的前端架构设计，采用 React + TypeScript 技术栈
- 优化首屏加载速度，从 3s 降至 800ms，提升 73%
- ...

# 项目经历
## 项目名称
- **技术栈**：React, TypeScript, Node.js, PostgreSQL
- **角色**：前端负责人
- **职责**：
  - 设计并实现组件库，包含 50+ 个通用组件
  - ...
- **成果**：
  - 组件复用率提升至 80%，开发效率提升 40%
  - ...

# 教育背景
## 学校名称 | 专业 | 本科 | 2018.09 - 2022.06
```

### 步骤 3：渲染为简历初稿

使用 `assets/templates/classic.html` 模板，将 base_info 渲染为 HTML，然后用脚本生成 PDF。

```bash
python scripts/render_pdf.py --input resume_base_info.md --template classic --output resume.pdf
```

### 步骤 4：引导优化

告知用户可以使用"简历优化"模式继续打磨：
> "简历初稿已生成！你可以用简历优化模式，针对具体 JD 进一步优化内容和措辞。"

---

## 模式 B：简历优化

### 步骤 1：解析现有简历 → base_info

1. **读取用户提供的简历**（支持 PDF、纯文本、Markdown）
2. **提取结构化信息**，按 base_info schema 整理
3. **保存为 resume_base_info.md**，让用户确认

如果用户给的是 PDF，先尝试提取文本：
```bash
python -c "import pdfplumber; pdf = pdfplumber.open('input.pdf'); print('\n'.join(p.extract_text() or '' for p in pdf.pages))"
```

### 步骤 2：内容优化

基于技术简历写作规范（参见 `references/tech_resume_guide.md`）优化内容：

**优化原则**：
1. **动词开头**：用"设计"、"实现"、"优化"、"重构"等强动词开头
2. **量化成果**：数字说话，"提升 30%"比"有所提升"强
3. **STAR 法则**：情境(Situation) → 任务(Task) → 行动(Action) → 结果(Result)
4. **技术关键词**：确保技术栈、工具名称准确完整

**优化示例**：
```
优化前：负责网站前端开发
优化后：使用 React + TypeScript 重构电商平台前端，首屏加载时间从 3.2s 优化至 0.9s，转化率提升 15%
```

将优化后的内容保存为 `resume_upgrade_info.md`。

### 步骤 3：JD 针对性改造

1. **获取目标 JD**：让用户提供 JD 文本或链接
2. **提取关键词**：分析 JD 中的核心要求（技术栈、经验年限、关键能力）
3. **讨论侧重点**：与用户确认哪些经历需要突出，哪些可以弱化
4. **调整内容顺序和措辞**：
   - 匹配 JD 关键词的经历前置
   - 用 JD 中的措辞改写简历描述
   - 补充 JD 要求但简历中缺失的关键词（前提是真实）

保存为 `resume_final.md`。

### 步骤 4：生成最终文件

用户确认内容后，选择模板并生成 PDF：

```bash
python scripts/render_pdf.py --input resume_final.md --template classic --output resume_final.pdf
```

可选模板：
- `classic` — 传统黑白，稳重正式
- `modern` — 带配色，侧边栏布局（待实现）
- `minimal` — 极简风格（待实现）

---

## base_info Schema

技术岗位简历的结构化数据格式：

```yaml
personal:
  name: string
  phone: string
  email: string
  github: string?      # 可选
  blog: string?
  location: string?

objective:
  target_position: string   # 如：高级前端工程师
  target_industry: string
  years_of_experience: string  # 如：3-5年
  job_type: string        # 全职/实习

skills:
  - category: string      # 如：前端、后端、数据库
    items:
      - name: string      # 如：React
        proficiency: string  # 精通/熟练/掌握/了解
        years: number?    # 使用年限

work_experience:
  - company: string
    position: string
    start_date: string    # YYYY.MM
    end_date: string      # YYYY.MM 或 "至今"
    highlights:           # 3-5 条，用 STAR 法则
      - string

projects:
  - name: string
    tech_stack: [string]
    role: string
    start_date: string
    end_date: string
    description: string?
    responsibilities:     # 3-5 条
      - string
    achievements:         # 量化成果
      - string
    link: string?

education:
  - school: string
    degree: string        # 本科/硕士/博士
    major: string
    start_date: string
    end_date: string
    gpa: string?
    honors: [string]?

extras:
  certifications:
    - name: string
      issuer: string
      date: string
  open_source:
    - name: string
      role: string
      url: string
      description: string
```

---

## 脚本使用

### render_pdf.py

将 Markdown 简历渲染为 PDF。

```bash
python scripts/render_pdf.py --input <markdown文件> --template <模板名> --output <输出路径>
```

参数：
- `--input`：Markdown 格式的简历文件路径
- `--template`：模板名称（classic / modern / minimal）
- `--output`：输出 PDF 文件路径
- `--preview`：可选，生成 HTML 预览而不生成 PDF

依赖：
- Python 3.8+
- WeasyPrint（`pip install weasyprint`）
- Jinja2（`pip install jinja2`）
- python-frontmatter（`pip install python-frontmatter`）

---

## 参考文档

- `references/tech_resume_guide.md` — 技术简历写作指南（STAR 法则、动词库、量化技巧）
- `assets/templates/classic.html` — 经典简历模板

---

## 注意事项

1. **内容真实性**：AI 辅助优化措辞，但所有信息必须基于用户真实经历，不要编造
2. **篇幅控制**：技术岗简历通常 2-3 页，不要强行压缩到一页
3. **关键词匹配**：针对 JD 优化时，确保技术关键词准确匹配，但不要堆砌
4. **排版优先**：内容质量 > 花哨排版，清晰易读是第一位的
