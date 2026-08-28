"""Internal parameter groups used before mapping to MeQLab ASM-HEMT names.

These are planning metadata, not a replacement for the official ASM-HEMT
parameter card. The final mapping must be checked against the MeQLab model
definition supplied for the competition.
"""

PARAMETER_GROUPS = {
    "dc": {
        "description": "直流导通、电流和阈值相关参数",
        "parameters": ["vth0", "mu0", "rds_on"],
    },
    "cv": {
        "description": "栅源、栅漏和结电容相关参数",
        "parameters": ["cgs0", "cgd0"],
    },
    "thermal": {
        "description": "自热和温升相关参数",
        "parameters": ["rth", "cth"],
    },
    "trap": {
        "description": "陷阱、动态导通电阻和脉冲响应相关参数",
        "parameters": ["trap_strength", "trap_time"],
    },
    "high_frequency": {
        "description": "高频小信号和寄生参数",
        "parameters": ["cgs_parasitic", "cgd_parasitic", "gate_resistance"],
    },
}


def get_parameter_groups(data_types: set[str]) -> list[str]:
    """Select fitting groups supported by the available measurements."""
    groups = ["dc"]
    if "cv" in data_types:
        groups.append("cv")
    if "pulse_iv" in data_types:
        groups.extend(["thermal", "trap"])
    if "s_params" in data_types:
        groups.append("high_frequency")
    return groups
