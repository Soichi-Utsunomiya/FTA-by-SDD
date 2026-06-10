import xml.etree.ElementTree as ET
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GateNode:
    gate_type: str
    children: List[str] = field(default=list)
    k: Optional[int] = None

class Expression(ABC):
    @abstractmethod
    def evaluate(self, time: float) -> float:
        pass

class FixedProbability(Expression):
    def __init__(self, value: float):
        self.value = value
    
    def evaluate(self, time: float) -> float:
        return self.value

class ExponentialModel(Expression):
    def __init__(self, lambda_rate: float):
        self.lambda_rate = lambda_rate

    def evaluate(self, time: float) -> float:
        return 1.0 - math.exp(-self.lambda_rate * time)
    
class GLMModel(Expression):
    def __init__(self, gamma: float, lambda_rate: float, mu: float):
        self.gamma = gamma
        self.lambda_rate = lambda_rate
        self.mu = mu

    def evaluate(self, time: float) -> float:
        denom = self.lambda_rate + self.mu
        # 故障も修理もゼロ（または完全な初期故障のみ）のゼロ除算回避
        if denom == 0.0:
            return self.gamma
        
        term1 = self.lambda_rate / denom
        term2 = (self.gamma - term1) * math.exp(-denom * time)
        
        # 確率が0〜1の範囲に収まるように安全策をとる（通常は不要ですが念のため）
        return max(0.0, min(1.0, term1 + term2))
    
class PeriodicTestModel(Expression):
    def __init__(self, lambda_rate: float, interval: float, duration: float):
        self.lambda_rate = lambda_rate
        self.interval = interval
        self.duration = duration

    def evaluate(self, time: float) -> float:
        # ゼロ除算の回避
        if self.lambda_rate == 0.0 or self.interval == 0.0:
            return 0.0
            
        # SCRAMが内部で採用している「厳密な平均不稼働率」の公式
        term1 = 1.0 - math.exp(-self.lambda_rate * self.interval)
        q_standby = 1.0 - (term1 / (self.lambda_rate * self.interval))
        
        # テスト・修理によるダウンタイム（通常は duration = 0）
        q_test = self.duration / self.interval
        
        return min(1.0, q_standby + q_test)

def read_FT(xml_files):

    def record_house_events(data, prefix):
        house_events = data.findall("define-house-event")
        for house_event in house_events:
            name = house_event.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            if house_event.find("constant").get("value") == "true":
                par_map[name] = 1
                all_basic_events.add(name)

    def record_parameters(data, prefix):
        parameters = data.findall("define-parameter")
        for parameter in parameters:
            name = parameter.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            if parameter.find("lognormal-deviate")is not None:
                lambda_rate = float(parameter.find("lognormal-deviate").find("float").get("value"))
                def_par[name] = ExponentialModel(lambda_rate)
            elif parameter.find("parameter") is not None:
                def_par[name] = def_par[parameter.find("parameter").get("name")]

    def record_basic_events(data, prefix):
        basic_events = data.findall("define-basic-event")
        for basic_event in basic_events:
            name = basic_event.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            if basic_event.find("exponential")is not None:
                value = def_par[basic_event.find("exponential").find("parameter").get("name")]
                time = 1
                if basic_event.find("exponential").find("mul") is not None:
                    time = float(basic_event.find("exponential").find("mul")[0].get("value"))
                par_map[name] = value.evaluate(mission_time*time)
            elif basic_event.find("GLM") is not None:
                glm_node = basic_event.find("GLM")
                # GLMは4つの引数を順番に取る
                gamma = float(glm_node[0].get("value"))
                lambda_rate = float(glm_node[1].get("value"))
                mu = float(glm_node[2].get("value"))
                
                # GLMモデルを生成して、ミッション時間を渡して確率を計算
                par_map[name] = GLMModel(gamma, lambda_rate, mu).evaluate(mission_time)

            elif basic_event.find("periodic-test") is not None:
                pt_node = basic_event.find("periodic-test")
                # periodic-test の代表的な引数構成
                lambda_rate = float(pt_node[0].get("value"))
                interval = float(pt_node[1].get("value"))
                duration = float(pt_node[2].get("value"))
                
                # PeriodicTestモデルを生成
                par_map[name] = PeriodicTestModel(lambda_rate, interval, duration).evaluate(mission_time)
            # 実装のイメージ
            elif basic_event.find("normal-deviate") is not None:
                # 最初のfloat（平均値）だけを取得して、代表値として使う
                mean_value = float(basic_event.find("normal-deviate")[0].get("value"))
                par_map[name] = mean_value
            else:
                par_map[name] = basic_event.find("float").get("value")
            all_basic_events.add(name)

    def record_gate_events(tree, prefix):
        gate_events = tree.findall("define-gate")
        for gate_event in gate_events:
            name = gate_event.get("name")
            if prefix != "":
                name = f"{prefix}.{name}"
            all_gates.add(name)
            
            elem = gate_event[0]
            if elem.tag == "label":
                elem = gate_event[1]
            gate_type = elem.tag
            children = []
            k = None
            
            # パターン1: 直下が <and> や <or> などの論理演算子の場合
            if gate_type in ["and", "or", "not", "nand", "nor", "xor"]:
                for child in elem:
                    if child.tag == "not":
                        child_name = child[0].get("name")
                        if child[0].tag == "gate":
                            if prefix != "":
                                child_name = f"{prefix}.{child_name}"
                        else:
                            if prefix != "":
                                if f"{prefix}.{child_name}" in par_map:
                                    child_name = f"{prefix}.{child_name}"
                        not_child_name = f"~{child_name}"
                        children.append(not_child_name)
                    else:
                        child_name = child.get("name")
                        if child.tag == "gate":
                            if  prefix != "":
                                child_name = f"{prefix}.{child_name}"
                        else:
                            if prefix != "":
                                if f"{prefix}.{child_name}" in par_map:
                                    child_name = f"{prefix}.{child_name}"
                        children.append(child_name)
                    if child_name not in all_basic_events:
                        all_children.add(child_name)
                    else:
                        exist_basic_events.add(child_name)
                        
            # パターン2: 直下が直接のイベントやゲート（パススルー）の場合
            elif gate_type in ["basic-event", "gate", "event", "house-event"]:
                child_name = elem.get("name")
                if elem.tag == "gate":
                    if  prefix != "":
                        child_name = f"{prefix}.{child_name}"
                else:
                    if prefix != "":
                        if f"{prefix}.{child_name}" in par_map:
                            child_name = f"{prefix}.{child_name}"
                children.append(child_name)
                if child_name not in all_basic_events:
                    all_children.add(child_name)
                else:
                    exist_basic_events.add(child_name)
                gate_type = "pass" 
            
            elif gate_type == "atleast":
                k = int(elem.get("min"))
                for child in elem:
                    child_name = child.get("name")
                    if child.tag == "gate":
                        if  prefix != "":
                            child_name = f"{prefix}.{child_name}"
                    else:
                        if prefix != "":
                            if f"{prefix}.{child_name}" in par_map:
                                child_name = f"{prefix}.{child_name}"
                    children.append(child_name)
                    if child_name not in all_basic_events:
                        all_children.add(child_name) 
                    else:   
                       exist_basic_events.add(child_name)
                
            gate_map[name] = GateNode(
                gate_type=gate_type,
                children=children,
                k = k
            )
    
    def process_component(component, prefix):
        name = component.get("name")
        if prefix == "":
            next_prefix = name
        else:
            next_prefix = f"{prefix}.{name}"
        
        records(component, next_prefix)
        record_gate_events(component, next_prefix)
        for child_component in component.findall("define-component"):
            process_component(child_component, next_prefix)

    def records(r, prefix):  
        record_house_events(r, prefix)
        record_parameters(r, prefix)
        record_basic_events(r, prefix)

    mission_time = 8760.0

    def_par = {}
    gate_map = {}
    all_basic_events = set()
    par_map = {}
    all_gates = set()
    all_children = set()
    exist_basic_events = set()
    for xmlfile in xml_files:
        print(xmlfile)
        root = ET.parse(xmlfile)
        if root.find("model-data") is not None:
            records(root.find("model-data"), "")

        if root.find("define-fault-tree") is not None:
            fault_trees = root.findall("define-fault-tree")
            for fault_tree in fault_trees:
                records(fault_tree, "")
            
            # Pass 1用のコンポーネント処理（名前と基本事象の収集だけ行う）
            def process_component_pass1(component, prefix):
                name = component.get("name")
                next_prefix = name if prefix == "" else f"{prefix}.{name}"
                records(component, next_prefix)
                for child_comp in component.findall("define-component"):
                    process_component_pass1(child_comp, next_prefix)
            
            components = root.find("define-fault-tree").findall("define-component")
            for component in components:
                process_component_pass1(component, "")

    for xmlfile in xml_files:
        root = ET.parse(xmlfile)
        if root.find("define-fault-tree") is not None:
            fault_trees = root.findall("define-fault-tree")
            for fault_tree in fault_trees:
                
                # Pass 2用のコンポーネント処理（ゲートの繋がりだけを処理する）
                def process_component_pass2(component, prefix):
                    name = component.get("name")
                    next_prefix = name if prefix == "" else f"{prefix}.{name}"
                    record_gate_events(component, next_prefix)
                    for child_comp in component.findall("define-component"):
                        process_component_pass2(child_comp, next_prefix)
                        
                components = fault_tree.findall("define-component")
                for component in components:
                    process_component_pass2(component, "")
                    
                # 一番外側のゲートの繋がりを処理
                record_gate_events(fault_tree, "")

    var_map = {}
    exist_par_map = {}
    count = 1
    for var in all_basic_events & exist_basic_events:
        var_map[var] = count
        exist_par_map[count] = par_map[var]
        count += 1

    top_gates = all_gates - all_children
    if len(top_gates) > 1:
        print(f"警告: 独立したトップゲートが複数存在します {top_gates}")
        return
    elif len(top_gates) == 0:
        print("エラー: トップゲートが見つかりません（循環参照の可能性があります）")
        return
    
    top_gate = top_gates.pop()

    return top_gate, var_map, gate_map, exist_par_map
