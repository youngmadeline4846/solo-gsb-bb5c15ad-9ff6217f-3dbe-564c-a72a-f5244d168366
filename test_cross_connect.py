"""临时供水跨接预览 — solver 端到端测试(不依赖 FastAPI)。

覆盖:
  - 恢复数优先于费用; 费用最小; 编号升序列表字典序决胜;
  - 始终保持漏点全隔离、必保点全有水; 与漏点同分量的普通点不可恢复;
  - 冗余跨接不计费; 空方案条件; 节点跨接前后状态;
  - 候选编号/端点/费用/数量/计划阀门等全部录入校验;
  - 多进水点连通; 备援方案快照同样可用。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from solver import solve_cross_connect, CrossConnectionInputError  # noqa: E402

ok = 0


def check(cond, msg):
    global ok
    assert cond, "FAIL: " + msg
    ok += 1


# 拓扑: S--A--L(s2 阀V1 关), S--H(必保), D--E 孤立干分量(无漏点)
NET = {
    "nodes": [
        {"id": "S", "role": "inlet"},
        {"id": "A", "role": "normal"},
        {"id": "L", "role": "leak"},
        {"id": "H", "role": "must_keep"},
        {"id": "D", "role": "normal"},
        {"id": "E", "role": "normal"},
    ],
    "segments": [
        {"id": "s1", "endpoint_a": "S", "endpoint_b": "A"},
        {"id": "s2", "endpoint_a": "A", "endpoint_b": "L"},
        {"id": "s3", "endpoint_a": "S", "endpoint_b": "H"},
        {"id": "s4", "endpoint_a": "D", "endpoint_b": "E"},
    ],
    "valves": [{"id": "V1", "segment_id": "s2", "cost": 1}],
}

# ---- 1) 基本恢复: 最便宜的跨接恢复 D,E ----
r = solve_cross_connect(NET, ["V1"], [
    {"id": "KA", "endpoint_a": "S", "endpoint_b": "D", "cost": 9},
    {"id": "KB", "endpoint_a": "H", "endpoint_b": "E", "cost": 3},
    {"id": "KC", "endpoint_a": "D", "endpoint_b": "E", "cost": 1},
])
check(r["can_recover"] is True, "can recover")
check(r["selected_ids"] == ["KB"], r["selected_ids"])  # KB 单独 3 元恢复 D,E
check(r["total_cost"] == 3, f"cost {r['total_cost']}")
check(r["recovered_node_ids"] == ["D", "E"], r["recovered_node_ids"])
check(r["recovered_node_count"] == 2, "recovered count")
ns = {n["id"]: n for n in r["node_status"]}
check(ns["D"]["recovered"] and ns["D"]["supplied"]
      and not ns["D"]["before_supplied"], "D recovered")
check(ns["E"]["recovered"] and ns["E"]["supplied"]
      and not ns["E"]["before_supplied"], "E recovered")
check(ns["L"]["status"] == "isolated" and not ns["L"]["supplied"], "L isolated")
check(ns["H"]["status"] == "supplied" and ns["H"]["supplied"], "H kept")
check(ns["S"]["status"] == "inlet_supply", "S inlet")
check(ns["A"]["status"] == "supplied" and not ns["A"]["recovered"], "A already fed")
check(r["solver"] == "cross_connect", "solver tag")
check(r["subset_count"] == 8 and r["valid_subset_count"] == 8, "all subsets valid")
check(r["plan_closed_valves"] == ["V1"], "plan valves echoed")
assert r["selected_cross_connections"] == [{
    "id": "KB", "endpoint_a": "H", "endpoint_b": "E",
    "cost": 3, "status": "flowing"}], r["selected_cross_connections"]

# ---- 2) 恢复数优先于费用: 多恢复一个节点宁可更贵 ----
NET2 = {**NET, "nodes": NET["nodes"] + [{"id": "F", "role": "normal"}]}
r2 = solve_cross_connect(NET2, ["V1"], [
    {"id": "C1", "endpoint_a": "S", "endpoint_b": "D", "cost": 1},  # 恢复 D,E=2
    {"id": "C2", "endpoint_a": "S", "endpoint_b": "F", "cost": 1},  # 再恢复 F=1
])
check(r2["selected_ids"] == ["C1", "C2"], r2["selected_ids"])
check(r2["recovered_node_count"] == 3
      and r2["recovered_node_ids"] == ["D", "E", "F"], "max recovered")
check(r2["total_cost"] == 2, "cost combined")

# ---- 3) 编号升序列表字典序决胜(同恢复数同费用) ----
r3 = solve_cross_connect(NET, ["V1"], [
    {"id": "Z9", "endpoint_a": "S", "endpoint_b": "D", "cost": 3},
    {"id": "A1", "endpoint_a": "H", "endpoint_b": "E", "cost": 3},
])
check(r3["selected_ids"] == ["A1"], f"lex tie {r3['selected_ids']}")

# ---- 4) 与漏点同分量的普通点不可恢复 -> 空方案 ----
LEAKY = {
    "nodes": [
        {"id": "S", "role": "inlet"}, {"id": "A", "role": "normal"},
        {"id": "L", "role": "leak"}, {"id": "B", "role": "normal"},
        {"id": "C", "role": "normal"}, {"id": "H", "role": "must_keep"},
    ],
    "segments": [
        {"id": "s1", "endpoint_a": "S", "endpoint_b": "A"},
        {"id": "s2", "endpoint_a": "A", "endpoint_b": "L"},
        {"id": "s3", "endpoint_a": "L", "endpoint_b": "B"},
        {"id": "s4", "endpoint_a": "B", "endpoint_b": "C"},
        {"id": "s5", "endpoint_a": "S", "endpoint_b": "H"},
    ],
    "valves": [{"id": "V1", "segment_id": "s2", "cost": 1}],
}
r4 = solve_cross_connect(LEAKY, ["V1"], [
    {"id": "X1", "endpoint_a": "A", "endpoint_b": "B", "cost": 3},  # 复通 L
    {"id": "X2", "endpoint_a": "S", "endpoint_b": "C", "cost": 5},  # 复通 L
])
check(r4["can_recover"] is False, "leak component unrecoverable")
check(r4["selected_ids"] == [] and r4["total_cost"] == 0, "empty plan")
check(r4["recovered_node_ids"] == [], "none recovered")
check(r4["valid_subset_count"] == 1, "only empty subset valid")
check("漏点" in r4["message"], "message mentions leak")
# 空方案节点状态: L 仍隔离, B/C 断水, 不存在 recovered
ns4 = {n["id"]: n for n in r4["node_status"]}
check(ns4["L"]["status"] == "isolated" and not ns4["B"]["supplied"]
      and not ns4["B"]["recovered"], "empty statuses")

# ---- 5) 没有断水普通节点 -> 空方案(无需跨接) ----
FED = {
    "nodes": [{"id": "S", "role": "inlet"}, {"id": "A", "role": "normal"},
              {"id": "L", "role": "leak"}, {"id": "H", "role": "must_keep"}],
    "segments": [
        {"id": "s1", "endpoint_a": "S", "endpoint_b": "A"},
        {"id": "s2", "endpoint_a": "A", "endpoint_b": "L"},
        {"id": "s3", "endpoint_a": "S", "endpoint_b": "H"},
    ],
    "valves": [{"id": "V1", "segment_id": "s2", "cost": 1}],
}
r5 = solve_cross_connect(FED, ["V1"],
                         [{"id": "K1", "endpoint_a": "S",
                           "endpoint_b": "A", "cost": 1}])
check(r5["can_recover"] is False and r5["selected_ids"] == [], "all fed -> empty")
check(r5["base_dry_normal_ids"] == [], "no dry normals")

# ---- 6) 空候选列表 -> 空方案 ----
r6 = solve_cross_connect(NET, ["V1"], [])
check(r6["can_recover"] is False and r6["total_cost"] == 0, "no candidates empty")

# ---- 7) 多进水点: 跨接把孤岛接到另一个进水点 ----
MULTI = {
    "nodes": [
        {"id": "S1", "role": "inlet"}, {"id": "S2", "role": "inlet"},
        {"id": "L", "role": "leak"}, {"id": "M", "role": "normal"},
        {"id": "H", "role": "must_keep"}, {"id": "G", "role": "normal"},
    ],
    "segments": [
        {"id": "a", "endpoint_a": "S1", "endpoint_b": "M"},
        {"id": "b", "endpoint_a": "M", "endpoint_b": "L"},
        {"id": "h", "endpoint_a": "S1", "endpoint_b": "H"},
    ],
    "valves": [{"id": "V1", "segment_id": "b", "cost": 1}],
}
r7 = solve_cross_connect(MULTI, ["V1"], [
    {"id": "J1", "endpoint_a": "S2", "endpoint_b": "G", "cost": 2}])
check(r7["selected_ids"] == ["J1"], r7["selected_ids"])
ns7 = {n["id"]: n for n in r7["node_status"]}
check(ns7["G"]["recovered"] and ns7["G"]["connected_inlets"] == ["S2"],
      "G fed via S2")
check(ns7["L"]["status"] == "isolated", "L still isolated")

# ---- 8) 录入校验 ----
def expect_err(closed, cands, needles):
    try:
        solve_cross_connect(NET, closed, cands)
        raise AssertionError("should have raised")
    except CrossConnectionInputError as e:
        joined = " | ".join(e.errors)
        for nd in needles:
            check(nd in joined, f"needle {nd!r} in {e.errors}")


cc = lambda **kw: {"id": "K1", "endpoint_a": "S",
                   "endpoint_b": "D", "cost": 1, **kw}
expect_err(["V1"], [cc(endpoint_a="X")], ["端点 X 不存在"])
expect_err(["V1"], [cc(endpoint_b="S")], ["端点不能相同"])
expect_err(["V1"], [cc(id="")], ["缺少编号"])
expect_err(["V1"], [cc(endpoint_a="")], ["必须选择两个端点"])
for bad in [0, -1, 1.5, True, None, "x"]:
    expect_err(["V1"], [cc(cost=bad)], ["铺设费必须是正整数"])
expect_err(["V1"], [cc(id="K1"), {**cc(), "id": "K1"}], ["跨接编号重复: K1"])
expect_err(["VX"], [cc()], ["计划阀门 VX 不存在"])
expect_err(["V1"], [{"id": f"K{i}", "endpoint_a": "S",
                     "endpoint_b": "D", "cost": 1} for i in range(7)],
           ["超过上限 6"])
try:
    solve_cross_connect(NET, ["V1"], {"id": "K1"})
    raise AssertionError
except CrossConnectionInputError as e:
    check("数组" in " ".join(e.errors), "non-list rejected")

# 十进制字符串费用被接受(与选址预览的严格正整数口径一致)
r8 = solve_cross_connect(NET, ["V1"], [
    {"id": "K1", "endpoint_a": "S", "endpoint_b": "D", "cost": "7"}])
check(r8["total_cost"] == 7, "numeric string accepted")

# ---- 9) 备援方案快照(多计划阀)同样可用 ----
FO = {
    "nodes": [
        {"id": "S", "role": "inlet"}, {"id": "M", "role": "normal"},
        {"id": "L", "role": "leak"}, {"id": "H", "role": "must_keep"},
        {"id": "Q", "role": "normal"},
    ],
    "segments": [
        {"id": "a", "endpoint_a": "S", "endpoint_b": "M"},
        {"id": "b", "endpoint_a": "M", "endpoint_b": "L"},
        {"id": "h", "endpoint_a": "S", "endpoint_b": "H"},
    ],
    "valves": [{"id": "V1", "segment_id": "a", "cost": 1},
               {"id": "V2", "segment_id": "b", "cost": 2}],
}
r9 = solve_cross_connect(FO, ["V1", "V2"], [
    {"id": "T1", "endpoint_a": "H", "endpoint_b": "Q", "cost": 4}])
# 关 a,b 后 M-L 分量含漏点; Q 孤岛可恢复
check(r9["selected_ids"] == ["T1"] and r9["recovered_node_ids"] == ["Q"],
      f"failover snapshot {r9['selected_ids']} {r9['recovered_node_ids']}")
ns9 = {n["id"]: n for n in r9["node_status"]}
check(ns9["M"]["status"] == "disconnected" and ns9["L"]["status"] == "isolated",
      "M dry with leak, L isolated")

# ---- 10) 只读: 入参不被修改 ----
snap_nodes_before = [dict(n) for n in NET["nodes"]]
_ = solve_cross_connect(NET, ["V1"], [dict(id="K1", endpoint_a="S",
                                           endpoint_b="D", cost=1)])
check(NET["nodes"] == snap_nodes_before, "snapshot not mutated")

print(f"cross-connect solver tests: {ok} checks passed")
