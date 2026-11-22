# Pilot Dataset and Evaluation Validation

작성일: 2026-11-22 (KST)  
검증 범위: AI-Hub Validation에서 선택된 33개 음원과 기존 H1/H2 결과  
상태: **자동 검증 완료, 인간 검토 0/33**

## 1. 검증 범위와 방법

이번 단계에서는 CLaMP 3, GPU, 추가 모델 추론을 사용하지 않았다. `pilot_dataset.csv`, 원본 JSON, 로컬 Git LFS WAV 객체, 기존 결과 CSV, 저장된 33×33 cosine-similarity matrix만 읽었다. 기존 `pilot_dataset.csv`, `h1_retrieval_results.csv`, `h2_retrieval_results.csv`는 수정하지 않았다.

재현 스크립트는 `scripts/build_pilot_validation.py`이며 다음을 수행한다.

1. Audio ID, WAV, JSON, 장르, 제목, 악기, sample rate, bit depth, Native-KR, H2 target을 행별로 대조한다.
2. 실제 WAV 객체의 SHA-256과 RIFF/WAVE header를 확인한다.
3. 설명 중복, 번역 의미 변화, H2 표현의 자동 검토 상태를 기록한다.
4. 기존 similarity matrix로만 H1 group-candidate 및 H2 instrument-presence 민감도 분석을 계산한다.

검증 입력의 SHA-256은 다음과 같다.

| 파일 | SHA-256 |
|---|---|
| `pilot_dataset.csv` | `d2d34281542183ea67a6da3a3136f0ac715f4ce4dfd3a74753632bc5eecea84b` |
| `h1_retrieval_results.csv` | `79836960d7137ad5ae1428fba3c8985c31b4f5f6b734e6a952b00bf038132ba2` |
| `h2_retrieval_results.csv` | `c9b46d76fc443df5afc4b4b258617a47f842c85462e97ec82d2b8130af7afb4e` |

## 2. WAV–JSON–CSV 일치성

| 검증 항목 | 결과 |
|---|---:|
| Pilot 행 / 고유 Audio ID | 33 / 33 |
| 정확히 대응하는 WAV–JSON | 33 / 33 |
| 행별 Label 필드 검사 | 13개 × 33행 = 429 / 429 통과 |
| WAV SHA-256 및 RIFF/WAVE header | 33 / 33 통과 |
| SHA-256가 서로 다른 WAV | 33 / 33 |
| RIFF/WAVE 형식 | 33 / 33 |
| 불완전 Label / ID 충돌 / byte-identical WAV 중복 | 0 / 0 / 0 |

WAV worktree 항목은 Git LFS pointer이며 실제 LFS 객체 33개가 모두 존재했다. pointer OID, `audio_sha256`, 실제 객체 SHA-256가 전부 일치했다. 전체 WAV 크기는 1,846,316,564 bytes이고 총 길이는 6,376.836초(약 106.3분)이다. 모두 stereo, 48 kHz, 24-bit이다.

Pilot 구축 당시 local Validation JSON은 100개였고, 그중 실제 WAV가 확보된 33개만 포함했으며 WAV가 없는 67개 Label은 제외했다. 이번 검증은 포함된 33개를 전수 재감사한 결과다.

## 3. Label과 Native Korean Description

Native-KR은 Label의 `genreMajor`, `genreSub`, stem별 `instrumentSub` 전체 목록으로 생성됐다. 33개 모두 현재 Label에서 동일 문장을 재생성할 수 있었다.

| Genre | 수 |
|---|---:|
| 풍류음악 | 5 |
| 궁중음악 | 5 |
| 산조 | 5 |
| 대풍류 | 3 |
| 판소리 | 5 |
| 민요 | 5 |
| 창작국악 | 5 |

Label상 주요 악기 출현은 대금·피리·해금 각 28개, 장구 25개, 아쟁 23개, 가야금 21개, 거문고 19개, 소리북 5개이다. 33개 모두 명시적 장단 annotation이 없어 설명에 장단을 넣지 않았다. `timeSignature`를 장단으로 추정하지도 않았다.

따라서 **Label 문자열과 Native-KR의 자동 일관성은 높다.** 다만 자동 검증은 실제 오디오에서 해당 악기가 청감상 존재하거나 두드러지는지 확인하지 않는다. `native_label_consistency`는 모두 `auto_verified_label_match_needs_human_review`이며 인간 검토 완료로 표시한 항목은 없다.

## 4. H1 번역 의미 검토

Native-KR, EN, MT-KR의 고유 문장은 조건별 17개다. MT-KR은 33개 모두 원문의 악기 정체성과 목록을 보존했지만 Native-KR과 문자열이 완전히 같은 행은 없다.

| 자동 분류 | 수 | 판단 |
|---|---:|---|
| 표면 변화 | 10 | `풍류음악→풍류 음악`, `궁중음악→궁중 음악`, 목록 구두점 변화 중심 |
| 장르 용어 일반화 | 18 | `민속악→folk music→민속 음악`; 전문 분류가 일반 표현으로 넓어질 수 있음 |
| 의미 범위 변화 | 5 | `창작국악→contemporary gugak→현대 국악`; 두 범주가 완전히 동일하다고 보기 어려움 |

H1 입력은 번역 과정에서 악기를 잃지는 않았으나, 번역에 따른 성능 차이를 순수한 “정보 손실”로만 해석할 수 없다. 특히 23개 행의 장르 용어 변화는 사람이 의미 등가성을 확인해야 한다.

## 5. H2 용어와 의미 등가성

H2 문장은 모두 `This piece features a <target noun phrase>.` 형식이며 두 조건은 target noun phrase만 다르다. target은 해당 행의 Label 악기 목록에 33/33 존재했다.

| 용어 | Target 배정 행 | Label 내 실제 출현 | 표현 쌍 | 자동 판단 |
|---|---:|---:|---|---|
| 장구 | 25 | 25 | `janggu` ↔ `Korean hourglass-shaped drum` | 가장 타당하나 사람 검토 전 |
| 소리북 | 5 | 5 | `soribuk` ↔ `Korean barrel drum` | 설명식 표현이 지나치게 넓음 |
| 대금 | 3 | 28 | `daegeum` ↔ `Korean transverse bamboo flute` | 악기 계열은 맞지만 대금을 고유하게 구별하지 못함 |

국립국악원 자료는 장구를 hourglass-shaped drum으로 설명하므로 장구 쌍은 형태 수준에서 가장 강하다. 소리북은 판소리에서 고수가 사용하는 북이라는 맥락과 못고정식 양면 북이라는 구별점이 있는데 `Korean barrel drum`은 이를 생략한다. 대금은 가로로 부는 큰 대나무 관악기이며 청공·청의 특성이 있으므로 `Korean transverse bamboo flute`은 상위 범주 설명으로는 타당하지만 충분히 고유하지 않다.

참고 자료: [국립국악원 장구](https://www.gugak.go.kr/site/program/board/basicboard/view?boardid=48346&boardtypeid=58&currentpage=1&lang=en&menuid=001005006001&pagesize=30&searchselect=all&searchword=), [국립국악원 국악사전 소리북](https://www.gugak.go.kr/ency/topic/view/2124), [국립부산국악원 대금](https://www.busan.gugak.go.kr/ENG/contents/ENG0301000000.do).

이 검토는 표현을 수정하지 않고 불확실성을 표시한 것이다. 기존 H2 실험 입력을 사후 보정하지 않았다.

## 6. 동일·중복 Query 분포

H1의 33개 행은 `(genre_major, genre, unordered instrument set)` 기준으로 17개 그룹이다.

| 그룹 크기 | 그룹 수 | 포함 행 수 |
|---:|---:|---:|
| 1 | 9 | 9 |
| 2 | 4 | 8 |
| 3 | 2 | 6 |
| 5 | 2 | 10 |
| 합계 | 17 | 33 |

중복 그룹 8개는 다음과 같다.

- `0004/0058`, `0012/0049`, `0157/0162`
- `0176/0217/0218`, `0225/0235`, `0406/0409/0411`
- `0439/0446/0470/0474/0480`
- `0736/0737/0739/0740/0747`

같은 H1 그룹 안에서는 Native-KR/EN/MT-KR이 각각 완전히 동일하다. 따라서 33-query MRR은 독립적인 문장 33개 평균이 아니라, 17개 문장을 그룹 크기로 반복 가중한 평균이다.

H2는 더 제한적이다. 조건별 고유 텍스트가 `janggu`, `soribuk`, `daegeum`의 **3개뿐**이다. 같은 target 행은 수치 반올림 오차 범위에서 같은 similarity ranking을 공유한다. 따라서 H2의 “33-query” 결과나 23행 개선/10행 악화는 33개의 독립 언어 사례로 셀 수 없다.

## 7. 정답 집합 타당성

### H1

동일 설명이 여러 오디오를 지칭하므로 단일 Audio ID만 정답으로 두는 것은 부당하다. 같은 장르 대분류·세부 장르·전체 악기 집합을 공유하는 오디오를 모두 positive로 둔 multi-positive 정의는 **현재 설명이 제공하는 정보와 일치한다는 점에서 방어 가능**하다.

그러나 이는 Label-equivalence이지 perceptual relevance가 아니다. 제목, 장단, 선율, 구간, 분위기를 설명에 쓰지 않았으므로 같은 그룹 안의 특정 오디오를 고유하게 지정할 수 없다. 현재 Label과 설명만으로 audio-specific 유일 정답은 정의할 수 없다.

### H2

17개 H1 metadata group을 H2 정답에 재사용하면 H2 문장에 없는 장르와 전체 편성을 요구하므로 under-specified proxy가 된다. 반대로 target instrument가 있는 모든 오디오를 positive로 두면 문장 의미에는 맞지만 장구 25/33, 대금 28/33이 positive여서 first-positive MRR에 강한 ceiling effect가 생긴다.

따라서 현재 H2에는 완전히 만족스러운 retrieval ground truth가 없다. metadata proxy 결과는 형식 비교용 잠정 결과, instrument-presence 결과는 정답 정의 민감도 분석으로만 해석해야 한다.

## 8. 현재 결과의 신뢰 수준

| 신뢰 수준 | 신뢰 가능한 내용 / 주의할 내용 |
|---|---|
| 높음 | 33개 WAV–JSON–CSV 일치, 저장된 similarity와 rank 재현, 조건별 동일 후보군·정답을 사용한 paired 비교, H1 결과가 그룹 가중과 `0066`에 민감함 |
| 중간 | 이 33개 후보 안에서 H2 표현 변경이 candidate ordering을 크게 바꾼다는 관찰 |
| 낮음 | 특정 언어나 H2 표현의 일반적 우월성, 전체 국악으로의 일반화, Label 일치가 청감 relevance를 보장한다는 해석 |

H1과 H2 모두 가설을 지지하거나 기각할 충분한 증거는 없다. 더 정확한 표현은 “현재 Pilot에서 안정적인 방향을 검출하지 못했다”이다.

## 9. Human Review 자료

`pilot_review.csv`에 33개 행을 저장했다. 각 행에는 원문·번역·H2 쌍, 세 가지 자동 검토 상태, 중복 그룹 크기, 청감 검증 미완료 메모가 포함된다.

- `review_status=needs_human_review`: 33/33
- `review_status=reviewed`: 0/33
- 자동 검증 결과를 인간 검토 완료로 승격한 행: 0

권장 수동 검토는 서로 배타적인 행 분할이 아니라 다음 순서의 검토 pass다: (1) 창작국악 5개, (2) 민속악 18개, (3) 소리북 target 5개, (4) 대금 target 3개, (5) 장구 target 25개. 같은 행이 장르 pass와 H2 용어 pass에 중복될 수 있다. 실제 오디오를 듣고 악기 존재·두드러짐과 positive relevance까지 별도로 판정해야 retrieval ground truth를 강화할 수 있다.

## 10. 산출물

- `pilot_review.csv`: 수동 검토용 33행
- `artifacts/pilot_validation/metrics.json`: 입력 hash, 자동 감사, no-GPU 보조 지표
- `artifacts/pilot_validation/h1_group_candidate_results.csv`: 17×17 group-candidate 민감도 분석
- `artifacts/pilot_validation/h2_term_detection_results.csv`: 고유 용어 3개의 AUROC/AP와 ranking 안정성
- `scripts/build_pilot_validation.py`: 재현 스크립트

재현 명령:

```bash
python3 scripts/build_pilot_validation.py
```

이 명령은 모델 추론이나 GPU를 사용하지 않으며, 기존 실험 결과 파일을 변경하지 않는다.
