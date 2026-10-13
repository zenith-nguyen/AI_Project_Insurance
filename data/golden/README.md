# Golden claims

`data/golden/claims` contains five deterministic engineering cases derived from de-identified public research rows. Their identifiers, documents and relationships are synthetic. Each case shares one `claim_id` across tabular input, document fields, image manifest, graph entities and expected analysis.

They test API orchestration and auditability. Document fields are precomputed fixtures and image manifests contain no binaries, so these cases do not claim live OCR, KIE or damage inference. Rebuild them with:

```powershell
python scripts/build_golden_claims.py
```

Start the locally integrated service with:

```powershell
$env:INSURANCE_API_MODE = "live"
python -m uvicorn src.api.app:app --reload
```

Analyze a case with `POST /claims/CLM-GOLD-001/analyze`. Reviews are appended to `runtime/audit/reviews.jsonl`, which is intentionally excluded from Git.
