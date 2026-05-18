from decimal import Decimal

class SDDEvaluator:
    def __init__(self, par_map):
        self.par_map = par_map
        self.cache = {}

    def explore(self, current_node):
        # ★【修正点1】 Pythonの id() ではなく、SDD固有の .id プロパティを使う！
        node_id = current_node.id 
        if node_id in self.cache:
            return self.cache[node_id]

        # ★【修正点2】 どんなノードが来ても最初に判定して処理を分ける（コードの重複をなくす）
        if current_node.is_true():
            return Decimal(1)
        
        if current_node.is_false():
            return Decimal(0)
            
        if current_node.is_literal():
            # 葉ノード（基本事象）の場合
            literal = current_node.literal
            if literal < 0:
                probability = Decimal(1) - Decimal(self.par_map[literal*(-1)])
            else:
                probability = Decimal(self.par_map[literal])
            
            self.cache[node_id] = probability
            return probability

        # 内部ノード（Decision Node）の場合
        probability = Decimal(0)
        for p, s in current_node.elements():
            # pとsに対しても自分自身（explore）を呼べば、上の条件分岐が全部よしなにやってくれる
            probability_p = self.explore(p)
            probability_s = self.explore(s)
            probability += probability_p * probability_s

        # 計算結果をキャッシュに保存して返す
        self.cache[node_id] = probability
        return probability