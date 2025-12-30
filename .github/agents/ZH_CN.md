# ==========================================================
#  Custom Agent : translator-zh-cn
#  作用域       : 整个仓库（PR / Issue / 代码评审）
#  官方文档     : 
#  https://docs.github.com/zh/copilot/reference/custom-agents-configuration
#  https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents
# ==========================================================

schema: agent.v1.0
name: translator-zh-cn
description: |
  自动把 Copilot 生成的「提交信息、PR 标题 / 描述、代码评审评论」从英文翻译成简体中文；
  具备计算机 / 编程专业词库，支持双语对照回写，方便国内同事 Review。
author: your-org-i18n-team
version: 1.2.0

# 1. 触发时机（官方枚举值）
when:
  - pull_request.opened
  - pull_request.edited
  - issue_comment.created
  - issue_comment.edited
  - commit_comment.created

# 2. 权限声明（最小可用）
permissions:
  pull-requests: write
  issues: write
  contents: write        # 需要回写 commit message 时开启

# 3. 模型参数（可选，默认即 gpt-4o）
model:
  name: gpt-4o
  temperature: 0.15      # 翻译任务需要确定性
  max_tokens: 4000
  top_p: 0.95

# 4. 系统级指令（System Prompt）
instructions: |
  你是 GitHub Copilot 官方认证的「翻译智能体」。
  收到英文内容后，仅返回简体中文译文，禁止输出任何额外解释。
  必须遵守下列规则：
  1. 严格使用下方 glossary 中的固定译法，禁止自由发挥。
  2. 遇到 `代码块 / 行内代码 / URL / @用户名 / 全大写缩写` 保持原文。
  3. 译文保持 GitHub Markdown 格式（列表、引用、任务框等）。
  4. 若原文已含中文 > 50%，直接返回原文并标注 `<!-- already-zh -->`。
  5. 双语场景：把译文放在「<details><summary>中文</summary>...」折叠区内，方便对照。

# 5. 专业词库（与 instructions 同级）
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
  mutex: 互斥锁
  deadlock: 死锁
  race condition: 竞态条件

# 6. 输出模板（官方 template 字段）
templates:
  commitMessage: |
    {{type}}({{scope}}): {{zhSubject}}

    {{zhBody}}

    Co-authored-by: translator-zh-cn <bot@github.com>
  prDescription: |
    <!-- translator-zh-cn -->
    <details>
    <summary>🌐 中文翻译</summary>

    {{zhDescription}}
    </details>
  reviewComment: |
    <!-- translator-zh-cn -->
    **原文**  
    > {{original}}

    **译文**  
    {{translated}}

# 7. 例外规则（官方 skip 语法）
skip:
  - if: contains(body, 'bot-ignore')   # 用户显式跳过
    action: ignore
  - if: language == 'zh'               # 已中文
    action: ignore
  - if: matches(body, '(?i)```[\s\S]*?```') and length(body) > 9000
    action: truncate                   # 超大代码块先截断，防 token 爆表

# 8. 动作链（官方 actions 语法）
actions:
  - name: translate-commit
    when: commit_comment.created
    run: |
      gh api repos/${{ github.repository }}/commits/${{ github.sha }}/comments \
        --jq '.[]|.body' | translator-zh-cn | gh api -X PATCH -F body=@-
  - name: translate-pr
    when: pull_request.opened or pull_request.edited
    run: |
      gh pr view ${{ github.event.number }} --json title,body \
        | jq -r '.title,.body' | translator-zh-cn \
        | ( read -r zhTitle; read -r zhBody; \
            gh pr edit ${{ github.event.number }} -t "$zhTitle" -b "$zhBody" )
