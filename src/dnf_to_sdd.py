from pysdd.sdd import SddManager, Vtree
import os
import csv
import time
import heapq
from itertools import count


class SDDBuilder:
    def __init__(
        self, sdd_manager, var_map, gate_map, gate_children, basic_parents,
        trace_writer=None, trace_writer_stream=None
    ):
        self.sdd_manager = sdd_manager
        self.var_map = var_map
        self.gate_map = gate_map
        self.gate_children = gate_children
        self.basic_parents = basic_parents
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

        if event_name[0] == '~':
            is_not = True
            event_name = event_name.removeprefix('~')

        # キャッシュのチェック
        if event_name in self.cache:
            result_sdd = self.cache[event_name]
            return ~result_sdd if is_not else result_sdd

        # 基本事象（葉ノード）
        if event_name not in self.gate_map:
            if event_name not in self.var_map:
                raise ValueError(f"Unknown event ID: {event_name}")

            result_sdd = self.sdd_manager.literal(
                self.var_map[event_name]
            )
            self.cache[event_name] = result_sdd

            self._record_status(event_name, "BASIC")

            return ~result_sdd if is_not else result_sdd

        # ゲート（中間ノード）
        gate_node = self.gate_map[event_name]
        print(gate_node.children)
        """basic = []
        gates = []
        for child in gate_node.children:
            if child in self.basic_parents:
                basic.append(child)
            else:
                gates.append(child)
        #basic.sort(key = lambda child:(-len(self.basic_parents[child])))
        #gates.sort(key = lambda child :(-len(self.gate_children[child])))
        #children = basic + gates
        #print(children)"""
        child_sdds = [
            self.build_from_name(child)
            for child in gate_node.children
        ]

        if not child_sdds:
            return None

        #print(child_sdds,[x.size() for x in child_sdds])
        child_sdds.sort(key=lambda child: child.size())
        #print(child_sdds,[x.size() for x in child_sdds])

        result_sdd = child_sdds[0]
        gate_type = gate_node.gate_type.upper()

        if gate_type == "AND":
            for child_sdd in child_sdds[1:]:
                result_sdd = result_sdd & child_sdd

        elif gate_type == "OR":
            for child_sdd in child_sdds[1:]:
                result_sdd = result_sdd | child_sdd

        elif gate_type == "NOT":
            result_sdd = ~result_sdd

        elif gate_type == "NAND":
            for child_sdd in child_sdds[1:]:
                result_sdd = result_sdd & child_sdd
            result_sdd = ~result_sdd

        elif gate_type == "NOR":
            for child_sdd in child_sdds[1:]:
                result_sdd = result_sdd | child_sdd
            result_sdd = ~result_sdd

        elif gate_type == "XOR":
            if len(child_sdds) != 2:
                raise ValueError(
                    f"XORゲート '{event_name}' には2つの子ノードが必要です"
                    f"（現在 {len(child_sdds)} 個）。"
                )

            a, b = child_sdds
            result_sdd = (a & ~b) | (~a & b)

        elif gate_type == "ATLEAST":
            if getattr(gate_node, 'k', None) is None:
                raise ValueError(
                    f"ATLEASTゲート '{event_name}' に閾値 'k' が設定されていません。"
                )

            result_sdd = self._build_at_least(
                gate_node.k, child_sdds
            )

        elif gate_type != "PASS":
            raise ValueError(f"Unknown gate type: {gate_type}")

        self.cache[event_name] = result_sdd

        # ゲートのSDD構築完了時に記録
        self._record_status(event_name, gate_type)

        return ~result_sdd if is_not else result_sdd


def run_sdd_from_pyeda_obj(
    top_gate, var_map, gate_map, vtree_bytes, gate_children, basic_parents,
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

    sdd_manager = SddManager.from_vtree(vtree)

    if trace_path is None:
        sdd_builder = SDDBuilder(
            sdd_manager, var_map, gate_map, gate_children, basic_parents
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

