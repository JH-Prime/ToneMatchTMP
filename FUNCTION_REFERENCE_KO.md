# ToneMatch TMP 0.0.06 함수 설명서

이 문서는 배포 소스의 모든 함수와 한국어 docstring을 자동으로 모은 색인입니다.
앱의 `개발자 옵션`에서는 처리 순서 블록을 클릭해 같은 함수의 실제 소스와 원본 줄 번호를 볼 수 있습니다.

## `app.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 32 | `_ensure_standard_streams` | 콘솔 없는 EXE에서도 외부 라이브러리가 표준 출력에 안전하게 쓰도록 한다. |
| 107 | `_center_window` | 주 모니터 가운데에 창을 배치하되 작은 화면 경계를 넘지 않게 한다. |
| 119 | `_portable_root` | 소스 실행 또는 PyInstaller onedir 실행의 포터블 루트를 반환한다. |
| 126 | `_runtime_data_root` | 우선 EXE 옆 data를 쓰고 권한이 없으면 LocalAppData로 안전하게 폴백한다. |
| 141 | `_input_method_label` | 입력 방법의 안정적인 코드에 대응하는 언어별 화면 라벨을 만든다. |
| 146 | `_input_method_code` | 한국어 또는 영어 입력 방법 라벨을 안정적인 코드로 되돌린다. |
| 157 | `ToneMatchApp.__init__` | 영구 상태를 준비하고 전체 Tkinter 화면과 이벤트 루프를 구성한다. |
| 229 | `ToneMatchApp.ui_font` | 현재 언어에 맞춰 사용자가 지정한 기본 UI 글꼴을 반환한다. |
| 233 | `ToneMatchApp._load_settings` | 이전 실행의 언어·장치·연산 백엔드 선택을 읽되 손상된 파일은 무시한다. |
| 248 | `ToneMatchApp._save_settings` | 다음 실행에서도 유지할 언어·장치·연산 백엔드 선택을 작은 JSON으로 저장한다. |
| 260 | `ToneMatchApp._configure_style` | 현재 언어 글꼴과 어두운 색상표를 모든 공통 위젯 스타일에 적용한다. |
| 298 | `ToneMatchApp._panel` | 공통 배경과 여백을 가진 카드형 패널을 만들어 즉시 배치한다. |
| 305 | `ToneMatchApp._field_label` | 입력 필드 위의 작은 설명 라벨을 지정한 그리드 위치에 배치한다. |
| 309 | `ToneMatchApp._sync_left_scroll_region` | 입력 카드 내용 높이가 바뀔 때 스크롤 가능한 전체 영역을 다시 계산한다. |
| 314 | `ToneMatchApp._resize_left_scroll_content` | 창 너비가 바뀌어도 입력 카드 내부 프레임이 캔버스 폭을 정확히 채우게 한다. |
| 319 | `ToneMatchApp._enable_left_mousewheel` | 포인터가 입력 카드 위에 있을 때 휠을 해당 세로 스크롤에 연결한다. |
| 323 | `ToneMatchApp._disable_left_mousewheel` | 포인터가 입력 카드를 벗어나면 다른 화면의 휠 동작을 방해하지 않게 연결을 푼다. |
| 327 | `ToneMatchApp._scroll_left_panel` | Windows 마우스 휠 회전량을 입력 카드의 세로 이동 단위로 변환한다. |
| 332 | `ToneMatchApp._build_ui` | 입력·결과·개발자·변경 기록과 하단 상태를 현재 언어로 구성한다. |
| 579 | `ToneMatchApp._build_debug_tab` | 처리 순서도, 클릭형 실제 소스, 런타임 로그와 디버그 번들 버튼을 만든다. |
| 622 | `ToneMatchApp._build_changelog_tab` | 패치 버전·변경사항·알려진 제한을 현재 언어로 읽는 탭을 만든다. |
| 633 | `ToneMatchApp._build_spectrum_tab` | 선택한 입력 장치의 파형·주파수·레벨을 보여주는 실시간 탭을 만든다. |
| 718 | `ToneMatchApp._build_reference_compare_tab` | 분석한 기준 스펙트럼과 실시간 입력의 레벨 정규화 차이 탭을 만든다. |
| 832 | `ToneMatchApp._spectrum_is_running` | 실시간 스펙트럼 세션이 종료 이벤트 처리 전까지 활성인지 반환한다. |
| 837 | `ToneMatchApp._spectrum_plot_x` | 20 Hz~20 kHz 로그 축의 주파수를 캔버스 가로 좌표로 바꾼다. |
| 846 | `ToneMatchApp._spectrum_plot_y` | -120~0 dBFS 레벨을 스펙트럼 캔버스 세로 좌표로 바꾼다. |
| 853 | `ToneMatchApp._spectrum_canvas_resized` | 스펙트럼 탭 크기가 바뀌면 축과 마지막 측정 프레임을 다시 그린다. |
| 863 | `ToneMatchApp._draw_waveform_grid` | 파형 캔버스에 기준 레벨과 시간 방향 보조선을 그린다. |
| 883 | `ToneMatchApp._draw_spectrum_grid` | 주파수 캔버스에 로그 주파수축과 dBFS 기준선을 그린다. |
| 917 | `ToneMatchApp._draw_waveform` | 최신 PCM 파형을 현재 캔버스 폭에 맞춰 줄여 그린다. |
| 940 | `ToneMatchApp._draw_spectrum` | 평활화된 FFT 레벨과 스펙트럼 중심을 로그 주파수축에 그린다. |
| 983 | `ToneMatchApp._reference_plot_y` | ±18 dB 비교 차이를 캔버스 세로 좌표로 제한해 변환한다. |
| 990 | `ToneMatchApp._reference_canvas_resized` | 비교 탭 크기가 바뀌면 차이 축과 마지막 유효 곡선을 다시 그린다. |
| 998 | `ToneMatchApp._draw_reference_grid` | 레퍼런스 차이 캔버스에 로그 주파수축과 ±18 dB 기준선을 그린다. |
| 1022 | `ToneMatchApp._draw_reference_difference` | 현재−기준의 주파수별 정규화 dB 차이를 로그 축에 그린다. |
| 1053 | `ToneMatchApp._format_frequency_range` | 대역 경계를 Hz 또는 kHz가 섞인 짧은 화면 문자열로 바꾼다. |
| 1055 | `ToneMatchApp._format_frequency_range.<local>.compact` | 한 주파수 값을 읽기 쉬운 Hz/kHz 숫자로 축약한다. |
| 1065 | `ToneMatchApp._reference_band_level` | 프로필 밴드의 버전 호환 레벨 키를 유한 실수로 읽는다. |
| 1071 | `ToneMatchApp._populate_reference_rows` | 기준 프로필 또는 최신 비교를 Reference·Current·Δ 여섯 행으로 표시한다. |
| 1107 | `ToneMatchApp._refresh_reference_profile` | 현재 분석 결과의 기준 파일·밴드·상태를 비교 탭에 반영한다. |
| 1139 | `ToneMatchApp._apply_spectrum_frame` | 최신 스펙트럼 프레임의 수치와 두 캔버스를 Tk 메인 스레드에서 갱신한다. |
| 1168 | `ToneMatchApp._clear_spectrum_frame_queue` | 새 세션 전에 남아 있는 이전 스펙트럼 화면 프레임을 버린다. |
| 1176 | `ToneMatchApp._offer_latest_spectrum` | 작업 스레드에서 가장 최신 프레임 하나만 bounded 큐에 남긴다. |
| 1192 | `ToneMatchApp._drain_spectrum_frames` | bounded 큐의 최신 측정치만 꺼내 메인 스레드에서 화면에 반영한다. |
| 1213 | `ToneMatchApp._toggle_spectrum_monitor` | 선택한 장치의 공용 실시간 스펙트럼 또는 레퍼런스 비교를 토글한다. |
| 1261 | `ToneMatchApp._spectrum_monitor_worker` | 장치 블록을 FFT 프레임으로 바꿔 UI bounded 큐에 공급한다. |
| 1271 | `ToneMatchApp._spectrum_monitor_worker.<local>.handle_block` | 녹음 콜백의 PCM 블록을 분석하고 최근 네 프레임을 평활화한다. |
| 1284 | `ToneMatchApp._finish_spectrum_monitor` | 현재 세션의 종료·오류를 반영하고 잠근 컨트롤을 안전하게 복구한다. |
| 1311 | `ToneMatchApp._update_spectrum_availability` | 다른 작업과 장치 상태를 보고 실시간 스펙트럼 컨트롤을 잠그거나 푼다. |
| 1358 | `ToneMatchApp._change_language` | 선택값과 결과 수치를 보존한 채 전체 화면을 새 언어와 글꼴로 다시 만든다. |
| 1390 | `ToneMatchApp._change_device` | 멀티이펙터 선택을 갱신하고 미구현 장치에서는 분석을 비활성화한다. |
| 1401 | `ToneMatchApp._start_hardware_probe` | PyTorch·CUDA 확인을 UI 밖의 스레드에서 시작해 창 멈춤을 방지한다. |
| 1417 | `ToneMatchApp._hardware_probe_worker` | Demucs와 GPU 런타임을 검사하고 메인 UI 큐로 결과를 전달한다. |
| 1425 | `ToneMatchApp._apply_hardware_status` | 하드웨어 검사 결과를 저장하고 가능한 선택값·진단표·로그를 갱신한다. |
| 1445 | `ToneMatchApp._change_compute_backend` | 표시된 AI 가속 선택을 안정적인 auto·cuda·cpu 코드로 저장한다. |
| 1453 | `ToneMatchApp._set_compute_controls_enabled` | 하드웨어 검사·분석 상태에 맞춰 가속 선택과 재검사 버튼을 함께 잠그거나 푼다. |
| 1467 | `ToneMatchApp._format_bytes` | 바이트 값을 진단표에서 읽기 쉬운 MiB 또는 GiB 문자열로 바꾼다. |
| 1479 | `ToneMatchApp._populate_diagnostics` | 하드웨어·AI 분리 벤치마크·DSP 특징을 한 진단표에 순서대로 표시한다. |
| 1486 | `ToneMatchApp._populate_diagnostics.<local>.add` | 번역된 항목명과 문자열 값을 진단표 끝에 추가한다. |
| 1530 | `ToneMatchApp._change_input_method` | 로컬 파일과 PC 재생음 녹음 모드에 맞춰 관련 컨트롤 상태를 바꾼다. |
| 1556 | `ToneMatchApp._refresh_capture_devices` | Windows 오디오 장치를 다시 열거하고 기존 선택이 가능하면 유지한다. |
| 1583 | `ToneMatchApp._capture_device_changed` | 녹음 콤보박스의 표시 라벨을 실제 장치 식별자로 저장한다. |
| 1589 | `ToneMatchApp._toggle_recording` | 현재 상태에 따라 PC 재생음 녹음을 시작하거나 중지 요청을 보낸다. |
| 1630 | `ToneMatchApp._recording_worker` | 오디오 녹음을 백그라운드에서 실행하고 UI 큐에 상태를 전달한다. |
| 1632 | `ToneMatchApp._recording_worker.<local>.progress` | 녹음 경과 시간을 메인 UI가 읽는 이벤트로 바꾼다. |
| 1642 | `ToneMatchApp._toggle_developer_mode` | 개발자 순서도와 변경 기록 탭을 표시하거나 숨긴다. |
| 1656 | `ToneMatchApp._draw_debug_diagram` | 실제 실행 순서대로 클릭 가능한 세로 블록과 연결 화살표를 그린다. |
| 1687 | `ToneMatchApp._select_debug_block` | 선택한 처리 블록의 언어별 설명과 연결된 실제 함수 원문을 표시한다. |
| 1715 | `ToneMatchApp._append_debug_log` | 시각 포함 이벤트를 화면과 EXE 옆 일별 UTF-8 로그 파일에 함께 남긴다. |
| 1733 | `ToneMatchApp._set_debug_progress` | 진행률로 활성·완료 블록을 계산하고 순서도와 로그를 갱신한다. |
| 1743 | `ToneMatchApp._refresh_analysis_progress` | 실제 콜백의 전체 단계 진행률과 독립적인 경과 시간을 표시한다. |
| 1751 | `ToneMatchApp._tick_analysis_progress` | 다운로드나 추론 콜백을 기다리는 동안에도 경과 시간을 계속 갱신한다. |
| 1761 | `ToneMatchApp._finish_analysis_progress` | 완료·오류·취소 시 마지막 진행률과 소요 시간을 화면에 보존한다. |
| 1766 | `ToneMatchApp._choose_audio` | 파일 선택 창에서 오디오 또는 영상 경로를 받아 입력 상태를 갱신한다. |
| 1774 | `ToneMatchApp._open_reference` | 참고 URL을 기본 브라우저에서 열되 앱이 YouTube 음원을 추출하지 않는다. |
| 1784 | `ToneMatchApp._parse_inputs` | 화면 문자열을 분석 요청으로 바꾸고 파일·시간·장치 조건을 검증한다. |
| 1806 | `ToneMatchApp._start_analysis` | 검증된 요청을 별도 스레드에서 시작하고 취소·내보내기 상태를 설정한다. |
| 1861 | `ToneMatchApp._cancel_analysis` | 다운로드 또는 Demucs 내부 처리 구간 경계에서 멈추도록 취소 신호를 보낸다. |
| 1869 | `ToneMatchApp._analysis_worker` | 전체 기타 분석을 실행하고 결과 또는 오류를 메인 UI 큐에 전달한다. |
| 1871 | `ToneMatchApp._analysis_worker.<local>.progress` | 엔진 콜백을 Tk 메인 스레드용 진행 이벤트로 변환한다. |
| 1881 | `ToneMatchApp._drain_events` | 백그라운드 분석·녹음·스펙트럼 제어 이벤트를 Tk 메인 스레드에서 처리한다. |
| 1920 | `ToneMatchApp._recording_completed` | 완료된 임시 녹음을 현재 분석 파일로 연결하고 버튼 상태를 복구한다. |
| 1933 | `ToneMatchApp._recording_failed` | 녹음 실패 메시지와 상세 로그를 남기고 UI를 다시 사용할 수 있게 한다. |
| 1943 | `ToneMatchApp._show_error` | 분석 실패 상태를 복구하고 사용자 메시지와 영구 개발 로그를 남긴다. |
| 1957 | `ToneMatchApp._show_result` | 추천 체인 세 개, 기타 stem 진단과 상태를 현재 언어 화면에 표시한다. |
| 1993 | `ToneMatchApp._render_recipe` | 한 추천 체인의 모델·순서·파라미터·이유를 읽기 쉬운 서식으로 그린다. |
| 2019 | `ToneMatchApp._render_voicing` | 실험 보이싱 타임라인과 연주 후보를 별도 결과 탭에 표시한다. |
| 2052 | `ToneMatchApp._format_time` | 초 단위 위치를 긴 곡에서도 읽기 쉬운 분:초 문자열로 바꾼다. |
| 2058 | `ToneMatchApp._update_analysis_availability` | 장치 지원과 분석·녹음·스펙트럼 상태를 보고 공통 컨트롤을 갱신한다. |
| 2073 | `ToneMatchApp._update_copy_availability` | 현재 탭에 복사할 표시 내용이 있고 작업 중이 아닐 때만 복사 버튼을 켠다. |
| 2086 | `ToneMatchApp._default_export_name` | 입력 파일명을 안전한 기본 내보내기 파일명으로 바꾼다. |
| 2092 | `ToneMatchApp._export_json` | 현재 전체 분석 데이터와 분리 진단을 UTF-8 JSON으로 저장한다. |
| 2104 | `ToneMatchApp._export_html` | 현재 결과를 외부 자원이 없는 한·영 HTML 리포트로 저장하고 선택 시 연다. |
| 2118 | `ToneMatchApp._mark_export` | 내보내기 단계를 순서도에 표시하고 상태와 영구 로그를 갱신한다. |
| 2127 | `ToneMatchApp._copy_recipe` | 현재 선택한 결과·진단·개발자 탭의 표시 내용을 클립보드에 복사한다. |
| 2187 | `ToneMatchApp._export_debug_bundle` | 다른 PC에서 진단·개발을 이어갈 소스, 로그, 이력, 환경 정보를 ZIP으로 묶는다. |
| 2221 | `ToneMatchApp._on_close` | 모든 작업에 중지 신호를 보내고 임시 녹음을 정리한 뒤 창을 닫는다. |
| 2245 | `_write_self_test_audio` | 패키지 자체 진단에 사용할 재현 가능한 기타 유사 스테레오 WAV를 만든다. |
| 2275 | `run_self_test` | 합성 기타로 오프라인 분석·한영 변환·개발자 소스와 런타임을 검사한다. |
| 2317 | `main` | 자체 진단 인수를 처리하거나 한·영 데스크톱 GUI 이벤트 루프를 시작한다. |

## `catalog.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| - | 함수 없음 | 상수·카탈로그 데이터 모듈 |

## `debug_info.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 280 | `block_by_id` | 블록 식별자에 해당하는 설명 사전을 반환한다. |
| 288 | `localized_block` | 개발자 블록의 제목·설명·입출력을 선택한 표시 언어로 복사한다. |
| 298 | `block_for_progress` | 0~100 진행률을 현재 처리 중인 블록 식별자로 바꾼다. |
| 308 | `_source_roots` | EXE 번들 및 소스 실행 환경에서 코드 원본 후보 폴더를 만든다. |
| 315 | `source_file_path` | 개발자 뷰어에 표시할 배포 소스 파일의 실제 경로를 찾는다. |
| 325 | `_find_symbol_node` | 점으로 구분된 함수 또는 클래스 메서드 이름의 AST 노드를 찾는다. |
| 346 | `source_for_symbol` | 한 함수의 한글 주석을 포함한 원문과 원본 줄 번호를 반환한다. |
| 365 | `code_for_block` | 선택 블록에 연결된 모든 함수 소스를 구분선과 함께 합친다. |
| 374 | `changelog_as_text` | 구조화된 변경 기록을 앱 화면용 한국어 또는 영어 텍스트로 변환한다. |

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
| 41 | `clamp` | 실수 값을 지정 범위(기본 0~1) 안으로 제한한다. |
| 46 | `pct` | 0~1 값을 반올림한 0~100 정수 백분율로 바꾼다. |
| 51 | `db` | 양의 선형 진폭 비율을 로그 dB 값으로 변환한다. |
| 85 | `bundled_path` | 소스 실행과 PyInstaller 실행 모두에서 번들 리소스 경로를 찾는다. |
| 99 | `ffmpeg_path` | 앱과 함께 배포된 FFmpeg 실행 파일 경로를 반환한다. |
| 104 | `_hidden_process_flags` | Windows에서 FFmpeg 콘솔 창이 잠깐 나타나지 않도록 실행 플래그를 만든다. |
| 109 | `decode_to_pcm_wav` | 선택 구간 또는 최대 20분 전체를 표준 PCM WAV로 디코딩한다. |
| 185 | `decode_segment` | 선택 구간 또는 전체 곡을 22.05 kHz 스테레오 배열로 디코딩한다. |
| 208 | `read_pcm_wav` | 8/16/24/32-bit PCM WAV를 -1~1 범위의 스테레오 float 배열로 읽는다. |
| 239 | `_frames` | 1차원 신호를 겹치는 고정 길이 프레임의 2차원 뷰로 나눈다. |
| 249 | `_frame_rms` | 긴 곡에서도 메모리가 급증하지 않도록 프레임 RMS를 묶음 단위로 계산한다. |
| 259 | `_band_ratio` | 전체 스펙트럼 파워 중 지정 주파수 대역이 차지하는 비율을 구한다. |
| 267 | `_autocorrelation_metrics` | 온셋 엔벨로프 자기상관으로 반복 강도, 딜레이 후보와 BPM을 추정한다. |
| 295 | `extract_features` | PCM에서 포화도·밝기·바디·다이내믹·공간 및 오염 특징을 계산한다. |
| 455 | `_parameter` | 정규화된 파라미터에 보정치를 적용하고 TMP 표시용 백분율로 만든다. |
| 460 | `_amp_parameters` | 앰프 모델별 실제 컨트롤 이름에 맞춘 게인·EQ 시작값을 만든다. |
| 539 | `_drive_parameters` | 드라이브·부스트·퍼즈 모델별 컨트롤 시작값을 계산한다. |
| 574 | `_reverb_parameters` | 리버브 모델 유형에 맞춰 믹스·감쇠·댐핑 등 공간 파라미터를 만든다. |
| 619 | `_parse_mic_position` | 카탈로그의 위치·거리·축 문자열을 검증해 TMP 표시값과 축 값으로 분리한다. |
| 637 | `_cabinet_parameters` | 검증한 TMP 캐비닛 마이크 위치·축과 톤 기반 컷 필터 시작값을 만든다. |
| 651 | `_make_block` | 화면과 내보내기에서 공통으로 쓰는 단일 TMP 블록 사전을 만든다. |
| 668 | `_recipe_from_template` | 한 톤 템플릿을 순서가 지정된 TMP 블록 레시피로 확장한다. |
| 783 | `_template_score` | 측정 특징과 템플릿 목표의 가중 제곱 거리를 0~1 유사도로 바꾼다. |
| 792 | `_adjust_for_mix` | 단독 기타 또는 풀믹스 선택에 따라 오염도와 핵심 특징을 보수적으로 보정한다. |
| 812 | `_application_steps` | 실제 출력 연결에서 포함되는 앰프·캐비닛 블록과 일치하는 적용 순서를 만든다. |
| 833 | `analyze_file` | 디코딩·기타 분리·DSP 분석·장치 레시피 조립의 전체 순서를 실행한다. |
| 980 | `save_json` | 분석 결과를 한글이 보존되는 들여쓰기 JSON 파일로 저장한다. |
| 985 | `relocalize_result` | 이미 계산한 수치는 유지하고 레시피·경고·적용 문구만 새 언어로 다시 만든다. |
| 1032 | `human_feature_rows` | 원시 특징 사전을 GUI와 HTML 표에서 읽기 쉬운 언어별 행으로 변환한다. |

## `i18n.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 333 | `tr` | 문자열 키를 선택 언어로 번역하고 선택적인 자리표시자를 채운다. |
| 344 | `choice_label` | 안정적인 선택 코드에 대응하는 현재 언어의 콤보박스 라벨을 만든다. |
| 349 | `choice_values` | 한 선택 그룹에 속한 모든 현재 언어 라벨을 정의 순서대로 반환한다. |
| 354 | `choice_code` | 한국어 또는 영어 라벨을 언어 독립적인 선택 코드로 되돌린다. |
| 368 | `language_code` | 언어 콤보박스 라벨을 ``ko`` 또는 ``en`` 코드로 변환한다. |

## `recorder.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 35 | `list_capture_devices` | 마이크·오디오 인터페이스와 PC 출력 loopback 장치를 함께 나열한다. |
| 61 | `capture_device_label` | 장치 종류가 드러나는 언어별 콤보박스 라벨을 만든다. |
| 67 | `_normalize_capture_block` | SoundCard 블록을 두 채널 float32 배열로 일정하게 정규화한다. |
| 83 | `monitor_capture_device` | 선택 장치의 짧은 블록을 중지 요청까지 실시간 콜백으로 전달한다. |
| 127 | `record_device_to_wav` | 선택 장치를 중지 요청 또는 제한 시간까지 PCM16 스테레오 WAV로 녹음한다. |

## `reference_compare.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 40 | `_checked_integer` | 불리언을 제외한 정수 설정값과 허용 범위를 검증한다. |
| 52 | `_prepare_pcm` | 실수 mono 또는 frames-by-channels PCM을 유한한 2차원 배열로 준비한다. |
| 77 | `_sample_frames` | 곡 전체에서 최대 프레임 수만큼 균등 표본을 뽑고 활성 프레임만 반환한다. |
| 100 | `_log_grid` | 20 Hz부터 유효 상한까지 고정 개수의 로그 주파수 셀을 만든다. |
| 110 | `_source_edges` | 주파수 중심점 배열을 파워 적분용 셀 경계 배열로 변환한다. |
| 122 | `_integrated_power_at` | 셀 안에서 일정한 파워 밀도를 가정해 임의 경계의 누적 파워를 구한다. |
| 139 | `_rebin_power` | 서로 다른 선형 주파수 격자의 파워를 공통 로그 셀에 보존적으로 투영한다. |
| 150 | `_normalize_power` | 주파수 파워 합을 1로 맞춰 전체 입력 게인의 영향을 제거한다. |
| 167 | `_mask_relative_noise` | 양쪽 FFT에 동일한 peak 대비 80 dB 범위를 적용해 수치잡음을 제외한다. |
| 178 | `_power_to_relative_db` | 총 파워 대비 80 dB 또는 공통 관측 하한으로 양쪽 상대 레벨을 제한한다. |
| 186 | `_band_power` | 로그 셀과 대역 경계의 겹침 비율을 반영해 한 대역의 파워를 합산한다. |
| 194 | `_single_band_rows` | 기준 프로필에 넣을 여섯 고정 대역의 상대 레벨 행을 만든다. |
| 217 | `_comparison_band_rows` | 기준·현재·차이를 포함한 여섯 고정 대역 비교 행을 만든다. |
| 257 | `build_reference_profile` | 오프라인 PCM의 활성 구간에서 레벨 정규화 기준 음색 프로필을 만든다. |
| 312 | `_profile_arrays` | 직렬화된 기준 프로필의 schema와 로그 격자·파워 배열을 엄격히 검증한다. |
| 338 | `_frame_arrays` | 공개 SpectrumFrame에서 유효한 주파수와 선형 파워 배열을 읽는다. |
| 381 | `compare_live_frame` | 실시간 프레임을 기준 로그 격자에 투영해 주파수별·대역별 상대 차이를 반환한다. |

## `report.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 58 | `_rt` | HTML·텍스트 리포트 전용 문구를 선택 언어로 반환한다. |
| 63 | `recipe_as_text` | 선택한 추천 레시피의 블록·파라미터·이유를 일반 텍스트로 만든다. |
| 85 | `_feature_bar` | 0~1 특징값 하나를 HTML 퍼센트 막대 조각으로 변환한다. |
| 95 | `_reference_link` | 참고 주소는 HTTP(S)일 때만 링크로 만들고 나머지는 안전한 글자로 표시한다. |
| 112 | `_reference_compare_html` | 저장된 참조 프로필의 6대역 값과 라이브 값의 비저장 상태를 안전하게 표시한다. |
| 166 | `save_html` | 외부 자원이 필요 없는 단일 HTML 분석 리포트를 UTF-8로 저장한다. |

## `separator.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 58 | `_hf_model_cache_root` | Hugging Face가 사용하는 기본 Demucs 모델 캐시 경로를 계산한다. |
| 71 | `separator_model_is_cached` | 공식 6-stem 모델 가중치가 사용자 캐시에 있는지 가볍게 확인한다. |
| 77 | `_check_cancelled` | 다운로드·모델 준비·추론의 경계에서 사용자의 취소 요청을 확인한다. |
| 83 | `_download_progress_class` | 터미널 없이 실제 Hugging Face 수신 바이트를 앱 콜백으로 전달하는 tqdm을 만든다. |
| 98 | `_download_progress_class.<local>.DownloadProgress.__init__` | 출력 대상을 메모리로 지정하고 다운로드의 실제 초기 수신량을 기록한다. |
| 107 | `_download_progress_class.<local>.DownloadProgress.display` | 콘솔 그리기를 생략해 진행률 때문에 GUI 실행이 실패하지 않도록 한다. |
| 111 | `_download_progress_class.<local>.DownloadProgress.update` | Hugging Face가 보고한 증가량만 반영하고 취소와 UI 알림을 처리한다. |
| 119 | `_download_progress_class.<local>.DownloadProgress._report` | 알려진 파일 크기로만 백분율을 계산하고 총량이 없으면 바이트만 알린다. |
| 148 | `_load_hf_separator_model` | 공식 safetensors 모델을 캐시 우선으로 준비하고 다운로드·로딩 단계를 구분한다. |
| 160 | `_load_hf_separator_model.<local>.download` | 캐시 파일을 먼저 찾고 없을 때만 공식 저장소에서 진행률과 함께 받는다. |
| 200 | `_model_error_key` | 예외 체인을 확인해 모델 준비 실패를 네트워크·캐시·메모리 원인으로 분류한다. |
| 222 | `_SeparationProgress.__init__` | 실행 콜백과 아직 시작하지 않은 조각의 상태를 저장한다. |
| 236 | `_SeparationProgress.begin_chunk` | 현재 모델의 실제 segment와 overlap으로 조각별 추론 블록 수를 계산한다. |
| 252 | `_SeparationProgress.__call__` | 실제로 끝난 추론 블록만 누적하고 블록 시작·종료 시 취소 요청을 처리한다. |
| 268 | `_SeparationProgress._report` | 모델 블록 완료 비율을 오디오 처리 초와 전체 단계 백분율로 알린다. |
| 279 | `_SeparationProgress.finish_chunk` | 콜백이 없는 호환 분리기에서도 실제 조각 완료 후 진행률을 확정한다. |
| 284 | `_normalize_compute_preference` | 사용자가 선택한 연산 장치 값을 검사하고 소문자 표준값으로 바꾼다. |
| 295 | `_torch_cuda_is_available` | PyTorch가 현재 시스템에서 CUDA 추론을 실제로 사용할 수 있는지 안전하게 확인한다. |
| 303 | `resolve_compute_device` | auto·cpu·cuda 설정을 실제 Demucs 실행 장치인 cpu 또는 cuda로 결정한다. |
| 332 | `_cuda_runtime_details` | 개발자 진단에 필요한 CUDA 빌드와 첫 번째 GPU의 메모리·연산 정보를 수집한다. |
| 372 | `separator_runtime_status` | 개발자 진단에 표시할 Demucs·PyTorch·CUDA 런타임 상태를 반환한다. |
| 416 | `_safe_cuda_synchronize` | CUDA 비동기 작업의 정확한 시간 측정을 위해 동기화하되 진단 실패는 무시한다. |
| 426 | `_safe_cuda_reset_peak_memory` | 이번 추론에 사용된 GPU 최대 메모리를 측정할 수 있도록 누적 통계를 초기화한다. |
| 436 | `_safe_cuda_peak_memory` | CUDA 추론 중 최대 할당 메모리를 바이트 단위로 반환하고 조회 실패 시 None을 돌려준다. |
| 446 | `_safe_cuda_empty_cache` | CUDA 실행 뒤 재사용 가능한 캐시를 안전하게 비워 다른 작업의 GPU 메모리를 확보한다. |
| 456 | `_pcm16_chunk` | 16-bit PCM 바이트를 Demucs가 받는 채널 우선 float32 배열로 바꾼다. |
| 469 | `_tensor_to_pcm16` | 분리된 PyTorch 텐서를 클리핑한 PCM과 레벨 통계로 변환한다. |
| 482 | `separate_guitar_wav` | 선택한 CPU·CUDA 장치로 44.1 kHz PCM에서 guitar stem WAV만 분리해 기록한다. |
| 516 | `separate_guitar_wav.<local>.ProgressSeparator._load_model` | 검증된 safetensors 모델을 주입하고 Demucs API의 입력 형식을 초기화한다. |
| 641 | `separation_info_dict` | 불변 진단 객체를 JSON 저장에 알맞은 일반 사전으로 바꾼다. |

## `spectrum.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 27 | `_validate_integer` | 불리언을 제외한 정수 설정값인지 확인하고 최소 범위를 적용한다. |
| 38 | `_validate_frequency` | 주파수 설정을 유한한 실수로 변환한다. |
| 52 | `_prepare_pcm` | 정규화 PCM과 왼쪽 0으로 채운 마지막 FFT 프레임을 함께 반환한다. |
| 82 | `_power_to_dbfs` | 선형 파워를 유한한 dBFS 값으로 바꾸고 표시 하한을 적용한다. |
| 94 | `_dbfs_to_power` | 표시 하한의 무음을 0으로 유지하며 dBFS를 선형 파워로 되돌린다. |
| 101 | `_spectral_centroid` | 주파수별 선형 파워의 무게중심을 계산하고 무음이면 0을 반환한다. |
| 110 | `analyze_spectrum_frame` | 정규화 PCM 한 구간에서 파형, 채널 파워 스펙트럼과 dBFS 통계를 계산한다. |
| 176 | `SpectrumSmoother.__init__` | 유지할 프레임 수를 검증하고 비어 있는 평활화 이력을 준비한다. |
| 182 | `SpectrumSmoother.reset` | 장치나 주파수 격자가 바뀔 때 이전 평활화 이력을 모두 지운다. |
| 188 | `SpectrumSmoother._validate_frame` | 평활화할 프레임의 배열 크기와 모든 통계값이 유효한지 확인한다. |
| 213 | `SpectrumSmoother._copy_frame` | 호출자가 나중에 배열을 바꿔도 이력이 흔들리지 않도록 프레임을 복사한다. |
| 225 | `SpectrumSmoother.push` | 새 프레임을 이력에 넣고 최신 파형과 롤링 스펙트럼을 결합해 반환한다. |

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
| 32 | `DeveloperModeTests.test_version_and_latest_changelog_match` | 앱 버전은 두 자리 패치 규칙이며 최신 변경 기록과 같아야 한다. |
| 38 | `DeveloperModeTests.test_pipeline_order_and_source_links_are_complete` | 블록 번호가 연속이고 각 클릭 대상에서 실제 코드가 추출되는지 검사한다. |
| 49 | `DeveloperModeTests.test_every_function_has_korean_docstring` | 배포 소스의 모든 함수가 개발자에게 보이는 한글 설명을 갖는지 검사한다. |
| 93 | `DeveloperModeTests.test_progress_maps_to_sequence_blocks` | 대표 진행률이 입력부터 결과까지 순서대로 해당 블록을 가리키는지 확인한다. |
| 99 | `DeveloperModeTests.test_windowed_import_repairs_missing_standard_streams` | 콘솔 없는 실행 환경도 출력 가능한 스트림을 만들고 기존 스트림은 유지해야 한다. |
| 125 | `DeveloperModeTests.test_analysis_progress_accepts_floats_without_regressing` | 실수 진행률은 표시되며 지연·잘못된 콜백에도 뒤로 가거나 범위를 벗어나지 않아야 한다. |
| 158 | `DeveloperModeTests.test_analysis_timer_refreshes_and_stops_on_error_or_cancellation` | 콜백이 없어도 경과 시간만 갱신하고 오류·취소 이후에는 마지막 값이 유지돼야 한다. |
| 198 | `DeveloperModeTests.test_analysis_completion_preserves_final_elapsed_time` | 완료 이벤트는 전체 진행률을 100%로 만들고 결과 화면에서도 소요 시간을 보존해야 한다. |
| 235 | `DeveloperModeTests.test_analysis_progress_footer_stays_visible_when_options_scroll` | 최소 크기의 한·영 화면에서 긴 상태와 진행률이 입력 스크롤 밖에 고정돼야 한다. |
| 305 | `DeveloperModeTests.test_debug_diagram_fits_and_displays_source` | 개발자 탭의 모든 블록이 화면 안에 들어오고 코드 내용이 표시되는지 확인한다. |
| 323 | `DeveloperModeTests.test_live_spectrum_tab_renders_latest_frame_without_hardware` | 실제 장치 없이 합성 FFT 프레임이 탭 수치와 두 캔버스에 표시돼야 한다. |
| 352 | `DeveloperModeTests.test_reference_compare_tab_renders_six_bands_without_hardware` | 숨긴 Tk 화면에서 기준 프로필과 합성 라이브 차이 여섯 대역을 표시해야 한다. |

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
| 205 | `EngineAnalysisTests.test_output_routes_match_amp_and_cabinet_policy` | 세 출력 연결의 Amp·Cabinet 구성과 적용 안내가 실제 추천 블록과 일치해야 한다. |
| 243 | `EngineAnalysisTests.test_reference_profile_is_deterministic_and_finite` | 같은 최종 PCM은 항상 같은 유한 참조 곡선과 6대역 값을 만들어야 한다. |
| 262 | `EngineAnalysisTests.test_catalog_cabinet_positions_are_structured_and_valid` | 모든 TMP 캐비닛 조합의 마이크 위치·거리·축이 검증 가능한 형식이어야 한다. |
| 277 | `EngineAnalysisTests.test_direct_template_remains_valid_without_amp_or_cabinet` | 앰프·캐비닛이 없는 다이렉트 템플릿도 모든 출력 경로에서 빈 참조값 없이 조립돼야 한다. |
| 293 | `EngineAnalysisTests.test_json_and_html_exports_are_complete_and_escape_url` | JSON/HTML 저장 내용과 HTML 특수문자 이스케이프를 검증한다. |

## `tests/test_recorder.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 28 | `_FakeRecorder.__init__` | 반환 블록 생성기와 선택적인 중지·실패 동작을 저장한다. |
| 43 | `_FakeRecorder.__enter__` | 가짜 녹음 컨텍스트가 열렸음을 기록한다. |
| 48 | `_FakeRecorder.__exit__` | 오류 유무와 관계없이 가짜 녹음 컨텍스트가 닫혔음을 기록한다. |
| 52 | `_FakeRecorder.record` | 요청 프레임 수를 기록하고 구성된 블록 또는 오류를 반환한다. |
| 65 | `_FakeMicrophone.__init__` | 테스트에서 돌려줄 가짜 녹음 컨텍스트를 저장한다. |
| 70 | `_FakeMicrophone.recorder` | 요청된 스트림 설정을 기록하고 가짜 컨텍스트를 반환한다. |
| 78 | `_fake_soundcard` | get_microphone 호출을 추적하는 가짜 soundcard 모듈을 만든다. |
| 87 | `_fake_soundcard.<local>.get_microphone` | 장치 조회 인자를 기록하고 지정된 마이크 또는 오류를 돌려준다. |
| 101 | `RecorderTests.test_normalize_capture_block_makes_stereo_float32` | 1차원·모노·다채널 입력을 예측 가능한 스테레오 float32로 바꾼다. |
| 115 | `RecorderTests.test_normalize_capture_block_rejects_invalid_shapes` | 프레임·채널 형태가 아닌 배열과 채널 없는 배열을 명확히 거부한다. |
| 122 | `RecorderTests.test_monitor_delivers_normalized_block_and_stops_from_callback` | 실시간 모니터는 정규화 블록과 샘플률을 전달하고 중지 뒤 스트림을 닫는다. |
| 130 | `RecorderTests.test_monitor_delivers_normalized_block_and_stops_from_callback.<local>.receive` | 첫 블록을 보관한 뒤 모니터 루프에 중지를 요청한다. |
| 158 | `RecorderTests.test_monitor_drops_block_when_cancelled_during_blocking_read` | record 대기 중 들어온 중지 요청은 낡은 블록 콜백을 발생시키지 않는다. |
| 168 | `RecorderTests.test_monitor_drops_block_when_cancelled_during_blocking_read.<local>.receive` | 취소 뒤 잘못 전달된 블록이 있는지 확인하도록 목록에 추가한다. |
| 178 | `RecorderTests.test_monitor_with_preexisting_stop_does_not_open_device` | 이미 중지된 모니터 요청은 오디오 장치를 열지 않고 즉시 끝난다. |
| 184 | `RecorderTests.test_monitor_with_preexisting_stop_does_not_open_device.<local>.receive` | 사전 중지된 호출에서는 실행되면 안 되는 콜백이다. |
| 193 | `RecorderTests.test_monitor_reports_missing_and_unopenable_devices` | 사라진 장치와 장치 조회 실패를 번역된 RecordingError로 구분한다. |
| 226 | `RecorderTests.test_monitor_wraps_stream_failure_and_closes_context` | 스트림 읽기 오류를 사용자용 실패로 감싸면서 컨텍스트를 반드시 닫는다. |
| 241 | `RecorderTests.test_wav_recording_reuses_mono_normalization` | 기존 WAV 녹음도 모노 블록을 스테레오 PCM으로 쓰는 공통 경로를 사용한다. |

## `tests/test_reference_compare.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 36 | `_tone` | 지정 주파수와 진폭을 합친 결정론적 합성 파형을 만든다. |
| 46 | `_manual_frame` | 임의 주파수 격자와 매끄러운 파워 분포를 공개 SpectrumFrame으로 포장한다. |
| 63 | `ReferenceProfileTests.test_profile_is_json_ready_finite_and_bounded` | 긴 PCM도 384개 이하 프레임으로 고정 길이 JSON 프로필을 만들어야 한다. |
| 80 | `ReferenceProfileTests.test_antiphase_stereo_preserves_the_reference_power` | 좌우 역상은 mono 합에서 상쇄되더라도 채널별 파워 프로필에서 보존돼야 한다. |
| 90 | `ReferenceProfileTests.test_reference_gain_changes_do_not_change_tone_shape` | 같은 파형의 전체 입력 게인만 달라지면 정규화 프로필은 동일해야 한다. |
| 99 | `ReferenceProfileTests.test_silence_nonfinite_and_invalid_settings_are_rejected` | 무음·비유한 PCM과 허용 범위를 벗어난 설정은 안전한 공개 오류를 내야 한다. |
| 117 | `ReferenceProfileTests.test_reference_quiet_gate_uses_practical_rms_threshold` | -75 dBFS 이하의 기준 잡음은 거부하고 그 위의 유효 신호는 분석해야 한다. |
| 128 | `ReferenceProfileTests.test_low_rate_profile_marks_unavailable_bands_without_reversed_ranges` | 8 kHz 표본률에서 Treble/Air는 뒤집힌 범위 없이 비가용으로 기록해야 한다. |
| 140 | `LiveComparisonTests.setUp` | 각 테스트에 동일한 두 톤 기준 프로필을 준비한다. |
| 146 | `LiveComparisonTests.test_live_gain_changes_leave_comparison_unchanged` | 현재 입력의 전체 게인만 바뀌면 모든 상대 곡선과 대역 차이는 같아야 한다. |
| 165 | `LiveComparisonTests.test_identical_pcm_has_zero_curve_and_band_deltas_at_supported_rates` | 같은 PCM의 양쪽 경로는 FFT 누설을 포함한 전체 차이 곡선에서 일치해야 한다. |
| 184 | `LiveComparisonTests.test_band_delta_sign_and_value_follow_normalized_energy_ratio` | 한 대역의 진폭을 두 배로 바꾸면 정규화 에너지 비율의 dB와 부호가 맞아야 한다. |
| 193 | `LiveComparisonTests.test_nyquist_and_antiphase_pcm_use_the_same_channel_power_convention` | 나이퀴스트 성분과 좌우 역상이 있어도 양쪽 단측 FFT 보정은 같아야 한다. |
| 203 | `LiveComparisonTests.test_quiet_live_noise_is_rejected_and_weak_valid_tones_remain_comparable` | 미약한 잡음의 정규화 확대를 막고 관측 가능한 약한 톤의 대역 차이는 보존한다. |
| 221 | `LiveComparisonTests.test_different_live_grid_and_rate_are_projected_to_reference_grid` | 다른 표본률·FFT 격자도 공통 로그 셀에 투영되어 유한한 비교를 반환해야 한다. |
| 237 | `LiveComparisonTests.test_smooth_spectrum_is_stable_across_different_input_grids` | 같은 매끄러운 스펙트럼을 다른 선형 격자로 주면 대역 결과가 거의 같아야 한다. |
| 243 | `LiveComparisonTests.test_smooth_spectrum_is_stable_across_different_input_grids.<local>.shape` | 두 봉우리를 가진 양의 매끄러운 테스트 파워 분포를 계산한다. |
| 257 | `LiveComparisonTests.test_wrong_schema_nonfinite_frame_and_silence_are_rejected` | 손상된 프로필 schema·비유한 실시간 값·무음 프레임은 공개 오류로 거부해야 한다. |

## `tests/test_separator.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 27 | `_FakeCuda.__init__` | 테스트할 CUDA 사용 가능 여부와 호출 기록을 초기화한다. |
| 34 | `_FakeCuda.is_available` | 설정된 CUDA 사용 가능 여부를 반환한다. |
| 38 | `_FakeCuda.device_count` | CUDA 사용 가능 여부에 따라 가상 GPU 개수를 반환한다. |
| 42 | `_FakeCuda.get_device_properties` | 가상 GPU의 이름·VRAM·연산 능력 정보를 반환한다. |
| 51 | `_FakeCuda.mem_get_info` | 가상 GPU의 여유 메모리와 전체 메모리를 바이트로 반환한다. |
| 55 | `_FakeCuda.synchronize` | 가상 CUDA 동기화 호출 횟수를 기록한다. |
| 59 | `_FakeCuda.reset_peak_memory_stats` | 가상 CUDA 최대 메모리 통계 초기화 호출을 기록한다. |
| 63 | `_FakeCuda.max_memory_allocated` | 테스트에서 확인할 고정 최대 GPU 메모리 사용량을 반환한다. |
| 67 | `_FakeCuda.empty_cache` | 가상 CUDA 캐시 정리 호출 횟수를 기록한다. |
| 75 | `_FakeTensor.__init__` | 텐서가 감쌀 float32 배열을 저장한다. |
| 79 | `_FakeTensor.detach` | 그래프가 없는 동일한 가상 텐서를 반환한다. |
| 83 | `_FakeTensor.to` | 장치 전송을 흉내 내고 동일한 가상 텐서를 반환한다. |
| 87 | `_FakeTensor.numpy` | 가상 텐서가 가진 NumPy 배열을 반환한다. |
| 95 | `_FakeInferenceMode.__init__` | 호출 횟수를 기록할 가상 PyTorch 모듈을 저장한다. |
| 99 | `_FakeInferenceMode.__enter__` | 추론 문맥 진입 횟수를 늘리고 자신을 반환한다. |
| 104 | `_FakeInferenceMode.__exit__` | 추론 문맥 종료를 정상 처리한다. |
| 112 | `_FakeTorch.__init__` | 가상 버전·CUDA 런타임과 호출 기록을 초기화한다. |
| 121 | `_FakeTorch.set_num_threads` | CPU 스레드 설정값을 테스트 기록으로 보존한다. |
| 125 | `_FakeTorch.from_numpy` | NumPy 배열을 가상 텐서로 감싸 반환한다. |
| 129 | `_FakeTorch.inference_mode` | 추론 전용 실행 여부를 검증할 문맥 관리자를 반환한다. |
| 139 | `_FakeSeparator.__init__` | 선택된 실행 장치를 기록하고 guitar 출력 모델을 준비한다. |
| 146 | `_FakeSeparator.separate_tensor` | 입력 레벨을 유지한 guitar stem을 반환해 파일 경로 전체를 검증한다. |
| 159 | `_write_test_wav` | 분리 진행률·취소 검증용으로 짧은 비무음 스테레오 PCM 파일을 만든다. |
| 169 | `_fake_separation_modules` | 분리기 생성과 콜백 테스트에 쓸 가상 Demucs·PyTorch 모듈을 묶는다. |
| 178 | `_fake_torch` | 장치 결정과 런타임 진단에 필요한 최소 PyTorch 모듈을 만든다. |
| 186 | `SeparatorDeviceTests.test_cpu_preference_always_resolves_to_cpu` | CUDA가 있어도 명시적 CPU 설정은 CPU를 유지해야 한다. |
| 190 | `SeparatorDeviceTests.test_auto_prefers_cuda_and_falls_back_to_cpu` | 자동 설정은 CUDA를 우선하고 사용할 수 없으면 CPU로 내려가야 한다. |
| 195 | `SeparatorDeviceTests.test_explicit_unavailable_cuda_has_clear_error` | 사용할 수 없는 CUDA를 명시하면 한영 안내가 포함된 분리 오류를 내야 한다. |
| 203 | `SeparatorDeviceTests.test_invalid_preference_is_rejected` | 지원 목록에 없는 장치 이름은 조용히 CPU로 바꾸지 않고 거부해야 한다. |
| 208 | `SeparatorDeviceTests.test_runtime_status_reports_gpu_build_memory_and_resolution` | 개발자 진단이 CUDA 빌드·GPU·VRAM·연산 능력과 실제 장치를 모두 보여야 한다. |
| 230 | `SeparatorDeviceTests.test_runtime_status_keeps_explicit_cuda_failure_visible` | 진단 화면에서는 명시적 CUDA 실패를 숨기지 않고 오류 설명으로 보존해야 한다. |
| 245 | `SeparatorDeviceTests.test_cuda_separation_uses_inference_mode_and_reports_timings` | CUDA 분리가 추론 문맥·메모리 정리를 사용하고 결과 진단에 실행 시간을 남겨야 한다. |
| 295 | `SeparatorProgressTests.test_windowless_download_progress_tracks_bytes_without_standard_streams` | stdout·stderr가 None인 GUI 환경에서도 실제 다운로드량이 표시되어야 한다. |
| 307 | `SeparatorProgressTests.test_unknown_download_total_does_not_invent_percentage` | 총 파일 크기를 모를 때는 수신 바이트만 표시하고 단계값을 올리지 않아야 한다. |
| 316 | `SeparatorProgressTests.test_download_cancellation_uses_supported_interrupt` | 다운로드 콜백 취소는 Hugging Face가 정리하는 KeyboardInterrupt로 전달되어야 한다. |
| 323 | `SeparatorProgressTests.test_segment_events_update_inside_first_chunk` | 30초 조각 하나가 끝나기 전에도 내부 분할 완료마다 진행률이 증가해야 한다. |
| 338 | `SeparatorProgressTests.test_cancel_between_internal_segments_removes_partial_file` | 내부 블록 완료 후 취소하면 다음 블록 전에 멈추고 미완성 stem을 제거해야 한다. |
| 352 | `SeparatorProgressTests.test_cancel_before_model_import_leaves_output_absent` | 시작 전 취소 요청은 모델 다운로드나 출력 파일 생성 전에 처리되어야 한다. |
| 363 | `SeparatorProgressTests.test_model_failure_preserves_type_and_does_not_claim_network_failure` | 일반 모델 초기화 오류의 원인을 그대로 남기고 인터넷 연결 문제로 단정하지 않아야 한다. |
| 368 | `SeparatorProgressTests.test_model_failure_preserves_type_and_does_not_claim_network_failure.<local>.FailingSeparator.__init__` | 상속된 로딩 지점을 호출해 오류 변환 경로를 검증한다. |
| 385 | `SeparatorProgressTests.test_model_error_classification_uses_exception_chain` | 상위 래퍼가 있어도 네트워크·캐시·메모리의 구체적인 예외 원인을 찾아야 한다. |
| 395 | `SeparatorProgressTests.test_multimodel_progress_ignores_duplicates_and_waits_for_every_model` | 여러 모델의 겹침 블록은 중복 집계하지 않고 모든 모델 완료 후에만 끝나야 한다. |
| 413 | `SeparatorProgressTests.test_hf_loader_uses_complete_cache_without_network_download` | 캐시가 완전하면 YAML·가중치를 네트워크 호출 없이 읽고 로딩 단계를 알려야 한다. |
| 441 | `SeparatorProgressTests.test_hf_loader_downloads_missing_file_with_progress_class` | 가중치 캐시가 없을 때만 다운로드를 수행하고 공식 tqdm 확장 인자를 넘겨야 한다. |
| 473 | `SeparatorProgressTests.test_hf_loader_preserves_network_failure_without_legacy_fallback` | HF 연결 실패가 legacy 다운로드의 stdout 예외로 덮이지 않고 그대로 전달되어야 한다. |
| 490 | `SeparatorProgressTests.test_installed_demucs_api_accepts_progress_model_loader_override` | 설치된 실제 Demucs API에서 로더 주입·샘플레이트·콜백 인자가 호환되어야 한다. |
| 499 | `SeparatorProgressTests.test_installed_demucs_api_accepts_progress_model_loader_override.<local>.mocked_inference` | 실제 API의 초기화 결과를 검증하고 모델 연산 없이 입력을 되돌린다. |

## `tests/test_spectrum.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 24 | `_bin_sine` | FFT bin 중심에 정확히 놓이는 위상 0의 결정론적 사인파를 만든다. |
| 31 | `_manual_frame` | 평활화 수치 계약을 직접 검증할 작은 스펙트럼 프레임을 만든다. |
| 57 | `SpectrumAnalysisTests.test_bin_centered_sine_has_calibrated_frequency_and_levels` | 정확한 bin 사인파의 주파수와 peak·RMS·스펙트럼 dBFS가 보정돼야 한다. |
| 77 | `SpectrumAnalysisTests.test_two_tones_keep_their_six_decibel_level_difference` | 진폭이 두 배인 bin 중심 성분은 약 6.02 dB 더 크게 표시돼야 한다. |
| 96 | `SpectrumAnalysisTests.test_antiphase_stereo_does_not_cancel_the_power_spectrum` | 좌우 역상은 표시 파형이 상쇄돼도 채널 파워 FFT에서는 사라지면 안 된다. |
| 110 | `SpectrumAnalysisTests.test_short_and_long_inputs_use_left_padding_and_latest_samples` | 짧은 블록은 왼쪽을 0으로 채우고 긴 블록은 마지막 FFT 구간만 사용해야 한다. |
| 128 | `SpectrumAnalysisTests.test_silence_and_nonfinite_samples_always_produce_finite_output` | 무음은 유한한 표시 하한을 사용하고 NaN·무한대 입력은 안전하게 정리해야 한다. |
| 148 | `SpectrumAnalysisTests.test_frequency_range_is_inclusive_and_capped_at_nyquist` | 선택 주파수의 양 끝을 포함하되 최대값은 나이퀴스트를 넘지 않아야 한다. |
| 162 | `SpectrumAnalysisTests.test_invalid_pcm_and_analysis_settings_are_rejected` | 빈 입력·잘못된 차원·복소 PCM과 유효하지 않은 분석 설정은 거부해야 한다. |
| 186 | `SpectrumSmootherTests.test_two_frames_are_averaged_in_linear_power` | dB 산술 평균이 아니라 선형 파워와 RMS 제곱 평균을 사용해야 한다. |
| 202 | `SpectrumSmootherTests.test_history_is_bounded_and_evicts_the_oldest_frame` | 설정된 프레임 수를 넘으면 가장 오래된 파워는 평균에서 빠져야 한다. |
| 218 | `SpectrumSmootherTests.test_reset_and_frequency_grid_change_clear_history` | 명시적 초기화와 서로 다른 주파수 격자는 이전 프레임을 섞지 않아야 한다. |
| 238 | `SpectrumSmootherTests.test_history_copies_frames_and_rejects_invalid_values` | 호출자 배열 변경은 이력에 소급되지 않고 잘못된 프레임은 거부돼야 한다. |

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
| 35 | `_function_rows` | 한 소스 파일에서 함수 줄 번호·정규 이름·설명을 소스 순으로 모은다. |
| 40 | `_function_rows.<local>.walk` | 클래스와 중첩 함수의 이름 경로를 유지하며 AST 본문을 순회한다. |
| 55 | `generate` | 모든 배포 모듈의 함수 설명을 버전이 적힌 단일 문서로 저장한다. |
| 79 | `main` | 현재 프로젝트 기준 함수 색인을 기본 파일명으로 생성한다. |

## `tools/write_manifest.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 13 | `_sha256` | 큰 바이너리도 메모리를 많이 쓰지 않고 SHA-256을 계산한다. |
| 22 | `write_manifest` | 배포 루트 아래 모든 일반 파일을 정렬해 재현 가능한 목록으로 저장한다. |
| 45 | `main` | 명령행 인수로 받은 배포 루트와 버전에 대해 manifest를 생성한다. |

---

총 함수 수: **376**
