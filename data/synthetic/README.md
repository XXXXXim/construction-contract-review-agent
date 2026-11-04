# data/synthetic: 평가용 합성 계약서 (SYNTHETIC)

- 이 폴더의 계약서는 **전부 합성 데이터**다. 실제 계약서가 아니며 어떤 회사의 자료도 아니다.
- `scripts/make_synthetic.py`가 공정위 건설업종 표준하도급계약서(2024.12.24) 본문을 바탕으로 생성한다 (seed=20261104, 결정적).
- 계약서마다: 정상 조항 10개 삭제 후 재번호 → 변형 8개 주입 → 당사자 명칭 치환(원사업자→갑, 수급사업자→을).
- 정답 라벨은 `eval/cases/synthetic_contract_NN.yaml`. 평가 숫자를 좋게 보이려고 이 파일을 손으로 고치지 않는다.
- 재생성: `.venv/bin/python scripts/make_synthetic.py`
