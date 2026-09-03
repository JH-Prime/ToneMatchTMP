"""멀티이펙터 선택기와 향후 장치 확장을 위한 프로필 카탈로그.

현재 분석 레시피 엔진이 구현된 장치는 Tone Master Pro 하나뿐이다. 사용자가
구상 중인 장치명을 나중에 넣기 쉽도록 나머지는 중립적인 슬롯으로 유지한다.
"""

from __future__ import annotations


DEVICE_PROFILES: list[dict] = [
    {
        "id": "tone_master_pro",
        "manufacturer": "Fender",
        "name": "Tone Master Pro",
        "name_ko": "Tone Master Pro",
        "name_en": "Tone Master Pro",
        "supported": True,
        "status_ko": "지원",
        "status_en": "Supported",
        "description_ko": "펌웨어 1.8.58 / Model Guide Rev. J 기반 레시피를 생성합니다.",
        "description_en": "Generates recipes for firmware 1.8.58 / Model Guide Rev. J.",
    },
    {
        "id": "quad_cortex",
        "manufacturer": "Neural DSP",
        "name": "Neural DSP Quad Cortex",
        "name_ko": "Neural DSP Quad Cortex",
        "name_en": "Neural DSP Quad Cortex",
        "supported": False,
        "status_ko": "미구현",
        "status_en": "Not implemented",
        "description_ko": "추후 제공받을 공식 매뉴얼·모델 정보를 기준으로 구현할 예정입니다.",
        "description_en": "Reserved for implementation after official manuals and model data are supplied.",
    },
    {
        "id": "line6_helix",
        "manufacturer": "Line 6",
        "name": "Line 6 Helix Family",
        "name_ko": "Line 6 Helix 패밀리",
        "name_en": "Line 6 Helix Family",
        "supported": False,
        "status_ko": "미구현",
        "status_en": "Not implemented",
        "description_ko": "추후 제공받을 공식 매뉴얼·모델 정보를 기준으로 구현할 예정입니다.",
        "description_en": "Reserved for implementation after official manuals and model data are supplied.",
    },
    {
        "id": "planned_slot_3",
        "manufacturer": "",
        "name": "Device Slot 3",
        "name_ko": "추가 장치 슬롯 3",
        "name_en": "Device Slot 3",
        "supported": False,
        "status_ko": "미구현",
        "status_en": "Not implemented",
        "description_ko": "구상한 멀티이펙터 이름과 모델 자료를 받으면 연결할 예정입니다.",
        "description_en": "Reserved for a multi-effects unit and model data you choose later.",
    },
    {
        "id": "planned_slot_4",
        "manufacturer": "",
        "name": "Device Slot 4",
        "name_ko": "추가 장치 슬롯 4",
        "name_en": "Device Slot 4",
        "supported": False,
        "status_ko": "미구현",
        "status_en": "Not implemented",
        "description_ko": "구상한 멀티이펙터 이름과 모델 자료를 받으면 연결할 예정입니다.",
        "description_en": "Reserved for a multi-effects unit and model data you choose later.",
    },
]


def device_by_id(device_id: str) -> dict:
    """장치 식별자와 일치하는 프로필을 반환한다."""
    for profile in DEVICE_PROFILES:
        if profile["id"] == device_id:
            return profile
    raise KeyError(device_id)


def device_label(device_id: str, language: str = "ko") -> str:
    """콤보박스에 표시할 장치명과 지원 상태를 선택 언어로 만든다."""
    profile = device_by_id(device_id)
    language = language if language in {"ko", "en"} else "ko"
    name = profile.get(f"name_{language}", profile["name"])
    status = profile[f"status_{language}"]
    return f"{name} — {status}"


def device_description(device_id: str, language: str = "ko") -> str:
    """선택한 장치가 현재 무엇을 지원하는지 설명하는 문장을 반환한다."""
    profile = device_by_id(device_id)
    language = language if language in {"ko", "en"} else "ko"
    return str(profile[f"description_{language}"])


def device_id_from_label(label: str) -> str:
    """어느 언어로 표시됐든 콤보박스 라벨을 안정적인 장치 ID로 되돌린다."""
    for profile in DEVICE_PROFILES:
        for language in ("ko", "en"):
            if device_label(profile["id"], language) == label:
                return str(profile["id"])
    return "tone_master_pro"


def is_supported_device(device_id: str) -> bool:
    """현재 레시피 생성기가 해당 장치를 구현했는지 확인한다."""
    try:
        return bool(device_by_id(device_id)["supported"])
    except KeyError:
        return False
