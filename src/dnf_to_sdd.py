from pysdd.sdd import SddManager, Vtree
import xml.etree.ElementTree as ET
import sys

class SDDBuilder:
    def __init__(self, sdd_manager, var_map, gate_map):
        self.sdd_manager = sdd_manager
        self.var_map = var_map
        self.gate_map = gate_map
        self.cache = {}

    def _build_at_least(self, k, child_sdds):
        """k-out-of-n (ATLEAST) ゲートを動的計画法で構築する内部メソッド"""
        n = len(child_sdds)
        
        # 安全対策：kが0以下なら常にTrue、変数の数より多ければ常にFalse
        if k <= 0: return child_sdds[0] | ~child_sdds[0]
        if k > n: return child_sdds[0] & ~child_sdds[0]

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
            res = (var_node & dp(i + 1, needed - 1)) | (~var_node & dp(i + 1, needed))
            memo[(i, needed)] = res
            return res

        return dp(0, k)
    
    def build_from_name(self, event_name):
        if event_name[0] == '~':
            event_name = event_name.removeprefix('~')
            if event_name in self.cache:
                return ~self.cache[event_name]
        if event_name in self.cache:
            return self.cache[event_name]

        if event_name not in self.gate_map:
            if event_name[0] == '~':
                event_name = event_name.removeprefix('~')
                result_sdd = self.sdd_manager.literal(self.var_map[event_name])
                return ~result_sdd
            if event_name not in self.var_map:
                raise ValueError(f"Unknown event ID: {event_name}")
            result_sdd = self.sdd_manager.literal(self.var_map[event_name])
            self.cache[event_name] = result_sdd
            return result_sdd

        gate_node = self.gate_map[event_name]
        
        child_sdds = [self.build_from_name(child) for child in gate_node.children]

        if not child_sdds:
            return None

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
            # フォールトツリーにおけるXORは通常「2つの事象のうちどちらか片方のみが起きる」ことを指します
            if len(child_sdds) != 2:
                raise ValueError(f"XORゲート '{event_name}' には2つの子ノードが必要です（現在 {len(child_sdds)} 個）。")
            
            node_A = child_sdds[0]
            node_B = child_sdds[1]
            
            # (A & ~B) | (~A & B) を計算
            result_sdd = (node_A & ~node_B) | (~node_A & node_B)
        elif gate_type == "ATLEAST":
            if getattr(gate_node, 'k', None) is None:
                raise ValueError(f"ATLEASTゲート '{event_name}' に閾値 'k' が設定されていません。")
            result_sdd = self._build_at_least(gate_node.k, child_sdds)
        elif gate_type != "PASS":
            raise ValueError(f"Unknown gate type: {gate_type}")

        # ★追加：完成したゲートのSDDを記憶しておく
        self.cache[event_name] = result_sdd
        return result_sdd

def run_sdd_from_pyeda_obj(top_gate, var_map, gate_map, output_file, vtree_file):
    
    print(f"Converting PyEDA object to SDD... ")

    vtree = Vtree.from_file(vtree_file.encode())
    sdd_manager = SddManager.from_vtree(vtree)

    sdd_builder = SDDBuilder(sdd_manager, var_map, gate_map)
    sdd_node = sdd_builder.build_from_name(top_gate)

    with open(output_file + "_sdd.dot", "w") as out:
        print(sdd_node.dot(), file=out)
    with open(output_file + "_vtree.dot", "w") as out:
        print(vtree.dot(), file=out)
    
    print("Conversion successful.")
    
    # ★修正：sdd_nodeだけでなく、絶対に sdd_manager も一緒に返す！
    return sdd_node, sdd_manager