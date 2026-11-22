# Pilot Dataset 구축 결과 — Selected Validation Data Only

작성일: 2026-11-22 (KST)  
범위: 현재 서버에 존재하는 AI-Hub Validation master WAV와 대응 JSON만 사용

## 1. 결론

- 로컬 Validation label JSON 100개와 master WAV 33개를 전수 확인했다.
- WAV와 JSON이 Audio ID 기준으로 정확히 매칭된 **33개**만 `pilot_dataset.csv`에 포함했다.
- JSON만 있고 WAV가 없는 67개는 제외하고 `pilot_dataset_exclusions.csv`에 `no_local_wav`로 기록했다.
- WAV만 존재하는 항목, JSON parse 오류, 불완전 label, ID 충돌, 중복 label, byte-level 중복 WAV는 모두 0개다.
- 한국어 설명 33개를 생성했으며 모두 `needs_human_review`로 표시했다.
- 후속 H1 작업에서 Codex 기반 LLM으로 `en`과 `mt_kr` 33쌍을 생성했다. 자세한 절차와 변화는 `H1_TRANSLATION_REPORT.md`에 기록했다.
- 모든 33개에 label로 확인된 국악 악기명이 있어 H2 후보 문장 쌍을 생성했다. 의미 등가성은 모두 수동 검토가 필요하다.
- CLaMP 3, GPU, retrieval, MRR은 실행하지 않았고 추가 데이터도 다운로드하지 않았다.

## 2. WAV–JSON 감사 결과

| 점검 항목 | 결과 |
|---|---:|
| Validation JSON | 100 |
| 로컬 Validation master WAV | 33 |
| 정확 매칭 | 33 |
| JSON만 존재하여 제외 | 67 |
| WAV만 존재 | 0 |
| JSON parse 오류 | 0 |
| 불완전 label | 0 |
| Audio ID–WAV–JSON 불일치 | 0 |
| 중복 Audio ID / 충돌 label | 0 / 0 |
| SHA-256가 같은 중복 WAV | 0 |

33개 모두에서 JSON `project_name`, `master.file_name`, 실제 WAV basename이 NFC 정규화 후 동일했다. WAV는 모두 정상 개방되며 stereo, 48 kHz, 24-bit이고 JSON 선언값과 일치한다. 길이는 21.417–486.869초이며 합계는 약 106.3분이다.

라벨에는 매칭된 33곡에 대해 215개 stem이 선언되어 있지만 stem WAV 자체는 로컬에 없다. Pilot에는 master WAV만 포함하고, 악기 목록은 label의 `stems[].tags.instrumentSub`에서 순서를 유지해 중복 제거했다. 네 곡에서 같은 악기의 복수 stem이 선언되어 있어 선언 stem 215개와 고유 악기 출현 211개의 차이가 난다.

기존 `metadata.csv`는 33개 ID의 Validation split은 정확하지만, 이 WAV들이 추가되기 전 생성되어 `has_local_audio`와 `audio_path`가 현재 상태를 반영하지 않는다. 원본 파일과 기존 metadata는 수정하지 않았으며, Pilot 생성기는 현재 WAV/JSON을 직접 재검증한다.

## 3. 포함된 데이터와 장르 분포

| `genreSub` | 곡 수 | 포함 Audio ID 앞자리 |
|---|---:|---|
| 풍류음악 | 5 | 0004, 0012, 0049, 0058, 0066 |
| 궁중음악 | 5 | 0118, 0142, 0147, 0157, 0162 |
| 산조 | 5 | 0176, 0217, 0218, 0225, 0235 |
| 대풍류 | 3 | 0406, 0409, 0411 |
| 판소리 | 5 | 0439, 0446, 0470, 0474, 0480 |
| 민요 | 5 | 0736, 0737, 0739, 0740, 0747 |
| 창작국악 | 5 | 0812, 0825, 0833, 0835, 0842 |
| 합계 | 33 | |

상위 장르는 정악 10곡, 민속악 18곡, 창작국악 5곡이다.

## 4. 악기 분포

아래 수치는 stem 파일 수가 아니라 각 악기가 포함된 **곡 수**다.

| 악기 | 곡 수 | 악기 | 곡 수 |
|---|---:|---|---:|
| 대금 | 28 | 피리 | 28 |
| 해금 | 28 | 장구 | 25 |
| 아쟁 | 23 | 가야금 | 21 |
| 거문고 | 19 | 소금 | 8 |
| 좌고 | 8 | 소리북 | 5 |
| 양금 | 3 | 단소 | 2 |
| 박 | 2 | 방향 | 2 |
| 편경 | 2 | 편종 | 2 |
| 대고 | 2 | 목탁 | 1 |
| 바라 | 1 | 북 | 1 |

명시적인 `jangdan`, `장단`, `장단명` annotation은 33곡 모두 없다. `timeSignature`를 장단으로 추정하지 않았고 `jangdan` 컬럼은 전부 비워 두었다.

## 5. Native Korean Description

설명은 label의 `genreMajor`, `genreSub`, 고유 `instrumentSub`만 사용한 2문장 템플릿이다. 제목·분위기·박자처럼 설명에 꼭 필요하지 않은 속성은 추가하지 않았고, label 밖의 특징은 추측하지 않았다.

예시 (`0004_정악_풍류음악`):

> 이 곡은 정악에 속하는 풍류음악이다. 편성에는 대금·소금·아쟁·장구·좌고·피리·해금이 포함된다.

33개 설명 모두 연구자 검토 전 초안이므로 `review_status=needs_human_review`다.

## 6. H1 Translation Conditions

별도 번역 모델/API를 설치하지 않고 현재 Codex 세션으로 33개를 한국어→영어 번역한 뒤, 원문을 제공하지 않은 별도 컨텍스트에서 영어만 보고 한국어로 역번역했다.

- `en`, `mt_kr`: 33개 모두 채움
- `translation_model=Codex-based LLM (current session)`
- `translation_status=completed_codex_llm_needs_human_review`
- `h1_eligible=true`

H1 구조적 후보는 **33개**지만 연구자 검토 완료는 0개다. 번역 전 CSV는 `pilot_dataset.pre_h1.csv`에 보존했고, 상세 내용은 `H1_TRANSLATION_REPORT.md`를 참조한다.

## 7. H2 Culture-Specific Terminology

모든 매칭 label에 국악 악기가 있으므로 33개 모두 H2 구조적 후보로 표시했다. 한 문장에서는 한 target term만 바꾸고 나머지 구조를 동일하게 유지했다.

| Target | 곡 수 | Romanized | Descriptive |
|---|---:|---|---|
| 장구 | 25 | `This piece features a janggu.` | `This piece features a Korean hourglass-shaped drum.` |
| 소리북 | 5 | `This piece features a soribuk.` | `This piece features a Korean barrel drum.` |
| 대금 | 3 | `This piece features a daegeum.` | `This piece features a Korean transverse bamboo flute.` |

`h2_eligible=true`는 label에 target instrument가 있고 두 조건을 만들 수 있다는 뜻이다. 로마자 표기와 설명식 표현의 의미 등가성은 아직 사람이 승인하지 않았으므로 `h2_equivalence_status=needs_human_review`이고, 검토 완료 상태의 H2 데이터는 현재 **0개**다.

## 8. Pilot CSV 상태

| 상태 | 수량 |
|---|---:|
| Pilot 포함 행 | 33 |
| Native Korean Description 초안 | 33 |
| H1 구조적 후보 | 33 |
| H1 검토 완료 | 0 |
| H2 구조적 후보 | 33 |
| H2 검토 완료 | 0 |
| 수동 검토 필요 | 33 |

주요 컬럼 외에 audit와 실험 조건을 명확히 하기 위해 `label_path`, WAV header, SHA-256, matching/duplicate 상태, translation 상태, H1/H2 eligibility, H2 target term, review note를 추가했다.

## 9. 현재 데이터로 Retrieval 평가할 때의 한계

1. 33곡은 사용자가 직접 선정해 저장한 일부 Validation 데이터이므로 전체 1,004곡이나 확보 label 100개의 대표 표본이 아니다.
2. 장르별 수량이 3–5곡으로 작고 같은 장르·동일 편성의 설명이 반복되어 caption 구별력이 낮다.
3. 악기는 stem label로 확인했지만 실제 stem WAV는 없으며, master 안에서 악기의 청감상 존재 여부를 별도로 검수하지 않았다.
4. 명시적 장단, 구간 구조, 주법, 가사 annotation이 없어 설명에 포함하지 못한다.
5. 오디오 길이 차이가 약 21초에서 487초까지 커서 후속 embedding/extraction 정책의 영향을 받을 수 있다.
6. H1/H2 자연어 표현 33개 모두 수동 검토 전이다.
7. 현재 단계에서는 retrieval, cosine similarity, MRR 등 성능 계산을 하지 않았으므로 benchmark 품질이나 난이도를 판단할 수 없다.

## 10. 재현 및 산출물

원본 WAV/JSON을 읽기만 하는 재현 명령:

```bash
python3 scripts/build_pilot_dataset.py
```

산출물:

- `pilot_dataset.csv`: 실제 WAV–JSON이 매칭된 33개 Pilot 행
- `pilot_dataset_exclusions.csv`: WAV가 없어 제외한 Validation label 67개
- `scripts/build_pilot_dataset.py`: 매칭·검증·생성 재현 스크립트
- `PILOT_DATASET.md`: 본 감사 및 결과 요약
- `pilot_dataset.pre_h1.csv`: H1 번역 전 원본 백업
- `h1_translation_pairs.csv`: H1 검토용 native/EN/MT-KR 비교표
- `scripts/apply_h1_translations.py`: H1 pair를 백업본에 병합하는 스크립트
- `H1_TRANSLATION_REPORT.md`: H1 번역 방식과 변화 보고서
