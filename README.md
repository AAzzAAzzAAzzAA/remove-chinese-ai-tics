# 中文 AI 口癖清理

`remove-chinese-ai-tics` 是一套面向简体中文的 Agent Skill，用于识别和清理模型化口癖、套话、固定句法、篇章惯性、客服腔、装饰性华丽词和格式反射。

当前测试版为 [`v0.1.0-beta`](https://github.com/AAzzAAzzAAzzAA/remove-chinese-ai-tics/releases/tag/v0.1.0-beta)。规则 ID 和文件布局在稳定版发布前仍可能调整。

## 安装

仓库根目录存放公开说明和维护工具。可安装的 Skill 位于内层 `remove-chinese-ai-tics/` 目录。

```bash
git clone --depth 1 --branch v0.1.0-beta https://github.com/AAzzAAzzAAzzAA/remove-chinese-ai-tics.git remove-chinese-ai-tics-repo
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R remove-chinese-ai-tics-repo/remove-chinese-ai-tics "${CODEX_HOME:-$HOME/.codex}/skills/"
```

安装后可用 `$remove-chinese-ai-tics` 调用。其他支持 `SKILL.md` 的 Agent 可能使用不同的技能目录，请按对应产品的目录规则放置内层文件夹。若目标位置已有同名 Skill，请先备份，再替换整个目录。

## 适用范围

可用于评论、说明文、技术文档、教程、学术写作、公文、商务材料、营销文案、社交媒体、新闻稿、翻译、私人消息及创意文本。小说、故事、剧本、角色对话和互动叙事拥有单独规则。

支持以下工作模式：

- 审计：标出问题、依据和修复方向，不改正文；
- 保守清理：删除助手残留、空套话、重复和格式反射；
- 标准改写：调整句法、节奏及篇章组织；
- 强力改写：在用户明确要求时重排段落和信息顺序；
- 严格去口癖：安全重构登记的高置信句法和成品套件；
- 写作护栏：在新写正文时直接约束生成；
- 批量处理：分块清理长文或多文件，并检查跨块一致性。

## 处理原则

改写前会锁定事实、数字、专名、引语、术语、立场、语体、人物目标、情节节点和输出格式。之后检查五个层面：助手交互残留、篇章组织惯性、逻辑空转、句法与修辞模板、词汇及格式反射。

普通规则依据功能、局部密度、同义轮换和跨段复现进行判断，不会因单个词出现便直接删改。严格模式会重构登记的高置信结构。引语、代码、固定术语和批准文案受逐字保护；否定、范围、模态、因果与人物意图不得损坏。无法安全重构的内容会保留并说明冲突。

修复优先采用删除、合并、具体化和句法重组。Skill 不会把命中词机械替换成另一组近义词，也不会用错字、俚语、随机断句或逻辑瑕疵制造所谓“人味”。

## 创意写作

创意文本会额外保护视角、时态、人物知识边界、世界观、时间线、动作连续性和人物声口。清理重点包括重复解释、动机越权、感官库存、统一声线、自动升华和强制收束。有发展作用的意象、有意重复及人物独有表达会被保留。互动叙事还会检查创作权限、人物主权和自然停止点。

## 使用示例

```text
使用 $remove-chinese-ai-tics 审计下面的文章，只报告问题，不修改正文。

使用 $remove-chinese-ai-tics 标准改写这份文稿，保留术语、数字和正式程度。

使用 $remove-chinese-ai-tics 严格清理这段小说，只输出终稿，保持人物声口和情节不变。
```

## 维护与验证

在仓库根目录运行：

```bash
python3 remove-chinese-ai-tics/scripts/validate_skill_content.py --evaluation-suite tests/evaluation-suite.md
python3 tools/audit_public_repo.py --self-test
python3 tools/audit_public_repo.py
```

内容校验检查元数据、规则 ID、参考文件、目录和 56 个合成回归案例。公开审计检查当前文件、可达历史、提交元数据、常见密钥形态、用户目录、IP 地址和私有来源词。审计报告只显示类别与文件位置，不回显命中内容。

回归案例位于 [`tests/evaluation-suite.md`](tests/evaluation-suite.md)。它们用于维护规则边界，目前不会自动调用模型生成结果。GitHub Actions 会在每次 push 和 pull request 时运行内容校验、审计器自测、公开审计与差异检查。

Skill 只负责语言与结构清理，不补写证据、专业判断、采访材料或未经提供的剧情设定。事实完整性与语言清理发生冲突时，优先保留事实。

## 社区

本项目已收录于 [LINUX DO](https://linux.do/)。
