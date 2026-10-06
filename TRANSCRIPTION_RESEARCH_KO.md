# 채보 정확도 개선 조사 · v0.1.01

## 2026-10-06 적용 기록

사용자 선택에 따라 실제 librosa CQT를 기본 코드 frontend로 도입했습니다.
원본 전체 음원 → 채널별 CQT magnitude RMS → 배음/타악기 마스크 →
옥타브 통합 chroma → 41종 화음 템플릿 → 인접 창의 작은 전이 비용 경로입니다.
고정 440 Hz 기준이며 자동 조율 추정이나 학습된 Bayesian/HMM은 아닙니다.
원본 믹스의 slash bass도 후보로 유지하되 실제 베이스 악기의 확정 채보는 아닙니다.

- 합성 246개 (41유형 × 3근음 × 2음색): FFT/CQT 모두 246개 대표 기호 일치.
  합계 시간 FFT 7.825초, CQT 31.014초. 고정 회귀 검사이지 실곡 정확도가 아닙니다.
- Room 335 원본 30–90초: CQT 4.974초, FFT 1.014초. 검출 구간 비율은 각각
  0.2323/0.4242로 다릅니다. 정답 주석이 없어 어느 쪽이 더 정확한지 결론낼 수 없습니다.
- C6/Am7 등 동일 피치 집합은 근거와 후보를 함께 제공하며 사용자가 직접 고칠 수 있습니다.
- Reddit 게시물의 CQT/chroma 설명은 댓글 작성자의 경험입니다. Chord AI 내부 구현을
  입증하지 않으며, 댓글에서 언급한 베이지안 접근도 실제 구현되었다는 뜻이 아닙니다.
  연결된 GPL 코드는 복사하지 않았습니다.

1차 자료:

- [librosa CQT 0.11](https://librosa.org/doc/0.11.0/generated/librosa.cqt.html)
- [CQT chroma](https://librosa.org/doc/0.11.0/generated/librosa.feature.chroma_cqt.html)
- [FMP 화음 템플릿](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C5/C5S2_ChordRec_Templates.html)
- [FMP HMM 비교](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C5/C5S3_ChordRec_HMM.html)
- [FMP 배음/타악기 분리](https://audiolabs-erlangen.de/resources/MIR/FMP/C8/C8S1_HPS.html)

## 아래는 v0.0.13 당시 조사 기록 (현행 구현과 구별)

조사일: 2026-10-04. 아래는 1차 자료를 바탕으로 한 구현 방향 검토입니다.
논문의 실험 성능을 ToneMatch TMP의 성능으로 인용하지 않습니다.

## 현재 코드에서 확인한 사실

- v0.0.12의 41종 화음 템플릿은 사전 전용이 아니라 실제 오디오 후보 비교에 사용됩니다.
- 악기별 신경망 채보 모델 41개를 추가한 것은 아닙니다. 기타 운지 후보는 종전
  major/minor/7/maj7/min7/power5의 E형·A형 바레 6계열만 지원했습니다.
- v0.0.13은 38유형 × 12근음에 대해 모든 구성음을 담는 표준 EADGBE 운지 후보를
  지원합니다. 기존 6계열은 유지하고 나머지는 제한된 프렛 탐색을 사용합니다.
  후보는 실제 녹음의 손가락·현·프렛을 검출한 결과가 아닙니다.
- 13/maj13/min13의 완전 템플릿은 피치 클래스가 7개이므로 6현에 모두 담을 수 없습니다.
  음을 임의로 생략하지 않고 그림을 비웁니다. 실제 연주용 생략음 보이싱은 후속 범위입니다.
- 현재 오디오 분석은 1.2초 창 / 0.6초 간격의 스펙트럼 근거와 시간 연결입니다.
  짧은 코드 변화, 왜곡·배음, 다른 악기 누출, 생략음 때문에 틀리거나 미확정일 수 있습니다.

## 조사한 알고리즘

| 접근 | 원 자료에서 확인한 내용 | 적용 판단 |
|---|---|---|
| NNLS Chroma / Chordino | 조율 보정·스펙트럼 whitening 후 배음 사전을 사용한 NNLS로 음 활동을 추정하고 저음/중고음 chroma를 분리합니다. Chordino는 사전 비교와 시간 평활화를 제공합니다. | 현행 피크 비교의 대안으로 동일 PCM 비교 실험 가치가 있습니다. 외부 코드를 도입하지 않았으며 라이선스·Windows 빌드 검토가 선행되어야 합니다. |
| Beat-synchronous chord evidence | Essentia ChordsDetectionBeats는 PCP와 beat timestamps를 입력받아 박 사이 median 또는 첫 프레임을 사용합니다. 문서는 해당 알고리즘을 실험적이라고 설명합니다. | 먼저 박/다운비트 품질을 평가해야 합니다. 거친 BPM 하나만으로 박 검출을 구현했다고 주장할 수 없습니다. |
| Deep Chroma | 시간 문맥을 이용해 화음에 필요한 chroma 특징을 학습하고 방해 성분을 줄이는 연구입니다. | 학습 가중치·코드·라이선스·의존성·Windows CPU 시간·지원 화음 사전을 별도로 검증해야 합니다. |
| Duration + harmonic language models | 프레임 수준 결과와 화음 시퀀스 사이를 지속시간 모델로 연결하고 화성 언어 모델을 분리한 실험입니다. | 문맥은 단발 오탐 감소에 도움이 될 가능성이 있지만, 없는 음을 추정으로 채우는 위험도 평가해야 합니다. |

출처:

- [NNLS Chroma / Chordino 원 구현 설명](https://github.com/c4dm/nnls-chroma/blob/master/README)
- [Essentia ChordsDetectionBeats 공식 문서](https://essentia.upf.edu/reference/std_ChordsDetectionBeats.html)
- [Korzeniowski & Widmer, Feature Learning for Chord Recognition: The Deep Chroma Extractor (2016)](https://arxiv.org/abs/1612.05065)
- [Korzeniowski & Widmer, Improved Chord Recognition by Combining Duration and Harmonic Language Models (2018)](https://arxiv.org/abs/1808.05335)

## 이번 버전에 적용한 것과 적용하지 않은 것

이번 적용은 코드표 UI, 기타 이론 운지 후보 확대, 긴 곡의 이벤트 보존입니다.
새 신경망이나 NNLS/Chordino를 통합하지 않았고 오디오 후보 판정 임계값을 낮추지
않았습니다. 이벤트 기본 상한만 96→4096으로 늘려 기존 검출 결과가 표시 한도 때문에
미확정으로 바뀌는 경우를 줄입니다. 이는 새로운 정확도 측정 결과가 아닙니다.

16마디 표는 4마디 × 4줄의 일정 템포 격자입니다. 기존 BPM 추정값을 시작값으로
사용하되 BPM·마디당 박 수·분석 구간 기준 첫 마디 시작(초)을 사용자가 보정합니다.
첫 마디 이전 구간, 마디 경계를 넘는 코드, 한 마디의 여러 변화와 미확정 구간을
보존합니다. 변박·루바토·스윙의 정확한 리듬 채보, 자동 다운비트, 가사와 카포
자동 검출은 구현하지 않았습니다. 풀믹스 화성에는 기타 운지를 붙이지 않습니다.

## 후속 실험 제안 (아직 구현/검증하지 않음)

1. 권한 있는 음원에 시간 정렬된 정답 코드·박·다운비트를 독립 주석합니다.
   Room 335 실행 성공이나 검출 구간 비율은 정답 코드가 없어 정확도 지표로 쓰지 않습니다.
2. 근음/장단조/7화음/확장화음 수준을 구분하고 같은 피치 집합의 여러 이름을 처리할
   기준을 고정합니다. 곡별 분리된 개발/평가 세트로 곡 기억 효과를 방지합니다.
3. 동일 원본/동일 기타 stem에서 현행, NNLS 계열, Deep Chroma 계열을 비교합니다.
   시간 가중 코드 일치율, 미확정 비율, 경계 오차를 함께 보고합니다.
4. 박 추적을 먼저 평가한 뒤 박 동기 근거 집계와 지속시간 모델을 별도로 비교합니다.
   한 요소씩 추가해 어떤 변경이 결과를 개선하거나 악화했는지 확인합니다.
5. CPU 처리 시간·메모리·포터블 설치·취소·오프라인 캐시·라이선스도 릴리스 게이트에 포함합니다.

이 순서는 조사 내용을 바탕으로 한 개발 제안이지, 특정 알고리즘이 이 음원에서
반드시 더 정확하다는 결론은 아닙니다.
