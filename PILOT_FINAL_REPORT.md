# A Pilot Evaluation of Cross-Lingual and Culture-Specific Semantic Understanding in Korean Traditional Music

작성일: 2026-11-22 (KST)  
연구 상태: **Selected Validation Data Pilot; human review pending**

## Abstract

본 Pilot은 국악 음악–언어 검색에서 번역이 유발하는 성능 변화(H1)와 국악 고유 용어의 로마자/설명식 표현에 대한 민감도(H2)를 CLaMP 3 SAAS zero-shot text-to-audio retrieval로 조사했다. AI-Hub Validation에서 실제 WAV와 JSON이 일치하는 33곡을 사용했고 추가 학습은 하지 않았다. H1의 Native-KR/EN/MT-KR 33행 MRR은 각각 0.166691/0.226806/0.169167이었으며, 중복 설명을 동일 가중한 17-group Macro-MRR은 0.118368/0.221191/0.126099였다. Native-KR−MT-KR의 group bootstrap 95% CI는 [-0.030493, 0.007413]으로 0을 포함했다. H2의 Romanized/Descriptive 17-group Macro-MRR은 0.157766/0.181487였으나 차이의 95% CI [-0.142128, 0.127176]도 0을 포함했고, 실제 고유 텍스트는 조건별 3개뿐이었다. 따라서 이 Pilot은 안정적인 H1 성능 저하나 H2 표현 우열을 확인하지 못했다. 대신 중복 설명, Label 기반 정답, positive 비율, 사람 검토 전 의미 등가성이 결론을 크게 좌우한다는 평가 설계상의 문제를 확인했다.

## 1. Research Overview

### 1.1 연구 질문

연구 질문은 “국악 설명의 번역과 문화 고유 용어의 영어 표현 방식이 음악–텍스트 검색에 어떤 영향을 주는가?”이다.

- **H1, Translation-Induced Degradation:** Native Korean을 영어로 번역한 뒤 다시 한국어로 역번역하면 Native-KR보다 retrieval 성능이 낮아질 것이라는 방향성 가설.
- **H2, Culture-Specific Sensitivity:** `janggu/soribuk/daegeum` 같은 로마자 표현과 설명식 영어 표현 사이에서 retrieval 결과가 달라질 것이라는 비방향성 가설.

Pretrained multimodal model이 국악을 얼마나 “이해한다”고 일반적으로 주장하는 것이 목적이 아니라, 선택된 소규모 데이터에서 controlled comparison pipeline과 평가 설계의 문제를 확인하는 것이 이번 단계의 목적이다.

### 1.2 핵심 결과

H1의 예상 방향인 `MRR(Native-KR) > MRR(MT-KR)`는 관찰되지 않았다. 차이는 작고 bootstrap CI가 0을 포함하며 한 singleton group 제외 시 부호가 바뀐다. H2는 표현에 따라 candidate ordering이 크게 달라졌지만, 어느 표현이 더 우수한지는 weighting과 정답 정의에 따라 방향이 바뀌었다. 따라서 **두 가설 모두 현재 Pilot에서 미해결**이다.

## 2. Dataset

### 2.1 음원과 Label

AI-Hub 「국악합주곡 디지털 음원 데이터」의 선택된 Validation 자료만 사용했다. 100개 local JSON 중 정확히 대응하는 WAV가 있는 33개만 포함했고, WAV가 없는 67개 Label은 제외했다. 추가 데이터는 다운로드하지 않았다.

| 항목 | 값 |
|---|---:|
| 음원 / 고유 Audio ID | 33 / 33 |
| 총 길이 | 6,376.836초, 약 106.3분 |
| WAV 형식 | stereo, 48 kHz, 24-bit |
| Label 필드 자동 검사 | 13개 × 33행 = 429/429 통과 |
| WAV SHA-256/header 검사 | 33/33 통과 |
| byte-identical WAV 중복 | 0 |
| 명시적 장단 annotation | 0/33 |

장르 분포는 풍류음악 5, 궁중음악 5, 산조 5, 대풍류 3, 판소리 5, 민요 5, 창작국악 5이다.

### 2.2 Description 구성

Native-KR은 Label의 장르 대분류·세부 장르와 전체 `instrumentSub` 목록으로 1–2문장을 생성했다. 33개 모두 현재 Label에서 같은 문장을 재생성할 수 있다. EN은 Codex 기반 LLM으로 Native-KR을 번역했고, MT-KR은 EN만 보고 역번역했다. 외부 번역 API나 별도 번역 모델을 사용하지 않았다.

H2는 Label에 실제 존재하는 target 한 개를 선택하고 아래처럼 noun phrase만 바꿨다.

| Target | 배정 행 | Romanized | Descriptive |
|---|---:|---|---|
| 장구 | 25 | `janggu` | `Korean hourglass-shaped drum` |
| 소리북 | 5 | `soribuk` | `Korean barrel drum` |
| 대금 | 3 | `daegeum` | `Korean transverse bamboo flute` |

모든 설명은 `needs_human_review`이며 인간 검토 완료 항목은 0/33이다.

### 2.3 데이터와 Annotation의 한계

H1의 조건별 고유 설명은 17개뿐이다. 그룹 크기는 singleton 9개, size-2 4개, size-3 2개, size-5 2개다. H2의 고유 텍스트는 조건별 3개뿐이다. 설명에 곡명, 선율, 구간, 분위기, 명시적 장단이 없으므로 동일 장르·편성의 개별 음원을 구별하지 못한다.

Label상 실제 악기 출현은 장구 25, 소리북 5, 대금 28개다. H2 target 배정 3개인 대금과 Label-positive 28개인 대금을 혼동하면 안 된다.

## 3. Experimental Setup

### 3.1 모델과 환경

| 항목 | 실제 사용 값 |
|---|---|
| Model | Pretrained CLaMP 3 SAAS, checkpoint epoch 10 |
| Official implementation | commit `9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8` |
| Audio frontend | `m-a-p/MERT-v1-95M` |
| Text encoder | `FacebookAI/xlm-roberta-base` |
| GPU | NVIDIA GeForce RTX 4060 Ti, 16,380 MiB |
| Runtime | Python 3.11.17, PyTorch 2.3.0+cu118, Transformers 4.40.0 |
| 최종 no-GPU 검증 | Python 3.12.3, NumPy 2.5.4 |
| Peak observed VRAM | 2,090 MiB, 약 12.8% |
| Embedding | `(1, 768)`, `float32`, NaN/Inf 0 |

Fine-tuning과 training은 하지 않았다. H2는 기존 H1 audio embedding 33개를 재사용했다. 이번 최종 검증 단계에서는 GPU와 모델 추론을 전혀 실행하지 않고 저장된 결과와 similarity matrix만 사용했다.

### 3.2 Retrieval과 정답 정의

모든 조건은 동일한 33개 audio candidate와 cosine similarity를 사용했다. H1 positive set은 다음 signature가 같은 모든 오디오다.

```text
(genre_major, genre, unordered validated instrument set)
```

동일 설명이 여러 오디오를 가리키므로 first matching Audio ID 하나가 아니라 group 내 모든 오디오를 positive로 처리했다. rank는 가장 높은 positive score보다 엄격히 큰 candidate 수에 1을 더해 계산했고 RR은 `1/rank`이다.

H2에는 두 정답 정의를 구분했다.

1. **17-group metadata proxy:** H1과 같은 signature. 비교 형식은 같지만 H2 문장에 없는 장르·전체 편성을 요구한다.
2. **Target-instrument presence:** Label에 target이 있는 모든 candidate. 문장 의미에는 맞지만 장구 25/33, 대금 28/33이 positive라 ceiling effect가 크다.

### 3.3 평가 지표와 불확실성

- 기존 33-query MRR: 저장된 33행을 동일 가중. 중복 문장을 반복 반영한다.
- 17-group Macro-MRR: metadata group별 RR을 먼저 하나로 두고 그룹에 같은 `1/17` 가중치를 부여한다. 이 기존 분석도 candidate set은 33개 audio를 그대로 유지한다.
- Paired group bootstrap: 17개 group을 replacement sampling, 100,000회, seed `20261122`, percentile 95% CI.
- 추가 no-GPU 민감도: H1 candidate도 17 group으로 max/mean 집계; H2 instrument presence에 AUROC/AP와 ranking overlap을 계산.

Bootstrap CI는 독립 표집된 전체 국악 모집단의 CI가 아니라, 현재 17개 Label-derived group 내 불확실성이다.

## 4. H1 Results

### 4.1 기존 결과와 group-level 결과

| 조건 | 기존 33-query MRR | 17-group Macro-MRR |
|---|---:|---:|
| Native-KR | 0.166691 | 0.118368 |
| EN | 0.226806 | 0.221191 |
| MT-KR | 0.169167 | 0.126099 |

| 비교 | 33-query ΔMRR | 17-group ΔMRR | Group bootstrap 95% CI |
|---|---:|---:|---:|
| Native-KR − MT-KR | -0.002476 | -0.007731 | [-0.030493, 0.007413] |
| Native-KR − EN | -0.060115 | -0.102823 | [-0.252066, 0.016815] |

두 CI 모두 0을 포함한다. EN 점추정치가 높지만 EN의 유의한 우월성을 주장할 수 없고, Native-KR과 MT-KR도 동등하다고 입증된 것이 아니다. 현재 표본에서 안정적인 차이 방향을 검출하지 못한 것이다.

### 4.2 반복 설명의 영향

5개 민요 그룹은 Native/MT RR 0.5, 5개 판소리 그룹은 Native/MT RR 0.2여서 33-query 평균에서 각각 다섯 번 반영된다. 이를 한 번씩만 반영하면 Native와 MT의 MRR이 각각 0.048322와 0.043068 낮아진다. EN은 0.005615만 낮아진다. 즉 33-query MRR의 조건별 차이는 단순 표본 수뿐 아니라 어느 group이 반복됐는지의 영향을 받는다.

### 4.3 영향력이 큰 Query

`0066_정악_풍류음악`은 Native rank 3/RR 0.333333, EN rank 1/RR 1.0, MT rank 2/RR 0.5다. 이 singleton group을 query에서 제외하되 candidate 33개는 유지하면 다음과 같이 Native−MT 부호가 뒤집힌다.

| 분석 | Native−MT ΔMRR |
|---|---:|
| 전체 33-query | -0.002476 |
| `0066` 제외 32-query | +0.002654 |
| `0066` group 제외 16-group Macro | +0.002203 |

이는 `0066`을 사후 제거해야 한다는 뜻이 아니라, 원래 방향이 한 group에 민감하다는 진단이다.

### 4.4 Candidate까지 group으로 집계한 보조 분석

이번 최종 단계에서 저장된 matrix만 사용해 query와 candidate를 모두 같은 17개 metadata group으로 축약했다. candidate group score를 max와 mean 두 방식으로 미리 고정해 각각 계산했다. 이는 기존 33-audio 결과와 별도인 민감도 분석이다.

| Candidate 집계 | Native | EN | MT | Native−MT | 95% CI |
|---|---:|---:|---:|---:|---:|
| Group max | 0.186774 | 0.255678 | 0.187331 | -0.000557 | [-0.008374, 0.008662] |
| Group mean | 0.214782 | 0.281046 | 0.223609 | -0.008827 | [-0.022986, 0.003869] |

두 집계에서도 CI가 0을 포함해 “안정적인 번역 유발 성능 저하를 검출하지 못했다”는 결론은 유지된다.

### 4.5 번역 과정 분석

악기 정보는 33/33 보존됐다. 그러나 Native→EN→MT 과정에서 표면 변화 10건, `민속악→민속 음악` 일반화 18건, `창작국악→현대 국악` 범위 변화 5건이 확인됐다. 따라서 Native/MT 차이는 동일 의미의 문체 변형만 비교하는 완전한 통제가 아니다.

## 5. H2 Results

### 5.1 17-group proxy 결과

| 분석 단위 | Romanized | Descriptive | Romanized−Descriptive |
|---|---:|---:|---:|
| 기존 33-row MRR | 0.192036 | 0.188851 | +0.003184 |
| 17-group Macro-MRR | 0.157766 | 0.181487 | -0.023721 |
| 3-term equal-weight Macro-MRR | 0.141974 | 0.174617 | -0.032643 |

Group-level 차이의 bootstrap 95% CI는 [-0.142128, 0.127176]이다. Query-row weighting과 group weighting 사이에서 방향이 뒤집히고 CI도 넓으므로 표현 우열을 결론 낼 수 없다. 특히 bootstrap unit은 metadata group 17개지만 실제 언어 text/ranking은 3개뿐이므로, 이를 독립 언어 query 17개에 대한 신뢰구간으로 해석할 수 없다.

### 5.2 용어별 proxy 결과

| Term | 배정 행 / group | Romanized query MRR | Descriptive query MRR | Romanized group MRR | Descriptive group MRR |
|---|---:|---:|---:|---:|---:|
| 장구 | 25 / 13 | 0.216986 | 0.196691 | 0.180072 | 0.187472 |
| 소리북 | 5 / 1 | 0.142857 | 0.166667 | 0.142857 | 0.166667 |
| 대금 | 3 / 3 | 0.066080 | 0.160494 | 0.066080 | 0.160494 |

소리북은 언어 query 하나이자 metadata group 하나뿐이며, 대금도 query 하나를 세 행에 반복한 것이다. 표본 수가 작고 장구에 편중되어 용어별 일반화를 할 수 없다.

### 5.3 Retrieval 순위 변화

Proxy에서 descriptive rank는 저장된 33행 중 23행에서 개선되고 10행에서 악화됐지만 이는 독립 사례 33개가 아니다. 같은 target은 동일한 text와 거의 동일한 ranking을 공유하고, 각 group positive가 그 공통 ranking에서 처음 등장하는 위치만 다르다.

| Metadata group | Target | Romanized rank | Descriptive rank | 변화 |
|---|---|---:|---:|---:|
| `0004/0058_정악_풍류음악` | 장구 | 27 | 3 | -24 |
| `0176/0217/0218_민속악_산조` | 장구 | 1 | 20 | +19 |
| `0812_창작국악_창작국악` | 장구 | 22 | 4 | -18 |
| `0066_정악_풍류음악` | 장구 | 13 | 30 | +17 |
| `0835_창작국악_창작국악` | 대금 | 12 | 3 | -9 |

이 변화는 표현이 candidate ordering에 영향을 준다는 증거지만, 개별 곡의 문화를 더 잘 이해했다는 증거는 아니다.

### 5.4 Instrument-presence 보조 분석

기존 target-presence first-positive MRR은 Romanized 0.809524, Descriptive 0.873737로 높았다. 그러나 positive가 많은 조건에서는 우연히 상위에 positive 하나가 나타나기 쉬우므로 ceiling effect가 강하다. 이를 확인하기 위해 저장된 similarity에서 고유 용어 3개를 query로 하고 33개 전체의 instrument presence를 AUROC/AP로 평가했다.

| Term | Positive/33 | AP prevalence baseline | Romanized AUROC / AP | Descriptive AUROC / AP |
|---|---:|---:|---:|---:|
| 장구 | 25 | 0.758 | 0.415 / 0.770 | 0.795 / 0.928 |
| 소리북 | 5 | 0.152 | 0.571 / 0.202 | 0.464 / 0.170 |
| 대금 | 28 | 0.848 | 0.207 / 0.734 | 0.407 / 0.823 |

대금은 Descriptive AP 0.823이 Romanized보다 높지만 prevalence baseline 0.848보다 낮다. 따라서 높은 first-positive MRR를 강한 retrieval 성능으로 해석할 수 없다.

두 표현의 전체 candidate ranking 비교는 다음과 같다.

| Term | Spearman ρ | Top-5 overlap | Top-10 overlap |
|---|---:|---:|---:|
| 장구 | 0.093 | 2/5 | 2/10 |
| 소리북 | 0.597 | 2/5 | 5/10 |
| 대금 | 0.467 | 2/5 | 5/10 |

특히 장구의 낮은 rank correlation은 표현 변화에 대한 민감도를 보여준다. 다만 어느 ranking이 더 옳은지는 human relevance annotation 없이는 결정할 수 없다.

### 5.5 의미 등가성

`janggu`와 `Korean hourglass-shaped drum`은 가장 강한 쌍이다. `Korean barrel drum`은 소리북의 판소리 반주 맥락과 구별 특징을 잃고, `Korean transverse bamboo flute`은 대금의 상위 범주일 뿐 고유 설명은 아니다. 모두 사람 검토 전이므로 H2 결과는 잠정적이다.

## 6. Discussion

### 6.1 H1과 H2의 종합 관찰

첫째, H1은 역번역이 성능을 낮춘다는 방향성 가설을 지지하지 않았다. Native와 MT의 차이는 작고, group weighting·candidate 집계·특정 query 포함 여부에 따라 크기와 부호가 달라졌다. 이 결과는 “번역이 해롭지 않다”거나 두 조건이 동등하다는 증명이 아니라, 현재 설계가 작은 효과를 안정적으로 식별하지 못했다는 뜻이다.

둘째, H2는 로마자/설명식 표현 변경이 이 33곡의 ordering을 바꾼다는 관찰은 제공한다. 그러나 Query-MRR와 Group-MRR의 방향이 반대이고, ground truth를 metadata group에서 instrument presence로 바꾸면 지표 크기가 크게 달라진다. 따라서 특정 표현의 우월성보다 **모델과 평가가 표현 및 정답 정의에 민감하다**는 결론이 타당하다.

셋째, EN 점추정치가 H1에서 가장 높다는 사실만으로 영어가 국악 검색에 더 적합하다고 말할 수 없다. 설명 구조, encoder pretraining, 번역 용어, 표본 구성 등이 함께 작용할 수 있고 Native−EN CI도 0을 포함한다.

### 6.2 평가 설계가 결과에 미친 영향

33행을 독립 query처럼 평균하면 size-5 그룹이 singleton보다 다섯 배 큰 영향을 준다. H2에서는 단 세 text embedding을 33행으로 복제해 개별 audio 결과처럼 보이게 한다. Multi-positive는 동일 설명 문제를 완화하지만 Label signature가 실제 음향적 relevance라는 보장은 없다. Instrument-presence 정답은 의미상 자연스럽지만 positive가 지나치게 많아 MRR가 포화된다.

평가 설계 효과가 관찰된 언어 효과보다 크거나 비슷할 수 있으므로, 점수 하나만으로 CLaMP 3의 교차언어·문화 이해를 판단해서는 안 된다.

### 6.3 무엇을 신뢰할 수 있는가

| 수준 | 판단 |
|---|---|
| 높음 | WAV–JSON–CSV 일치, 저장 embedding/similarity/rank의 재현, 조건별 동일 후보·정답의 paired 비교, H1 결과의 불안정성 |
| 중간 | 현재 33곡 안에서 H2 표현 변경이 ranking을 바꾼다는 관찰 |
| 낮음 | 특정 언어/표현의 일반적 우월성, 전체 국악으로 일반화, Label match를 청감 relevance로 간주, 모델의 문화적 이해 주장 |

## 7. Limitations & Future Work

### 7.1 주요 한계

1. 33곡과 17개 H1 그룹, 3개 H2 text뿐이라 통계적 불확실성이 매우 크다.
2. 동일 설명이 반복되고 자연어 표현 다양성이 없다.
3. Label 기반 정답은 실제 청감상 악기 존재·두드러짐과 의미적 relevance를 보장하지 않는다.
4. H2 gloss와 H1 번역 모두 인간 검토가 완료되지 않았다.
5. H2 target 분포가 장구 25/소리북 5/대금 3으로 불균형하다.
6. 하나의 pretrained model과 하나의 selected pilot만 사용해 외적 타당성이 낮다.
7. LLM 번역의 decoding parameter가 노출되지 않아 완전한 재생성에는 한계가 있다.

### 7.2 추가 데이터 없이 개선 가능한 평가

- **중복 완화:** H1의 17개 고유 group에 같은 가중치를 주고 33-row 결과는 반복 가중 참고치로 병기한다. H2는 독립 query 수를 3으로 명시한다.
- **Candidate 구성:** 33개 전체를 primary candidate set으로 유지한다. 균형 contrast set을 만들 경우 장르·악기 규칙을 결과 확인 전에 고정하고 기존 결과와 별도 sensitivity analysis로 보고한다. 점수가 좋아지는 subset을 사후 선택하지 않는다.
- **공정 비교:** H1의 세 조건, H2의 두 조건 안에서는 항상 같은 candidate와 positive definition을 사용한다.
- **Group candidate:** 17개 candidate group의 max/mean 집계를 모두 보고해 오디오 수가 많은 group의 영향을 점검한다.
- **H2 지표:** first-positive MRR 외에 prevalence baseline, AUROC/AP, Spearman, fixed Top-k overlap을 함께 보고한다.
- **Human review:** `pilot_review.csv`로 번역·gloss를 검토하고, 실제 음원을 들어 악기 존재·salience와 query–audio relevance를 별도 annotation한다.

현재 Label만으로는 의미상 유일한 audio 정답을 정의할 수 없다. audio-specific 평가가 필요하면 추가 다운로드가 아니라, 현재 33곡에 대한 전문가 또는 다중 평가자의 relevance annotation이 먼저 필요하다.

## 8. Conclusion

이 Pilot은 CLaMP 3 SAAS로 국악의 H1/H2 controlled retrieval pipeline을 실제로 실행하고, 저장된 결과를 재현 가능하게 검증했다. 그러나 H1의 안정적인 translation-induced degradation과 H2의 특정 표현 우월성은 확인되지 않았다. 가장 중요한 결과는 모델 성능 순위가 아니라, 17개 반복 설명 그룹, 3개 H2 고유 query, 모호한 Label-derived positives, 높은 positive prevalence가 해석을 지배한다는 점이다. 따라서 현재 결과는 가설 검증의 최종 증거가 아니라 평가 설계를 교정하기 위한 Pilot evidence로 사용하는 것이 적절하다.

---

## Appendix A. Existing Results and New Analyses

| 구분 | 분석 | 입력 |
|---|---|---|
| 기존 결과 | H1 33-query MRR, H2 proxy MRR | 기존 result CSV와 실험 metrics |
| 기존 추가 분석 | H1/H2 17-group Macro-MRR, group bootstrap, `0066` 영향 | 저장 rank/RR |
| 이번 최종 검증의 신규 수치 | H1 17×17 candidate max/mean, H2 term-presence AUROC/AP·rank stability | 저장 33×33 similarity matrix; GPU 추론 없음 |

새 수치는 기존 MRR을 수정하거나 대체하지 않는다. 계산 원본은 `artifacts/pilot_validation/`에 별도 저장했다.

## Appendix B. Revision Plan

| 현재 약점 | 위치 | 수정 계획 | 완료 기준 |
|---|---|---|---|
| 사람 검토 0/33 | Dataset, H2 | 국악 용어와 번역을 두 명 이상이 독립 검토 | 합의 결과와 disagreement 기록 |
| 청감 relevance 부재 | Setup, Discussion | 33곡에 query–audio 관련성 및 악기 salience annotation | 평가자 지침, agreement, 확정 positive set 공개 |
| H2 고유 text 3개 | H2 Results | 현재 Label 범위 안에서 검증된 paraphrase 설계 | 의미 등가성 검토를 통과한 독립 표현 수 명시 |
| Group bootstrap의 제한 | H1/H2 Results | group 수와 독립성 한계를 본문 표 옆에 유지 | CI를 모집단 유의성으로 표현한 문장 0개 |
| 단일 모델 Pilot | Limitations | 후속 연구에서 사전 등록된 동일 설계로 모델 비교 | 후보·정답·지표를 결과 확인 전에 고정 |

## Appendix C. AI Usage Disclosure

- Codex 기반 LLM: 33개 Native-KR의 EN 번역, EN-only MT-KR 역번역, 검증·평가 스크립트 작성, 결과 보고서 초안 작성에 사용.
- CLaMP 3 SAAS: 기존 단계에서 audio/text embedding과 cosine similarity 생성에 사용. Fine-tuning/training 없음.
- 자동 검증: Label 필드 429개, WAV SHA/header, CSV hash, 저장 matrix shape/finite 여부, metric 재계산.
- 인간 독립 검토: 아직 완료되지 않았으며 33개 모두 `needs_human_review`로 유지. 본 문서는 제출 전 연구자가 원자료·수치·용어를 직접 확인해야 하는 분석 초안이다.

## Appendix D. Reproducibility

주요 기존 재현 명령은 각 단계 보고서에 기록돼 있다. 모델 추론 환경은 Python 3.11.17/NumPy 1.26.4였고, 이번 저장 결과 검증은 Python 3.12.3/NumPy 2.5.4에서 실행했다. 이번 no-GPU 검증은 다음 한 줄로 재현된다.

```bash
python3 scripts/build_pilot_validation.py
```

주요 파일:

- `pilot_review.csv`
- `PILOT_VALIDATION.md`
- `artifacts/pilot_validation/metrics.json`
- `artifacts/pilot_validation/h1_group_candidate_results.csv`
- `artifacts/pilot_validation/h2_term_detection_results.csv`
- `scripts/build_pilot_validation.py`

Bootstrap은 100,000회, seed `20261122`를 사용했다. 최종 검증 입력 hash는 `PILOT_VALIDATION.md`에 기록했다.

## References

- CLaMP 3 official repository: <https://github.com/sanderwood/clamp3>
- 국립국악원 장구 자료: <https://www.gugak.go.kr/site/program/board/basicboard/view?boardid=48346&boardtypeid=58&currentpage=1&lang=en&menuid=001005006001&pagesize=30&searchselect=all&searchword=>
- 국립국악원 국악사전 소리북: <https://www.gugak.go.kr/ency/topic/view/2124>
- 국립부산국악원 대금 자료: <https://www.busan.gugak.go.kr/ENG/contents/ENG0301000000.do>
