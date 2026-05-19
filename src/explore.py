from decimal import Decimal

class SDDEvaluator:
    def __init__(self, par_map):
        self.par_map = par_map
        self.cache = {}

    def explore(self, current_node):
        node_id = current_node.id 
        if node_id in self.cache:
            return self.cache[node_id]

        if current_node.is_true():
            return Decimal(1)
        
        if current_node.is_false():
            return Decimal(0)
            
        if current_node.is_literal():
            literal = current_node.literal
            if literal < 0:
                probability = Decimal(1) - Decimal(self.par_map[literal*(-1)])
            else:
                probability = Decimal(self.par_map[literal])
            
            self.cache[node_id] = probability
            return probability

        probability = Decimal(0)
        for p, s in current_node.elements():
            probability_p = self.explore(p)
            probability_s = self.explore(s)
            probability += probability_p * probability_s

        self.cache[node_id] = probability
        return probability