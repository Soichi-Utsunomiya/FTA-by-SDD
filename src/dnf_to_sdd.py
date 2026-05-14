from pysdd.sdd import SddManager, Vtree
from pyeda.boolalg.expr import Variable, Complement, AndOp, OrOp
import xml.etree.ElementTree as ET
import os
import sys

class SDDBuilder:
    def __init__(self, sdd_manager, var_map, gate_map):
        self.sdd_manager = sdd_manager
        self.var_map = var_map
        self.gate_map = gate_map

    def build_from_name(self, event_name):
        """名前（文字列）からSDDノードを構築するよう修正"""
        if event_name not in self.gate_map:
            # 基本事象の場合
            if event_name not in self.var_map:
                raise ValueError(f"Unknown event ID: {event_name}")
            return self.sdd_manager.literal(self.var_map[event_name])

        # ゲートの場合
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
        else:
            raise ValueError(f"Unknown gate type: {gate_type}")

        return result_sdd

def run_sdd_from_pyeda_obj(top_gate, var_map, gate_map, output_file, vtree_file):
    
    print(f"Converting PyEDA object to SDD... ")

    vtree = Vtree.from_file(vtree_file.encode())
    sdd_manager = SddManager.from_vtree(vtree)
    print(var_map)
    #sdd_manager.minimize()

    # 変数名とSDD変数の対応付け
    #sdd_node = build_SDD_node(root, sdd_manager, var_map)
    sdd_builder = SDDBuilder(sdd_manager, var_map, gate_map)
    sdd_node = sdd_builder.build_from_name(top_gate)

    with open(output_file + "_sdd.dot", "w") as out:
        print(sdd_node.dot(), file=out)
    with open(output_file + "_vtree.dot", "w") as out:
        print(vtree.dot(), file=out)
    
    print("Conversion successful.")
    return sdd_node