"""图编译与结构门禁共用的规则引用、生命周期校验；不执行业务条件。"""

from __future__ import annotations

from typing import Any

STATE_TYPES = {"start", "active", "waiting", "decision", "success", "failure", "neutral", "external"}


def issue(code: str, message: str, identifier: str = "", field: str = "") -> dict[str, str]:
    return {"code": code, "message": message, **({"object_id": identifier} if identifier else {}), **({"field": field} if field else {})}


def rule_issues(owners: list[dict[str, Any]], definitions: Any) -> list[dict[str, str]]:
    """旧字符串只展示；新的结构化引用必须命中已声明规则及精确版本。"""
    errors: list[dict[str, str]] = []
    if not isinstance(definitions, list):
        return [issue("rules.definitions", "rule_definitions 必须是列表", field="rule_definitions")]
    registry: dict[str, str] = {}
    for rule in definitions:
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str) or not rule["id"] or not isinstance(rule.get("version"), str) or not rule["version"]:
            errors.append(issue("rules.definition", "规则定义必须包含非空字符串 id、version", field="rule_definitions"))
            continue
        if rule["id"] in registry:
            errors.append(issue("rules.duplicate", "规则定义 ID 重复", rule["id"], "rule_definitions"))
        registry[rule["id"]] = rule["version"]
    for owner in owners:
        if not isinstance(owner, dict):
            continue
        identifier = str(owner.get("id", ""))
        rules = owner.get("rules", [])
        if not isinstance(rules, list):
            errors.append(issue("rules.list", "rules 必须是列表", identifier, "rules"))
            continue
        for rule in rules:
            if isinstance(rule, str) and rule.strip():
                continue
            if not isinstance(rule, dict) or not isinstance(rule.get("id"), str) or not isinstance(rule.get("version"), str) or not rule.get("version"):
                errors.append(issue("rules.reference", "新规则引用必须包含 id、version", identifier, "rules"))
            elif registry.get(rule["id"]) != rule["version"]:
                errors.append(issue("rules.version", f"规则不存在或版本不一致：{rule['id']}@{rule['version']}", identifier, "rules"))
    return errors


def components(ids: set[str], pairs: list[tuple[str, str]]) -> set[frozenset[str]]:
    """返回存在环的强连通分量；分量与声明一一对应，不能用笼统说明放行。"""
    adjacency = {identifier: [] for identifier in ids}
    for source, target in pairs:
        if source in ids and target in ids:
            adjacency[source].append(target)
    reach: dict[str, set[str]] = {}
    for identifier in ids:
        visited: set[str] = set()
        pending = list(adjacency[identifier])
        while pending:
            target = pending.pop()
            if target in visited:
                continue
            visited.add(target)
            pending.extend(adjacency[target])
        reach[identifier] = visited
    return {frozenset(target for target in ids if target in reach[source] and source in reach[target]) for source in ids if source in reach[source]}


def lifecycle_issues(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], config: Any) -> list[dict[str, str]]:
    """只检查明确结构；无法表达或缺失的业务语义留给需求确认门禁。"""
    errors: list[dict[str, str]] = []
    if not isinstance(config, dict):
        return [issue("lifecycle.missing", "state 布局必须声明 lifecycle 初终状态与主路径", field="lifecycle")]
    ids = {node["id"] for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)}
    if len(ids) < 2:
        errors.append(issue("lifecycle.states", "生命周期至少需要两个状态", field="nodes"))
    initial = config.get("initial_state_id")
    terminals = config.get("terminal_state_ids")
    if not isinstance(initial, str) or initial not in ids:
        errors.append(issue("lifecycle.initial", "初始状态不存在", field="lifecycle.initial_state_id"))
    if not isinstance(terminals, list) or not terminals or any(not isinstance(value, str) or value not in ids for value in terminals):
        errors.append(issue("lifecycle.terminal", "终止状态必须是非空且有效的状态列表", field="lifecycle.terminal_state_ids"))
        terminals = []
    elif len(set(terminals)) != len(terminals):
        errors.append(issue("lifecycle.terminal_duplicate", "终止状态不能重复", field="lifecycle.terminal_state_ids"))
    initial_flags = {node["id"] for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str) and node.get("initial") is True}
    terminal_flags = {node["id"] for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str) and node.get("terminal") is True}
    expected_initial = {initial} if isinstance(initial, str) else set()
    if initial_flags != expected_initial:
        errors.append(issue("lifecycle.initial_flags", "节点 initial 标记必须与唯一初始状态一致", field="lifecycle.initial_state_id"))
    if terminal_flags != set(terminals):
        errors.append(issue("lifecycle.terminal_flags", "节点 terminal 标记必须与终止状态列表一致", field="lifecycle.terminal_state_ids"))
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for field in ("initial", "terminal"):
            if field in node and type(node[field]) is not bool:
                errors.append(issue("lifecycle.flag", f"{field} 必须是布尔值", str(node.get("id", "")), field))
        if node.get("state_type") is not None and (not isinstance(node["state_type"], str) or node["state_type"] not in STATE_TYPES):
            errors.append(issue("lifecycle.state_type", "状态呈现类型无效", str(node.get("id", "")), "state_type"))
    pairs = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source, target = edge.get("source"), edge.get("target")
        if not isinstance(source, str) or not isinstance(target, str) or source not in ids or target not in ids:
            errors.append(issue("lifecycle.endpoint", "迁移起止必须引用有效状态", str(edge.get("id", "")), "source/target"))
            continue
        pairs.append((source, target))
        if source in terminals:
            errors.append(issue("lifecycle.terminal_outgoing", "终止状态不能有出边", source, "terminal"))
    main = config.get("main_path")
    if not isinstance(main, list) or len(main) < 2 or any(not isinstance(value, str) or value not in ids for value in main):
        errors.append(issue("lifecycle.main_path", "主路径必须包含至少两个有效状态", field="lifecycle.main_path"))
    else:
        if len(set(main)) != len(main):
            errors.append(issue("lifecycle.main_path_repeat", "主路径不能重复状态，重试请声明独立迁移与环", field="lifecycle.main_path"))
        if main[0] != initial or main[-1] not in terminals:
            errors.append(issue("lifecycle.main_path_ends", "主路径必须从初始状态到终止状态", field="lifecycle.main_path"))
        for source, target in zip(main, main[1:]):
            if (source, target) not in pairs:
                errors.append(issue("lifecycle.main_path_edge", f"主路径缺少迁移：{source} → {target}", source, "lifecycle.main_path"))
    def reachable(starts: set[str], reverse: bool = False) -> set[str]:
        seen = set(starts)
        pending = list(starts)
        while pending:
            current = pending.pop()
            for source, target in pairs:
                source, target = (target, source) if reverse else (source, target)
                if source == current and target not in seen:
                    seen.add(target)
                    pending.append(target)
        return seen
    if isinstance(initial, str) and initial in ids:
        for identifier in sorted(ids - reachable({initial})):
            errors.append(issue("lifecycle.unreachable", "状态无法从初始状态到达", identifier, "lifecycle"))
    if terminals:
        for identifier in sorted(ids - reachable(set(terminals), True)):
            errors.append(issue("lifecycle.no_terminal", "状态没有到达终止状态的路径", identifier, "lifecycle"))
    cycles = config.get("cycles", [])
    declared: set[frozenset[str]] = set()
    if not isinstance(cycles, list):
        errors.append(issue("lifecycle.cycles", "cycles 必须是列表", field="lifecycle.cycles"))
    else:
        for cycle in cycles:
            if not isinstance(cycle, dict) or not isinstance(cycle.get("nodes"), list) or not cycle["nodes"] or any(not isinstance(value, str) or value not in ids for value in cycle["nodes"]) or not isinstance(cycle.get("reason"), str) or not cycle["reason"].strip():
                errors.append(issue("lifecycle.cycle_reason", "合法环必须声明有效状态集合与原因", field="lifecycle.cycles"))
            else:
                declared.add(frozenset(cycle["nodes"]))
    actual = components(ids, pairs)
    for cycle in actual - declared:
        errors.append(issue("lifecycle.undeclared_cycle", "存在未声明环：" + "、".join(sorted(cycle)), field="lifecycle.cycles"))
    for cycle in declared - actual:
        errors.append(issue("lifecycle.stale_cycle", "声明的环已不存在：" + "、".join(sorted(cycle)), field="lifecycle.cycles"))
    return errors
