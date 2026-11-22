# H2 Culture-Specific Sensitivity Pilot Experiment

작성일: 2026-11-22 (KST)  
상태: **잠정 결과 — 모든 표현의 사람 검토가 완료되지 않음**

## 1. 결론

기존 CLaMP 3 SAAS Audio Embedding 33개를 재사용하고, `romanized_en`과 `descriptive_en` Text Embedding만 각각 33개 실제 추출했다. H1과 형식을 맞춘 17개 metadata-group proxy 정답에서 결과는 다음과 같다.

| 분석 단위 | Romanized-EN | Descriptive-EN | ΔMRR (Romanized − Descriptive) |
|---|---:|---:|---:|
| 33-query MRR | 0.192036 | 0.188851 | **+0.003184** |
| 17-group Macro-MRR | 0.157766 | 0.181487 | **-0.023721** |

Query-level에서는 Romanized가 아주 조금 높지만, 각 그룹을 동일 가중하면 Descriptive가 높아져 방향이 뒤집힌다. 17-group paired bootstrap의 95% CI는 **[-0.142128, 0.127176]**으로 매우 넓고 0을 포함한다. 따라서 어느 표현이 우세하다는 확정적 결론을 내릴 수 없다.

더 근본적인 문제는 H2 문장이 목표 악기 하나만 언급한다는 점이다. 조건별 고유 문장은 `janggu`, `soribuk`, `daegeum`의 **3개뿐**이며, H1의 장르·전체 편성 17개 그룹을 구분할 정보가 문장에 없다. 본 보고서는 17-group 결과를 H1 비교용 **under-specified proxy**로 명시하고, 악기 존재 자체를 정답으로 삼는 보조 분석을 함께 제시한다.

## 2. H2 설명 감사

기존 `pilot_dataset.csv`에는 두 조건이 이미 33/33 저장돼 있었다. 이번 작업에서는 문장을 변경하지 않고 label 및 template과 전수 대조했다.

| Target | Target 배정 행 | Label 내 실제 출현 | Romanized | Descriptive | 자동 감사 |
|---|---:|---:|---|---|---|
| 장구 | 25 | 25 | `janggu` | `Korean hourglass-shaped drum` | 가장 명확하지만 사람 검토 전 |
| 소리북 | 5 | 5 | `soribuk` | `Korean barrel drum` | 표현이 너무 넓어 우선 검토 필요 |
| 대금 | 3 | 28 | `daegeum` | `Korean transverse bamboo flute` | 다른 한국 횡적과 구별되지 않아 검토 필요 |

모든 문장은 아래 구조이며 target noun phrase만 바뀐다.

```text
This piece features a <target noun phrase>.
```

- target term이 해당 행의 label instrument에 존재: 33/33
- 원문에 없는 곡별 특징 추가: 0
- `h2_equivalence_status=needs_human_review`: 33/33
- `review_status=needs_human_review`: 33/33
- 사람 검토 완료로 자동 승격한 행: 0

용어 의미는 공신력 있는 자료와 대조했다. 국립국악원은 장구를 hourglass-shaped drum으로 소개하며, 대금은 국립국악원 자료에서 큰 가로형 대나무 관악기로 설명된다. 소리북은 국립국악원 국악사전상 판소리 고수가 사용하는 못고정식 양면 북이므로 단순한 `Korean barrel drum`은 형태 범주만 전달하고 용도와 구별 특징을 잃는다. ([장구](https://www.gugak.go.kr/site/program/board/basicboard/view?boardid=48346&boardtypeid=58&currentpage=1&lang=en&menuid=001005006001&pagesize=30&searchselect=all&searchword=), [대금](https://www.busan.gugak.go.kr/ENG/contents/ENG0301000000.do), [소리북](https://www.gugak.go.kr/ency/topic/view/2124))

기존 condition을 사후 보정하면 실험 입력이 달라지므로 문장은 그대로 유지하고 이 불확실성을 결과에 표시했다.

## 3. 모델 및 실행 환경

| 항목 | 실제 실행 값 |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Ti, 16,380 MiB |
| Driver / 표시 CUDA | 595.99.02 / CUDA 13.2 |
| Python | 3.11.17 |
| PyTorch | 2.3.0+cu118 |
| Transformers / Accelerate | 4.40.0 / 0.34.0 |
| NumPy | 1.26.4 |
| CLaMP 3 | 공식 repository commit `9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8` |
| Model | Pretrained CLaMP 3 SAAS, checkpoint epoch 10 |
| Text encoder | `FacebookAI/xlm-roberta-base` |

Fine-tuning, training, H2 Audio Embedding 재추출, MERT 실행은 하지 않았다. H1의 기존 Audio Embedding 33개를 그대로 로드했다.

## 4. Embedding 검증

| Modality / condition | 파일 수 | Shape | dtype | NaN | Inf |
|---|---:|---|---|---:|---:|
| Audio, H1에서 재사용 | 33 | `(1, 768)` | `float32` | 0 | 0 |
| Romanized-EN Text | 33 | `(1, 768)` | `float32` | 0 | 0 |
| Descriptive-EN Text | 33 | `(1, 768)` | `float32` | 0 | 0 |

99개 검증 대상의 L2 norm은 `2.162097`–`17.651791`이고 zero vector는 없다. 두 H2 Text Encoder 실행의 GPU 메모리 측정값은 다음과 같다.

- idle 최소: 48 MiB
- 관측 최대: **2,090 MiB**
- idle 대비 최대 증가: 2,042 MiB
- 16 GB 제한 대비 최대 사용률: 약 12.8%

## 5. 정답 정의

두 조건은 항상 같은 Candidate set과 같은 positive set을 사용했다. Cosine similarity, tie 처리, first-positive rank 계산은 H1과 동일하다.

### A. 17-group proxy — 주 분석

```text
(genre_major, genre, unordered validated instrument set)
```

- H1과 동일한 17개 그룹이라 직접적인 형식 비교가 가능
- 그룹 내 모든 audio를 positive로 처리
- 그러나 H2 query에는 장르와 전체 악기 구성이 없으므로 정답이 과도하게 좁음
- 따라서 H2 가설 검증의 확정적 ground truth가 아니라 잠정 proxy

### B. Target-instrument presence — 보조 민감도 분석

```text
query target instrument가 validated label instrument set에 있는 모든 candidate
```

- 장구 positive: 25개
- 소리북 positive: 5개
- 대금 positive: 28개

문장 의미에는 더 충실하지만 positive가 너무 많아 retrieval이 쉬워지고, 특히 대금은 33개 중 28개가 positive여서 ceiling effect가 심하다. 두 정의 모두 한계가 있으므로 결과를 함께 제시한다.

## 6. 17-group proxy 결과

### 전체 및 그룹 동일 가중

| 지표 | Romanized | Descriptive | Δ |
|---|---:|---:|---:|
| 33-query MRR | 0.192036 | 0.188851 | +0.003184 |
| 17-group Macro-MRR | 0.157766 | 0.181487 | -0.023721 |
| 3-term equal-weight Macro-MRR | 0.141974 | 0.174617 | -0.032643 |

Group-level ΔMRR bootstrap:

- estimate: `-0.023721`
- 95% percentile CI: **[-0.142128, 0.127176]**
- paired resampling unit: 17 metadata groups
- replicates: 100,000
- seed: `20261122`

### 용어별 결과

| Term | Query 수 | Group 수 | Romanized query MRR | Descriptive query MRR | Query Δ | Romanized group MRR | Descriptive group MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| 장구 | 25 | 13 | 0.216986 | 0.196691 | +0.020295 | 0.180072 | 0.187472 |
| 소리북 | 5 | 1 | 0.142857 | 0.166667 | -0.023810 | 0.142857 | 0.166667 |
| 대금 | 3 | 3 | 0.066080 | 0.160494 | -0.094414 | 0.066080 | 0.160494 |

장구는 Query-level에서 Romanized가 높지만 13개 그룹 동일 가중에서는 Descriptive가 약간 높다. 소리북은 한 그룹뿐이므로 변동성을 추정할 수 없다. 대금은 3개 query/그룹뿐이며 Descriptive가 높지만 표본 수와 정답 모호성이 매우 크다.

## 7. Target-presence 보조 결과

| 지표 | Romanized | Descriptive | Δ |
|---|---:|---:|---:|
| 33-query 가중 MRR | 0.809524 | 0.873737 | -0.064214 |
| 3-term 동일 가중 Macro-MRR | 0.492063 | 0.722222 | -0.230159 |

| Term | Positive 수 | Romanized MRR | Descriptive MRR |
|---|---:|---:|---:|
| 장구 | 25 | 1.000000 | 1.000000 |
| 소리북 | 5 | 0.142857 | 0.166667 |
| 대금 | 28 | 0.333333 | 1.000000 |

이 정의에서는 Descriptive가 높지만, 장구가 양 조건 모두 rank 1이고 대금의 positive 비율이 28/33이므로 절대 MRR이 과도하게 높다. 3개 용어만으로 계산한 term macro 역시 통계적 검증값이 아니라 정답 정의 민감도 예시다.

## 8. 대표적인 순위 변화

17-group proxy에서 `descriptive_rank - romanized_rank` 기준으로 Descriptive 개선 23개, 동일 0개, 악화 10개였으며 최대 절대 변화는 24칸이다.

| Query/group | Target | Romanized rank | Descriptive rank | 변화 | 관찰 |
|---|---|---:|---:|---:|---|
| `0004/0058_정악_풍류음악` | 장구 | 27 | 3 | -24 | Descriptive가 크게 개선 |
| `0176/0217/0218_민속악_산조` | 장구 | 1 | 20 | +19 | Descriptive가 크게 악화 |
| `0812_창작국악_창작국악` | 장구 | 22 | 4 | -18 | Descriptive 개선 |
| `0066_정악_풍류음악` | 장구 | 13 | 30 | +17 | Descriptive 악화 |
| `0142_정악_궁중음악` | 장구 | 33 | 18 | -15 | Descriptive 개선 |
| `0835_창작국악_창작국악` | 대금 | 12 | 3 | -9 | Descriptive 개선 |

같은 target의 모든 query는 완전히 같은 text embedding과 candidate ranking을 공유한다. 위 그룹별 rank 차이는 query 문장이 그룹을 구별해서가 아니라, 동일한 ranking에서 각 그룹의 positive set이 처음 나타나는 위치가 다르기 때문에 발생한다. 이를 개별 곡에 대한 언어 이해 차이로 해석하면 안 된다.

## 9. 디스크 및 실행 관리

- 실험 전 overlay 여유: 8.4 GB
- 기존 Audio Embedding: 33개 전부 재사용, 재추출 0개
- H2 Text Embedding: 66개 신규 생성
- Python text-only environment: 실행 중 약 5.3 GB
- SAAS/XLM-R/download cache: `/dev/shm`에만 저장
- `torchaudio`, `torchvision`, MERT: 설치·다운로드·실행하지 않음
- 추가 WAV 또는 데이터셋 다운로드: 없음
- 완료 후 가상환경, 관리 Python, RAM model/cache 제거
- 실험 후 overlay 여유: **8.3 GB** (49% 사용), `/dev/shm` 23 GB 전체 여유
- 최종 H2 artifact: 약 604 KB
- 기존 `pilot_dataset.csv`와 `h1_retrieval_results.csv`: 수정하지 않음

## 10. 한계

1. 조건별 실제 고유 문장은 3개뿐이며, 33개 독립 query가 아니다.
2. 17-group proxy는 H2 문장에 없는 장르·전체 편성을 정답 구분에 사용한다.
3. Target-presence 정의는 positive가 너무 많아 ceiling effect가 생긴다.
4. 장구 25개, 소리북 5개, 대금 target 3개로 심하게 불균형하다.
5. 소리북 descriptive phrase는 지나치게 넓고, 대금 phrase도 고유 구별력이 부족하다.
6. 17개 bootstrap unit만 있으며, 같은 target의 그룹들이 동일 text embedding을 공유해 독립성도 제한된다.
7. Label상 악기 존재를 사용했으며 실제 audio에서 악기가 청감상 두드러지는지 별도 검수하지 않았다.
8. 두 정답 정의에서 결론 크기와 방향이 달라질 수 있으므로 H2 가설 검증은 잠정적이다.

## 11. 산출물

- `h2_retrieval_results.csv`: query별 두 조건 rank/RR, group, 두 positive 정의 결과, 검토 상태
- `artifacts/h2_retrieval/embeddings/text/romanized_en/`: 33개
- `artifacts/h2_retrieval/embeddings/text/descriptive_en/`: 33개
- `artifacts/h2_retrieval/similarity/`: 두 33×33 cosine matrix
- `artifacts/h2_retrieval/embedding_validation.csv`: 재사용 audio와 H2 text 검증
- `artifacts/h2_retrieval/description_audit.json`: H2 문장과 label 감사
- `artifacts/h2_retrieval/metrics.json`: 전체·group·term별 지표와 bootstrap
- `scripts/run_h1_robustness_h2.py`: 준비·평가·H1 추가 분석 코드
- `H2_EXPERIMENT_REPORT.md`: 본 보고서

재평가 명령:

```bash
# 기존 H2 문장 검증 및 text input 재생성
python3 scripts/run_h1_robustness_h2.py prepare-h2

# CLaMP 3/NumPy 환경에서 저장된 embedding으로 평가
python scripts/run_h1_robustness_h2.py evaluate-h2
```
