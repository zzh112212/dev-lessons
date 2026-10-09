#!/usr/bin/env python3
"""dev-lessons 经验文件工具（单文件版）：条目校验（check）与目录生成（toc）。

所有经验集中在 experiences/lessons.md 一个文件：
    python3 skills/dev-lessons/scripts/lessons.py check   # 校验分区/条目三要素/ID 唯一
    python3 skills/dev-lessons/scripts/lessons.py toc     # 原位重建文件头目录表
"""
import re
import sys
from datetime import datetime
from pathlib import Path

LESSONS = Path("experiences/lessons.md")
ID_RE = re.compile(r"^### (GEN-[A-Z]{3,4}-\d{3}|PRJ-\d{3}) · .+")
SEC_RE = re.compile(r"^## (通用 · .+|专用 · .+)\s*$")
REQ_KEYS = ("问题", "原因", "解决")


def parse(path: Path):
    """返回 (条目列表, 错误列表)。条目 = dict(id, title, section, draft, lineno)。"""
    errors, entries, section = [], [], None
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
            cur = None  # 条目天然结束于下一标题，无需收尾标记
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
        if cur is not None:
            km = re.match(r"^\*\*(问题|原因|解决|验证)\*\*", line)
            if km:
                cur["keys"].add(km.group(1))

    for e in entries:
        for k in REQ_KEYS:
            if k not in e["keys"]:
                errors.append(f"L{e['lineno']}: {e['title'].split(' · ')[0]} 缺少 **{k}**")
        if "验证" not in e["keys"]:
            errors.append(f"L{e['lineno']}: {e['title'].split(' · ')[0]} 缺少 **验证**（未实证可写'待验证'）")

    ids = [e["title"].split(" · ")[0] for e in entries]
    for d in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"重复 ID：{d}")
    return entries, errors


def cmd_check():
    if not LESSONS.exists():
        print(f"[FAIL] {LESSONS} 不存在")
        return 1
    entries, errors = parse(LESSONS)
    formal = [e for e in entries if "（draft）" not in e["title"]]
    draft = [e for e in entries if "（draft）" in e["title"]]
    print(f"共校验 {len(entries)} 条经验（正式 {len(formal)} / draft {len(draft)}）")
    if not errors:
        print("校验通过：分区正确、三要素齐全、ID 唯一")
        return 0
    for e in errors:
        print(f"  [FAIL] {e}")
    return 1


def cmd_toc():
    if not LESSONS.exists():
        print(f"[FAIL] {LESSONS} 不存在")
        return 1
    entries, errors = parse(LESSONS)
    if errors:
        print("存在格式错误，先运行 check 修复：")
        for e in errors:
            print(f"  - {e}")
        return 1

    rows = ["| ID | 分区 | 标题 | 状态 |", "|---|---|---|---|"]
    for e in entries:
        eid, title = e["title"].split(" · ", 1)
        rows.append(f"| {eid} | {e['section'].replace(' · ', '·')} | {title} | {'draft' if '（draft）' in e['title'] else '正式'} |")

    text = LESSONS.read_text(encoding="utf-8")
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
            replaced = True
            i = j
            continue
        out.append(lines[i])
        i += 1
    if not replaced:  # 无目录区 → 插到第一个分区前
        for k, line in enumerate(out):
            if SEC_RE.match(line):
                out = out[:k] + [new_toc] + out[k:]
                break
    LESSONS.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"已重建目录（{len(entries)} 条）→ {LESSONS}")
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("check", "toc"):
        print(__doc__)
        sys.exit(2)
    sys.exit(cmd_check() if sys.argv[1] == "check" else cmd_toc())


if __name__ == "__main__":
    main()
