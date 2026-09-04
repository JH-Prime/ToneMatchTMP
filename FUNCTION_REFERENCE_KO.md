# ToneMatch TMP 0.0.04 함수 설명서

이 문서는 배포 소스의 모든 함수와 한국어 docstring을 자동으로 모은 색인입니다.
앱의 `개발자 옵션`에서는 처리 순서 블록을 클릭해 같은 함수의 실제 소스와 원본 줄 번호를 볼 수 있습니다.

## `app.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 90 | `_center_window` | 주 모니터 가운데에 창을 배치하되 작은 화면 경계를 넘지 않게 한다. |
| 102 | `_portable_root` | 소스 실행 또는 PyInstaller onedir 실행의 포터블 루트를 반환한다. |
| 109 | `_runtime_data_root` | 우선 EXE 옆 data를 쓰고 권한이 없으면 LocalAppData로 안전하게 폴백한다. |
| 124 | `_input_method_label` | 입력 방법의 안정적인 코드에 대응하는 언어별 화면 라벨을 만든다. |
| 129 | `_input_method_code` | 한국어 또는 영어 입력 방법 라벨을 안정적인 코드로 되돌린다. |
| 140 | `ToneMatchApp.__init__` | 영구 상태를 준비하고 전체 Tkinter 화면과 이벤트 루프를 구성한다. |
| 199 | `ToneMatchApp.ui_font` | 현재 언어에 맞춰 사용자가 지정한 기본 UI 글꼴을 반환한다. |
| 203 | `ToneMatchApp._load_settings` | 이전 실행의 언어·장치·연산 백엔드 선택을 읽되 손상된 파일은 무시한다. |
| 218 | `ToneMatchApp._save_settings` | 다음 실행에서도 유지할 언어·장치·연산 백엔드 선택을 작은 JSON으로 저장한다. |
| 230 | `ToneMatchApp._configure_style` | 현재 언어 글꼴과 어두운 색상표를 모든 공통 위젯 스타일에 적용한다. |
| 268 | `ToneMatchApp._panel` | 공통 배경과 여백을 가진 카드형 패널을 만들어 즉시 배치한다. |
| 275 | `ToneMatchApp._field_label` | 입력 필드 위의 작은 설명 라벨을 지정한 그리드 위치에 배치한다. |
| 279 | `ToneMatchApp._sync_left_scroll_region` | 입력 카드 내용 높이가 바뀔 때 스크롤 가능한 전체 영역을 다시 계산한다. |
| 284 | `ToneMatchApp._resize_left_scroll_content` | 창 너비가 바뀌어도 입력 카드 내부 프레임이 캔버스 폭을 정확히 채우게 한다. |
| 289 | `ToneMatchApp._enable_left_mousewheel` | 포인터가 입력 카드 위에 있을 때 휠을 해당 세로 스크롤에 연결한다. |
| 293 | `ToneMatchApp._disable_left_mousewheel` | 포인터가 입력 카드를 벗어나면 다른 화면의 휠 동작을 방해하지 않게 연결을 푼다. |
| 297 | `ToneMatchApp._scroll_left_panel` | Windows 마우스 휠 회전량을 입력 카드의 세로 이동 단위로 변환한다. |
| 302 | `ToneMatchApp._build_ui` | 입력·결과·개발자·변경 기록과 하단 상태를 현재 언어로 구성한다. |
| 540 | `ToneMatchApp._build_debug_tab` | 처리 순서도, 클릭형 실제 소스, 런타임 로그와 디버그 번들 버튼을 만든다. |
| 583 | `ToneMatchApp._build_changelog_tab` | 패치 버전·변경사항·알려진 제한을 현재 언어로 읽는 탭을 만든다. |
| 594 | `ToneMatchApp._change_language` | 선택값과 결과 수치를 보존한 채 전체 화면을 새 언어와 글꼴로 다시 만든다. |
| 622 | `ToneMatchApp._change_device` | 멀티이펙터 선택을 갱신하고 미구현 장치에서는 분석을 비활성화한다. |
| 633 | `ToneMatchApp._start_hardware_probe` | PyTorch·CUDA 확인을 UI 밖의 스레드에서 시작해 창 멈춤을 방지한다. |
| 644 | `ToneMatchApp._hardware_probe_worker` | Demucs와 GPU 런타임을 검사하고 메인 UI 큐로 결과를 전달한다. |
| 652 | `ToneMatchApp._apply_hardware_status` | 하드웨어 검사 결과를 저장하고 가능한 선택값·진단표·로그를 갱신한다. |
| 672 | `ToneMatchApp._change_compute_backend` | 표시된 AI 가속 선택을 안정적인 auto·cuda·cpu 코드로 저장한다. |
| 680 | `ToneMatchApp._set_compute_controls_enabled` | 하드웨어 검사·분석 상태에 맞춰 가속 선택과 재검사 버튼을 함께 잠그거나 푼다. |
| 690 | `ToneMatchApp._format_bytes` | 바이트 값을 진단표에서 읽기 쉬운 MiB 또는 GiB 문자열로 바꾼다. |
| 702 | `ToneMatchApp._populate_diagnostics` | 하드웨어·AI 분리 벤치마크·DSP 특징을 한 진단표에 순서대로 표시한다. |
| 709 | `ToneMatchApp._populate_diagnostics.<local>.add` | 번역된 항목명과 문자열 값을 진단표 끝에 추가한다. |
| 753 | `ToneMatchApp._change_input_method` | 로컬 파일과 PC 재생음 녹음 모드에 맞춰 관련 컨트롤 상태를 바꾼다. |
| 779 | `ToneMatchApp._refresh_capture_devices` | Windows 오디오 장치를 다시 열거하고 기존 선택이 가능하면 유지한다. |
| 800 | `ToneMatchApp._capture_device_changed` | 녹음 콤보박스의 표시 라벨을 실제 장치 식별자로 저장한다. |
| 805 | `ToneMatchApp._toggle_recording` | 현재 상태에 따라 PC 재생음 녹음을 시작하거나 중지 요청을 보낸다. |
| 838 | `ToneMatchApp._recording_worker` | 오디오 녹음을 백그라운드에서 실행하고 UI 큐에 상태를 전달한다. |
| 840 | `ToneMatchApp._recording_worker.<local>.progress` | 녹음 경과 시간을 메인 UI가 읽는 이벤트로 바꾼다. |
| 850 | `ToneMatchApp._toggle_developer_mode` | 개발자 순서도와 변경 기록 탭을 표시하거나 숨긴다. |
| 864 | `ToneMatchApp._draw_debug_diagram` | 실제 실행 순서대로 클릭 가능한 세로 블록과 연결 화살표를 그린다. |
| 895 | `ToneMatchApp._select_debug_block` | 선택한 처리 블록의 언어별 설명과 연결된 실제 함수 원문을 표시한다. |
| 923 | `ToneMatchApp._append_debug_log` | 시각 포함 이벤트를 화면과 EXE 옆 일별 UTF-8 로그 파일에 함께 남긴다. |
| 941 | `ToneMatchApp._set_debug_progress` | 진행률로 활성·완료 블록을 계산하고 순서도와 로그를 갱신한다. |
| 951 | `ToneMatchApp._choose_audio` | 파일 선택 창에서 오디오 또는 영상 경로를 받아 입력 상태를 갱신한다. |
| 959 | `ToneMatchApp._open_reference` | 참고 URL을 기본 브라우저에서 열되 앱이 YouTube 음원을 추출하지 않는다. |
| 969 | `ToneMatchApp._parse_inputs` | 화면 문자열을 분석 요청으로 바꾸고 파일·시간·장치 조건을 검증한다. |
| 991 | `ToneMatchApp._start_analysis` | 검증된 요청을 별도 스레드에서 시작하고 취소·내보내기 상태를 설정한다. |
| 1037 | `ToneMatchApp._cancel_analysis` | Demucs의 현재 30초 조각이 끝난 뒤 멈추도록 안전한 취소 신호를 보낸다. |
| 1045 | `ToneMatchApp._analysis_worker` | 전체 기타 분석을 실행하고 결과 또는 오류를 메인 UI 큐에 전달한다. |
| 1047 | `ToneMatchApp._analysis_worker.<local>.progress` | 엔진 콜백을 Tk 메인 스레드용 진행 이벤트로 변환한다. |
| 1057 | `ToneMatchApp._drain_events` | 백그라운드 분석·녹음 이벤트를 Tk 메인 스레드에서 순서대로 처리한다. |
| 1083 | `ToneMatchApp._recording_completed` | 완료된 임시 녹음을 현재 분석 파일로 연결하고 버튼 상태를 복구한다. |
| 1096 | `ToneMatchApp._recording_failed` | 녹음 실패 메시지와 상세 로그를 남기고 UI를 다시 사용할 수 있게 한다. |
| 1106 | `ToneMatchApp._show_error` | 분석 실패 상태를 복구하고 사용자 메시지와 영구 개발 로그를 남긴다. |
| 1120 | `ToneMatchApp._show_result` | 추천 체인 세 개, 기타 stem 진단과 상태를 현재 언어 화면에 표시한다. |
| 1153 | `ToneMatchApp._render_recipe` | 한 추천 체인의 모델·순서·파라미터·이유를 읽기 쉬운 서식으로 그린다. |
| 1179 | `ToneMatchApp._render_voicing` | 실험 보이싱 타임라인과 연주 후보를 별도 결과 탭에 표시한다. |
| 1212 | `ToneMatchApp._format_time` | 초 단위 위치를 긴 곡에서도 읽기 쉬운 분:초 문자열로 바꾼다. |
| 1218 | `ToneMatchApp._update_analysis_availability` | 장치 지원, 분석 및 녹음 실행 상태를 보고 분석 버튼 활성 여부를 결정한다. |
| 1230 | `ToneMatchApp._update_copy_availability` | 현재 탭에 복사할 표시 내용이 있고 작업 중이 아닐 때만 복사 버튼을 켠다. |
| 1243 | `ToneMatchApp._default_export_name` | 입력 파일명을 안전한 기본 내보내기 파일명으로 바꾼다. |
| 1249 | `ToneMatchApp._export_json` | 현재 전체 분석 데이터와 분리 진단을 UTF-8 JSON으로 저장한다. |
| 1261 | `ToneMatchApp._export_html` | 현재 결과를 외부 자원이 없는 한·영 HTML 리포트로 저장하고 선택 시 연다. |
| 1275 | `ToneMatchApp._mark_export` | 내보내기 단계를 순서도에 표시하고 상태와 영구 로그를 갱신한다. |
| 1284 | `ToneMatchApp._copy_recipe` | 현재 선택한 결과·진단·개발자 탭의 표시 내용을 클립보드에 복사한다. |
| 1330 | `ToneMatchApp._export_debug_bundle` | 다른 PC에서 진단·개발을 이어갈 소스, 로그, 이력, 환경 정보를 ZIP으로 묶는다. |
| 1364 | `ToneMatchApp._on_close` | 진행 중 작업에 중지 신호를 보내고 임시 녹음을 정리한 뒤 창을 닫는다. |
| 1383 | `_write_self_test_audio` | 패키지 자체 진단에 사용할 재현 가능한 기타 유사 스테레오 WAV를 만든다. |
| 1413 | `run_self_test` | 합성 기타로 오프라인 분석·한영 변환·개발자 소스와 런타임을 검사한다. |
| 1444 | `main` | 자체 진단 인수를 처리하거나 한·영 데스크톱 GUI 이벤트 루프를 시작한다. |

## `catalog.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| - | 함수 없음 | 상수·카탈로그 데이터 모듈 |

## `debug_info.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 266 | `block_by_id` | 블록 식별자에 해당하는 설명 사전을 반환한다. |
| 274 | `localized_block` | 개발자 블록의 제목·설명·입출력을 선택한 표시 언어로 복사한다. |
| 284 | `block_for_progress` | 0~100 진행률을 현재 처리 중인 블록 식별자로 바꾼다. |
| 294 | `_source_roots` | EXE 번들 및 소스 실행 환경에서 코드 원본 후보 폴더를 만든다. |
| 301 | `source_file_path` | 개발자 뷰어에 표시할 배포 소스 파일의 실제 경로를 찾는다. |
| 311 | `_find_symbol_node` | 점으로 구분된 함수 또는 클래스 메서드 이름의 AST 노드를 찾는다. |
| 332 | `source_for_symbol` | 한 함수의 한글 주석을 포함한 원문과 원본 줄 번호를 반환한다. |
| 351 | `code_for_block` | 선택 블록에 연결된 모든 함수 소스를 구분선과 함께 합친다. |
| 360 | `changelog_as_text` | 구조화된 변경 기록을 앱 화면용 한국어 또는 영어 텍스트로 변환한다. |

## `devices.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 74 | `device_by_id` | 장치 식별자와 일치하는 프로필을 반환한다. |
| 82 | `device_label` | 콤보박스에 표시할 장치명과 지원 상태를 선택 언어로 만든다. |
| 91 | `device_description` | 선택한 장치가 현재 무엇을 지원하는지 설명하는 문장을 반환한다. |
| 98 | `device_id_from_label` | 어느 언어로 표시됐든 콤보박스 라벨을 안정적인 장치 ID로 되돌린다. |
| 107 | `is_supported_device` | 현재 레시피 생성기가 해당 장치를 구현했는지 확인한다. |

## `engine.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 40 | `clamp` | 실수 값을 지정 범위(기본 0~1) 안으로 제한한다. |
| 45 | `pct` | 0~1 값을 반올림한 0~100 정수 백분율로 바꾼다. |
| 50 | `db` | 양의 선형 진폭 비율을 로그 dB 값으로 변환한다. |
| 84 | `bundled_path` | 소스 실행과 PyInstaller 실행 모두에서 번들 리소스 경로를 찾는다. |
| 98 | `ffmpeg_path` | 앱과 함께 배포된 FFmpeg 실행 파일 경로를 반환한다. |
| 103 | `_hidden_process_flags` | Windows에서 FFmpeg 콘솔 창이 잠깐 나타나지 않도록 실행 플래그를 만든다. |
| 108 | `decode_to_pcm_wav` | 선택 구간 또는 최대 20분 전체를 표준 PCM WAV로 디코딩한다. |
| 184 | `decode_segment` | 선택 구간 또는 전체 곡을 22.05 kHz 스테레오 배열로 디코딩한다. |
| 207 | `read_pcm_wav` | 8/16/24/32-bit PCM WAV를 -1~1 범위의 스테레오 float 배열로 읽는다. |
| 238 | `_frames` | 1차원 신호를 겹치는 고정 길이 프레임의 2차원 뷰로 나눈다. |
| 248 | `_frame_rms` | 긴 곡에서도 메모리가 급증하지 않도록 프레임 RMS를 묶음 단위로 계산한다. |
| 258 | `_band_ratio` | 전체 스펙트럼 파워 중 지정 주파수 대역이 차지하는 비율을 구한다. |
| 266 | `_autocorrelation_metrics` | 온셋 엔벨로프 자기상관으로 반복 강도, 딜레이 후보와 BPM을 추정한다. |
| 294 | `extract_features` | PCM에서 포화도·밝기·바디·다이내믹·공간 및 오염 특징을 계산한다. |
| 454 | `_parameter` | 정규화된 파라미터에 보정치를 적용하고 TMP 표시용 백분율로 만든다. |
| 459 | `_amp_parameters` | 앰프 모델별 실제 컨트롤 이름에 맞춘 게인·EQ 시작값을 만든다. |
| 538 | `_drive_parameters` | 드라이브·부스트·퍼즈 모델별 컨트롤 시작값을 계산한다. |
| 573 | `_reverb_parameters` | 리버브 모델 유형에 맞춰 믹스·감쇠·댐핑 등 공간 파라미터를 만든다. |
| 618 | `_parse_mic_position` | 카탈로그의 위치·거리·축 문자열을 검증해 TMP 표시값과 축 값으로 분리한다. |
| 636 | `_cabinet_parameters` | 검증한 TMP 캐비닛 마이크 위치·축과 톤 기반 컷 필터 시작값을 만든다. |
| 650 | `_make_block` | 화면과 내보내기에서 공통으로 쓰는 단일 TMP 블록 사전을 만든다. |
| 667 | `_recipe_from_template` | 한 톤 템플릿을 순서가 지정된 TMP 블록 레시피로 확장한다. |
| 782 | `_template_score` | 측정 특징과 템플릿 목표의 가중 제곱 거리를 0~1 유사도로 바꾼다. |
| 791 | `_adjust_for_mix` | 단독 기타 또는 풀믹스 선택에 따라 오염도와 핵심 특징을 보수적으로 보정한다. |
| 811 | `_application_steps` | 실제 출력 연결에서 포함되는 앰프·캐비닛 블록과 일치하는 적용 순서를 만든다. |
| 832 | `analyze_file` | 디코딩·기타 분리·DSP 분석·장치 레시피 조립의 전체 순서를 실행한다. |
| 977 | `save_json` | 분석 결과를 한글이 보존되는 들여쓰기 JSON 파일로 저장한다. |
| 982 | `relocalize_result` | 이미 계산한 수치는 유지하고 레시피·경고·적용 문구만 새 언어로 다시 만든다. |
| 1029 | `human_feature_rows` | 원시 특징 사전을 GUI와 HTML 표에서 읽기 쉬운 언어별 행으로 변환한다. |

## `i18n.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 290 | `tr` | 문자열 키를 선택 언어로 번역하고 선택적인 자리표시자를 채운다. |
| 301 | `choice_label` | 안정적인 선택 코드에 대응하는 현재 언어의 콤보박스 라벨을 만든다. |
| 306 | `choice_values` | 한 선택 그룹에 속한 모든 현재 언어 라벨을 정의 순서대로 반환한다. |
| 311 | `choice_code` | 한국어 또는 영어 라벨을 언어 독립적인 선택 코드로 되돌린다. |
| 325 | `language_code` | 언어 콤보박스 라벨을 ``ko`` 또는 ``en`` 코드로 변환한다. |

## `recorder.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 34 | `list_capture_devices` | 마이크·오디오 인터페이스와 PC 출력 loopback 장치를 함께 나열한다. |
| 60 | `capture_device_label` | 장치 종류가 드러나는 언어별 콤보박스 라벨을 만든다. |
| 66 | `record_device_to_wav` | 선택 장치를 중지 요청 또는 제한 시간까지 PCM16 스테레오 WAV로 녹음한다. |

## `report.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 45 | `_rt` | HTML·텍스트 리포트 전용 문구를 선택 언어로 반환한다. |
| 50 | `recipe_as_text` | 선택한 추천 레시피의 블록·파라미터·이유를 일반 텍스트로 만든다. |
| 72 | `_feature_bar` | 0~1 특징값 하나를 HTML 퍼센트 막대 조각으로 변환한다. |
| 82 | `_reference_link` | 참고 주소는 HTTP(S)일 때만 링크로 만들고 나머지는 안전한 글자로 표시한다. |
| 99 | `save_html` | 외부 자원이 필요 없는 단일 HTML 분석 리포트를 UTF-8로 저장한다. |

## `separator.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 55 | `_hf_model_cache_root` | Hugging Face가 사용하는 기본 Demucs 모델 캐시 경로를 계산한다. |
| 63 | `separator_model_is_cached` | 공식 6-stem 모델 가중치가 사용자 캐시에 있는지 가볍게 확인한다. |
| 69 | `_normalize_compute_preference` | 사용자가 선택한 연산 장치 값을 검사하고 소문자 표준값으로 바꾼다. |
| 80 | `_torch_cuda_is_available` | PyTorch가 현재 시스템에서 CUDA 추론을 실제로 사용할 수 있는지 안전하게 확인한다. |
| 88 | `resolve_compute_device` | auto·cpu·cuda 설정을 실제 Demucs 실행 장치인 cpu 또는 cuda로 결정한다. |
| 117 | `_cuda_runtime_details` | 개발자 진단에 필요한 CUDA 빌드와 첫 번째 GPU의 메모리·연산 정보를 수집한다. |
| 157 | `separator_runtime_status` | 개발자 진단에 표시할 Demucs·PyTorch·CUDA 런타임 상태를 반환한다. |
| 201 | `_safe_cuda_synchronize` | CUDA 비동기 작업의 정확한 시간 측정을 위해 동기화하되 진단 실패는 무시한다. |
| 211 | `_safe_cuda_reset_peak_memory` | 이번 추론에 사용된 GPU 최대 메모리를 측정할 수 있도록 누적 통계를 초기화한다. |
| 221 | `_safe_cuda_peak_memory` | CUDA 추론 중 최대 할당 메모리를 바이트 단위로 반환하고 조회 실패 시 None을 돌려준다. |
| 231 | `_safe_cuda_empty_cache` | CUDA 실행 뒤 재사용 가능한 캐시를 안전하게 비워 다른 작업의 GPU 메모리를 확보한다. |
| 241 | `_pcm16_chunk` | 16-bit PCM 바이트를 Demucs가 받는 채널 우선 float32 배열로 바꾼다. |
| 254 | `_tensor_to_pcm16` | 분리된 PyTorch 텐서를 클리핑한 PCM과 레벨 통계로 변환한다. |
| 267 | `separate_guitar_wav` | 선택한 CPU·CUDA 장치로 44.1 kHz PCM에서 guitar stem WAV만 분리해 기록한다. |
| 414 | `separation_info_dict` | 불변 진단 객체를 JSON 저장에 알맞은 일반 사전으로 바꾼다. |

## `voicing.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 75 | `_next_power_of_two` | FFT 효율을 위해 입력 이상인 가장 작은 2의 거듭제곱을 구한다. |
| 81 | `_guitar_midi_frequencies` | 기타 기본음과 주요 배음을 포괄하는 MIDI 번호와 주파수를 만든다. |
| 89 | `_analysis_window` | 같은 길이의 보이싱 창이 반복될 때 재사용할 Hann 창을 만든다. |
| 94 | `_local_spectral_peak` | 목표 주파수 부근 세 FFT bin 중 가장 큰 크기를 반환한다. |
| 102 | `_spectral_peaks` | 여러 목표 주파수 주변의 세 FFT bin 최댓값을 네이티브 NumPy 연산으로 함께 구한다. |
| 116 | `_window_pitch_profile` | 한 시간창에서 HPCP형 chroma, 음별 salience, 기본음 크기와 RMS를 계산한다. |
| 140 | `_score_chord` | 구성음 보상과 비구성음 벌점을 조합해 한 코드 템플릿 점수를 만든다. |
| 160 | `_infer_bass_pc` | 충분히 강한 가장 낮은 기타 음을 찾아 베이스 pitch class로 사용한다. |
| 169 | `_voicing_profile` | 활성 음들의 pitch class, 평균 음역과 음 간격 폭을 보수적으로 분류한다. |
| 190 | `_barre_shape` | 검출값과 별개로 연주해 볼 수 있는 E형 또는 A형 바레 후보를 만든다. |
| 220 | `candidate_guitar_shapes` | 코드 이름을 실제로 시험할 수 있는 최대 두 개의 일반 운지 후보로 바꾼다. |
| 235 | `_classify_window` | 한 분석창을 코드, 베이스/역위, 음역, 간격과 신뢰도로 분류한다. |
| 273 | `_smooth_labels` | 앞뒤 두 창이 같은 코드일 때 가운데의 짧은 오검출을 그 코드로 평활화한다. |
| 293 | `_merge_events` | 연속해서 같은 코드로 분류된 시간창을 하나의 타임라인 이벤트로 합친다. |
| 348 | `analyze_voicings` | guitar stem 전체에서 시간대별 코드와 보이싱 프로필을 결정론적으로 추정한다. |
| 408 | `voicing_analysis_dict` | 불변 보이싱 분석 객체와 이벤트를 JSON 직렬화 가능한 사전으로 바꾼다. |
| 413 | `pitch_class_names` | pitch class 정수 모음을 사람이 읽는 음이름 문자열로 바꾼다. |

## `tests/test_developer_mode.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 25 | `DeveloperModeTests.test_version_and_latest_changelog_match` | 앱 버전은 두 자리 패치 규칙이며 최신 변경 기록과 같아야 한다. |
| 31 | `DeveloperModeTests.test_pipeline_order_and_source_links_are_complete` | 블록 번호가 연속이고 각 클릭 대상에서 실제 코드가 추출되는지 검사한다. |
| 42 | `DeveloperModeTests.test_every_function_has_korean_docstring` | 배포 소스의 모든 함수가 개발자에게 보이는 한글 설명을 갖는지 검사한다. |
| 81 | `DeveloperModeTests.test_progress_maps_to_sequence_blocks` | 대표 진행률이 입력부터 결과까지 순서대로 해당 블록을 가리키는지 확인한다. |
| 87 | `DeveloperModeTests.test_debug_diagram_fits_and_displays_source` | 개발자 탭의 모든 블록이 화면 안에 들어오고 코드 내용이 표시되는지 확인한다. |

## `tests/test_engine.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 28 | `_guitar_like_stereo` | 약간의 스테레오 폭을 가진 재현 가능한 기타 플럭 신호를 합성한다. |
| 67 | `_spectral_shape` | 밝기와 바디 테스트용으로 서로 다른 완만한 스펙트럼 외형을 적용한다. |
| 94 | `_write_pcm16_stereo` | float 스테레오 배열을 16-bit PCM WAV 테스트 파일로 저장한다. |
| 106 | `EngineAnalysisTests.setUpClass` | 모든 테스트가 공유하는 합성 원본과 두 스펙트럼 변형을 준비한다. |
| 113 | `EngineAnalysisTests._analyze_result` | 파일 디코딩만 대체하고 나머지 전체 분석·추천 시퀀스를 실행한다. |
| 136 | `EngineAnalysisTests.test_near_silence_raises_analysis_error` | 거의 무음인 입력은 사용자에게 의미 있는 분석 오류를 내야 한다. |
| 142 | `EngineAnalysisTests.test_bright_and_body_profiles_have_expected_relative_order` | 고역 강조 신호와 중저역 강조 신호의 상대 특징 순서를 검증한다. |
| 158 | `EngineAnalysisTests.test_pcm16_wav_round_trip_is_stereo_and_close_to_source` | 16-bit WAV 입출력 뒤 채널·길이·샘플 오차가 허용 범위인지 확인한다. |
| 169 | `EngineAnalysisTests.test_analysis_returns_three_ordered_recipes` | 상위 레시피 세 개와 각 체인의 블록 순번·카테고리 순서를 검사한다. |
| 199 | `EngineAnalysisTests.test_output_routes_match_amp_and_cabinet_policy` | 세 출력 연결의 Amp·Cabinet 구성과 적용 안내가 실제 추천 블록과 일치해야 한다. |
| 235 | `EngineAnalysisTests.test_catalog_cabinet_positions_are_structured_and_valid` | 모든 TMP 캐비닛 조합의 마이크 위치·거리·축이 검증 가능한 형식이어야 한다. |
| 250 | `EngineAnalysisTests.test_direct_template_remains_valid_without_amp_or_cabinet` | 앰프·캐비닛이 없는 다이렉트 템플릿도 모든 출력 경로에서 빈 참조값 없이 조립돼야 한다. |
| 266 | `EngineAnalysisTests.test_json_and_html_exports_are_complete_and_escape_url` | JSON/HTML 저장 내용과 HTML 특수문자 이스케이프를 검증한다. |

## `tests/test_separator.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 26 | `_FakeCuda.__init__` | 테스트할 CUDA 사용 가능 여부와 호출 기록을 초기화한다. |
| 33 | `_FakeCuda.is_available` | 설정된 CUDA 사용 가능 여부를 반환한다. |
| 37 | `_FakeCuda.device_count` | CUDA 사용 가능 여부에 따라 가상 GPU 개수를 반환한다. |
| 41 | `_FakeCuda.get_device_properties` | 가상 GPU의 이름·VRAM·연산 능력 정보를 반환한다. |
| 50 | `_FakeCuda.mem_get_info` | 가상 GPU의 여유 메모리와 전체 메모리를 바이트로 반환한다. |
| 54 | `_FakeCuda.synchronize` | 가상 CUDA 동기화 호출 횟수를 기록한다. |
| 58 | `_FakeCuda.reset_peak_memory_stats` | 가상 CUDA 최대 메모리 통계 초기화 호출을 기록한다. |
| 62 | `_FakeCuda.max_memory_allocated` | 테스트에서 확인할 고정 최대 GPU 메모리 사용량을 반환한다. |
| 66 | `_FakeCuda.empty_cache` | 가상 CUDA 캐시 정리 호출 횟수를 기록한다. |
| 74 | `_FakeTensor.__init__` | 텐서가 감쌀 float32 배열을 저장한다. |
| 78 | `_FakeTensor.detach` | 그래프가 없는 동일한 가상 텐서를 반환한다. |
| 82 | `_FakeTensor.to` | 장치 전송을 흉내 내고 동일한 가상 텐서를 반환한다. |
| 86 | `_FakeTensor.numpy` | 가상 텐서가 가진 NumPy 배열을 반환한다. |
| 94 | `_FakeInferenceMode.__init__` | 호출 횟수를 기록할 가상 PyTorch 모듈을 저장한다. |
| 98 | `_FakeInferenceMode.__enter__` | 추론 문맥 진입 횟수를 늘리고 자신을 반환한다. |
| 103 | `_FakeInferenceMode.__exit__` | 추론 문맥 종료를 정상 처리한다. |
| 111 | `_FakeTorch.__init__` | 가상 버전·CUDA 런타임과 호출 기록을 초기화한다. |
| 120 | `_FakeTorch.set_num_threads` | CPU 스레드 설정값을 테스트 기록으로 보존한다. |
| 124 | `_FakeTorch.from_numpy` | NumPy 배열을 가상 텐서로 감싸 반환한다. |
| 128 | `_FakeTorch.inference_mode` | 추론 전용 실행 여부를 검증할 문맥 관리자를 반환한다. |
| 138 | `_FakeSeparator.__init__` | 선택된 실행 장치를 기록하고 guitar 출력 모델을 준비한다. |
| 143 | `_FakeSeparator.separate_tensor` | 입력 레벨을 유지한 guitar stem을 반환해 파일 경로 전체를 검증한다. |
| 150 | `_fake_torch` | 장치 결정과 런타임 진단에 필요한 최소 PyTorch 모듈을 만든다. |
| 158 | `SeparatorDeviceTests.test_cpu_preference_always_resolves_to_cpu` | CUDA가 있어도 명시적 CPU 설정은 CPU를 유지해야 한다. |
| 162 | `SeparatorDeviceTests.test_auto_prefers_cuda_and_falls_back_to_cpu` | 자동 설정은 CUDA를 우선하고 사용할 수 없으면 CPU로 내려가야 한다. |
| 167 | `SeparatorDeviceTests.test_explicit_unavailable_cuda_has_clear_error` | 사용할 수 없는 CUDA를 명시하면 한영 안내가 포함된 분리 오류를 내야 한다. |
| 175 | `SeparatorDeviceTests.test_invalid_preference_is_rejected` | 지원 목록에 없는 장치 이름은 조용히 CPU로 바꾸지 않고 거부해야 한다. |
| 180 | `SeparatorDeviceTests.test_runtime_status_reports_gpu_build_memory_and_resolution` | 개발자 진단이 CUDA 빌드·GPU·VRAM·연산 능력과 실제 장치를 모두 보여야 한다. |
| 202 | `SeparatorDeviceTests.test_runtime_status_keeps_explicit_cuda_failure_visible` | 진단 화면에서는 명시적 CUDA 실패를 숨기지 않고 오류 설명으로 보존해야 한다. |
| 217 | `SeparatorDeviceTests.test_cuda_separation_uses_inference_mode_and_reports_timings` | CUDA 분리가 추론 문맥·메모리 정리를 사용하고 결과 진단에 실행 시간을 남겨야 한다. |

## `tests/test_voicing.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 22 | `_synth_chord` | 테스트 코드의 기본음과 약한 고조파를 가진 스테레오 신호를 합성한다. |
| 41 | `VoicingAnalysisTests.test_major_minor_and_power_chords` | C, Am, E5의 코드 유형과 근음이 예상값으로 판정되어야 한다. |
| 57 | `VoicingAnalysisTests.test_inversion_uses_lowest_audible_pitch` | 낮은 E가 포함된 C 코드는 C/E 역위 후보로 표시되어야 한다. |
| 66 | `VoicingAnalysisTests.test_timeline_preserves_three_chord_order` | C→G→Am 연결은 시간 순서가 유지된 세 대표 화음으로 나타나야 한다. |
| 89 | `VoicingAnalysisTests.test_candidate_shapes_are_explicitly_not_detected` | 연주 후보 운지는 실제 음원에서 검출한 것처럼 표시되면 안 된다. |
| 96 | `VoicingAnalysisTests.test_silence_is_unknown_and_result_is_deterministic` | 무음은 unknown이며 같은 입력은 직렬화 결과까지 완전히 같아야 한다. |
| 107 | `VoicingAnalysisTests.test_invalid_pcm_is_rejected` | 채널 차원이 없거나 지나치게 낮은 샘플레이트 입력은 거부해야 한다. |

## `tools/collect_licenses.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 13 | `_requirement_names` | requirements.txt에서 옵션과 주석을 제외한 배포판 이름을 읽는다. |
| 24 | `_license_files` | 설치 배포판 안에서 LICENSE·COPYING·NOTICE 계열 파일을 찾는다. |
| 42 | `collect` | 라이선스 파일을 구성요소별 폴더로 복사하고 사람이 읽는 목록을 쓴다. |
| 93 | `main` | 명령행 경로를 해석하여 라이선스 수집 작업을 실행한다. |

## `tools/generate_function_reference.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 30 | `_function_rows` | 한 소스 파일에서 함수 줄 번호·정규 이름·설명을 소스 순으로 모은다. |
| 35 | `_function_rows.<local>.walk` | 클래스와 중첩 함수의 이름 경로를 유지하며 AST 본문을 순회한다. |
| 50 | `generate` | 모든 배포 모듈의 함수 설명을 버전이 적힌 단일 문서로 저장한다. |
| 74 | `main` | 현재 프로젝트 기준 함수 색인을 기본 파일명으로 생성한다. |

## `tools/write_manifest.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 13 | `_sha256` | 큰 바이너리도 메모리를 많이 쓰지 않고 SHA-256을 계산한다. |
| 22 | `write_manifest` | 배포 루트 아래 모든 일반 파일을 정렬해 재현 가능한 목록으로 저장한다. |
| 45 | `main` | 명령행 인수로 받은 배포 루트와 버전에 대해 manifest를 생성한다. |

---

총 함수 수: **222**
