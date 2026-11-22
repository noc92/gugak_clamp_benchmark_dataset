# H1 Pilot Retrieval Experiment

작성일: 2026-11-22 (KST)  
목적: CLaMP 3 SAAS의 동일한 33곡 후보군에서 `native_kr`, `en`, `mt_kr`의 text-to-audio retrieval을 비교하고, 번역·역번역으로 인한 검색 순위 변화를 점검

## 1. 결론

33개 음원과 세 텍스트 조건을 모두 실제 추론했다. 모든 global embedding은 `(1, 768)` `float32`이고 NaN/Inf는 없었다. 장르와 검증된 악기 구성이 같은 음원을 모두 정답으로 취급하는 multi-positive 평가 결과는 다음과 같다.

| 조건 | MRR |
|---|---:|
| Native-KR | **0.166691** |
| EN | **0.226806** |
| MT-KR | **0.169167** |

핵심 비교는 다음과 같다.

```text
ΔMRR = MRR(Native-KR) - MRR(MT-KR)
     = 0.166691 - 0.169167
     = -0.002476
```

이 Pilot에서는 역번역 한국어가 Native-KR보다 MRR이 약 `0.00248` 높아, **translation-induced degradation은 관찰되지 않았다**. 차이는 매우 작고 표본도 작으므로 성능 향상이나 동등성을 주장할 수 없다. EN의 MRR이 가장 높았지만 이 역시 통계적 유의성 검정 없이 일반화하지 않는다.

## 2. 데이터 확인

- 평가 음원: 33개
- Candidate set: 모든 조건에서 동일한 33개 음원
- `audio_id`, WAV 경로: 각각 33개 고유값
- `native_kr`, `en`, `mt_kr`: 각 33개 모두 존재
- 실제 WAV 객체: 33/33 RIFF/WAVE, CSV의 SHA-256과 33/33 일치
- WAV 총 크기: 1,846,316,564 bytes (약 1.72 GiB)
- 실험 전후 `pilot_dataset.csv` SHA-256: `d2d34281542183ea67a6da3a3136f0ac715f4ce4dfd3a74753632bc5eecea84b`로 동일
- 기존 설명과 번역문은 수정하지 않음

작업 트리의 `.wav`는 132–134 byte Git LFS pointer였지만, 실제 오디오 33개는 `.git/lfs/objects`에 모두 존재했다. 각 pointer의 OID, 파일 크기, RIFF/WAVE header, 전체 SHA-256을 확인한 뒤 LFS 객체에 직접 연결한 staging symlink를 사용했다. 따라서 1.72 GiB의 WAV를 작업 트리에 중복 materialize하지 않았다.

### 동일 설명과 정답 모호성

각 텍스트 조건에는 17개의 고유 설명만 있다. 24개 음원이 8개 동일 설명 그룹에 속하고, 나머지 9개는 단독 설명이다.

| 그룹 크기 | 그룹 수 | 포함 query 수 |
|---:|---:|---:|
| 1 | 9 | 9 |
| 2 | 4 | 8 |
| 3 | 2 | 6 |
| 5 | 2 | 10 |

동일 설명 그룹은 세 조건 모두에서 `(genre_major, genre, unordered instrument set)` 그룹과 정확히 일치했다. 중복 그룹은 다음과 같다.

- `0004_정악_풍류음악`, `0058_정악_풍류음악`
- `0012_정악_풍류음악`, `0049_정악_풍류음악`
- `0157_정악_궁중음악`, `0162_정악_궁중음악`
- `0176_민속악_산조`, `0217_민속악_산조`, `0218_민속악_산조`
- `0225_민속악_산조`, `0235_민속악_산조`
- `0406_민속악_대풍류`, `0409_민속악_대풍류`, `0411_민속악_대풍류`
- `0439_민속악_판소리`, `0446_민속악_판소리`, `0470_민속악_판소리`, `0474_민속악_판소리`, `0480_민속악_판소리`
- `0736_민속악_민요`, `0737_민속악_민요`, `0739_민속악_민요`, `0740_민속악_민요`, `0747_민속악_민요`

동일한 label-derived 설명으로 특정 한 음원만 정답이라고 정하면 모델이 구별할 근거가 없다. 따라서 위 metadata signature가 같은 모든 음원을 정답으로 두는 multi-positive 기준을 세 조건에 공통 적용했다.

## 3. 모델 및 실행 환경

| 항목 | 실제 실행 값 |
|---|---|
| OS / kernel | Ubuntu 24.04.5 LTS / 6.8.0-138-generic |
| GPU | NVIDIA GeForce RTX 4060 Ti, 16,380 MiB |
| Driver / 표시 CUDA | 595.99.02 / CUDA 13.2 |
| Python | 3.11.17 |
| PyTorch / torchaudio / torchvision | 2.3.0+cu118 / 2.3.0+cu118 / 0.18.0+cu118 |
| Transformers / Accelerate | 4.40.0 / 0.34.0 |
| NumPy | 1.26.4 |
| CLaMP 3 | 공식 repository commit `9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8` |
| Retrieval model | Pretrained **CLaMP 3 SAAS**, checkpoint epoch 10 |
| Audio frontend | `m-a-p/MERT-v1-95M` |
| Text encoder | `FacebookAI/xlm-roberta-base` |
| 추론 방식 | 공식 `clamp3_embd.py --get_global`, 파일 단위 순차 처리 |

Fine-tuning, training, H2 실험은 수행하지 않았다. 기존 런타임과 모델 캐시는 삭제된 상태였으므로 공식 source, Python package, SAAS/MERT/XLM-R을 각각 한 번만 내려받았다. 추가 데이터셋은 다운로드하지 않았다.

## 4. Embedding 추출 및 검증

공식 pipeline을 그대로 사용했다.

```text
WAV → 24 kHz mono → 5-second MERT windows → layer mean
    → CLaMP 3 Audio Encoder → global embedding

Text → XLM-R tokenizer/encoder → CLaMP 3 projection
     → global embedding
```

| Modality / condition | 파일 수 | Shape | dtype | NaN | Inf |
|---|---:|---|---|---:|---:|
| Audio | 33 | `(1, 768)` | `float32` | 0 | 0 |
| Text: `native_kr` | 33 | `(1, 768)` | `float32` | 0 | 0 |
| Text: `en` | 33 | `(1, 768)` | `float32` | 0 | 0 |
| Text: `mt_kr` | 33 | `(1, 768)` | `float32` | 0 | 0 |

총 132개 embedding의 L2 norm은 `2.883214`–`17.651791` 범위이고 zero vector는 없다. 전체 추출 동안 200 ms 간격으로 측정한 GPU 메모리는 다음과 같다.

- idle 최소: 48 MiB
- 관측 최대: **2,090 MiB**
- idle 대비 최대 증가: 2,042 MiB
- GPU 16 GB 제한 대비 최대 사용률: 약 12.8%

## 5. Retrieval 및 MRR 정의

각 embedding을 L2-normalize한 뒤 text matrix와 audio matrix의 내적으로 33×33 cosine similarity matrix를 만들었다.

- Query: 조건별 33개 설명
- Candidate: 동일한 33개 audio embedding
- Positive set: query와 `(genre_major, genre, instrument set)`이 같은 모든 audio
- 정답 순위: positive 중 cosine similarity가 가장 높은 음원의 순위
- exact similarity tie: `1 + (best positive보다 점수가 엄격히 큰 후보 수)`로 계산해 CSV 순서 영향을 제거
- Reciprocal Rank: `1 / first-positive rank`
- MRR: 33개 query RR의 산술 평균

`h1_retrieval_results.csv`에는 요청된 rank/RR 외에 정답 수 `positive_count`와 `native_to_mt_rank_change`를 추가했다. Rank change는 `MT-KR rank - Native-KR rank`이므로 양수는 악화, 음수는 개선이다.

## 6. 순위 변화 관찰

Native-KR에서 MT-KR로의 first-positive rank 변화는 다음과 같다.

| 변화 | Query 수 |
|---|---:|
| 개선 (`change < 0`) | 11 |
| 동일 | 15 |
| 악화 (`change > 0`) | 7 |

평균 rank change는 `-0.303`이며, 최대 절대 변화는 3칸이었다. 따라서 이 Pilot에서 매우 큰 순위 붕괴 사례는 없었다.

| Query | Native rank | MT rank | 변화 | 번역상 관찰 |
|---|---:|---:|---:|---|
| `0842_창작국악_창작국악` | 23 | 20 | -3 | `창작국악` → `현대 국악`; 의미 범위 변화 가능 |
| `0012_정악_풍류음악` | 12 | 14 | +2 | `풍류음악` 띄어쓰기 및 악기 구분자 변화 |
| `0049_정악_풍류음악` | 12 | 14 | +2 | 위와 동일한 설명의 multi-positive group |
| `0118_정악_궁중음악` | 21 | 19 | -2 | `궁중음악` 띄어쓰기 및 구분자 변화 |
| `0176/0217/0218_민속악_산조` | 22 | 20 | -2 | `민속악` → `민속 음악`, `가야금·장구` → `가야금과 장구` |
| `0812_창작국악_창작국악` | 23 | 21 | -2 | `창작국악` → `현대 국악` |
| `0835_창작국악_창작국악` | 21 | 19 | -2 | `창작국악` → `현대 국악` |

번역 감사 결과와 동일하게 악기 정체성은 33/33 유지됐다. 의미 범위 검토가 필요한 변화는 `창작국악 → contemporary gugak → 현대 국악` 5건과 `민속악 → folk music → 민속 음악` 18건이다. 나머지 주요 차이는 복합어 띄어쓰기, 가운데점/쉼표, 두 항목의 `와/과` 연결이다. 관찰된 순위 변화가 특정 어휘 변화의 인과 효과라고 단정할 수는 없다.

## 7. 디스크 확인 및 정리

### 실험 전

- overlay: 16 GB 중 7.6 GB 사용, **8.5 GB 여유** (48% 사용)
- project: 약 3.4 GB
  - `.git/objects`: 약 1.65 GiB, 원격에 존재하는 과거 Git 이력
  - `.git/lfs`: 약 1.72 GiB, 현재 유일한 로컬 실제 WAV 객체
- Git worktree: clean
- `HEAD`, `origin/main`, GitHub `main`: 모두 `28b7c01bfd3186f10078aab618e823523e5d64e7`
- LFS push 대기 객체: 없음

`.git/objects`를 개별 삭제하면 repository가 손상되고 `.git/lfs`를 지우면 유일한 로컬 WAV 원본이 사라지므로 둘 다 유지했다. 현재 IDE가 사용하는 `/root/.vscode-server`도 삭제하지 않았다.

### 공간 절약 방법

1. 실제 WAV를 checkout하지 않고 LFS object에 zero-copy symlink를 만들어 약 1.72 GiB 중복을 방지했다.
2. SAAS checkpoint, XLM-R, MERT, package download cache와 MERT 임시 특징을 `/dev/shm`에 두었다.
3. 실험 중 디스크에는 5.6 GB Python environment만 설치했고, 추론 완료 후 삭제했다.
4. RAM model/cache 약 3.9 GB와 실행 중 생성된 `__pycache__`도 완료 후 제거했다.
5. 공식 CLaMP 3 source, 실행 스크립트, WAV 원본, 최종 embedding과 평가 산출물은 유지했다.

### 실험 후

- overlay: 16 GB 중 7.7 GB 사용, **8.4 GB 여유** (49% 사용)
- `/dev/shm`: 23 GB 전체 여유
- 유지한 공식 CLaMP 3 source: 약 93 MB
- 최종 H1 artifact: 약 1.1 MB
- embedding 132개와 유효한 WAV staging link 33개 유지

실험 결과 파일은 새로 생성됐으므로 아직 Git commit/push 상태가 아니다. 실험 전 기존 작업만 원격과 동기화된 상태임을 확인했다.

## 8. 발생한 문제와 해결

1. **WAV가 Git LFS pointer로 보임**  
   작업 트리의 pointer를 오디오로 잘못 읽지 않고 `.git/lfs/objects`의 실제 content를 hash/header 검증해 직접 연결했다.

2. **기존 CLaMP runtime과 model cache가 없음**  
   중복 파일이 없음을 전수 검색한 뒤 공식 source와 모델을 한 번만 받았다. 모델과 다운로드 cache는 RAM에 배치했다.

3. **공식 wrapper 내부의 `python` 호출**  
   처음에는 가상환경 interpreter로 wrapper만 실행해 내부 subprocess가 `python`을 찾지 못했다. 가상환경 `bin`을 `PATH`에 넣어 공식 코드를 수정하지 않고 해결했다.

4. **RAM `temp` symlink 정리 오류**  
   `shutil.rmtree`가 symlink를 삭제하지 못해 첫 Native-KR 실행이 embedding 33개 생성 후 cleanup 단계에서만 종료 코드 1을 냈다. 출력은 모두 finite임을 확인했고, 이후 공식 source 자체를 `/dev/shm`에 로컬 복제해 real RAM directory를 사용함으로써 EN, MT-KR, audio 실행은 cleanup까지 종료 코드 0으로 완료했다.

5. **MERT weight-normalization 및 cuDNN warning**  
   이전 `CLAMP3_SETUP.md` 단계에서 weight-normalization 이름 변경에도 실제 checkpoint tensor가 bit-identical하게 로드됨을 확인했다. cuDNN은 지원되는 fallback으로 계속 실행했다. 이번 33개 결과도 모두 생성됐고 finite 검증을 통과했다.

## 9. 한계

1. 사용자가 선택한 Validation 33곡뿐이며 전체 AI-Hub 분포를 대표하지 않는다.
2. 33 query 중 고유 설명은 17개뿐이다. 큰 동일 설명 그룹이 33-query MRR에서 반복 가중되므로 query가 통계적으로 독립적이지 않다.
3. Multi-positive 정답은 label-derived 장르·악기 정보가 같은 음원을 모두 관련 있다고 가정한다. 음악적으로 완전히 같은 relevance annotation은 아니다.
4. 설명에 곡명, 장단, 구간 구조, 분위기 등이 없어 같은 편성의 개별 음원을 구별하지 못한다.
5. 수동 검토 전 번역이며 특히 `창작국악/현대 국악`, `민속악/민속 음악`의 의미 범위가 달라질 수 있다.
6. 통계적 유의성, bootstrap confidence interval, 다른 seed/model 비교는 수행하지 않았다.
7. 이번 결과는 H1 pipeline 작동 여부를 보는 Pilot이며 CLaMP 3의 국악 이해 성능을 확정하는 평가가 아니다.

## 10. 산출물

- `h1_retrieval_results.csv`: query별 multi-positive rank, RR, Native→MT rank change
- `artifacts/h1_retrieval/embeddings/audio/`: audio global embedding 33개
- `artifacts/h1_retrieval/embeddings/text/{native_kr,en,mt_kr}/`: text global embedding 각 33개
- `artifacts/h1_retrieval/embedding_validation.csv`: 132개 shape/dtype/finite/norm 감사
- `artifacts/h1_retrieval/similarity/`: 세 조건 33×33 cosine matrix와 candidate 순서
- `artifacts/h1_retrieval/metrics.json`: MRR와 변화 요약
- `artifacts/h1_retrieval/data_audit.json`: WAV, text, answer group 감사
- `artifacts/h1_retrieval/gpu_memory_samples.csv`: VRAM 측정 원본
- `scripts/run_h1_retrieval.py`: zero-copy 준비와 multi-positive 평가 코드
- `H1_EXPERIMENT_REPORT.md`: 본 보고서

최종 embedding에서 다시 평가하는 명령은 다음과 같다. 환경 설치 방법은 `CLAMP3_SETUP.md`에 기록돼 있다.

```bash
python3 scripts/run_h1_retrieval.py prepare

# NumPy 1.26.4가 설치된 환경에서
python scripts/run_h1_retrieval.py evaluate
```
