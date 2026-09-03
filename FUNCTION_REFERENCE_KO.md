# ToneMatch TMP 0.0.03 함수 설명서

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
| 194 | `ToneMatchApp.ui_font` | 현재 언어에 맞춰 사용자가 지정한 기본 UI 글꼴을 반환한다. |
| 198 | `ToneMatchApp._load_settings` | 이전 실행의 언어와 장치 선택을 읽되 손상된 파일은 무시한다. |
| 210 | `ToneMatchApp._save_settings` | 다음 실행에서도 유지할 언어와 장치 선택을 작은 JSON으로 저장한다. |
| 218 | `ToneMatchApp._configure_style` | 현재 언어 글꼴과 어두운 색상표를 모든 공통 위젯 스타일에 적용한다. |
| 256 | `ToneMatchApp._panel` | 공통 배경과 여백을 가진 카드형 패널을 만들어 즉시 배치한다. |
| 263 | `ToneMatchApp._field_label` | 입력 필드 위의 작은 설명 라벨을 지정한 그리드 위치에 배치한다. |
| 267 | `ToneMatchApp._build_ui` | 입력·결과·개발자·변경 기록과 하단 상태를 현재 언어로 구성한다. |
| 469 | `ToneMatchApp._build_debug_tab` | 처리 순서도, 클릭형 실제 소스, 런타임 로그와 디버그 번들 버튼을 만든다. |
| 512 | `ToneMatchApp._build_changelog_tab` | 패치 버전·변경사항·알려진 제한을 현재 언어로 읽는 탭을 만든다. |
| 523 | `ToneMatchApp._change_language` | 선택값과 결과 수치를 보존한 채 전체 화면을 새 언어와 글꼴로 다시 만든다. |
| 550 | `ToneMatchApp._change_device` | 멀티이펙터 선택을 갱신하고 미구현 장치에서는 분석을 비활성화한다. |
| 561 | `ToneMatchApp._change_input_method` | 로컬 파일과 PC 재생음 녹음 모드에 맞춰 관련 컨트롤 상태를 바꾼다. |
| 587 | `ToneMatchApp._refresh_capture_devices` | Windows 오디오 장치를 다시 열거하고 기존 선택이 가능하면 유지한다. |
| 608 | `ToneMatchApp._capture_device_changed` | 녹음 콤보박스의 표시 라벨을 실제 장치 식별자로 저장한다. |
| 613 | `ToneMatchApp._toggle_recording` | 현재 상태에 따라 PC 재생음 녹음을 시작하거나 중지 요청을 보낸다. |
| 646 | `ToneMatchApp._recording_worker` | 오디오 녹음을 백그라운드에서 실행하고 UI 큐에 상태를 전달한다. |
| 648 | `ToneMatchApp._recording_worker.<local>.progress` | 녹음 경과 시간을 메인 UI가 읽는 이벤트로 바꾼다. |
| 658 | `ToneMatchApp._toggle_developer_mode` | 개발자 순서도와 변경 기록 탭을 표시하거나 숨긴다. |
| 672 | `ToneMatchApp._draw_debug_diagram` | 실제 실행 순서대로 클릭 가능한 세로 블록과 연결 화살표를 그린다. |
| 703 | `ToneMatchApp._select_debug_block` | 선택한 처리 블록의 언어별 설명과 연결된 실제 함수 원문을 표시한다. |
| 731 | `ToneMatchApp._append_debug_log` | 시각 포함 이벤트를 화면과 EXE 옆 일별 UTF-8 로그 파일에 함께 남긴다. |
| 749 | `ToneMatchApp._set_debug_progress` | 진행률로 활성·완료 블록을 계산하고 순서도와 로그를 갱신한다. |
| 759 | `ToneMatchApp._choose_audio` | 파일 선택 창에서 오디오 또는 영상 경로를 받아 입력 상태를 갱신한다. |
| 767 | `ToneMatchApp._open_reference` | 참고 URL을 기본 브라우저에서 열되 앱이 YouTube 음원을 추출하지 않는다. |
| 777 | `ToneMatchApp._parse_inputs` | 화면 문자열을 분석 요청으로 바꾸고 파일·시간·장치 조건을 검증한다. |
| 799 | `ToneMatchApp._start_analysis` | 검증된 요청을 별도 스레드에서 시작하고 취소·내보내기 상태를 설정한다. |
| 839 | `ToneMatchApp._cancel_analysis` | Demucs의 현재 30초 조각이 끝난 뒤 멈추도록 안전한 취소 신호를 보낸다. |
| 847 | `ToneMatchApp._analysis_worker` | 전체 기타 분석을 실행하고 결과 또는 오류를 메인 UI 큐에 전달한다. |
| 849 | `ToneMatchApp._analysis_worker.<local>.progress` | 엔진 콜백을 Tk 메인 스레드용 진행 이벤트로 변환한다. |
| 859 | `ToneMatchApp._drain_events` | 백그라운드 분석·녹음 이벤트를 Tk 메인 스레드에서 순서대로 처리한다. |
| 883 | `ToneMatchApp._recording_completed` | 완료된 임시 녹음을 현재 분석 파일로 연결하고 버튼 상태를 복구한다. |
| 895 | `ToneMatchApp._recording_failed` | 녹음 실패 메시지와 상세 로그를 남기고 UI를 다시 사용할 수 있게 한다. |
| 904 | `ToneMatchApp._show_error` | 분석 실패 상태를 복구하고 사용자 메시지와 영구 개발 로그를 남긴다. |
| 917 | `ToneMatchApp._show_result` | 추천 체인 세 개, 기타 stem 진단과 상태를 현재 언어 화면에 표시한다. |
| 948 | `ToneMatchApp._render_recipe` | 한 추천 체인의 모델·순서·파라미터·이유를 읽기 쉬운 서식으로 그린다. |
| 968 | `ToneMatchApp._render_voicing` | 실험 보이싱 타임라인과 연주 후보를 별도 결과 탭에 표시한다. |
| 1001 | `ToneMatchApp._format_time` | 초 단위 위치를 긴 곡에서도 읽기 쉬운 분:초 문자열로 바꾼다. |
| 1007 | `ToneMatchApp._update_analysis_availability` | 장치 지원, 분석 및 녹음 실행 상태를 보고 분석 버튼 활성 여부를 결정한다. |
| 1014 | `ToneMatchApp._update_copy_availability` | 현재 탭에 복사할 표시 내용이 있고 작업 중이 아닐 때만 복사 버튼을 켠다. |
| 1027 | `ToneMatchApp._default_export_name` | 입력 파일명을 안전한 기본 내보내기 파일명으로 바꾼다. |
| 1033 | `ToneMatchApp._export_json` | 현재 전체 분석 데이터와 분리 진단을 UTF-8 JSON으로 저장한다. |
| 1045 | `ToneMatchApp._export_html` | 현재 결과를 외부 자원이 없는 한·영 HTML 리포트로 저장하고 선택 시 연다. |
| 1059 | `ToneMatchApp._mark_export` | 내보내기 단계를 순서도에 표시하고 상태와 영구 로그를 갱신한다. |
| 1068 | `ToneMatchApp._copy_recipe` | 현재 선택한 결과·진단·개발자 탭의 표시 내용을 클립보드에 복사한다. |
| 1114 | `ToneMatchApp._export_debug_bundle` | 다른 PC에서 진단·개발을 이어갈 소스, 로그, 이력, 환경 정보를 ZIP으로 묶는다. |
| 1140 | `ToneMatchApp._on_close` | 진행 중 작업에 중지 신호를 보내고 임시 녹음을 정리한 뒤 창을 닫는다. |
| 1159 | `_write_self_test_audio` | 패키지 자체 진단에 사용할 재현 가능한 기타 유사 스테레오 WAV를 만든다. |
| 1189 | `run_self_test` | 합성 기타로 오프라인 분석·한영 변환·개발자 소스와 런타임을 검사한다. |
| 1220 | `main` | 자체 진단 인수를 처리하거나 한·영 데스크톱 GUI 이벤트 루프를 시작한다. |

## `catalog.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| - | 함수 없음 | 상수·카탈로그 데이터 모듈 |

## `debug_info.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 256 | `block_by_id` | 블록 식별자에 해당하는 설명 사전을 반환한다. |
| 264 | `localized_block` | 개발자 블록의 제목·설명·입출력을 선택한 표시 언어로 복사한다. |
| 274 | `block_for_progress` | 0~100 진행률을 현재 처리 중인 블록 식별자로 바꾼다. |
| 284 | `_source_roots` | EXE 번들 및 소스 실행 환경에서 코드 원본 후보 폴더를 만든다. |
| 291 | `source_file_path` | 개발자 뷰어에 표시할 배포 소스 파일의 실제 경로를 찾는다. |
| 301 | `_find_symbol_node` | 점으로 구분된 함수 또는 클래스 메서드 이름의 AST 노드를 찾는다. |
| 322 | `source_for_symbol` | 한 함수의 한글 주석을 포함한 원문과 원본 줄 번호를 반환한다. |
| 341 | `code_for_block` | 선택 블록에 연결된 모든 함수 소스를 구분선과 함께 합친다. |
| 350 | `changelog_as_text` | 구조화된 변경 기록을 앱 화면용 한국어 또는 영어 텍스트로 변환한다. |

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
| 618 | `_cabinet_parameters` | 템플릿 위치 문자열을 TMP의 마이크 위치·축·컷 필터 항목으로 분리한다. |
| 638 | `_make_block` | 화면과 내보내기에서 공통으로 쓰는 단일 TMP 블록 사전을 만든다. |
| 655 | `_recipe_from_template` | 한 톤 템플릿을 순서가 지정된 TMP 블록 레시피로 확장한다. |
| 760 | `_template_score` | 측정 특징과 템플릿 목표의 가중 제곱 거리를 0~1 유사도로 바꾼다. |
| 769 | `_adjust_for_mix` | 단독 기타 또는 풀믹스 선택에 따라 오염도와 핵심 특징을 보수적으로 보정한다. |
| 789 | `analyze_file` | 디코딩·기타 분리·DSP 분석·장치 레시피 조립의 전체 순서를 실행한다. |
| 933 | `save_json` | 분석 결과를 한글이 보존되는 들여쓰기 JSON 파일로 저장한다. |
| 938 | `relocalize_result` | 이미 계산한 수치는 유지하고 레시피·경고·적용 문구만 새 언어로 다시 만든다. |
| 989 | `human_feature_rows` | 원시 특징 사전을 GUI와 HTML 표에서 읽기 쉬운 언어별 행으로 변환한다. |

## `i18n.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 244 | `tr` | 문자열 키를 선택 언어로 번역하고 선택적인 자리표시자를 채운다. |
| 255 | `choice_label` | 안정적인 선택 코드에 대응하는 현재 언어의 콤보박스 라벨을 만든다. |
| 260 | `choice_values` | 한 선택 그룹에 속한 모든 현재 언어 라벨을 정의 순서대로 반환한다. |
| 265 | `choice_code` | 한국어 또는 영어 라벨을 언어 독립적인 선택 코드로 되돌린다. |
| 279 | `language_code` | 언어 콤보박스 라벨을 ``ko`` 또는 ``en`` 코드로 변환한다. |

## `recorder.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 34 | `list_capture_devices` | 마이크·오디오 인터페이스와 PC 출력 loopback 장치를 함께 나열한다. |
| 60 | `capture_device_label` | 장치 종류가 드러나는 언어별 콤보박스 라벨을 만든다. |
| 66 | `record_device_to_wav` | 선택 장치를 중지 요청 또는 제한 시간까지 PCM16 스테레오 WAV로 녹음한다. |

## `report.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 44 | `_rt` | HTML·텍스트 리포트 전용 문구를 선택 언어로 반환한다. |
| 49 | `recipe_as_text` | 선택한 추천 레시피의 블록·파라미터·이유를 일반 텍스트로 만든다. |
| 69 | `_feature_bar` | 0~1 특징값 하나를 HTML 퍼센트 막대 조각으로 변환한다. |
| 79 | `_reference_link` | 참고 주소는 HTTP(S)일 때만 링크로 만들고 나머지는 안전한 글자로 표시한다. |
| 96 | `save_html` | 외부 자원이 필요 없는 단일 HTML 분석 리포트를 UTF-8로 저장한다. |

## `separator.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 48 | `_hf_model_cache_root` | Hugging Face가 사용하는 기본 Demucs 모델 캐시 경로를 계산한다. |
| 56 | `separator_model_is_cached` | 공식 6-stem 모델 가중치가 사용자 캐시에 있는지 가볍게 확인한다. |
| 62 | `separator_runtime_status` | 개발자 진단에 표시할 Demucs·PyTorch 런타임 상태를 반환한다. |
| 87 | `_pcm16_chunk` | 16-bit PCM 바이트를 Demucs가 받는 채널 우선 float32 배열로 바꾼다. |
| 100 | `_tensor_to_pcm16` | 분리된 PyTorch 텐서를 클리핑한 PCM과 레벨 통계로 변환한다. |
| 113 | `separate_guitar_wav` | 44.1 kHz PCM 원본을 작은 조각으로 나눠 guitar stem WAV만 기록한다. |
| 239 | `separation_info_dict` | 불변 진단 객체를 JSON 저장에 알맞은 일반 사전으로 바꾼다. |

## `voicing.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 74 | `_next_power_of_two` | FFT 효율을 위해 입력 이상인 가장 작은 2의 거듭제곱을 구한다. |
| 79 | `_guitar_midi_frequencies` | 기타 기본음과 주요 배음을 포괄하는 MIDI 번호와 주파수를 만든다. |
| 86 | `_local_spectral_peak` | 목표 주파수 부근 세 FFT bin 중 가장 큰 크기를 반환한다. |
| 94 | `_window_pitch_profile` | 한 시간창에서 HPCP형 chroma, 음별 salience, 기본음 크기와 RMS를 계산한다. |
| 128 | `_score_chord` | 구성음 보상과 비구성음 벌점을 조합해 한 코드 템플릿 점수를 만든다. |
| 148 | `_infer_bass_pc` | 충분히 강한 가장 낮은 기타 음을 찾아 베이스 pitch class로 사용한다. |
| 157 | `_voicing_profile` | 활성 음들의 pitch class, 평균 음역과 음 간격 폭을 보수적으로 분류한다. |
| 178 | `_barre_shape` | 검출값과 별개로 연주해 볼 수 있는 E형 또는 A형 바레 후보를 만든다. |
| 208 | `candidate_guitar_shapes` | 코드 이름을 실제로 시험할 수 있는 최대 두 개의 일반 운지 후보로 바꾼다. |
| 223 | `_classify_window` | 한 분석창을 코드, 베이스/역위, 음역, 간격과 신뢰도로 분류한다. |
| 261 | `_smooth_labels` | 앞뒤 두 창이 같은 코드일 때 가운데의 짧은 오검출을 그 코드로 평활화한다. |
| 281 | `_merge_events` | 연속해서 같은 코드로 분류된 시간창을 하나의 타임라인 이벤트로 합친다. |
| 336 | `analyze_voicings` | guitar stem 전체에서 시간대별 코드와 보이싱 프로필을 결정론적으로 추정한다. |
| 396 | `voicing_analysis_dict` | 불변 보이싱 분석 객체와 이벤트를 JSON 직렬화 가능한 사전으로 바꾼다. |
| 401 | `pitch_class_names` | pitch class 정수 모음을 사람이 읽는 음이름 문자열로 바꾼다. |

## `tests/test_developer_mode.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 25 | `DeveloperModeTests.test_version_and_latest_changelog_match` | 앱 버전은 두 자리 패치 규칙이며 최신 변경 기록과 같아야 한다. |
| 31 | `DeveloperModeTests.test_pipeline_order_and_source_links_are_complete` | 블록 번호가 연속이고 각 클릭 대상에서 실제 코드가 추출되는지 검사한다. |
| 42 | `DeveloperModeTests.test_every_function_has_korean_docstring` | 배포 소스의 모든 함수가 개발자에게 보이는 한글 설명을 갖는지 검사한다. |
| 80 | `DeveloperModeTests.test_progress_maps_to_sequence_blocks` | 대표 진행률이 입력부터 결과까지 순서대로 해당 블록을 가리키는지 확인한다. |
| 86 | `DeveloperModeTests.test_debug_diagram_fits_and_displays_source` | 개발자 탭의 모든 블록이 화면 안에 들어오고 코드 내용이 표시되는지 확인한다. |

## `tests/test_engine.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 28 | `_guitar_like_stereo` | 약간의 스테레오 폭을 가진 재현 가능한 기타 플럭 신호를 합성한다. |
| 67 | `_spectral_shape` | 밝기와 바디 테스트용으로 서로 다른 완만한 스펙트럼 외형을 적용한다. |
| 94 | `_write_pcm16_stereo` | float 스테레오 배열을 16-bit PCM WAV 테스트 파일로 저장한다. |
| 106 | `EngineAnalysisTests.setUpClass` | 모든 테스트가 공유하는 합성 원본과 두 스펙트럼 변형을 준비한다. |
| 113 | `EngineAnalysisTests._analyze_result` | 파일 디코딩만 대체하고 나머지 전체 분석·추천 시퀀스를 실행한다. |
| 131 | `EngineAnalysisTests.test_near_silence_raises_analysis_error` | 거의 무음인 입력은 사용자에게 의미 있는 분석 오류를 내야 한다. |
| 137 | `EngineAnalysisTests.test_bright_and_body_profiles_have_expected_relative_order` | 고역 강조 신호와 중저역 강조 신호의 상대 특징 순서를 검증한다. |
| 153 | `EngineAnalysisTests.test_pcm16_wav_round_trip_is_stereo_and_close_to_source` | 16-bit WAV 입출력 뒤 채널·길이·샘플 오차가 허용 범위인지 확인한다. |
| 164 | `EngineAnalysisTests.test_analysis_returns_three_ordered_recipes` | 상위 레시피 세 개와 각 체인의 블록 순번·카테고리 순서를 검사한다. |
| 194 | `EngineAnalysisTests.test_json_and_html_exports_are_complete_and_escape_url` | JSON/HTML 저장 내용과 HTML 특수문자 이스케이프를 검증한다. |

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
| 29 | `_function_rows` | 한 소스 파일에서 함수 줄 번호·정규 이름·설명을 소스 순으로 모은다. |
| 34 | `_function_rows.<local>.walk` | 클래스와 중첩 함수의 이름 경로를 유지하며 AST 본문을 순회한다. |
| 49 | `generate` | 모든 배포 모듈의 함수 설명을 버전이 적힌 단일 문서로 저장한다. |
| 73 | `main` | 현재 프로젝트 기준 함수 색인을 기본 파일명으로 생성한다. |

## `tools/write_manifest.py`

| 줄 | 함수 | 설명 |
|---:|---|---|
| 13 | `_sha256` | 큰 바이너리도 메모리를 많이 쓰지 않고 SHA-256을 계산한다. |
| 22 | `write_manifest` | 배포 루트 아래 모든 일반 파일을 정렬해 재현 가능한 목록으로 저장한다. |
| 45 | `main` | 명령행 인수로 받은 배포 루트와 버전에 대해 manifest를 생성한다. |

---

총 함수 수: **164**
