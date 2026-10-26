# ONNX export cho model bảng (Phase 6)

**Ngày:** 26/10/2026 · **Người làm:** Huy Nhật (hỗ trợ Task 6, Operationalization) · Trạng thái: **đã làm, parity đạt**.

Mục backlog của Task 6 ("Có thể export ONNX để chạy CPU") đã được hiện thực và kiểm chứng parity.

## Đã làm

- `scripts/export_tabular_onnx.py`: xuất tầng **XGBoost** của bundle `artifacts/models/tabular_v1/bundle.joblib` sang **ONNX** (`tabular_xgb.onnx`), kèm `tabular_preprocess.joblib` (ColumnTransformer) và `tabular_onnx_meta.json` (feature columns, calibrator, ngưỡng t1/t2, kết quả parity).
- `src/models/onnx_infer.py` (`OnnxTabularScorer`): chấm điểm hồ sơ bằng **onnxruntime**, không cần `xgboost` lúc chạy. Phụ thuộc runtime: `onnxruntime` + `scikit-learn` (preprocess) + `numpy`.
- `tests/test_tabular_onnx.py`: test parity so với bundle joblib gốc.

## Kết quả parity

Trên frozen test `dataset_v2/test.parquet` (200 hồ sơ), xác suất hiệu chỉnh cuối cùng của đường ONNX so với đường joblib gốc: **sai khác tuyệt đối tối đa 2,4e-07** (ngưỡng chấp nhận 1e-5). Khớp cả hành động hàng đợi (STP/manual/SIU).

## Hai điểm kỹ thuật quan trọng (ghi lại để người sau không vấp)

1. **base_score**: XGBoost 3.4 học `base_score = 0,2471` (đúng bằng prevalence), không phải 0,5. onnxmltools 1.16 có xử lý đúng, nên không cần chỉnh tay.
2. **Sparse = missing**: pipeline gốc đưa **ma trận thưa** vào XGBoost, nên các ô 0 (one-hot và numeric) được coi là **missing**. Khi densify cho onnxruntime phải **thay 0,0 thành NaN** (giá trị missing của booster), nếu không điểm sẽ sai lệch lớn (~0,63). Đây là mấu chốt để parity khớp.

## Phạm vi và giới hạn

- Chỉ tầng **XGBoost** ở ONNX; **preprocess vẫn là sklearn** (nhẹ). Lý do: skl2onnx hiện chưa convert được `SimpleImputer` giá trị thiếu kiểu float trên cột chữ, nên chưa gộp cả pipeline vào một đồ thị ONNX. Đây là việc còn lại.
- Model `tabular_v1` giữ nhóm proxy (`insured_hobbies`...), trong khi chính sách bias hiện tại loại chúng ở `features()`; script tự thêm lại cột proxy từ raw cho khớp bundle. Nếu đổi sang bundle `tabular_bias_excluded_v1`, xuất lại ONNX tương ứng.

## Quyết định (PIC, 26/10)

Hai mục backlog của Task 6 được chốt như sau:

- **Export ONNX cho model bảng: LÀM — đã xong** (tài liệu này). Tầng XGBoost (phần nặng) chạy onnxruntime trên CPU, parity 2,4e-07. Đạt yêu cầu "có thể export ONNX để chạy CPU".
- **Gộp cả preprocess vào ONNX: HOÃN (backlog có lý do).** Khả thi về kỹ thuật (categorical imputer là `constant`='__UNKNOWN__', có thể tiền-điền chuỗi ngoài ONNX rồi onehot+numeric+xgboost trong ONNX), nhưng phải lách giới hạn skl2onnx với imputer chuỗi, đổi lại lợi ích rất nhỏ vì preprocess sklearn đã nhẹ, và thêm rủi ro lệch parity. Không xứng công ở giai đoạn đồ án.
- **Tách microservices: HOÃN (backlog có lý do).** Monolith + module adapters + endpoint `/verify` kiểu gateway đang chạy tốt. Tách thành nhiều service + gateway là thay đổi kiến trúc lớn, tăng bề mặt triển khai và rủi ro, gần như không thêm giá trị học thuật. Giữ như backlog kèm điều kiện nghiệm thu (đã nêu trong `reports/final/06_OPERATIONALIZATION_PHASE6.md`).

## Tái lập

```bash
pip install -r requirements-onnx.txt
PYTHONPATH=. python scripts/export_tabular_onnx.py          # tạo artifacts + đo parity
python -m pytest -q tests/test_tabular_onnx.py              # kiểm tra parity
```
