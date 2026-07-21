from pysdd.sdd import SddManager, Vtree
import os

class SDDBuilder:
    def __init__(self, sdd_manager, var_map, gate_map):
        self.sdd_manager = sdd_manager
        self.var_map = var_map
        self.gate_map = gate_map
        self.cache = {}

    def _build_at_least(self, k, child_sdds):
        """k-out-of-n (ATLEAST) ゲートを動的計画法で構築する内部メソッド"""
        n = len(child_sdds)

        if k <= 0: return child_sdds[0] | ~child_sdds[0]
        if k > n:  return child_sdds[0] & ~child_sdds[0]

        memo = {}
        true_node  = child_sdds[0] | ~child_sdds[0]
        false_node = child_sdds[0] & ~child_sdds[0]

        def dp(i, needed):
            if needed <= 0:
                return true_node
            if n - i < needed:
                return false_node
            if (i, needed) in memo:
                return memo[(i, needed)]
            var_node = child_sdds[i]
            res = (var_node & dp(i + 1, needed - 1)) | (~var_node & dp(i + 1, needed))
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
            result_sdd = self.sdd_manager.literal(self.var_map[event_name])
            self.cache[event_name] = result_sdd
            return ~result_sdd if is_not else result_sdd

        # ゲート（中間ノード）
        gate_node  = self.gate_map[event_name]
        child_sdds = [self.build_from_name(child) for child in gate_node.children]

        if not child_sdds:
            return None

        result_sdd = child_sdds[0]
        gate_type  = gate_node.gate_type.upper()

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
            result_sdd = self._build_at_least(gate_node.k, child_sdds)
        elif gate_type != "PASS":
            raise ValueError(f"Unknown gate type: {gate_type}")

        self.cache[event_name] = result_sdd
        return ~result_sdd if is_not else result_sdd


def run_sdd_from_pyeda_obj(top_gate, var_map, gate_map, vtree_bytes):
    """
    vtree_bytes: BFS_vtree() が返すバイト列。
    一時ファイル経由でVtreeを構築し、構築直後に削除する。
    """
    import tempfile

    # 一時ファイルに書いてすぐ読み込み、直後に削除
    tmp = tempfile.NamedTemporaryFile(
        mode='wb', suffix='.vtree', delete=False
    )
    try:
        tmp.write(vtree_bytes)
        tmp.close()
        vtree = Vtree.from_file(tmp.name.encode())
    finally:
        os.unlink(tmp.name)   # 確実に削除（例外が起きても）

    sdd_manager = SddManager.from_vtree(vtree)
    sdd_builder = SDDBuilder(sdd_manager, var_map, gate_map)
    sdd_node    = sdd_builder.build_from_name(top_gate)

    return sdd_node, sdd_manager
