from pysdd.sdd import SddManager, Vtree

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
       # 元の名前を保持しておく
        original_event_name = event_name
        is_not = False

        if event_name[0] == '~':
            is_not = True
            event_name = event_name.removeprefix('~') # ここで prefix を外す

        # 【1】キャッシュのチェック
        if event_name in self.cache:
            result_sdd = self.cache[event_name]
            # 否定として呼ばれたなら、キャッシュのSDDを否定にして返す
            if is_not:
                return ~result_sdd
            return result_sdd

        # 【2】基本事象（葉ノード）の処理
        if event_name not in self.gate_map:
            if event_name not in self.var_map:
                raise ValueError(f"Unknown event ID: {event_name}")
            
            # PySDDの肯定リテラルノードを生成
            result_sdd = self.sdd_manager.literal(self.var_map[event_name])
            
            # キャッシュには「肯定のノード」として保存する（※重要）
            self.cache[event_name] = result_sdd
            
            # 否定として呼ばれていたなら、否定にして返す
            if is_not:
                return ~result_sdd
            return result_sdd
        
        # 【3】ゲート（中間ノード）の処理はここから下へ続く...
        # ゲートの計算結果（gate_sdd）が得られたら、
        # self.cache[event_name] = gate_sdd  でキャッシュに保存し、
        # if is_not: return ~gate_sdd
        # return gate_sdd  のように返す。

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
        # キャッシュには必ず「肯定（ベース）」の形で保存する
        self.cache[event_name] = result_sdd
        
        # ★★★ここが抜けていました！★★★
        # もし親から「否定（~）」として呼ばれていたなら、反転させてから返す
        if is_not:
            return ~result_sdd
            
        return result_sdd

def run_sdd_from_pyeda_obj(top_gate, var_map, gate_map, output_file, vtree_file):
    
    #print(f"Converting PyEDA object to SDD... ")

    vtree = Vtree.from_file(vtree_file.encode())
    sdd_manager = SddManager.from_vtree(vtree)

    sdd_builder = SDDBuilder(sdd_manager, var_map, gate_map)
    sdd_node = sdd_builder.build_from_name(top_gate)

    #print("Conversion successful.")
    
    return sdd_node, sdd_manager