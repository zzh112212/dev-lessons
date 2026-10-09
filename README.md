# dev-lessons

开发经验沉淀与复用技能——把踩过的坑变成可检索的资产。

## 核心特性

- **单一经验文件**：所有经验集中在 `experiences/lessons.md`（文件内按通用/专用分类，不碎片化）
- **三要素条目**：每条经验只记 问题 / 原因 / 解决方法，禁止写成文档
- **任务完成验收弹窗**：通过 / 不通过 / 生成临时经验 / 上传 ima 知识库，四选项语义固定
- **内嵌 ima 模块**：经验上传至 ima 知识库，供任何 AI 助手遇到相同问题时快速查找

## 安装

```bash
npx -y skills add zzh112212/dev-lessons -g -y --agent claude-code
```

## 结构

```
SKILL.md                     技能主文件
references/entry-template.md 经验条目模板
scripts/lessons.py           经验文件操作脚本
ima/                         内嵌 ima 模块
  ├── meta.json              版本与重建来源
  ├── ima_api.cjs            ima OpenAPI 封装（按官方指南契约重建）
  ├── knowledge-base/        知识库上传子模块
  └── notes/                 笔记子模块
```

## 来源说明

`ima/` 模块重建自社区镜像 `bighardperson/computer-science-skills-collection@v1.1.2`，契约依据《ima 技能安装指南》（官方 v1.1.10，2026-09-29 实测补充），详见 `ima/meta.json`。
