from .param_schema import PARAMETER_GROUPS, get_parameter_groups


def select_asm_hemt_model(
    analysis_result: dict[str, dict], llm_advice: dict | None = None
) -> dict:
    """Create an auditable ASM-HEMT selection plan from available data."""
    data_types = set(analysis_result)
    parameter_groups = get_parameter_groups(data_types)

    reasons = ["GaN HEMT 建模流程固定使用 ASM-HEMT 作为目标模型"]
    if "pulse_iv" in data_types:
        reasons.append("存在 Pulse I-V 数据，需要启用自热和陷阱参数组")
    if "s_params" in data_types:
        reasons.append("存在 S 参数，需要启用高频寄生参数组")
    if "cv" in data_types:
        reasons.append("存在 C-V 数据，需要启用电容参数组")

    plan = {
        "model_name": "ASM-HEMT",
        "data_types": sorted(data_types),
        "parameter_groups": parameter_groups,
        "parameters_to_fit": [
            parameter
            for group in parameter_groups
            for parameter in PARAMETER_GROUPS[group]["parameters"]
        ],
        "fit_order": ["dc"]
        + [group for group in parameter_groups if group != "dc"],
        "reason": reasons,
        "llm_advice_used": bool(llm_advice),
    }

    if llm_advice and llm_advice.get("next_step"):
        plan["llm_next_step"] = llm_advice["next_step"]
    return plan
