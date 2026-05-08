from FT_to_dnf import prob_map
#from make_vtree import name_prob_map
from BFS_vtree import name_prob_map
from decimal import *

def explore(current_node):
    probability = Decimal(0)
    for node in current_node.elements():
        p, s = node
        if p.is_decision():
            probability_p = Decimal(explore(p))
        elif p.is_true():
            probability_p = Decimal(1)
        elif p.is_false():
            probability_p = Decimal(0)
        else:
            if p.literal<0:
                probability_p = Decimal(1) - Decimal(name_prob_map[p.literal*(-1)-1])
            else:
                probability_p = Decimal(name_prob_map[p.literal-1])

        if s.is_decision():
            probability_s = Decimal(explore(s))
        elif s.is_true():
            probability_s = Decimal(1)
        elif s.is_false():
            probability_s = Decimal(0)
        else:
            if s.literal<0:
                probability_s = Decimal(1)- Decimal(name_prob_map[s.literal*(-1)-1])
            else:
                probability_s = Decimal(name_prob_map[s.literal-1])
        probability += probability_p * probability_s
        #print(probability)
    return probability