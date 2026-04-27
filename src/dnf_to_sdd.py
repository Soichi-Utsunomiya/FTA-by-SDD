from pysdd.sdd import SddManager, Vtree
from pyeda.boolalg.expr import Variable, Complement, AndOp, OrOp
import os

def dnf_to_str(node):
    if isinstance(node, Variable):
        return str(node)
    elif isinstance(node, AndOp):
        child_nodes = [dnf_to_str(child) for child in node.xs]
        return "(" + " & ".join(child_nodes) + ")"
    elif isinstance(node, OrOp):
        child_nodes = [dnf_to_str(child) for child in node.xs]
        return "(" + " | ".join(child_nodes) + ")"
    else:
        raise ValueError(f"Unknown node type: {type(node)}")

def run_sdd_from_pyeda_obj(pyeda_expr, output_file, vtree_file):
    
    print(f"\nConverting PyEDA object to SDD... ")

    # 1. 変数集合の取得
    support_vars = sorted([str(v) for v in pyeda_expr.support])
    print(support_vars)
    if not support_vars:
        if pyeda_expr.is_one():
            print("Formula is always TRUE")
            return None
        elif pyeda_expr.is_zero():
            print("Formula is always FALSE")
            return None

    # 2. SDDマネージャーの初期化
    var_count = len(support_vars)
    var_order = list(range(1, var_count + 1))

    #vtree = Vtree(var_count=var_count, var_order=var_order, vtree_type="balanced")
    vtree = Vtree.from_file(vtree_file.encode())
    sdd_manager = SddManager.from_vtree(vtree)
    #sdd_manager.minimize()

    # 変数名とSDD変数の対応付け
    name_to_sdd_var = {name: sdd_manager.vars[i+1] for i, name in enumerate(support_vars)}

    dnf_str = dnf_to_str(pyeda_expr)
    print(dnf_str)

    # 変換実行
    print(name_to_sdd_var)
    sdd_node = eval(dnf_str, {}, name_to_sdd_var)

    with open(output_file + "_sdd.dot", "w") as out:
        print(sdd_node.dot(), file=out)
    with open(output_file + "_vtree.dot", "w") as out:
        print(vtree.dot(), file=out)
    
    print("Conversion successful.")
    return sdd_node, sdd_manager, name_to_sdd_var