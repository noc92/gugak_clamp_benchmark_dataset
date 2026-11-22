# 데이터 배치와 재현 방법

AI-Hub에서 승인받아 내려받은 원본 ZIP과 해제한 파일은 수정하지 않는다.

```text
data/
├─ label_download/          # 수동 다운로드한 라벨 ZIP 297개
└─ raw/
   ├─ labels_training/      # TL JSON 197개
   ├─ labels_validation/    # VL JSON 100개
   └─ Sample/               # 샘플 JSON 1개 + 마스터 WAV 1개 + 스템 WAV 8개
```

샘플 JSON은 TL의 `0010_정악_풍류음악`과 동일하다. 아래 명령은 이를 자동으로
한 행으로 합치며 샘플 WAV 경로와 길이는 보존한다.

```powershell
python scripts/prepare_metadata.py
```

결과는 프로젝트 루트의 `metadata.csv`와 `metadata_summary.json`에 생성된다.
스크립트는 `data/raw/`를 읽기만 하며 원본 파일을 변경하지 않는다.

`timeSignature`는 `jangdan`으로 변환하지 않는다. 명시적인 `jangdan`, `장단`,
`장단명` 필드가 있을 때만 `metadata.csv`의 `jangdan`을 채운다.
