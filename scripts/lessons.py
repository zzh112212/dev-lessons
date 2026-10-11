#!/usr/bin/env python3
"""dev-lessons 经验文件工具（单文件版）：校验、目录、查看与统计。

所有经验集中在 experiences/lessons.md 一个文件：
    python3 <技能目录>/scripts/lessons.py check   # 校验分区/条目三要素/ID 唯一
    python3 <技能目录>/scripts/lessons.py toc     # 原位重建文件头目录表
    python3 <技能目录>/scripts/lessons.py view    # 带计数地读取经验文件（AI 查用必走此命令）
    python3 <技能目录>/scripts/lessons.py stats   # 查看经验文件被查阅次数统计

路径说明：
    <技能目录> = 技能实际安装路径（如 ~/.claude/skills/dev-lessons），以安装位置为准。
    经验文件默认相对当前工作区根解析 experiences/lessons.md；
    可用 --file 指定其他路径，或环境变量 LESSONS_FILE 指定默认值。

使用计数：check/toc/view 每次运行都会在经验文件同目录的 lessons_usage.jsonl
追加一条事件（时间戳 + 事件类型 + 文件是否存在）。stats 命令汇总该日志，
让用户直观看到经验文件是否被 AI 查看及查看次数。

退出码：0 成功（含仅有警告）；1 存在格式错误或文件缺失；2 参数错误。
警告不阻断 toc 重建（如缺「验证」字段、draft 标记错位）。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ID_RE = re.compile(r"^### (GEN-[A-Z]{3,4}-\d{3}|PRJ-\d{3}) · .+")
SEC_RE = re.compile(r"^## (通用 · .+|专用 · .+)\s*$")
DRAFT_RE = re.compile(r"[（(]\s*draft\s*[)）]\s*$")
DRAFT_ANY = re.compile(r"[（(]\s*draft\s*[)）]")  # 任意位置的 draft 标记（用于错位检测）
REQ_KEYS = ("问题", "原因", "解决")


def parse(path: Path):
    """返回 (条目列表, 错误列表, 警告列表)。条目 = dict(id, title, section, draft, lineno)。"""
    errors, warnings, entries, section = [], [], [], None
    lines = path.read_text(encoding="utf-8").splitlines()
    cur, in_toc = None, False

    for i, line in enumerate(lines, 1):
        if line.strip() == "## 目录":
            in_toc = True
            continue
        if in_toc:
            if line.startswith("## "):  # 目录区结束（下一分区开始）
                in_toc = False
            else:
                continue
        m = SEC_RE.match(line)
        if m:
            section = line[3:].strip()
            cur = None
            continue
        if line.startswith("### "):
            if not ID_RE.match(line):
                errors.append(f"L{i}: 条目标题格式非法：{line[:60]}（应形如 '### GEN-XXX-001 · 标题'）")
                cur = None
                continue
            cur = {"lineno": i, "section": section, "title": line[4:].strip(), "keys": set()}
            if cur["section"] is None:
                errors.append(f"L{i}: 条目 {line[4:20]}… 不在任何分区（## 通用 · … / ## 专用 · …）内")
            entries.append(cur)
            continue
        # P4 检测：draft 标记出现在非标题行（正文/验证行）会被静默忽略，状态仍按正式计
        if DRAFT_ANY.search(line) and not line.startswith("|"):
            warnings.append(f"L{i}: draft 标记出现在非标题行（应写在条目标题行尾，否则状态计为正式）：{line.strip()[:50]}")
        if cur is not None:
            km = re.match(r"^\*\*(问题|原因|解决|验证)\*\*", line)
            if km:
                cur["keys"].add(km.group(1))

    for e in entries:
        for k in REQ_KEYS:
            if k not in e["keys"]:
                errors.append(f"L{e['lineno']}: {e['title'].split(' · ')[0]} 缺少 **{k}**")
        if "验证" not in e["keys"]:  # 警告不阻断：文档规定验证可选
            warnings.append(f"L{e['lineno']}: {e['title'].split(' · ')[0]} 缺少 **验证**（可选；未实证建议写'待验证'）")

    ids = [e["title"].split(" · ")[0] for e in entries]
    for d in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"重复 ID：{d}")
    return entries, errors, warnings


def _is_draft(title: str) -> bool:
    return bool(DRAFT_RE.search(title))


def log_event(path: Path, event: str):
    """使用计数：每次 check/toc/view 记一条事件到经验文件同目录 lessons_usage.jsonl。"""
    try:
        logf = path.parent / "lessons_usage.jsonl"
        entry = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 "event": event, "file": str(path), "exists": path.exists()}
        with logf.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 统计失败不影响主功能


def _missing(path: Path, event: str):
    print(f"[FAIL] {path} 不存在（可用 --file 指定，或确认当前目录为工作区根）")
    return 1


def cmd_check(path: Path):
    log_event(path, "check")
    if not path.exists():
        return _missing(path, "check-miss")
    entries, errors, warnings = parse(path)
    formal = [e for e in entries if not _is_draft(e["title"])]
    draft = [e for e in entries if _is_draft(e["title"])]
    print(f"共校验 {len(entries)} 条经验（正式 {len(formal)} / draft {len(draft)}）")
    if not entries:
        print("提示：经验库为空（0 条）")
    if not errors:
        print("校验通过：分区正确、三要素齐全、ID 唯一")
        for w in warnings:
            print(f"  [WARN] {w}")
        return 0
    for e in errors:
        print(f"  [FAIL] {e}")
    return 1


def cmd_toc(path: Path):
    log_event(path, "toc")
    if not path.exists():
        return _missing(path, "toc-miss")
    entries, errors, warnings = parse(path)
    if errors:
        print("存在格式错误，先运行 check 修复：")
        for e in errors:
            print(f"  - {e}")
        return 1

    rows = ["| ID | 分区 | 标题 | 状态 |", "|---|---|---|---|"]
    for e in entries:
        eid, title = e["title"].split(" · ", 1)
        rows.append(f"| {eid} | {e['section'].replace(' · ', '·')} | {title} | {'draft' if _is_draft(e['title']) else '正式'} |")

    text = path.read_text(encoding="utf-8")
    new_toc = "\n".join(["## 目录", "", "> 自动生成，勿手改。按 ID/关键词定位条目后精读三要素。",
                         f"> 最近更新：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 共 {len(entries)} 条", ""] + rows)
    out, replaced = [], False
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == "## 目录":
            j = i + 1
            while j < len(lines) and lines[j].strip() != "## 目录" and not SEC_RE.match(lines[j]):
                j += 1
            out.append(new_toc)
            out.append("")  # 目录表与后续内容之间保留空行（Markdown 渲染需要）
            replaced = True
            i = j
            continue
        out.append(lines[i])
        i += 1
    if not replaced:  # 无目录区 → 插到第一个分区前
        for k, line in enumerate(out):
            if SEC_RE.match(line):
                out = out[:k] + [new_toc, ""] + out[k:]
                break
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"已重建目录（{len(entries)} 条）→ {path}")
    for w in warnings:
        print(f"  [WARN] {w}")
    return 0


def cmd_view(path: Path):
    log_event(path, "view")
    if not path.exists():
        return _missing(path, "view-miss")
    print(path.read_text(encoding="utf-8"), end="")
    return 0


def cmd_stats(path: Path):
    logf = path.parent / "lessons_usage.jsonl"
    if not logf.exists():
        print(f"暂无使用记录（日志将生成于 {logf}）")
        return 0
    events = []
    for line in logf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    hits = [e for e in events if e.get("event") == "view" and e.get("exists")]
    misses = [e for e in events if not e.get("exists")]
    print(f"经验文件使用统计（{logf}）")
    print(f"  成功查看 {len(hits)} 次 | 未命中尝试 {len(misses)} 次 | 各类事件：", end="")
    for ev, n in Counter(e.get("event", "?") for e in events).most_common():
        print(f"{ev}×{n} ", end="")
    print()
    if misses:
        print("  ⚠ 未命中明细（文件不存在时的访问）：")
        for e in misses[-5:]:
            print(f"    {e.get('ts', '?')}  {e.get('event', '?')}")
    if hits:
        print("  最近 5 次成功查看：")
        for e in hits[-5:]:
            print(f"    {e.get('ts', '?')}")
    return 0


def main():
    p = argparse.ArgumentParser(prog="lessons.py", description="dev-lessons 经验文件工具（check/toc/view/stats）",
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=("check", "toc", "view", "stats"),
                   help="check=校验；toc=重建目录表；view=带计数读取；stats=查看次数统计")
    p.add_argument("--file", default=os.environ.get("LESSONS_FILE", "experiences/lessons.md"),
                   help="经验文件路径（默认 experiences/lessons.md，相对当前目录）")
    a = p.parse_args()
    fn = {"check": cmd_check, "toc": cmd_toc, "view": cmd_view, "stats": cmd_stats}[a.cmd]
    try:
        sys.exit(fn(Path(a.file)))
    except BrokenPipeError:  # 输出被管道截断（如 stats | head）属正常用法，静默退出
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)


if __name__ == "__main__":
    main()
