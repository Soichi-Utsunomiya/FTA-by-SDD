from pysdd.sdd import SddManager, Vtree
from collections import deque
import time
import os
import csv

def BDD_vtree(top_gate, var_map, gate_map):

    global custum_vtree, event_count
    event_count = 0
    custum_vtree = []

    order_event = [top_gate]
    visited_event = set()
    basic_parents = {}
    gate_children = {}
    ref_count = {}
    
    def Counter(event):
        if event in gate_children:
            return gate_children[event]
        gate_children[event] = 0
        for child_event in gate_map[event].children:
            if child_event[0] == '~':
                child_event = child_event.removeprefix('~')
            ref_count[child_event] = ref_count.get(child_event, 0) + 1
            if child_event not in gate_map:
                if child_event not in basic_parents:
                    basic_parents[child_event] = []
                basic_parents[child_event].append(event)
                gate_children[event] += 1
            else:  
                gate_children[event] += Counter(child_event)
        return gate_children[event]
    
    ref_count[top_gate] = 1
    Counter(top_gate)

    sorted_children = {}
    for g,c in gate_map.items():

        children = [
            child.removeprefix("~")
            for child in c.children
        ]

        basic_events = list((set(children) & set(basic_parents)))
        sorted_basic_events = sorted(
            basic_events,
            key = lambda child: (
                -len(basic_parents[child.removeprefix("~")]),
                child.removeprefix("~")
            )
        )
        gate_events =list(set(children) - set(basic_events))
        sorted_gate_events = sorted(
            gate_events,
            key = lambda child: (
                gate_children[child.removeprefix("~")],
                child.removeprefix("~")
            )   
        )
        sorted_children[g] = sorted_basic_events + sorted_gate_events

    order_event = deque()
    var_order = []
    visited_event = set()

    def DFS(event):
        visited_event.add(event)
        if event in gate_map:
            for child_event in sorted_children[event]:
                if child_event[0] == '~':
                    child_event = child_event.removeprefix('~')
                if child_event not in visited_event:
                    if child_event not in gate_map:
                        order_event.appendleft(child_event)
                        var_order.append(child_event)
                    visited_event.add(child_event)
                    DFS(child_event)
    DFS(top_gate)

    custum_vtree.append("L " + str(event_count) + " " + str(var_map[order_event.popleft()]))
    right = event_count
    event_count += 1
    while order_event:
        event = order_event.popleft()
        custum_vtree.append("L " + str(event_count) + " " + str(var_map[event]))
        left = event_count
        event_count += 1
        custum_vtree.append("I " + str(event_count) + " " + str(left) + " " + str(right))
        right = event_count
        event_count += 1

    print(f"Order:{list(var_order)}")
    lines = ["vtree " + str(event_count)] + custum_vtree
    return "\n".join(lines).encode(), gate_children, basic_parents, ref_count


class SDDBuilder:
    def __init__(
        self, sdd_manager, var_map, gate_map, gate_children, basic_parents, ref_count,
        trace_writer=None, trace_writer_stream=None
    ):
        self.sdd_manager = sdd_manager
        self.var_map = var_map
        self.gate_map = gate_map
        self.gate_children = gate_children
        self.basic_parents = basic_parents
        self.ref_count = ref_count
        self.cache = {}

        self.trace_writer = trace_writer
        self.trace_writer_stream = trace_writer_stream
        self.start_time = time.perf_counter()
        self.stage = 0

    def _read_cgroup_value(self, filename):
        """cgroup v2のメモリ情報をbytesで取得"""
        path = f"/sys/fs/cgroup/{filename}"

        try:
            with open(path, "r") as f:
                value = f.read().strip()

            if value == "max":
                return None

            return int(value)

        except (OSError, ValueError):
            return None

    def _record_status(self, event_name, event_type):
        """現在のSDD統計情報とメモリ使用量をCSVに記録"""
        if self.trace_writer is None:
            return

        manager = self.sdd_manager

        current_memory = self._read_cgroup_value("memory.current")
        peak_memory = self._read_cgroup_value("memory.peak")

        self.stage += 1

        self.trace_writer.writerow([
            self.stage,
            event_name,
            event_type,
            round(time.perf_counter() - self.start_time, 6),

            manager.count(),
            manager.live_count(),
            manager.dead_count(),

            manager.size(),
            manager.live_size(),
            manager.dead_size(),

            current_memory,
            peak_memory
        ])

        # コンテナが異常終了しても、途中までの記録を残しやすくする
        self.trace_writer_stream.flush()

    def _build_at_least(self, k, child_sdds):
        """k-out-of-n (ATLEAST) ゲートを動的計画法で構築する内部メソッド"""
        n = len(child_sdds)

        if k <= 0:
            return child_sdds[0] | ~child_sdds[0]

        if k > n:
            return child_sdds[0] & ~child_sdds[0]

        memo = {}
        true_node = child_sdds[0] | ~child_sdds[0]
        false_node = child_sdds[0] & ~child_sdds[0]

        def dp(i, needed):
            if needed <= 0:
                return true_node

            if n - i < needed:
                return false_node

            if (i, needed) in memo:
                return memo[(i, needed)]

            var_node = child_sdds[i]
            res = (
                (var_node & dp(i + 1, needed - 1))
                | (~var_node & dp(i + 1, needed))
            )

            memo[(i, needed)] = res
            return res

        return dp(0, k)

    def build_from_name(self, event_name):
        is_not = False
        GC = False

        if event_name[0] == '~':
            is_not = True
            event_name = event_name.removeprefix('~')

        # キャッシュのチェック
        if event_name in self.cache:
            self.ref_count[event_name] -= 1
            result_sdd = self.cache[event_name]
            return ~result_sdd if is_not else result_sdd

        # 基本事象（葉ノード）
        if event_name not in self.gate_map:
            if event_name not in self.var_map:
                raise ValueError(f"Unknown event ID: {event_name}")

            result_sdd = self.sdd_manager.literal(
                self.var_map[event_name]
            )
            result_sdd.ref()
            self.cache[event_name] = result_sdd
            self.ref_count[event_name] -= 1

            self._record_status(event_name, "BASIC")

            return ~result_sdd if is_not else result_sdd

        # ゲート（中間ノード）
        gate_node = self.gate_map[event_name]

        gate_type = gate_node.gate_type.upper()

        if gate_type == "AND":
            result_sdd = None

            for child in gate_node.children:
                child_sdd = self.build_from_name(child)
                if result_sdd is None:
                    result_sdd = child_sdd
                else:
                    result_sdd = result_sdd & child_sdd

                if self.ref_count[child.removeprefix('~')] == 0:
                    child_sdd.deref()
                    self.cache.pop(child.removeprefix('~'))
                    if child.removeprefix('~') in self.gate_map:
                        GC = True
 
        elif gate_type == "OR":
            result_sdd = None

            for child in gate_node.children:
                child_sdd = self.build_from_name(child)

                if result_sdd is None:
                    result_sdd = child_sdd
                else:
                    result_sdd = result_sdd | child_sdd

                if self.ref_count[child.removeprefix('~')] == 0:
                    child_sdd.deref()
                    self.cache.pop(child.removeprefix('~'))
                    if child.removeprefix('~') in self.gate_map:
                        GC = True

        elif gate_type == "NOT":
            result_sdd = ~self.build_from_name(gate_node.children[0])

        elif gate_type == "NAND":
            result_sdd = None

            for child in gate_node.children:
                child_sdd = self.build_from_name(child)

                if result_sdd is None:
                    result_sdd = child_sdd
                else:
                    result_sdd = result_sdd & child_sdd

                if self.ref_count[child.removeprefix('~')] == 0:
                    child_sdd.deref()
                    self.cache.pop(child.removeprefix('~'))
                    if child.removeprefix('~') in self.gate_map:
                        GC = True
            result_sdd = ~result_sdd

        elif gate_type == "NOR":
            result_sdd = None

            for child in gate_node.children:
                child_sdd = self.build_from_name(child)

                if result_sdd is None:
                    result_sdd = child_sdd
                else:
                    result_sdd = result_sdd & child_sdd

                if self.ref_count[child.removeprefix('~')] == 0:
                    child_sdd.deref()
                    self.cache.pop(child.removeprefix('~'))
                    if child.removeprefix('~') in self.gate_map:
                        GC = True
            result_sdd = ~result_sdd

        elif gate_type == "XOR":
            if len(gate_node.children) != 2:
                raise ValueError(
                    f"XORゲート '{event_name}' には2つの子ノードが必要です"
                    f"（現在 {len(gate_node.children)} 個）。"
                )

            a = self.build_from_name(gate_node.children[0])
            b = self.build_from_name(gate_node.children[1])
            result_sdd = (a & ~b) | (~a & b)

        elif gate_type == "ATLEAST":
            if getattr(gate_node, 'k', None) is None:
                raise ValueError(
                    f"ATLEASTゲート '{event_name}' に閾値 'k' が設定されていません。"
                )
            
            child_sdds = [
                        self.build_from_name(child)
                        for child in gate_node.children
                    ]
            
            result_sdd = self._build_at_least(
                gate_node.k, child_sdds
            )

        elif gate_type != "PASS":
            raise ValueError(f"Unknown gate type: {gate_type}")

        result_sdd.ref()
        self.ref_count[event_name] -= 1
        self.cache[event_name] = result_sdd

        if GC:
            self.sdd_manager.garbage_collect()
        # ゲートのSDD構築完了時に記録
        self._record_status(event_name, gate_type)

        return ~result_sdd if is_not else result_sdd


def run_dynamic_sdd_from_pyeda_obj(
    top_gate, var_map, gate_map, vtree_bytes, gate_children, basic_parents, ref_count,
    trace_path
):
    """
    vtree_bytes: BFS_vtree() が返すバイト列。
    trace_path: コンパイル途中の統計情報を保存するCSVファイル。
    """
    import tempfile

    tmp = tempfile.NamedTemporaryFile(
        mode='wb', suffix='.vtree', delete=False
    )

    try:
        tmp.write(vtree_bytes)
        tmp.close()
        vtree = Vtree.from_file(tmp.name.encode())

    finally:
        os.unlink(tmp.name)

    sdd_manager = SddManager(
        vtree=vtree,
        auto_gc_and_minimize=True
    )

    sdd_manager.auto_gc_and_minimize_on()

    print("Auto GC and minimize:",
        sdd_manager.is_auto_gc_and_minimize_on())

    print("Prevent transformation:",
        sdd_manager.is_prevent_transformation_on())

    if trace_path is None:
        sdd_builder = SDDBuilder(
            sdd_manager, var_map, gate_map, gate_children, basic_parents, ref_count
        )

        sdd_node = sdd_builder.build_from_name(top_gate)

    else:
        with open(trace_path, "w", newline="") as f:
            writer = csv.writer(f)

            writer.writerow([
                "Stage",
                "Event",
                "Type",
                "ElapsedTime",
                "TotalNodes",
                "LiveNodes",
                "DeadNodes",
                "TotalSize",
                "LiveSize",
                "DeadSize",
                "MemoryCurrentBytes",
                "MemoryPeakBytes"
            ])

            sdd_builder = SDDBuilder(
                sdd_manager,
                var_map,
                gate_map,
                gate_children,
                basic_parents,
                ref_count,
                trace_writer=writer,
                trace_writer_stream=f
            )

            # Manager生成直後の状態
            sdd_builder._record_status(
                "MANAGER_INITIALIZED", "INITIAL"
            )

            sdd_node = sdd_builder.build_from_name(top_gate)

            # 最上位事象の構築完了
            sdd_builder._record_status(
                top_gate, "TOP_EVENT_COMPLETED"
            )

    return sdd_node, sdd_manager

