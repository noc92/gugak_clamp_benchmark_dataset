# H1 Translation Dataset Report

작성일: 2026-11-22 (KST)  
대상: `pilot_dataset.csv`의 33개 `native_kr` 설명

## 1. 완료 상태

| 항목 | 결과 |
|---|---:|
| Korean → English 완료 | 33 / 33 |
| English → Korean 역번역 완료 | 33 / 33 |
| 번역 실패·누락 | 0 |
| H1 구조적 완성 행 (`h1_eligible=true`) | 33 |
| 수동 검토 완료 | 0 |

33개 `en`과 `mt_kr`를 모두 실제로 생성해 `pilot_dataset.csv`에 저장했다. `review_status=needs_human_review`는 유지했으며, H1은 구조적으로 완성됐지만 연구 투입 전 사람의 검토가 필요하다.

번역 전 CSV는 `pilot_dataset.pre_h1.csv`에 byte-for-byte 백업했다. 백업 SHA-256은 다음과 같다.

```text
69045878f8310f996d066c7adeab7f312b10e19b500822109614369aee75b4b7
```

## 2. 번역 방식

- 방식: 현재 세션의 **Codex 기반 LLM 번역**
- 외부 번역 모델/API, 네트워크, GPU: 사용하지 않음
- Forward translation: `audio_id`와 `native_kr`만 사용해 한국어→영어 생성
- Back-translation: 별도의 새 Codex 컨텍스트가 `audio_id`와 생성된 `en`만 읽어 영어→한국어 생성
- 역번역 컨텍스트에는 `native_kr`, 원본 label, H2 문장을 제공하지 않음
- 정확한 내부 모델 버전과 decoding parameter는 노출되지 않아 기록할 수 없음

영어 번역은 원문의 두 문장 구조를 유지하고, 장르와 악기 외 정보를 추가하지 않았다. 국악 악기는 설명식 표현으로 확장하지 않고 동일한 로마자 표기를 적용했다.

주요 고정 표기 예:

- `정악` → `jeongak`
- `풍류음악` → `pungnyu music`
- `궁중음악` → `court music`
- `민속악` → `folk music`
- `산조` → `sanjo`
- `대풍류` → `daepungnyu`
- `판소리` → `pansori`
- `민요` → `folk song`
- `창작국악` → `contemporary gugak`
- 악기명 → `gayageum`, `geomungo`, `daegeum`, `janggu`, `piri`, `haegeum` 등의 로마자 표기

CSV의 H1 metadata는 다음과 같이 갱신했다.

- `translation_model=Codex-based LLM (current session)`
- `translation_settings=two_pass_separate_contexts;fixed_glossary;back_translation_en_only;decoding_parameters_not_exposed`
- `translation_status=completed_codex_llm_needs_human_review`
- `h1_eligible=true`

## 3. 번역 예시

### 일반적인 표기·구두점 변화

`0004_정악_풍류음악`

- Native-KR: 이 곡은 정악에 속하는 풍류음악이다. 편성에는 대금·소금·아쟁·장구·좌고·피리·해금이 포함된다.
- EN: This piece is pungnyu music within jeongak. The instrumentation includes daegeum, sogeum, ajaeng, janggu, jwago, piri, and haegeum.
- MT-KR: 이 곡은 정악에 속하는 풍류 음악이다. 편성에는 대금, 소금, 아쟁, 장구, 좌고, 피리, 해금이 포함된다.

의미는 유지됐지만 `풍류음악`이 `풍류 음악`으로 띄어 쓰이고 악기 구분자가 가운데점에서 쉼표로 바뀌었다.

### 의미 범위 검토가 필요한 변화

`0812_창작국악_창작국악`

- Native-KR: 이 곡은 창작국악이다. 편성에는 가야금·거문고·대고·대금·목탁·바라·소금·아쟁·양금·장구·피리·해금이 포함된다.
- EN: This piece is contemporary gugak. The instrumentation includes gayageum, geomungo, daego, daegeum, moktak, bara, sogeum, ajaeng, yanggeum, janggu, piri, and haegeum.
- MT-KR: 이 곡은 현대 국악이다. 편성에는 가야금, 거문고, 대고, 대금, 목탁, 바라, 소금, 아쟁, 양금, 장구, 피리, 해금이 포함된다.

`창작국악`이 `contemporary gugak`을 거쳐 `현대 국악`으로 바뀌었다. 두 표현의 범위가 완전히 동일하다고 단정할 수 없어 해당 5개 행은 우선 검토 대상이다.

## 4. 국악 용어 변화

| Native-KR | EN | MT-KR | 행 수 | 해석 |
|---|---|---|---:|---|
| 풍류음악 | pungnyu music | 풍류 음악 | 5 | 띄어쓰기 변화, 의미는 대체로 유지 |
| 궁중음악 | court music | 궁중 음악 | 5 | 띄어쓰기 변화, 의미는 대체로 유지 |
| 민속악 | folk music | 민속 음악 | 18 | 고유 장르 표기에서 일반 명사형으로 변화 |
| 창작국악 | contemporary gugak | 현대 국악 | 5 | 의미 범위 변화 가능, 우선 검토 필요 |

`정악`, `산조`, `대풍류`, `판소리`, `민요`와 모든 악기명은 역번역에서 원래 한국어 명칭으로 돌아왔다. 다만 2개 악기만 있는 산조 5곡은 가운데점 나열이 `가야금과 장구` 또는 `거문고와 장구` 같은 접속 표현으로 바뀌었다.

## 5. Native-KR과 MT-KR 차이

- 문자열이 완전히 동일한 행: 0 / 33
- 주된 비의미적 차이: 복합어 띄어쓰기, `·`→`,` 구분자, 두 항목의 `와/과` 연결
- 악기 정체성/목록이 유지된 행: 33 / 33
- 의미 범위 변화 가능성이 뚜렷한 행: 창작국악 5개
  - `0812`, `0825`, `0833`, `0835`, `0842`

나머지 28개는 자동 비교와 수동 표본 점검에서 장르·악기 정보가 유지됐지만, 아직 연구자 승인 전이다.

## 6. 추가 수동 검토 권고

1. `창작국악` ↔ `contemporary gugak` ↔ `현대 국악`의 의미 범위
2. `민속악` ↔ `folk music` ↔ `민속 음악`이 benchmark에서 같은 장르명으로 취급 가능한지
3. `pungnyu`, `daepungnyu`, `jwago`, `pyeongyeong`, `banghyang`, `soribuk` 등 로마자 표기의 연구 표준 일치 여부
4. 쉼표/가운데점 및 `와/과` 변화가 text encoder 결과에 미치는 영향을 H1 degradation으로 그대로 둘지 여부
5. 33개 전체의 문법·용어를 사람이 승인한 뒤 `review_status`를 변경할 것

이번 단계에서는 위 변화를 원문에 맞춰 보정하지 않았다. 특히 역번역은 영어 문장만을 근거로 생성한 결과를 그대로 보존했다.

## 7. 불변성 검증과 산출물

번역 병합 전후를 비교해 다음 컬럼이 모두 byte-for-byte 동일한 값임을 확인했다.

- Audio ID, WAV/JSON 경로, WAV hash/header, 장르·제목·악기, `native_kr`
- 모든 H2 관련 컬럼: target term, `romanized_en`, `descriptive_en`, 생성 방식, eligibility, equivalence status

산출물:

- `pilot_dataset.csv`: H1 번역/역번역과 H1 metadata가 채워진 최종 데이터
- `pilot_dataset.pre_h1.csv`: 번역 전 원본 백업
- `h1_translation_pairs.csv`: 검토용 `audio_id`, `native_kr`, `en`, `mt_kr`
- `scripts/apply_h1_translations.py`: 분리 생성 결과를 안전하게 병합하는 스크립트
- `H1_TRANSLATION_REPORT.md`: 본 보고서

저장된 번역 pair를 백업본에 다시 적용하는 명령:

```bash
python3 scripts/apply_h1_translations.py \
  --translations h1_translation_pairs.csv
```

CLaMP 3, GPU, retrieval, similarity, MRR 계산은 실행하지 않았다.
