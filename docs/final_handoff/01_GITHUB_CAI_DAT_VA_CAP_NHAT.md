# 01 — GitHub, cài đặt và cập nhật phiên bản mới

## Lần đầu nhận dự án

Windows:

```powershell
git clone https://github.com/zenith-nguyen/AI_Project_Insurance.git
cd AI_Project_Insurance
python scripts/handoff.py up
```

macOS:

```bash
git clone https://github.com/zenith-nguyen/AI_Project_Insurance.git
cd AI_Project_Insurance
python3 scripts/handoff.py up
```

Lệnh `up` tự chạy preflight, build lại Docker image, đợi API healthy và smoke-test giao diện/API. Mở `http://127.0.0.1:8000/` sau khi báo PASS.

## Nhận bản cập nhật khi không sửa code local

```bash
cd AI_Project_Insurance
git switch main
git pull --ff-only origin main
python scripts/handoff.py up
```

macOS dùng `python3` thay cho `python` nếu cần. `--ff-only` dừng an toàn nếu lịch sử local khác GitHub, tránh tự tạo merge commit khó hiểu.

## Đang sửa code local nhưng cần lấy bản mới

Kiểm tra trước:

```bash
git status
```

Nếu thay đổi đã hoàn chỉnh, commit vào branch riêng:

```bash
git switch -c feature/ten-cong-viec
git add <cac-file-da-sua>
git commit -m "Mo ta thay doi"
git pull --rebase origin main
git push -u origin feature/ten-cong-viec
```

Sau đó tạo Pull Request để review. Không dùng `git add .` nếu thư mục có raw data, checkpoint, token, PII hoặc file runtime.

Nếu thay đổi còn dang dở:

```bash
git stash push -u -m "dang-do-truoc-khi-cap-nhat"
git switch main
git pull --ff-only origin main
git stash list
```

Chỉ `git stash pop` trên branch làm việc sau khi đã xem thay đổi mới. Nếu có conflict, giữ cả hai phía để đối chiếu rồi nhờ người phụ trách module review; không chọn “Accept All” hàng loạt.

## Sau khi pull cần làm gì?

```bash
python scripts/handoff.py up
python scripts/handoff.py smoke
```

Docker sẽ build lại phần source thay đổi. Với native Python environment, nếu file requirements đổi thì cài lại dependency trong `.venv` đúng hệ điều hành. Không copy `.venv` từ máy khác.

Nếu OpenAPI đổi, đội backend chạy:

```bash
python scripts/export_openapi.py
git diff contracts/claim_review_openapi.v1.json
```

Đội UI cập nhật theo contract mới và vẫn dùng `prototype/api-client.js` thay vì tự rải nhiều lệnh `fetch`.

## Git không tự mang theo model và dữ liệu riêng

`git pull` chỉ cập nhật code, config, contract và tài liệu. Các nội dung sau nằm ngoài Git:

- raw/processed data bị giới hạn quyền;
- checkpoint YOLO/LayoutLMv3 và artifact lớn;
- `.env`, token và credential;
- claim upload, analysis và audit trong `runtime/`.

Khi model có phiên bản mới, người phụ trách ML phải:

1. Đưa artifact vào artifact store/release được cấp quyền.
2. Cập nhật version, đường dẫn, metric, split và hash trong model registry.
3. Người nhận tải artifact đúng cấu trúc `artifacts/models/...`.
4. Chạy `scripts/check_live_readiness.py` và golden smoke.
5. Chỉ bật adapter nếu hash/dependency PASS.

Không ghi đè checkpoint cũ bằng file mới nhưng giữ nguyên version/hash. Nên phát hành `v2`, `v3` để rollback được.

## Quy trình nhóm đề xuất

```text
Tạo branch → sửa code/config → chạy test → cập nhật OpenAPI/registry nếu cần
→ Pull Request → review → merge main → thành viên git pull --ff-only
→ handoff.py up → smoke test
```

Mỗi bản demo/handoff nên có Git commit, release version, model hash và checksum ZIP. Nhờ đó nhóm có thể tiếp tục nâng cấp sau lần bàn giao này mà không mất lịch sử hoặc làm hỏng bản đang demo.
