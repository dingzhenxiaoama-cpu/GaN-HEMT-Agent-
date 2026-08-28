import csv
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class ModelingState(TypedDict, total=False):
    device_id: str
    data_file: str
    raw_data: list[dict[str, float]]
    analysis_result: dict


def load_data(state: ModelingState):
    data_file = Path(state["data_file"])

    with data_file.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [
            {
                "Vgs": float(row["Vgs"]),
                "Vds": float(row["Vds"]),
                "Ids": float(row["Ids"]),
            }
            for row in reader
        ]

    return {
        "raw_data": rows
    }


def analyze_data(state: ModelingState):
    rows = state["raw_data"]

    result = {
        "data_type": "DC I-V",
        "point_count": len(rows),
        "max_Ids": max(row["Ids"] for row in rows),
        "min_Vgs": min(row["Vgs"] for row in rows),
        "max_Vgs": max(row["Vgs"] for row in rows),
    }

    return {
        "analysis_result": result
    }


graph_builder = StateGraph(ModelingState)

graph_builder.add_node("load_data", load_data)
graph_builder.add_node("analyze_data", analyze_data)

graph_builder.add_edge(START, "load_data")
graph_builder.add_edge("load_data", "analyze_data")
graph_builder.add_edge("analyze_data", END)

graph = graph_builder.compile()

result = graph.invoke({
    "device_id": "demo_gan_hemt",
    "data_file": "data/demo_dc_iv.csv",
})

print("Agent 运行结果：")
print(result["analysis_result"])