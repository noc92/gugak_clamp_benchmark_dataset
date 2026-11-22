# CLaMP 3 SAAS 환경 구축 및 임베딩 스모크 테스트

실행일: 2026-11-21 (UTC)  
목적: 학습이나 성능 평가 없이, 국악 WAV/한국어·영어 텍스트가 같은 CLaMP 3 공간의 global embedding으로 변환되고 cosine similarity까지 계산되는지 확인

## 1. 결론

- 공식 CLaMP 3 저장소의 커밋 [`9016d2b`](https://github.com/sanderwood/clamp3/tree/9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8)와 pretrained **CLaMP 3 SAAS** 체크포인트를 사용했다.
- `metadata.csv`에 ID가 존재하고 장구가 편성에 포함된 마스터 WAV 4개만 처리했다. Fine-tuning/training은 수행하지 않았다.
- 공식 `clamp3_embd.py --get_global` 경로가 MERT 전처리와 CLaMP 3 Audio/Text Encoder를 모두 정상 실행했다.
- 오디오 4개와 텍스트 4개의 결과는 모두 `(1, 768)`, `float32`이며 NaN/Inf는 각각 0개다.
- 전체 audio+text 추론 동안 `nvidia-smi`로 관측한 최대 장치 메모리는 **2,089 MiB**였다. 16 GB GPU 한도 안이다.

## 2. 데이터 확인과 테스트 샘플

`DATASET_ANALYSIS.md`와 `metadata.csv`를 기준으로 샘플을 연결했다. 분석 문서 작성 당시에는 로컬 WAV가 샘플 9개뿐이었지만, 현재 작업공간에는 이후 추가된 마스터 7개를 포함해 WAV가 16개 있다. `metadata.csv`의 `has_local_audio`도 새 파일 3개를 아직 반영하지 않는다. 이번 작업에서는 메타데이터 자체를 갱신하지 않고, ID가 실제로 대응하는 다음 4개만 사용했다.

| ID | 장르 | 길이(초) | `metadata.csv` 악기 | 입력 WAV |
|---|---|---:|---|---|
| `0001_정악_풍류음악` | 풍류음악 | 255.600 | 대금·소금·아쟁·장구·좌고·피리·해금 | `data/raw/audio_training/0001_정악_풍류음악_master/0001_정악_풍류음악.wav` |
| `0010_정악_풍류음악` | 풍류음악 | 146.400 | 가야금·거문고·단소·대금·양금·장구·피리·해금 | `data/raw/Sample/01.원천데이터/0010_정악_풍류음악/0010_정악_풍류음악_master/0010_정악_풍류음악.wav` |
| `0123_정악_궁중음악` | 궁중음악 | 355.500 | 대금·소금·아쟁·장구·좌고·피리·해금 | `data/raw/audio_training/0123_정악_궁중음악_master/0123_정악_궁중음악.wav` |
| `0174_민속악_산조` | 산조 | 135.000 | 가야금·장구 | `data/raw/audio_training/0174_민속악_산조_master/0174_민속악_산조.wav` |

네 파일은 모두 48 kHz, stereo, 24-bit PCM이다. 원본은 수정하거나 복사하지 않았고, 무시 대상인 `artifacts/clamp3_test/staging/audio/`에 심볼릭 링크만 만들었다.

텍스트 입력은 다음과 같다.

| 파일 ID | 원문 |
|---|---|
| `ko_janggu` | 이 곡에서는 장구가 연주된다. |
| `ko_traditional` | 이 곡은 한국 전통 음악이다. |
| `en_janggu` | This piece features a janggu. |
| `en_traditional` | This piece is Korean traditional music. |

## 3. 모델과 실행 환경

| 항목 | 실제 실행 환경 |
|---|---|
| OS | Ubuntu 24.04.5 LTS, kernel 6.8.0-138-generic |
| GPU | NVIDIA GeForce RTX 4060 Ti, `nvidia-smi` 총 16,380 MiB |
| Driver / 표시 CUDA | 595.99.02 / CUDA 13.2 |
| 로컬 CUDA toolkit | 12.8 (`nvcc` 12.8.93) |
| Python | 3.11.17, 프로젝트 전용 `.venv-clamp3` |
| PyTorch | 2.3.0+cu118 |
| torchvision / torchaudio | 0.18.0+cu118 / 2.3.0+cu118 |
| transformers / accelerate | 4.40.0 / 0.34.0 |
| NumPy | 1.26.4 |
| CLaMP 3 | 공식 저장소 commit `9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8` |
| Retrieval checkpoint | [CLaMP 3 SAAS](https://huggingface.co/sander-wood/clamp3/blob/main/weights_clamp3_saas_h_size_768_t_model_FacebookAI_xlm-roberta-base_t_length_128_a_size_768_a_layers_12_a_length_128_s_size_768_s_layers_12_p_size_64_p_length_512.pth), epoch 10 |
| Audio frontend | [MERT-v1-95M](https://huggingface.co/m-a-p/MERT-v1-95M) |
| Text encoder | `FacebookAI/xlm-roberta-base` |

공식 README는 Conda와 Python 3.10.16을 예시로 든다. 이 머신에는 Conda가 없어서 시스템 Python을 변경하지 않고 `uv` 전용 환경을 사용했다. 공식 `requirements.txt`의 버전은 그대로 설치했고, Python 3.11.17에서 import/CUDA/실제 추론을 모두 통과했다.

공식 오디오 경로는 WAV를 24 kHz mono로 변환한 뒤, 5초 non-overlap window마다 MERT의 시간축 평균 특징을 만들고 `--mean_features`로 layer축을 평균한다. 이어 CLaMP 3 Audio Encoder가 global average pooling과 projection을 적용한다. 텍스트는 XLM-R tokenizer/encoder와 같은 CLaMP 3 projection을 사용한다. 두 경로 모두 `--get_global`을 지정했다.

## 4. 설치 방법

아래 명령은 프로젝트 루트에서 실행하는 재현 절차다. 모델과 환경은 저장소에 포함하지 않도록 `.clamp3-runtime/`, `.venv-clamp3/`, `.cache/`, `*.pth`, `*.safetensors`를 `.gitignore`에 추가했다.

```bash
git clone https://github.com/sanderwood/clamp3.git .clamp3-runtime/repo
git -C .clamp3-runtime/repo checkout 9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8

UV_CACHE_DIR=.cache/uv uv venv .venv-clamp3 \
  --python 3.11
source .venv-clamp3/bin/activate

UV_CACHE_DIR=.cache/uv uv pip install --no-cache \
  torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 \
  --index-url https://download.pytorch.org/whl/cu118
UV_CACHE_DIR=.cache/uv uv pip install --no-cache \
  -r .clamp3-runtime/repo/requirements.txt

export HF_HOME="$PWD/.cache/huggingface"
export TOKENIZERS_PARALLELISM=false
```

최초 실행 시 MERT, XLM-R 및 약 2.39 GiB의 CLaMP 3 SAAS 체크포인트를 내려받는다. 이 실행에서 `.venv-clamp3`는 약 5.6 GiB, Hugging Face cache는 약 1.5 GiB, SAAS 체크포인트는 약 2.4 GiB를 사용했다.

## 5. 입력 staging과 임베딩 추출

새 환경에서 오디오 staging 링크를 다시 만들 때는 프로젝트 루트에서 다음을 실행한다.

```bash
mkdir -p artifacts/clamp3_test/staging/audio
ln -s ../../../../data/raw/audio_training/0001_정악_풍류음악_master/0001_정악_풍류음악.wav \
  artifacts/clamp3_test/staging/audio/0001_정악_풍류음악.wav
ln -s ../../../../data/raw/Sample/01.원천데이터/0010_정악_풍류음악/0010_정악_풍류음악_master/0010_정악_풍류음악.wav \
  artifacts/clamp3_test/staging/audio/0010_정악_풍류음악.wav
ln -s ../../../../data/raw/audio_training/0123_정악_궁중음악_master/0123_정악_궁중음악.wav \
  artifacts/clamp3_test/staging/audio/0123_정악_궁중음악.wav
ln -s ../../../../data/raw/audio_training/0174_민속악_산조_master/0174_민속악_산조.wav \
  artifacts/clamp3_test/staging/audio/0174_민속악_산조.wav
```

공식 top-level wrapper는 저장소 루트에서 실행해야 한다.

```bash
cd .clamp3-runtime/repo

# 공식 MERT 전처리 -> CLaMP 3 Audio Encoder -> global .npy
python clamp3_embd.py \
  ../../artifacts/clamp3_test/staging/audio \
  ../../artifacts/clamp3_test/embeddings/audio \
  --get_global

# 동일 SAAS 체크포인트의 Text Encoder -> global .npy
python clamp3_embd.py \
  ../../artifacts/clamp3_test/inputs/text \
  ../../artifacts/clamp3_test/embeddings/text \
  --get_global
```

주의: 공식 wrapper는 출력 디렉터리가 이미 존재하면 전체 추출을 건너뛴다. 재실행 검증에는 기존 결과를 보관한 뒤 새 출력 디렉터리 이름을 사용해야 한다.

## 6. 임베딩 검증

| modality | 파일 수 | 각 shape | dtype | NaN | Inf |
|---|---:|---|---|---:|---:|
| Audio | 4 | `(1, 768)` | `float32` | 0 | 0 |
| Text | 4 | `(1, 768)` | `float32` | 0 | 0 |

파일별 L2 norm을 포함한 검증값은 `artifacts/clamp3_test/embedding_validation.csv`에 저장했다. 실제 global embedding은 다음 위치에 있다.

- `artifacts/clamp3_test/embeddings/audio/*.npy`
- `artifacts/clamp3_test/embeddings/text/*.npy`

## 7. Cosine similarity 스모크 테스트

공식 `inference/clamp3_search.py`의 `torch.cosine_similarity` 구현으로 각 텍스트를 네 오디오 전체와 비교했다. 아래는 같은 값을 소수점 6자리로 표시한 4×4 표다.

| Audio ID | `ko_janggu` | `ko_traditional` | `en_janggu` | `en_traditional` |
|---|---:|---:|---:|---:|
| `0001_정악_풍류음악` | 0.224395 | 0.110220 | 0.222706 | 0.110965 |
| `0010_정악_풍류음악` | 0.249255 | 0.148269 | 0.234659 | 0.143025 |
| `0123_정악_궁중음악` | 0.269733 | 0.166523 | 0.258601 | 0.164146 |
| `0174_민속악_산조` | 0.267405 | 0.153522 | 0.290966 | 0.151666 |

원시 표는 `artifacts/clamp3_test/similarity.csv`에 저장했다. 이 수치는 4곡짜리 pipeline smoke test 결과일 뿐이며, 모델 성능·정확도나 국악 의미 이해 수준을 평가하는 지표로 해석하지 않는다.

공식 검색 스크립트의 재현 명령은 다음과 같다.

```bash
for query in ../../artifacts/clamp3_test/embeddings/text/*.npy; do
  python inference/clamp3_search.py "$query" \
    ../../artifacts/clamp3_test/embeddings/audio --top_k 4
done
```

## 8. GPU VRAM 측정

audio MERT 전처리, CLaMP 3 Audio Encoder, CLaMP 3 Text Encoder를 포함한 전체 실행 동안 다음 명령으로 200 ms마다 장치 전체 사용량을 기록했다.

```bash
nvidia-smi --query-gpu=timestamp,memory.used \
  --format=csv,noheader,nounits --loop-ms=200 \
  --filename=artifacts/clamp3_test/gpu_memory_samples.csv
```

- 샘플 수: 683
- idle 기준: 47 MiB
- 관측 최대: **2,089 MiB** (약 2.04 GiB)
- idle 대비 증가량: 약 2,042 MiB
- GPU 총량 대비 최대 사용률: 약 12.8%

파일 단위 순차 처리와 batch size 1 동작을 유지했으며, 전체 데이터셋을 처리하지 않았다.

## 9. 발생한 문제와 확인 결과

1. **MERT weight-normalization 경고**  
   `from_pretrained`가 `weight_g/weight_v`를 새 `parametrizations.weight.original0/1` 이름으로 보고하지 못해 “newly initialized” 경고를 출력했다. `output_loading_info`와 체크포인트 텐서를 직접 대조한 결과, PyTorch load hook이 두 텐서를 이미 정확히 로드했으며 값은 bit-identical이었다. 강제 strict reload 전후 오디오 임베딩도 완전히 동일했다. 따라서 별도 소스 패치는 적용하지 않았고 공식 tracked source는 변경 없는 상태로 복원했다.

2. **cuDNN execution-plan 경고**  
   MERT의 첫 convolution에서 특정 cuDNN plan을 지원하지 않는다는 경고가 한 번 발생했다. PyTorch가 지원되는 fallback 경로로 계속 실행했고 4개 파일이 모두 성공했다. 출력의 유한값 검증도 통과했으므로 별도 조치는 하지 않았다.

3. **기존 분석과 현재 오디오 수의 차이**  
   `DATASET_ANALYSIS.md` 작성 후 마스터 WAV 7개가 추가돼 문서의 “로컬 WAV 9개”와 현재 16개가 다르다. 이번 범위를 벗어나는 전체 메타데이터 재생성은 하지 않았으며, 실제 파일과 metadata ID가 모두 대응하는 4개만 선택했다.

4. **대용량 로컬 파일 관리**  
   현재 작업공간은 Git 저장소가 아니지만, 추후 실수로 가중치·cache·가상환경을 commit하지 않도록 `.gitignore`를 추가했다. 저장 대상은 작은 global embedding, 검증 CSV, similarity CSV, VRAM 로그뿐이다.

## 10. 산출물

```text
CLAMP3_SETUP.md
.gitignore
artifacts/clamp3_test/
├── embedding_validation.csv
├── similarity.csv
├── gpu_memory_samples.csv
├── inputs/text/*.txt
└── embeddings/
    ├── audio/*.npy   # 4개
    └── text/*.npy    # 4개
```

모델 checkpoint, Hugging Face cache, Python environment, 임시 MERT feature와 staging link는 산출물 목록에서 제외하고 `.gitignore`로 관리한다.
