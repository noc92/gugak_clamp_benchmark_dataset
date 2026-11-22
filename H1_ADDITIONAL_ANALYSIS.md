# H1 Additional Robustness Analysis

작성일: 2026-11-22 (KST)  
대상: 기존 `h1_retrieval_results.csv`의 33개 query와 17개 고유 metadata/설명 그룹

## 1. 결론

33개 행을 동일 가중한 기존 결과와 달리, 동일 설명 그룹 17개에 각각 같은 가중치 `1/17`을 주면 Native-KR과 MT-KR의 차이는 다음과 같다.

```text
Group Macro ΔMRR = Native-KR - MT-KR
                = 0.118368 - 0.126099
                = -0.007731
```

17개 그룹 paired bootstrap 95% 신뢰구간은 **[-0.030493, 0.007413]**으로 0을 포함한다. 또한 영향력이 큰 `0066_정악_풍류음악` 그룹을 제외하면 ΔMRR 부호가 양수로 바뀐다. 따라서 현재 Pilot은 Native-KR과 MT-KR 중 어느 조건이 안정적으로 우세하다는 결론을 지원하지 않는다.

## 2. 그룹과 계산 방법

그룹 key는 H1 본 실험과 동일하다.

```text
(genre_major, genre, unordered validated instrument set)
```

- 그룹 수: 17
- 그룹 크기 분포: singleton 9개, size-2 4개, size-3 2개, size-5 2개
- 같은 그룹 안에서는 세 조건의 text, rank, RR이 모두 동일함
- Group Macro-MRR: 각 그룹 RR의 산술 평균, 그룹당 가중치 `1/17`
- Candidate set: 모든 분석에서 기존 33개 audio를 그대로 유지

### Paired bootstrap

- resampling unit: 17개 metadata group
- 한 replicate에서 17개 그룹을 replacement를 허용해 재표집
- 각 그룹의 paired RR difference를 평균
- percentile 95% CI
- 반복 수: 100,000
- seed: `20261122`
- RR은 반올림된 CSV 문자열이 아니라 integer rank에서 `1/rank`로 다시 계산

17개뿐이므로 bootstrap 신뢰구간 자체도 불확실하며, 모집단에 대한 강한 추론으로 사용하지 않는다.

## 3. Query-level과 Group-level 비교

| 조건 | 기존 33-query MRR | 17-group Macro-MRR | 변화 |
|---|---:|---:|---:|
| Native-KR | 0.166691 | 0.118368 | -0.048322 |
| EN | 0.226806 | 0.221191 | -0.005615 |
| MT-KR | 0.169167 | 0.126099 | -0.043068 |

Native-KR과 MT-KR의 Macro-MRR이 크게 낮아진 이유는 크기가 큰 일부 그룹이 비교적 높은 RR을 가지고 기존 33-query 평균에서 반복 가중됐기 때문이다.

- 5개 민요 그룹: Native/MT RR `1/2 = 0.5`
- 5개 판소리 그룹: Native/MT RR `1/5 = 0.2`

Query-level에서는 각각 5번 반영되지만 Group-level에서는 한 번만 반영된다. EN은 큰 그룹에 의한 상승 효과가 상대적으로 작아 Macro-MRR 변화도 작다.

## 4. Bootstrap 결과

| 비교 | Query-level ΔMRR | Group Macro ΔMRR | Group bootstrap 95% CI |
|---|---:|---:|---:|
| Native-KR − MT-KR | -0.002476 | -0.007731 | **[-0.030493, 0.007413]** |
| Native-KR − EN | -0.060115 | -0.102823 | **[-0.252066, 0.016815]** |

두 구간 모두 0을 포함한다. 점추정치에서는 EN이 높고 Native-KR/MT-KR은 가깝지만, 현재 17개 그룹만으로 안정적인 방향성을 확정할 수 없다.

## 5. `0066_정악_풍류음악` 영향

이 query의 first-positive rank와 RR은 다음과 같다.

| 조건 | Rank | RR |
|---|---:|---:|
| Native-KR | 3 | 0.333333 |
| EN | 1 | 1.000000 |
| MT-KR | 2 | 0.500000 |

MRR은 상위 순위 변화에 민감하므로 Native 3위→MT 2위 한 건이 Native−MT RR 합에 `-0.166667`을 기여한다. 이 값은 전체 33-query RR 차이 합보다 크다.

아래 제외 분석은 query만 제거하며 Candidate set 33개는 바꾸지 않았다. `0066`은 singleton 그룹이므로 Group Macro 분석에서는 해당 한 그룹을 제거했다.

| 분석 | Native | EN | MT | Native−MT | Native−EN |
|---|---:|---:|---:|---:|---:|
| 33 queries / 17 groups의 Query MRR | 0.166691 | 0.226806 | 0.169167 | -0.002476 | -0.060115 |
| 32 queries, `0066` 제외 | 0.161483 | 0.202644 | 0.158829 | **+0.002654** | -0.041161 |
| 16-group Macro, `0066` 그룹 제외 | 0.104933 | 0.172516 | 0.102731 | **+0.002203** | -0.067583 |

Native−MT의 부호가 두 제외 분석 모두에서 음수에서 양수로 바뀐다. 원래 ΔMRR의 방향이 한 singleton query에 민감하다는 직접적인 증거다.

## 6. 영향력이 큰 다른 그룹

- `0225/0235_민속악_산조`: Native rank 14, EN rank 1. Native−EN 차이를 크게 만든다.
- `0835_창작국악_창작국악`: Native rank 21, EN rank 2.
- `0157/0162_정악_궁중음악`: Native rank 4, MT rank 5로 Native에 유리하며 Query-level에서 두 번 반영된다.
- 5개 민요 그룹: Native rank 2, EN rank 3으로 Native에 유리하며 Query-level에서 다섯 번 반영된다.

이는 소수 그룹과 그룹 크기가 점추정치를 크게 움직일 수 있음을 보여준다.

## 7. 해석과 한계

1. Group-equal weighting 후에도 EN 점추정치는 높고 Native-KR/MT-KR은 가깝다는 정성적 패턴은 유지된다.
2. 그러나 두 bootstrap CI가 0을 포함하고 `0066` 제외 시 Native−MT 부호가 바뀐다.
3. 17개 그룹은 신뢰구간을 안정적으로 추정하기에 매우 작다.
4. 그룹은 label-derived 설명 기준이며 독립적으로 표집한 자연어 query가 아니다.
5. 동일 그룹의 여러 오디오는 같은 query를 공유하므로 기존 33-query MRR을 독립 표본 33개로 해석하면 안 된다.
6. 본 분석은 기존 rank를 재사용했으며 embedding 추출이나 retrieval을 다시 실행하지 않았다.

따라서 H1에 대한 적절한 결론은 “현재 Pilot에서는 translation-induced degradation의 안정적인 방향을 검출하지 못했다”이다.

## 8. 산출물

- `artifacts/h1_additional_analysis/group_results.csv`: 17개 그룹별 rank/RR
- `artifacts/h1_additional_analysis/metrics.json`: Macro-MRR, bootstrap, `0066` 제외 결과
- `scripts/run_h1_robustness_h2.py`: 재현 코드
- `H1_ADDITIONAL_ANALYSIS.md`: 본 보고서

재현 명령:

```bash
python3 scripts/run_h1_robustness_h2.py analyze-h1
```
