from decimal import Decimal

class SDDEvaluator:
    def __init__(self, par_map):
        self.par_map = par_map
        self.cache = {}  # 一度計算したノードの確率を保存する辞書

    def explore(self, current_node):
        # ★【超重要】既に計算済みのノードなら、一瞬でキャッシュを返して再帰を打ち切る
        # ※ nodeに id 属性など、一意に識別できるプロパティがあることを想定
        node_id = id(current_node) 
        if node_id in self.cache:
            return self.cache[node_id]

        probability = Decimal(0)
        for node in current_node.elements():
            p, s = node
            
            # --- pの処理 ---
            if p.is_decision():
                probability_p = Decimal(self.explore(p))
            elif p.is_true():
                probability_p = Decimal(1)
            elif p.is_false():
                probability_p = Decimal(0)
            else:
                if p.literal < 0:
                    probability_p = Decimal(1) - Decimal(self.par_map[p.literal*(-1)])
                else:
                    probability_p = Decimal(self.par_map[p.literal])

            # --- sの処理 ---
            if s.is_decision():
                probability_s = Decimal(self.explore(s))
            elif s.is_true():
                probability_s = Decimal(1)
            elif s.is_false():
                probability_s = Decimal(0)
            else:
                if s.literal < 0:
                    probability_s = Decimal(1) - Decimal(self.par_map[s.literal*(-1)])
                else:
                    probability_s = Decimal(self.par_map[s.literal])
                    
            probability += probability_p * probability_s

        # ★ 計算結果をキャッシュに保存してから返す
        self.cache[node_id] = probability
        return probability