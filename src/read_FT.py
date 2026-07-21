import xml.etree.ElementTree as ET
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GateNode:
    gate_type: str
    children: List[str] = field(default_factory=list)  # fix: default_factory
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
        if denom == 0.0:
            return self.gamma
        term1 = self.lambda_rate / denom
        term2 = (self.gamma - term1) * math.exp(-denom * time)
        return max(0.0, min(1.0, term1 + term2))

class PeriodicTestModel(Expression):
    def __init__(self, lambda_rate: float, interval: float, duration: float):
        self.lambda_rate = lambda_rate
        self.interval = interval
        self.duration = duration

    def evaluate(self, time: float) -> float:
        if self.lambda_rate == 0.0 or self.interval == 0.0:
            return 0.0
        term1 = 1.0 - math.exp(-self.lambda_rate * self.interval)
        q_standby = 1.0 - (term1 / (self.lambda_rate * self.interval))
        q_test = self.duration / self.interval
        return min(1.0, q_standby + q_test)


def read_FT(xml_files):

    def record_house_events(data, prefix):
        for house_event in data.findall("define-house-event"):
            name = house_event.get("name")
            if prefix:
                name = f"{prefix}.{name}"
            if house_event.find("constant").get("value") == "true":
                par_map[name] = 1
                all_basic_events.add(name)

    def record_parameters(data, prefix):
        for parameter in data.findall("define-parameter"):
            name = parameter.get("name")
            if prefix:
                name = f"{prefix}.{name}"
            if parameter.find("lognormal-deviate") is not None:
                lambda_rate = float(
                    parameter.find("lognormal-deviate").find("float").get("value")
                )
                def_par[name] = ExponentialModel(lambda_rate)
            elif parameter.find("parameter") is not None:
                def_par[name] = def_par[parameter.find("parameter").get("name")]

    def record_basic_events(data, prefix):
        for basic_event in data.findall("define-basic-event"):
            name = basic_event.get("name")
            if prefix:
                name = f"{prefix}.{name}"
            if basic_event.find("exponential") is not None:
                value = def_par[
                    basic_event.find("exponential").find("parameter").get("name")
                ]
                time = 1
                if basic_event.find("exponential").find("mul") is not None:
                    time = float(
                        basic_event.find("exponential").find("mul")[0].get("value")
                    )
                par_map[name] = value.evaluate(mission_time * time)
            elif basic_event.find("GLM") is not None:
                glm_node = basic_event.find("GLM")
                gamma       = float(glm_node[0].get("value"))
                lambda_rate = float(glm_node[1].get("value"))
                mu          = float(glm_node[2].get("value"))
                par_map[name] = GLMModel(gamma, lambda_rate, mu).evaluate(mission_time)
            elif basic_event.find("periodic-test") is not None:
                pt_node     = basic_event.find("periodic-test")
                lambda_rate = float(pt_node[0].get("value"))
                interval    = float(pt_node[1].get("value"))
                duration    = float(pt_node[2].get("value"))
                par_map[name] = PeriodicTestModel(
                    lambda_rate, interval, duration
                ).evaluate(mission_time)
            elif basic_event.find("normal-deviate") is not None:
                mean_value = float(basic_event.find("normal-deviate")[0].get("value"))
                par_map[name] = mean_value
            else:
                par_map[name] = basic_event.find("float").get("value")
            all_basic_events.add(name)

    def record_gate_events(tree, prefix):
        for gate_event in tree.findall("define-gate"):
            name = gate_event.get("name")
            if prefix:
                name = f"{prefix}.{name}"
            all_gates.add(name)

            elem = gate_event[0]
            if elem.tag == "label":
                elem = gate_event[1]
            gate_type = elem.tag
            children  = []
            k         = None

            if gate_type in ["and", "or", "not", "nand", "nor", "xor"]:
                for child in elem:
                    if child.tag == "not":
                        child_name = child[0].get("name")
                        if child[0].tag == "gate":
                            if prefix:
                                child_name = f"{prefix}.{child_name}"
                        else:
                            if prefix and f"{prefix}.{child_name}" in par_map:
                                child_name = f"{prefix}.{child_name}"
                        children.append(f"~{child_name}")
                    else:
                        child_name = child.get("name")
                        if child.tag == "gate":
                            if prefix:
                                child_name = f"{prefix}.{child_name}"
                        else:
                            if prefix and f"{prefix}.{child_name}" in par_map:
                                child_name = f"{prefix}.{child_name}"
                        children.append(child_name)
                    if child_name not in all_basic_events:
                        all_children.add(child_name)
                    else:
                        exist_basic_events.add(child_name)

            elif gate_type in ["basic-event", "gate", "event", "house-event"]:
                child_name = elem.get("name")
                if elem.tag == "gate":
                    if prefix:
                        child_name = f"{prefix}.{child_name}"
                else:
                    if prefix and f"{prefix}.{child_name}" in par_map:
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
                        if prefix:
                            child_name = f"{prefix}.{child_name}"
                    else:
                        if prefix and f"{prefix}.{child_name}" in par_map:
                            child_name = f"{prefix}.{child_name}"
                    children.append(child_name)
                    if child_name not in all_basic_events:
                        all_children.add(child_name)
                    else:
                        exist_basic_events.add(child_name)

            gate_map[name] = GateNode(gate_type=gate_type, children=children, k=k)

    def records(r, prefix):
        record_house_events(r, prefix)
        record_parameters(r, prefix)
        record_basic_events(r, prefix)

    def process_component_pass1(component, prefix):
        name = component.get("name")
        next_prefix = name if not prefix else f"{prefix}.{name}"
        records(component, next_prefix)
        for child_comp in component.findall("define-component"):
            process_component_pass1(child_comp, next_prefix)

    def process_component_pass2(component, prefix):
        name = component.get("name")
        next_prefix = name if not prefix else f"{prefix}.{name}"
        record_gate_events(component, next_prefix)
        for child_comp in component.findall("define-component"):
            process_component_pass2(child_comp, next_prefix)

    mission_time = 8760.0

    def_par             = {}
    gate_map            = {}
    all_basic_events    = set()
    par_map             = {}
    all_gates           = set()
    all_children        = set()
    exist_basic_events  = set()

    # ---- 1回のパースでElementTreeをキャッシュ ----
    parsed = {str(f): ET.parse(f) for f in xml_files}

    # Pass 1: 基本事象・パラメータ・ハウスイベントを収集
    for xmlfile in xml_files:
        root = parsed[str(xmlfile)]
        if root.find("model-data") is not None:
            records(root.find("model-data"), "")
        if root.find("define-fault-tree") is not None:
            for fault_tree in root.findall("define-fault-tree"):
                records(fault_tree, "")
            for component in root.find("define-fault-tree").findall("define-component"):
                process_component_pass1(component, "")

    # Pass 2: ゲートの接続情報を収集（Pass1で確定したpar_mapを参照）
    for xmlfile in xml_files:
        root = parsed[str(xmlfile)]
        if root.find("define-fault-tree") is not None:
            for fault_tree in root.findall("define-fault-tree"):
                for component in fault_tree.findall("define-component"):
                    process_component_pass2(component, "")
                record_gate_events(fault_tree, "")

    var_map        = {}
    exist_par_map  = {}
    count = 1
    for var in all_basic_events & exist_basic_events:
        var_map[var]         = count
        exist_par_map[count] = par_map[var]
        count += 1

    top_gates = all_gates - all_children
    if len(top_gates) > 1:
        print(f"警告: 独立したトップゲートが複数存在します {top_gates}")
        return None, None, None, None
    elif len(top_gates) == 0:
        print("エラー: トップゲートが見つかりません（循環参照の可能性があります）")
        return None, None, None, None

    top_gate = top_gates.pop()
    return top_gate, var_map, gate_map, exist_par_map
