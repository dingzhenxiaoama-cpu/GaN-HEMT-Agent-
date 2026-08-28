import csv
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from llm_client import LLMClient


class ModelingState(TypedDict, total=False):
    device_id: str
    data_files: dict[str, str]
    raw_data: dict[str, list[dict[str, float]]]
    analysis_result: dict[str, dict]
    llm_status: str
    llm_advice: dict
    llm_usage: dict


def read_numeric_csv(file_path: str) -> list[dict[str, float]]:
    """Read a CSV file whose data columns contain numeric values."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError(f"CSV 缺少表头: {path}")

        rows = []
        for line_number, row in enumerate(reader, start=2):
            if not row or all(value in (None, "") for value in row.values()):
                continue
            try:
                rows.append({key: float(value) for key, value in row.items() if key})
            except (TypeError, ValueError) as error:
                raise ValueError(f"{path} 第 {line_number} 行包含非数字数据") from error

    if not rows:
        raise ValueError(f"CSV 没有有效数据行: {path}")
    return rows


def require_columns(rows: list[dict[str, float]], columns: list[str], data_type: str):
    missing = [column for column in columns if column not in rows[0]]
    if missing:
        raise ValueError(f"{data_type} 缺少必要列: {', '.join(missing)}")


def load_data(state: ModelingState):
    raw_data = {
        data_type: read_numeric_csv(file_path)
        for data_type, file_path in state["data_files"].items()
    }
    return {"raw_data": raw_data}


def analyze_data(state: ModelingState):
    raw_data = state["raw_data"]
    result: dict[str, dict] = {}

    if "dc_iv" in raw_data:
        rows = raw_data["dc_iv"]
        require_columns(rows, ["Vgs", "Vds", "Ids"], "DC I-V")
        result["dc_iv"] = {
            "data_type": "DC I-V",
            "point_count": len(rows),
            "max_Ids": max(row["Ids"] for row in rows),
            "min_Vgs": min(row["Vgs"] for row in rows),
            "max_Vgs": max(row["Vgs"] for row in rows),
        }

    if "cv" in raw_data:
        rows = raw_data["cv"]
        require_columns(rows, ["Vg", "Cgg"], "C-V")
        result["cv"] = {
            "data_type": "C-V",
            "point_count": len(rows),
            "min_Cgg": min(row["Cgg"] for row in rows),
            "max_Cgg": max(row["Cgg"] for row in rows),
            "min_Vg": min(row["Vg"] for row in rows),
            "max_Vg": max(row["Vg"] for row in rows),
        }

    if "pulse_iv" in raw_data:
        rows = raw_data["pulse_iv"]
        require_columns(rows, ["Vgs", "Vds", "Ids_pulse"], "Pulse I-V")
        result["pulse_iv"] = {
            "data_type": "Pulse I-V",
            "point_count": len(rows),
            "max_Ids_pulse": max(row["Ids_pulse"] for row in rows),
        }

    if "s_params" in raw_data:
        rows = raw_data["s_params"]
        require_columns(rows, ["Frequency", "S21_real", "S21_imag"], "S 参数")
        s21_magnitudes = [
            (row["S21_real"] ** 2 + row["S21_imag"] ** 2) ** 0.5
            for row in rows
        ]
        result["s_params"] = {
            "data_type": "S 参数",
            "point_count": len(rows),
            "min_frequency": min(row["Frequency"] for row in rows),
            "max_frequency": max(row["Frequency"] for row in rows),
            "max_S21_magnitude": max(s21_magnitudes),
        }

    return {"analysis_result": result}


def ask_model(state: ModelingState):
    """Ask the configured model for a next-step suggestion, or use mock mode."""
    client = LLMClient.from_env()
    if client is None:
        return {
            "llm_status": "mock",
            "llm_advice": {
                "next_step": "先进行 DC I-V 参数提取，再用 C-V 和 Pulse I-V 校准模型",
                "reason": "当前未启用真实大模型 API，使用本地演示建议",
                "parameters_to_check": ["Vth", "Ids", "Cgg", "自热和陷阱参数"],
            },
            "llm_usage": {"total_tokens": 0},
        }

    response = client.advise(state["analysis_result"])
    return {
        "llm_status": "live",
        "llm_advice": response["advice"],
        "llm_usage": response["usage"],
    }


graph_builder = StateGraph(ModelingState)
graph_builder.add_node("load_data", load_data)
graph_builder.add_node("analyze_data", analyze_data)
graph_builder.add_node("ask_model", ask_model)
graph_builder.add_edge(START, "load_data")
graph_builder.add_edge("load_data", "analyze_data")
graph_builder.add_edge("analyze_data", "ask_model")
graph_builder.add_edge("ask_model", END)

graph = graph_builder.compile()

result = graph.invoke(
    {
        "device_id": "demo_gan_hemt",
        "data_files": {
            "dc_iv": "data/demo_dc_iv.csv",
            "cv": "data/demo_cv.csv",
            "pulse_iv": "data/demo_pulse_iv.csv",
            "s_params": "data/demo_s_params.csv",
        },
    }
)

print("Agent 运行结果：")
for data_type, analysis in result["analysis_result"].items():
    print(f"{data_type}: {analysis}")
print(f"大模型状态: {result['llm_status']}")
print(f"建模建议: {result['llm_advice']}")
