# Audit nguồn và liên kết dữ liệu chứng từ v1

**Ngày kiểm tra:** 10/10/2026  
**Phạm vi:** kiểm tra nguồn công bố, đường dẫn tải, giấy phép được công bố và rủi ro đã biết. Chưa kiểm tra các file dữ liệu mà nhóm đang giữ trên Google Drive.

## Kết luận sử dụng

Các nguồn phù hợp để xây module chứng từ độc lập. Chúng không có `claim_id` chung với CarDD hoặc bảng fraud hiện tại, nên không ghép theo từng dòng và không dùng nhãn của chúng để kết luận fraud. Khi tích hợp hệ thống, module chứng từ chỉ xuất tín hiệu có schema rõ ràng; việc nối vào hồ sơ thật phải dựa trên `claim_id` do hệ thống nghiệp vụ cấp.

## Nguồn chuẩn và trạng thái

| Dataset | Nguồn chuẩn nên lưu trong manifest | Trạng thái | Hành động trước baseline |
|---|---|---|---|
| CORD v2 | [Kho chính thức](https://github.com/clovaai/cord), [Hugging Face của Naver Clova](https://huggingface.co/datasets/naver-clova-ix/cord-v2) | Xác minh được 1.000 ảnh, split 800/100/100, khoảng 2,31 GB và giấy phép CC BY 4.0. | Lưu bản license, revision/commit và checksum. Dùng split chính thức. |
| ICDAR2019 SROIE | [RRC chính thức](https://rrc.cvc.uab.es/?ch=13&com=downloads) | Cổng chính thức tồn tại; có thể yêu cầu tài khoản RRC. Các bản Hugging Face/Kaggle là mirror. | Ưu tiên tải từ RRC. Nếu buộc dùng mirror, ghi URL mirror, checksum và đối chiếu số file/schema với mô tả chính thức. |
| FUNSD | [Trang tác giả](https://guillaumejaume.github.io/FUNSD/), [điều kiện sử dụng](https://guillaumejaume.github.io/FUNSD/work/) | 199 form đã gán nhãn; nguồn công bố giới hạn cho nghiên cứu/giáo dục phi thương mại. | Lưu nguyên văn điều kiện sử dụng. Audit lỗi annotation trước KIE; không coi nhãn gốc là hoàn hảo. |
| XFUND | [Kho Microsoft chính thức](https://github.com/doc-analysis/XFUND) | 1.393 form, bảy ngôn ngữ; không có tiếng Việt; license CC BY-NC-SA 4.0. | Lưu release và license; đánh giá riêng domain/language shift trước khi suy ra cho tiếng Việt. |
| MIDV-500 | [Trang Smart Engines](https://smartengines.ru/science/dataset/), [Zenodo của tác giả](https://zenodo.org/records/18504926), [bài báo nguồn](https://arxiv.org/abs/1807.05786) | 500 video clip cho 50 loại giấy tờ; bộ file Zenodo khoảng 32,9 GB. `fcakyon/midv500` là công cụ/mirror cộng đồng, không phải nguồn gốc. | Ưu tiên Zenodo/nguồn tác giả và kiểm checksum công bố. Split theo document identity/template để tránh leakage giữa frame. |
| MIDV-2020 | [Zenodo của tác giả](https://zenodo.org/records/18786808), [trang L3i](https://l3i-share.univ-lr.fr/MIDV2020/midv2020.html) | Bản Zenodo khoảng 17,4 GB gồm clip/photo/scan/template; bản gốc TIFF/video đầy đủ trên L3i lớn hơn và cần quy trình truy cập riêng. | Tải từng thành phần theo task; lưu license và MD5 công bố. Chỉ lấy bản L3i đầy đủ khi thật sự cần. |
| RVL-CDIP | [Mirror Hugging Face đang được dùng](https://huggingface.co/datasets/aharley/rvl_cdip), [audit EACL 2023](https://aclanthology.org/2023.eacl-main.195/) | 400.000 ảnh/16 lớp, archive khoảng 38,8 GB, nhưng có label noise, tài liệu mơ hồ, chồng lấn train-test và PII. Mirror không thay thế việc xác minh quyền sử dụng nguồn gốc. | Chỉ lấy sample cân bằng sau khi scan PII, deduplicate và khóa split theo nhóm gần trùng. Không dùng test gốc để chọn model. |

## Link mirror cần phân loại rõ

- `naver-clova-ix/cord-v2` là namespace của đơn vị phát hành và được repo CORD chính thức trỏ tới.
- Mirror SROIE trên Hugging Face/Kaggle có thể tiện tải, nhưng phải lưu provenance và checksum; RRC vẫn là mốc đối chiếu.
- `fcakyon/midv500` là tiện ích cộng đồng. Không ghi nó là đơn vị phát hành MIDV-500.
- `aharley/rvl_cdip` là mirror phổ biến. Không suy ra quyền tái phân phối chỉ từ việc dataset có trên Hugging Face.

## Rủi ro chất lượng đã xác minh

- CORD v2 là bản sửa dữ liệu; repo chính thức mô tả việc sửa nhãn và loại một số trường vì lý do pháp lý. Vì vậy phải ghi đúng version `v2`.
- FUNSD có các bất nhất annotation đã được công bố trong nghiên cứu sửa FUNSD. Với baseline KIE, cần sample audit và quy tắc chuẩn hóa trước khi đo.
- XFUND phủ bảy ngôn ngữ nhưng không có tiếng Việt; kết quả không đại diện trực tiếp cho chứng từ bảo hiểm Việt Nam.
- Audit EACL 2023 ước lượng label noise RVL-CDIP khoảng 8,1%, đồng thời báo cáo overlap giữa train/test và PII. Dataset này chỉ phù hợp cho baseline có kiểm soát, không phải ground truth sạch mặc định.
- MIDV là dữ liệu giấy tờ định danh/mock document. Nó phù hợp cho detection/field extraction, không chứng minh khả năng xác minh danh tính thật trong production.

## Gate trước khi nhập dữ liệu vào pipeline

Mỗi dataset chỉ chuyển từ `bronze` sang bước xử lý khi có đủ:

1. `source_url`, ngày tải, version/revision và SHA-256.
2. File license/terms được lưu cùng manifest.
3. File count, dung lượng, extension, corrupt count và schema annotation.
4. Báo cáo exact/near duplicate giữa các split.
5. Sample gallery được kiểm tra bằng mắt.
6. Quy tắc ẩn hoặc loại PII.
7. Mapping task cụ thể: classification, OCR, layout, KIE hoặc ID extraction.
8. `claim_id` để trống đối với dữ liệu công khai; không tạo ID giả để nối với fraud/CarDD.

## Thứ tự triển khai đề xuất

1. CORD v2 làm baseline receipt/KIE nhỏ và dễ kiểm soát.
2. SROIE làm đối chứng OCR/KIE receipt sau khi xác minh mirror hoặc tải từ RRC.
3. FUNSD/XFUND cho form understanding và quan hệ key-value, có audit annotation riêng.
4. MIDV chỉ mở khi scope thật sự cần giấy tờ định danh.
5. RVL-CDIP chỉ lấy sample theo lớp cho document classification; chưa tải/chạy toàn bộ 400.000 ảnh.

RAG chưa nằm trong baseline nên không cần prompt/retrieval test ở giai đoạn này.
