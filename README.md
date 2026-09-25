# 管网漏点隔离规划台

在无向供水管网上录入**管段、进水点、漏点、必保供水点**以及**绑定管段的阀门**
（最多 14 个，关闭代价为正整数），系统提供五种规划：

1. **常规规划**：计算使全部漏点与全部进水点断开、同时每个必保供水点仍连通
   至少一个进水点的**最低代价关阀组合**。
2. **单阀失效备援规划**：计划关闭的**任意一枚阀门都可能关不上、保持开启**。
   要求方案在正常执行时、以及每一种单阀失效情形（该阀绑定管段保持通水）下，
   全部漏点均与进水点断开、全部必保点仍连通至少一个进水点；在此前提下最小化
   计划关闭阀门的代价总和。
3. **现场执行顺序规划**：对**已保存的可行方案**（常规或备援均可），按方案
   快照为每枚计划阀门录入**正整数操作时长（分钟）**、为每个漏点录入
   **正整数漏水权重**。操作期间该阀仍开启，每步完成后按多进水点连通性更新
   仍通水漏点；求使各操作时段
   **「时长 × 仍通水漏点权重之和」累计暴露量**最小的执行顺序，所有计划
   阀门都要执行，同暴露量取阀门编号序列字典序最小的唯一顺序。入口在
   **历史方案详情**（也可在刚求解出的可行结果下方直接使用），计算只读、
   不修改原方案。
4. **新增阀门选址预览**：对**当前编辑中的管网**，从**尚无阀门的管段**中
   选择至多 **6 个候选位置**，为每个候选录入**唯一新阀编号、正整数安装费、
   正整数关阀代价**（原阀与候选合计仍不超过 14 个）。系统在「原阀 + 全部
   候选」上寻找能使全部漏点断开进水点且全部必保点仍有水的**增设及关阀
   方案**：**只为实际关闭的候选阀计安装费**，依次最小化
   **安装费合计 → 本次关阀代价**，仍并列时按**新增管段编号列表、关阀编号
   列表**字典序决胜。返回新增位置、费用、关阀清单与供水状态；无解时说明
   **候选范围内不可修复**。本规划为**只读预览**：不修改当前管网，也不写入
   历史方案。
5. **临时供水跨接预览**：在**历史可行隔离方案详情**（也可在刚求解出的可行
   结果下方直接使用）中，基于**方案快照与已关阀管段**录入至多 **6 条**候选
   **跨接**，每条含**唯一编号、两个不同的现有节点、正整数铺设费**，跨接视为
   **新增的通水管段**（无阀，始终通水）。系统枚举候选跨接的全部铺设组合，在
   **始终保持全部漏点与进水点断开、全部必保点仍有水**的前提下，先最大化
   **由断水转为有水的普通节点数**，再最小化**铺设费合计**，并列时按
   **跨接编号升序列表字典序**选取。返回**选中跨接、铺设费、恢复供水节点及各
   节点状态**（含跨接前/后供水对比）；最优组合也无法恢复普通节点时返回
   **空方案**（不铺设跨接，费用 0）。本预览为**只读计算**：不修改管网，也不
   修改历史方案。

> 前两种规划同代价时，均取“关闭阀门编号按升序排列后的列表”字典序最小的方案。
> 备援规划无解时会区分：**原本就没有常规可行方案**（`no_base_plan`）与
> **仅缺少备援方案**（`no_failover_plan`，常规方案存在但都扛不住单阀失效）。

- 常规规划无解时给出明确原因（不存在进水点 / 必保点本来就断水 / 漏点有切不断的
  无阀通路 / 任何隔离方案都会饿死某个必保点）。选址预览无解时复用同一套原因
  分析（在候选扩展后的管网上），并注明候选范围内不可修复。

## 技术栈

Python 3.11 · FastAPI · SQLite（标准库 `sqlite3`）· 原生 HTML/CSS/JavaScript
（无前端构建、无框架）。求解方式：枚举全部阀门子集（≤2¹⁴=16384），对每个
子集做 BFS 连通性判定，保证全局最优。备援规划在此基础上预计算每个子集的
常规可行性，方案 `M` 备援可行当且仅当 `M` 与每个 `M\{j}`（阀门 j 关不上）
均常规可行。执行顺序规划对方案的计划阀门做**子集 DP**（
`suffix[S] = min(d_v·W(S) + suffix[S∪{v}])`，`W(S)` 为关闭集合 S 后仍通水
漏点权重之和，由多进水点 BFS 求出），再正向取字典序最小的最优排列。
选址预览把候选新阀并入管网（原阀 + 候选 ≤ 14），复用同一套图校验与
连通性判定枚举全部「原阀 + 候选」关阀子集，按
`（安装费合计, 本次关阀代价, 新增管段编号列表, 关阀编号列表）` 的
字典序取最优；安装但未关闭的候选阀不影响连通性也不计费，最优解不会
包含它，故关阀子集即方案。临时供水跨接预览在方案关阀后的基线上枚举至多
2⁶=64 个候选跨接铺设子集（跨接为无阀新增边，选中即通水），按
`（-新恢复普通节点数, 铺设费合计, 跨接编号升序列表）` 取最优；恢复数为
0 时返回空方案。

## 一键启动

```bash
docker compose up --build -d
```

启动后访问：

| 用途 | 地址 |
| --- | --- |
| 规划台页面（含常规/备援求解与选址预览入口；执行顺序规划、临时供水跨接预览入口均在历史方案详情内） | http://localhost:8000/ |
| API 健康检查 | http://localhost:8000/api/health |
| 新增阀门选址预览 API | http://localhost:8000/api/plan-siting |
| 执行顺序规划 API（`{id}` 替换为历史可行方案编号） | http://localhost:8000/api/plans/{id}/sequence |
| 临时供水跨接预览 API（`{id}` 替换为历史可行方案编号） | http://localhost:8000/api/plans/{id}/cross-connect |
| OpenAPI 文档 | http://localhost:8000/docs |

服务端口固定为宿主机 **8000**（compose 端口映射 `8000:8000`，容器内监听
8000）。容器**首次启动自动建表**，并在空库中写入一份示例管网（页面上点
「载入示例管网」可随时恢复）。停止：`docker compose down`；连同数据一起
删除：`docker compose down -v`。

## 配置

| 配置项 | 方式 | 默认值 | 说明 |
| --- | --- | --- | --- |
| 服务端口 | compose 的 `ports`，如 `"8080:8000"` | `8000:8000` | 宿主机端口可改，容器内固定 8000 |
| SQLite 文件 | 环境变量 `DB_PATH`（Dockerfile 已设） | `/data/pipeline.db` | `/data` 已挂载为命名卷 `pipeline-data` |

## 本地（无 Docker）运行

```bash
pip install -r requirements.txt
DB_PATH=./pipeline.db uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir app
```
首次运行同样会自动初始化数据库并写入示例数据。

## 页面用法

1. **管网输入**：三张表分别维护节点（选角色：进水点/漏点/必保供水点/普通点）、
   无向管段（选两个端点）、阀门（选一条绑定管段并填正整数代价，≤14 个）。
   下方 Canvas 自动绘制力导向管网示意，红色虚线方块表示被关闭的阀门。
2. 点 **求解最优关阀方案**（常规）：依次展示
   - 关阀清单（编号升序、各阀代价、总代价、枚举统计）；
   - 各节点隔离后的供水状态（含每个节点仍连通的进水点）；
   - 各管段状态：`通水 / 已关阀 / 停水`。
3. 点 **求解单阀失效备援方案**：从当前编辑的管网直接发起备援求解，展示
   - **备援关阀清单与总代价**（编号升序、各阀绑定管段与代价）；
   - **逐阀失效校验表**：正常执行 + 计划清单中每一枚阀门“关不上、保持开启”
     两种情形下，全部漏点是否与进水点断开、全部必保点是否仍有供水；任一情形
     不通过会列出仍通水的漏点 / 断水的必保点；
   - 正常执行时的节点供水状态与管段状态。
   - 无解时横幅明确区分 **无备援方案（存在常规可行方案）** 与
     **常规规划本身无解**，并展示最低代价常规方案逐阀失效的校验明细。
4. **历史方案**：两种求解都会自动入库，历史表“类型”列区分 `常规 / 单阀备援`，
   可回看任一方案及其管网快照（备援方案含全部逐阀失效校验结果）。
5. **现场执行顺序规划**：在第 4 步打开的**方案详情**底部（或刚求解出的可行
   方案结果下方）出现规划卡片：为每枚计划阀门填正整数操作时长（分钟）、为
   每个漏点填正整数漏水权重，点「计算最优执行顺序」后展示
   - 最优阀门顺序、总时长、**累计暴露量**与执行前/完成后的仍通水漏点；
   - 每一步的**起止时间（分钟）**、操作期间仍通水漏点（该阀仍开启，暴露量
     据此计算）、**本步暴露量、刚隔离的漏点、完成后仍通水漏点**与
     **累计暴露量**；
   - 不可行方案不显示入口；录入时遗漏/多余编号或填非正整数会逐条报错，
     计算过程**只读**，原方案与管网快照均不改变。
6. **新增阀门选址预览**：在①管网输入下方的候选卡片中「＋ 添加候选位置」
   （至多 6 行），每行填**新阀编号**、下拉选择**尚无阀门的管段**、填正整数
   **安装费**与**关阀代价**（卡片实时提示「原阀 + 候选 ≤ 14」）。点
   **选址预览求解**后在③区展示只读预览：
   - **新增位置**（新阀编号、安装管段、安装费、关阀代价）；
   - **费用**：安装费合计（仅实际关闭的候选阀）与本次关阀代价合计；
   - **关阀清单**（编号升序，标注每个阀门为「新增」或「原有」）；
   - 方案执行后的各节点供水状态与各管段状态；
   - 无解时横幅明确「候选范围内不可修复」并给出原因（附证据通路等明细）。
   预览**不写入管网、不保存历史方案**，可反复调整候选重新求解。
7. **临时供水跨接预览**：在第 4 步打开的**可行方案详情**底部（或刚求解出的
   可行结果下方）出现跨接预览卡片（不可行方案不显示入口）。卡片先列出方案下
   **当前断水的普通节点**；点「＋ 添加候选跨接」录入至多 **6 条**候选，每条选
   **跨接编号、两个不同的现有节点（下拉）、正整数铺设费**。点**跨接预览求解**
   后展示只读预览：
   - **选中跨接**（编号、两端点、铺设费、状态）与**铺设费合计**；
   - **新恢复普通节点**数量与编号；
   - **各节点状态**：逐节点给出跨接前（有水/断水）、跨接后状态，新恢复的普通
     节点标注「有水 · 新恢复」；
   - 枚举统计（全部组合数与满足「漏点全断开 + 必保点全有水」的组合数）；
   - 无法恢复普通节点时横幅显示**空方案**（不铺设跨接、费用 0）并说明原因
     （例如断水普通点与漏点同处一个断水分量，任何跨接都会使漏点复通）。
   预览**只读**，不修改管网与历史方案；候选编号重复、端点不存在或相同、铺设费
   非正整数、超过 6 条等都会逐条报错。
8. **保存输入**把当前编辑内容落库（求解时也会随方案保存快照，无需先保存）。

> 示例管网中漏点 L 的两条通路各只有一枚阀门（V2、V4），常规方案为
> `V2+V4`（代价 7），但任一枚关不上 L 都会复通，故备援求解返回
> `NO_FAILOVER_PLAN`，可直接在页面上看到逐阀失效校验。

## API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/network` | 读取当前管网输入 |
| PUT | `/api/network` | 校验并整体覆盖管网输入 |
| POST | `/api/plan` | 常规求解并保存方案；请求体可空（用已保存管网），也可直接提交管网 |
| POST | `/api/plan-failover` | **单阀失效备援求解**（独立 API）；请求体规则同 `/api/plan`，复用同一套管网结构与输入校验 |
| POST | `/api/plan-siting` | **新增阀门选址预览**（独立 API，只读：不写管网、不入库方案）；提交当前管网 + 至多 6 个候选新阀 |
| GET | `/api/plans?limit=20` | 最近方案列表（含 `solver`：`base`/`failover`） |
| GET | `/api/plans/{id}` | 方案详情（含节点/管段状态与管网快照） |
| POST | `/api/plans/{id}/sequence` | **现场执行顺序规划**（只读计算，不改原方案）：按快照录入计划阀门时长与漏点权重 |
| POST | `/api/plans/{id}/cross-connect` | **临时供水跨接预览**（只读计算，不改管网/不改方案）：按方案快照与已关阀清单录入至多 6 条候选跨接 |
| POST | `/api/demo` | 恢复内置示例管网 |
| POST | `/api/clear` | 清空管网输入 |

### 请求示例

```bash
curl -X POST http://localhost:8000/api/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "nodes": [
      {"id":"S","role":"inlet"},
      {"id":"L","role":"leak"},
      {"id":"H","role":"must_keep"},
      {"id":"A","role":"normal"}
    ],
    "segments": [
      {"id":"p1","endpoint_a":"S","endpoint_b":"A"},
      {"id":"p2","endpoint_a":"A","endpoint_b":"L"},
      {"id":"p3","endpoint_a":"A","endpoint_b":"H"}
    ],
    "valves": [
      {"id":"V1","segment_id":"p2","cost":2}
    ]
  }'
```

### 可行响应（节选）

```json
{
  "feasible": true,
  "total_cost": 2,
  "closed_valves": ["V1"],
  "subset_count": 2,
  "isolating_subset_count": 1,
  "node_status": [
    {"id":"S","role":"inlet","supplied":true,"status":"inlet_supply","connected_inlets":["S"]},
    {"id":"H","role":"must_keep","supplied":true,"status":"supplied","connected_inlets":["S"]},
    {"id":"L","role":"leak","supplied":false,"status":"isolated","connected_inlets":[]}
  ],
  "segment_status": [
    {"id":"p2","status":"closed","flowing":false}
  ]
}
```

### 无解响应

`feasible:false`，`reason_code` 取值：

| reason_code | 含义 |
| --- | --- |
| `NO_INLET` | 管网没有进水点 |
| `GUARANTEED_ALREADY_DISCONNECTED` | 一个阀门都不关，已有必保点不通任何进水点 |
| `UNCUTTABLE_LEAK_PATH` | 漏点经**不含任何阀门**的管段连到进水点，无法切断（附一条证据通路） |
| `GUARANTEED_CONFLICT` | 每个能隔离漏点的组合都会使某个必保点失去全部进水点（附在所有方案中都断水的必保点及示例组合） |

`/api/plan` 只可能返回以上四种代码。`/api/plan-failover` 除复用以上代码外，
还可能返回下表代码，并用 `solver:"failover"` 与 `infeasible_kind` 区分两类无解：

| reason_code | infeasible_kind | 含义 |
| --- | --- | --- |
| `NO_INLET` / `GUARANTEED_ALREADY_DISCONNECTED` / `UNCUTTABLE_LEAK_PATH` / `GUARANTEED_CONFLICT` | `no_base_plan` | **原本就没有常规可行方案**（与常规规划同因） |
| `NO_FAILOVER_PLAN` | `no_failover_plan` | **仅缺少备援方案**：存在常规可行方案，但没有任何方案能承受任意单阀关不上 |

### 备援求解请求示例

请求体格式与 `/api/plan` 完全一致。例如漏点唯一通路上有两枚串联阀（任一失效，
另一枚仍可切断漏点）：

```bash
curl -X POST http://localhost:8000/api/plan-failover \
  -H 'Content-Type: application/json' \
  -d '{
    "nodes": [
      {"id":"S","role":"inlet"},
      {"id":"M","role":"normal"},
      {"id":"L","role":"leak"},
      {"id":"H","role":"must_keep"}
    ],
    "segments": [
      {"id":"a","endpoint_a":"S","endpoint_b":"M"},
      {"id":"b","endpoint_a":"M","endpoint_b":"L"},
      {"id":"h","endpoint_a":"S","endpoint_b":"H"}
    ],
    "valves": [
      {"id":"V1","segment_id":"a","cost":1},
      {"id":"V2","segment_id":"b","cost":2}
    ]
  }'
```

### 备援可行响应（节选）

```json
{
  "feasible": true,
  "solver": "failover",
  "total_cost": 3,
  "closed_valves": ["V1", "V2"],
  "subset_count": 4,
  "isolating_subset_count": 3,
  "base_feasible_subset_count": 3,
  "failover_candidate_count": 1,
  "normal_check": {
    "scenario": "normal",
    "failed_valve": null,
    "effective_closed_valves": ["V1", "V2"],
    "leaks_isolated": true, "leaks_reachable": [],
    "keeps_supplied": true, "keeps_starved": [],
    "ok": true
  },
  "failure_checks": [
    {
      "scenario": "valve_failure",
      "failed_valve": "V1",
      "segment_id": "a",
      "cost": 1,
      "effective_closed_valves": ["V2"],
      "leaks_isolated": true, "leaks_reachable": [],
      "keeps_supplied": true, "keeps_starved": [],
      "ok": true
    },
    {
      "scenario": "valve_failure",
      "failed_valve": "V2",
      "segment_id": "b",
      "cost": 2,
      "effective_closed_valves": ["V1"],
      "leaks_isolated": true, "leaks_reachable": [],
      "keeps_supplied": true, "keeps_starved": [],
      "ok": true
    }
  ],
  "node_status": ["…同常规规划（正常执行视角）…"],
  "segment_status": ["…同常规规划（正常执行视角）…"]
}
```

`failure_checks` 对计划清单中的**每一枚阀门**给出一行：该阀关不上、其绑定管段
保持通水时的实际关阀集合、仍可达进水点的漏点（`leaks_reachable`）、断水的
必保点（`keeps_starved`）以及本行是否通过（`ok`）。

### 备援无解响应（仅缺少备援方案）

`feasible:false`、`reason_code:"NO_FAILOVER_PLAN"`、
`infeasible_kind:"no_failover_plan"`；`reason_detail.best_base_plan` 给出最低代价
常规方案（编号升序、总代价）及其逐阀失效校验：

```json
{
  "feasible": false,
  "solver": "failover",
  "reason_code": "NO_FAILOVER_PLAN",
  "infeasible_kind": "no_failover_plan",
  "reason_detail": {
    "base_feasible_subset_count": 1,
    "best_base_plan": {
      "closed_valves": ["V2", "V4"],
      "total_cost": 7,
      "failure_checks": ["…每个计划阀门一行, 结构同上…"]
    }
  }
}
```

### 选址预览请求示例

`POST /api/plan-siting` 的请求体为 `{"network": …, "candidates": …}`：
`network` 为当前编辑中的管网（结构同 `/api/plan`，**可省略**，省略时使用
已保存管网）；`candidates` 为至多 6 个候选新阀，每个包含唯一新阀编号
`id`、一条**尚无阀门**的管段 `segment_id`、正整数 `install_cost`（安装费）
与正整数 `close_cost`（关阀代价）。**只读**：不修改管网、不写入历史方案。

```bash
curl -X POST http://localhost:8000/api/plan-siting \
  -H 'Content-Type: application/json' \
  -d '{
    "network": {
      "nodes": [
        {"id":"S","role":"inlet"},
        {"id":"M","role":"normal"},
        {"id":"L","role":"leak"},
        {"id":"H","role":"must_keep"}
      ],
      "segments": [
        {"id":"p1","endpoint_a":"S","endpoint_b":"M"},
        {"id":"p2","endpoint_a":"M","endpoint_b":"L"},
        {"id":"p3","endpoint_a":"S","endpoint_b":"H"}
      ],
      "valves": []
    },
    "candidates": [
      {"id":"NV1","segment_id":"p2","install_cost":5,"close_cost":2},
      {"id":"NV2","segment_id":"p1","install_cost":9,"close_cost":1}
    ]
  }'
```

### 选址预览可行响应（节选）

```json
{
  "feasible": true,
  "solver": "siting",
  "new_valves": [
    {"id":"NV1","segment_id":"p2","install_cost":5,"close_cost":2}
  ],
  "new_segment_ids": ["p2"],
  "install_cost_total": 5,
  "close_cost_total": 2,
  "closed_valves": ["NV1"],
  "closed_valve_details": [
    {"id":"NV1","segment_id":"p2","close_cost":2,"is_new":true,"install_cost":5}
  ],
  "candidate_count": 2,
  "subset_count": 4,
  "isolating_subset_count": 3,
  "node_status": ["…同常规规划（方案执行后视角）…"],
  "segment_status": ["…未增设的候选阀不会出现在管段 valve_id 上…"]
}
```

- 优化次序：`install_cost_total`（只为实际关闭的候选阀计安装费）最小 →
  `close_cost_total`（本次关阀代价 = 被关闭原阀的关闭代价 + 新阀关阀代价
  之和）最小 → 新增管段编号升序列表 `new_segment_ids` 字典序 → 关阀编号
  升序列表 `closed_valves` 字典序。
- 上例中 NV2（安装费 9）单独也能隔离漏点，但 NV1（安装费 5）安装费更低，
  故选 NV1；未被增设的候选阀不计费，也不会出现在 `new_valves` 与管段
  状态中。

### 选址预览无解响应

`feasible:false`、`solver:"siting"`，`message` 以「候选范围内不可修复」
开头；`reason_code` 复用常规规划的四种（`NO_INLET` /
`GUARANTEED_ALREADY_DISCONNECTED` / `UNCUTTABLE_LEAK_PATH` /
`GUARANTEED_CONFLICT`），在「原阀 + 全部候选」扩展管网上判定，即
**把全部候选新阀都装上也无法修复**。

### 选址预览错误响应（422，`detail.errors` 逐条列出）

| 场景 | 示例错误 |
| --- | --- |
| 候选超过 6 个 | `候选位置数量为 7, 超过上限 6 个` |
| 新阀编号与原阀/其他候选重复 | `阀门编号重复: V1` |
| 候选管段已有阀门 / 两候选共用管段 | `管段 p1 同时绑定了阀门 V1 和 NV1(每条管段最多 1 个阀门)` |
| 候选管段不存在 | `阀门 NV1: 绑定的管段 pX 不存在` |
| 缺少新阀编号 / 未选管段 | `候选 #1: 缺少新阀编号`、`候选阀门 NV1: 必须选择安装管段` |
| 安装费非正整数 | `候选阀门 NV1: 安装费必须是正整数, 收到: 0` |
| 关阀代价非正整数 | `阀门 NV1: 关闭代价必须是正整数` |
| 原阀 + 候选合计超过 14 个 | `阀门数量为 15, 超过上限 14 个` |

### 现场执行顺序规划请求示例

对已保存的**可行方案** `id=1` 调用（只读，不入库、不改方案）。`durations`
的键必须**恰好**是方案 `closed_valves` 中的全部计划阀门，`leak_weights` 的键
必须**恰好**是方案快照中的全部漏点，值均为正整数：

```bash
curl -X POST http://localhost:8000/api/plans/1/sequence \
  -H 'Content-Type: application/json' \
  -d '{"durations":{"V2":10,"V4":20},"leak_weights":{"L":5}}'
```

### 执行顺序可行响应（节选）

```json
{
  "ok": true,
  "plan_id": 1,
  "solver": "base",
  "closed_valves": ["V2", "V4"],
  "durations": {"V2": 10, "V4": 20},
  "leak_weights": {"L": 5},
  "initial_flowing_leaks": ["L"],
  "initial_flowing_weight": 5,
  "final_flowing_leaks": [],
  "sequence": ["V2", "V4"],
  "total_duration": 30,
  "total_exposure": 150,
  "steps": [
    {
      "order": 1,
      "valve_id": "V2",
      "segment_id": "s5",
      "duration": 10,
      "start": 0,
      "end": 10,
      "flowing_leaks_during": ["L"],
      "flowing_weight_during": 5,
      "exposure": 50,
      "newly_isolated_leaks": [],
      "flowing_leaks_after": ["L"],
      "flowing_weight_after": 5,
      "cumulative_exposure": 50
    },
    {
      "order": 2,
      "valve_id": "V4",
      "segment_id": "s6",
      "duration": 20,
      "start": 10,
      "end": 30,
      "flowing_leaks_during": ["L"],
      "flowing_weight_during": 5,
      "exposure": 100,
      "newly_isolated_leaks": ["L"],
      "flowing_leaks_after": [],
      "flowing_weight_after": 0,
      "cumulative_exposure": 150
    }
  ]
}
```

- 第 k 步的暴露量 = 该阀时长 × **操作期间**（该阀仍开启，已关闭的只有前
  k-1 枚）仍通水漏点权重之和；`start/end` 为累计分钟时刻，从 0 起算。
- `newly_isolated_leaks` 为本步完成后由通水变隔离的漏点，
  `flowing_leaks_after` 为本步完成后仍通水的漏点；`cumulative_exposure`
  为截至本步的累计暴露量。
- 顺序**唯一**：达到最小累计暴露量的多个排列中，取阀门编号序列字典序
  （按编号字符串比较，如 `V10 < V2`）最小者。
- 方案不关闭任何阀门时返回空 `steps`、`total_exposure: 0`。

### 执行顺序错误响应

| 场景 | HTTP 状态 | 返回内容 |
| --- | --- | --- |
| 方案编号不存在 | 404 | `方案不存在` |
| 目标方案不可行（无解方案） | 422 | `detail.errors` 指明方案不可行及 `reason_code`，不可规划 |
| 遗漏计划阀门时长 / 漏点权重 | 422 | 如 `缺少计划阀门的操作时长: V4`、`缺少漏点的漏水权重: L` |
| 多余编号（非计划阀门 / 非漏点） | 422 | 如 `提供了非计划阀门的操作时长(多余编号): V1`、`提供了非漏点的漏水权重(多余编号): X` |
| 时长或权重不是正整数（0、负数、小数、字符串、布尔、null） | 422 | 如 `阀门 V2 的操作时长必须是正整数(分钟), 收到: 0`、`漏点 L 的漏水权重必须是正整数, 收到: 1.5` |

### 临时供水跨接预览请求示例

对已保存的**可行方案** `id=1` 调用（只读，不修改管网与历史方案）。请求体为
`{"cross_connections": …}`，候选跨接至多 **6 条**，每条包含唯一编号 `id`、
两个**不同的现有节点** `endpoint_a` / `endpoint_b`（必须是方案快照中的节点）、
正整数 `cost`（铺设费）。跨接视为**无阀、始终通水的新增管段**：

```bash
curl -X POST http://localhost:8000/api/plans/1/cross-connect \
  -H 'Content-Type: application/json' \
  -d '{"cross_connections":[
    {"id":"K1","endpoint_a":"S","endpoint_b":"D","cost":3},
    {"id":"K2","endpoint_a":"H","endpoint_b":"E","cost":5}
  ]}'
```

### 跨接预览可行响应（节选）

```json
{
  "ok": true,
  "plan_id": 1,
  "solver": "cross_connect",
  "plan_closed_valves": ["V1"],
  "candidate_count": 2,
  "subset_count": 4,
  "valid_subset_count": 4,
  "base_dry_normal_ids": ["D", "E"],
  "can_recover": true,
  "selected_cross_connections": [
    {"id": "K1", "endpoint_a": "S", "endpoint_b": "D", "cost": 3, "status": "flowing"}
  ],
  "selected_ids": ["K1"],
  "total_cost": 3,
  "recovered_node_count": 2,
  "recovered_node_ids": ["D", "E"],
  "message": "…铺设跨接 K1(S—D, 费用 3); 铺设费合计 3, 新恢复 2 个断水普通节点供水(D, E)…",
  "node_status": [
    {"id":"S","role":"inlet","supplied":true,"status":"inlet_supply",
     "before_supplied":true,"recovered":false,"connected_inlets":["S"]},
    {"id":"D","role":"normal","supplied":true,"status":"supplied",
     "before_supplied":false,"recovered":true,"connected_inlets":["S"]},
    {"id":"L","role":"leak","supplied":false,"status":"isolated",
     "before_supplied":false,"recovered":false,"connected_inlets":[]}
  ]
}
```

- 优化次序：`recovered_node_count`（由断水转为有水的**普通节点**数）最多 →
  `total_cost`（选中跨接铺设费合计）最小 → `selected_ids`（跨接编号升序列表）
  字典序最小；`subset_count` 为全部候选组合数（2ⁿ），`valid_subset_count`
  为其中满足「全部漏点与进水点断开 + 全部必保点仍有水」的组合数。
- `node_status` 对每个节点额外给出 `before_supplied`（方案基线是否有水）与
  `recovered`（本次是否由断水新恢复）；漏点保持 `isolated`，复通漏点的组合
  直接被排除。
- 只统计**普通节点（normal）**的恢复数；必保点本就必须有水，不计入恢复数。

### 跨接预览空方案响应

最优组合也无法恢复任何普通节点时 `can_recover:false`、`selected_ids:[]`、
`total_cost:0`，`message` 说明原因（如断水普通点与漏点同处一个断水分量，任何
跨接都会使漏点复通进水点）：

```json
{
  "ok": true,
  "solver": "cross_connect",
  "can_recover": false,
  "selected_cross_connections": [],
  "selected_ids": [],
  "total_cost": 0,
  "recovered_node_count": 0,
  "recovered_node_ids": [],
  "base_dry_normal_ids": ["B", "C"],
  "message": "临时供水跨接预览(只读…): 断水普通节点均与漏点同处断水分量… 返回空方案: 不铺设跨接, 铺设费 0。",
  "node_status": ["…同可行响应结构（不铺设任何跨接时的状态）…"]
}
```

### 跨接预览错误响应

| 场景 | HTTP 状态 | 返回内容 |
| --- | --- | --- |
| 方案编号不存在 | 404 | `方案不存在` |
| 目标方案不可行（无解方案） | 422 | `detail.errors` 指明方案不可行及 `reason_code`，不能预览 |
| 候选跨接超过 6 条 | 422 | `候选跨接数量为 7, 超过上限 6 个` |
| 跨接编号为空 / 重复 | 422 | `跨接 #1: 缺少编号`、`跨接编号重复: K1` |
| 端点不存在 / 两端相同 / 缺端点 | 422 | `跨接 K1: 端点 X 不存在于方案快照节点中`、`跨接 K1: 两个端点不能相同(S)`、`跨接 K1: 必须选择两个端点` |
| 铺设费非正整数（0、负数、小数、布尔、null、非数字串） | 422 | `跨接 K1: 铺设费必须是正整数, 收到: 0` |
| 计划阀门不在快照中（历史数据异常） | 422 | `计划阀门 VX 不存在于方案快照的管网中` |

## 建模约定

- 管段为无向边；每条管段最多绑定 1 个阀门，关阀等价于从图中删除该管段。
- 节点四种角色互斥；漏点本身隔离后为“已隔离”，与漏点处于同一无水分量的
  普通点显示为“断水”。
- 多个漏点必须**全部**与所有进水点断开才算隔离成功。
- **单阀失效备援**：计划关阀集合 M 中每一枚阀门都可能“关不上、保持开启”，
  失效时实际关阀集合为 M 去掉该阀（其余阀门照常关闭）。备援可行要求 M 本身
  及每个 M\\{j} 都满足“漏点全隔离 + 必保点全有水”。失效的仅是“关闭动作”，
  因此计划清单之外的阀门不受影响；不关闭任何阀门的方案天然备援可行。
- 备援规划与常规规划**目标一致**：仅在可行解集合上不同，优化目标仍是计划
  关闭阀门的代价总和最小，同代价按编号升序列表的字典序取最小。
- **现场执行顺序**：计划阀门逐枚操作，操作阀门 v 的时段内 v 仍开启，故该
  时段生效的关阀集合是此前已完成的阀门；暴露量 = v 的正整数时长 × 此时段
  仍通水漏点（与至少一个进水点连通）的正整数权重之和。所有计划阀门都必须
  执行，全部完成后可行方案的漏点必全部隔离。仍通水漏点集合只取决于已关闭
  阀门集合，与顺序无关，因此用 2^k（k=计划阀门数≤14）个子集的子集 DP 求
  最小累计暴露量，并正向构造阀门编号序列字典序最小的唯一最优排列；该计算
  完全只读，不修改原方案与管网快照。
- **新增阀门选址预览**：候选位置只能选在**尚无阀门的管段**上，至多 6 个，
  每个候选有唯一新阀编号（不得与原阀或其他候选重复）、正整数安装费与正整数
  关阀代价，且原阀与候选合计不超过 14 个。方案 = 在「原阀 + 候选」中选择
  要关闭的阀门子集：被关闭的候选阀即**增设位置**，**只为实际关闭的候选阀
  计安装费**（安装但不关闭的候选阀不影响连通性也不计费，最优解不会包含
  它）。优化次序：安装费合计最小 → 本次关阀代价（被关闭原阀的关闭代价 +
  新阀关阀代价之和）最小 → 新增管段编号升序列表字典序 → 关阀编号升序
  列表字典序。求解复用常规规划的图校验与 BFS 连通性判定（在候选扩展后的
  管网上枚举，≤2¹⁴ 个子集）；无解原因同样复用常规分析并注明**候选范围内
  不可修复**。整个规划为只读预览：不修改当前管网，也不写入历史方案。
- **临时供水跨接预览**：以方案快照 + 计划关阀清单为基线（关阀即删边）。候选
  跨接为**无阀、始终通水的新增管段**，至多 6 条，每条有唯一编号（候选之间不得
  重复）、两个**不同的现有节点**（取自方案快照）、正整数铺设费。枚举全部 2⁶
  个铺设子集，逐一在加边后的图上做 BFS，仅保留铺设后**全部漏点仍与进水点断开、
  全部必保点仍有水**的组合；在此集合上依次最大化**由断水转为有水的普通节点数**
  （只计 normal，不含必保点）、最小化**铺设费合计**、取**跨接编号升序列表字典序
  最小**者。与漏点同处一个断水分量的普通点无法在不复通漏点的前提下恢复；最优
  组合恢复数为 0 时返回**空方案**（不铺设跨接、费用 0）。计算完全只读，不修改
  管网与历史方案，仅适用于**可行**方案。
