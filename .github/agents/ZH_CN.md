---
name:ZH_CN
description:翻译智能体，参与Copilot的工作，将Copilot的包括提交信息，代码评审中的非中文信息翻译成中文并修改提交
---


# 1. 触发范围
on:
  pull_request:
    types: [opened, synchronize, edited]
  issue_comment:
    types: [created, edited]
  push:
    branches-ignore: ["translate-bot/**"]   # 避免机器人自己触发自己

# 2. 权限
permissions:
  contents: write          # 推送翻译后的提交
  pull-requests: write     # 修改 PR 标题 / 描述
  issues: write            # 修改 Issue 评论

# 3. 翻译策略
strategy:
  # 遇到以下字段不翻译（正则，忽略大小写）
  skipPatterns:
    - '(?i)github\.com'
    - '(?i)@[a-z0-9\-]+'        # @用户名
    - '(?i)`[^`]+`'             # 行内代码
    - '(?i)```[\s\S]*?```'      # 代码块
    - '(?i)\b[A-Z]{2,}\b'       # 全大写缩写（API、HTTP…）
  # 专业词库（优先采用左侧译文）
  glossary:
    refactor: 重构
    chore: 杂务
    feat: 新功能
    fix: 修复
    docs: 文档
    style: 格式
    perf: 性能
    test: 测试
    build: 构建
    ci: 持续集成
    revert: 回滚
    WIP: 进行中
    nit: 细节
    LGTM: 可合并
    ASAP: 尽快
    deprecated: 已弃用
    breaking change: 不兼容变更
    edge case: 边界情况
    flaky test: 不稳定测试
  # 单次最大字符数（防止 token 爆表）
  maxLength: 8000

# 4. 提交信息模板
commitTemplate:
  zh: |
    {{type}}({{scope}}): {{zhSubject}}

    {{zhBody}}

    {{footer}}
  en: |
    {{type}}({{scope}}): {{enSubject}}

    {{enBody}}

    {{footer}}

# 5. PR 评论模板（双语对照）
prTemplate: |
  🤖 **Copilot Translator** 已自动完成中文化：

  ---
  **原文**  
  {{original}}

  **译文**  
  {{translated}}

  ---
  如需调整，请直接编辑上方评论，机器人会跳过包含 `bot-ignore` 的评论。

# 6. GitHub Actions 最小范例（可选，复制到 .github/workflows/translate.yml 即可生效）
jobs:
  translate:
    runs-on: ubuntu-latest
    if: ${{ github.actor != 'translate-bot[bot]' }}
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0

      - name: Run Copilot Translator
        uses: your-org/copilot-translator-action@v1
        with:
          config: .github/copilot-translator.yml
          openaiApiKey: ${{ secrets.OPENAI_API_KEY }}   # 或 Azure、Gemini key
          commitTranslation: true                         # 是否回写提交
          debug: ${{ runner.debug == '1' }}

