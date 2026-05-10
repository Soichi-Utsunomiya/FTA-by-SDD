from pysdd.sdd import SddManager, Vtree
from pyeda.boolalg.expr import Variable, Complement, AndOp, OrOp
import xml.etree.ElementTree as ET
import os
import sys

def build_SDD_node(event_elem, sdd_manager, var_map):
    gate = event_elem.get("gate")
    event_id = event_elem.get("id")

    # 1. 葉ノード（基本事象）の場合
    if gate is None:
        if event_id not in var_map:
            raise ValueError(f"Unknown event ID: {event_id}")
        # Vtree/Managerにおける変数のインデックス(1, 2, 3...)を取得し、リテラル(SDDノード)化
        var_index = var_map[event_id]
        return sdd_manager.literal(var_index)

    # 2. 子ノードを再帰的に評価して、子ノードのSDDリストを取得
    child_sdds = []
    for child_elem in event_elem.findall("event"):
        child_sdd = build_SDD_node(child_elem, sdd_manager, var_map)
        if child_sdd is not None:
            child_sdds.append(child_sdd)

    if not child_sdds:
        return None

    # 3. ゲートの種類に応じてSDD同士を結合 (Apply演算)
    result_sdd = child_sdds[0]
    
    if gate.upper() == "AND":
        for child_sdd in child_sdds[1:]:
            result_sdd = result_sdd & child_sdd  # PySDDのAND演算
            
    elif gate.upper() == "OR":
        for child_sdd in child_sdds[1:]:
            result_sdd = result_sdd | child_sdd  # PySDDのOR演算
            
    else:
        raise ValueError(f"Unknown gate type: {gate}")

    return result_sdd

def run_sdd_from_pyeda_obj(xml_path, output_file, vtree_file):
    
    print(f"Converting PyEDA object to SDD... ")

    # 1. 変数集合の取得

    tree = ET.parse(xml_path)
    root = tree.getroot()

    support_vars_set = set()
    for elem in root.iter("event"):
        if elem.get("gate") is None and elem.get("id") is not None:
            support_vars_set.add(elem.get("id"))
    support_vars = sorted(list(support_vars_set))

    var_count = len(support_vars)
    var_order = list(range(1, var_count + 1))
    #vtree = Vtree(var_count=var_count, var_order=var_order, vtree_type="right")

    vtree = Vtree.from_file(vtree_file.encode())
    sdd_manager = SddManager.from_vtree(vtree)
    #sdd_manager.minimize()

    # 変数名とSDD変数の対応付け
    var_map = {var : i for i, var in enumerate(support_vars, start=1)}

    sdd_node = build_SDD_node(root, sdd_manager, var_map)

    with open(output_file + "_sdd.dot", "w") as out:
        print(sdd_node.dot(), file=out)
    with open(output_file + "_vtree.dot", "w") as out:
        print(vtree.dot(), file=out)
    
    print("Conversion successful.")
    return sdd_node