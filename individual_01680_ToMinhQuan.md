# Member Role Report — Day 9: Multi Agent A2A

> **LƯU Ý:** File này là khung nháp, phần 1-3 được điền sẵn dựa trên bằng chứng commit thật (`git log`). Các phần 4-8 (giải thích kỹ thuật, quyết định, blocker, hiểu biết end-to-end, cam kết) **PHẢI do chính bạn tự viết** dựa trên phần việc bạn thực sự làm — không sao chép, không để trống khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                          |
| --------------- | ---------------------------------- |
| Họ và tên       | Tô Minh Quân                       |
| MSSV            | 2A202601680                        |
| Khóa/Lớp        | [K4]                                |
| Vai trò chính   | Data layer, LLM client, Policy rules engine, orchestration & kiến trúc |
| Ngày hoàn thành | [YYYY-MM-DD]                       |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Theo commit `754685e` ("commit ai agent", tài khoản `quanto260903`):

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | ------------------- | ---------------- | ------------------ | ----------- |
| Kiến trúc hệ thống | `architecture.md` | Đề bài README, cấu trúc CSV Olist | Sơ đồ agent, vai trò/quyền truy cập, luồng handoff | [Tự đánh giá] |
| Cấu hình & giới hạn | `src/config.py` | — | Model name/params, đường dẫn, `LIMITS` (giới hạn mảng theo schema) | [Tự đánh giá] |
| Tầng đọc dữ liệu | `src/data_store.py` (`DataStore`) | 9 CSV Olist trong `data/` | Index tra cứu order/customer/item/payment/seller/product theo ID | [Tự đánh giá] |
| LLM client | `src/llm_client.py` (`chat`, `chat_json`) | system/user prompt | Gọi Ollama, retry, fallback an toàn khi model không khả dụng | [Tự đánh giá] |
| Policy rules engine | `src/policy_rules.py` (`apply_policy`) | Evidence bundle | primary/secondary issue, root cause, refund, action, evidence_ids theo EC_POLICY_V2 | [Tự đánh giá] |
| Trace logger | `src/trace_logger.py` | case_id, agent, event, data | `logging/trace.jsonl` (không append lịch sử cũ) | [Tự đánh giá] |
| Entry point | `main.py` | `input/EC_*.json` | `output/EC_*.json`, `logging/metadata.json` | [Tự đánh giá] |

Chỉ nhận ownership cho phần bạn **trực tiếp** viết/hiểu — nếu phần nào bạn không tự viết dù đứng tên commit, hãy ghi rõ và không nhận ownership.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | -------------------------------- | -------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| [Mô tả cụ thể] | [Đường dẫn file] | [Artifact/metrics/report] | [Lệnh/artifact] |

Ví dụ output cụ thể có thể dùng: chạy `python main.py` cho ra 50/50 case pass Verifier (0 lỗi), số liệu `delivery_variance_hours`/`item_total_brl`/`freight_total_brl` của case EC_002 khớp chính xác với ví dụ mẫu trong README mục 6 — xác nhận `policy_rules.py` và `data_store.py` tính đúng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

[TODO: Phần của bạn giải quyết vấn đề gì trong pipeline?]

### Cách triển khai

[TODO: Mô tả cách DataStore index CSV để tra cứu O(1), vì sao Policy Agent tách phần tính toán deterministic (`policy_rules.py`) ra khỏi LLM để tránh hallucination số tiền/ID, cách LLM client fallback khi Ollama không khả dụng, thứ tự ưu tiên áp EC_POLICY_V2. Không chỉ chép lại tên hàm.]

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ------------------------ | ---------------------------------------- |
| Input                    | [Schema, artifact hoặc tham số]         |
| Output                   | [Schema, artifact hoặc giá trị trả về]  |
| Module phụ thuộc         | [Module/file liên quan]                 |
| Module sử dụng output    | [Module/file liên quan]                 |
| Điều kiện lỗi cần xử lý  | [Trường hợp thực tế]                    |

### Cách xác minh

```bash
python main.py
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả — ví dụ số case pass/fail, thời gian chạy từ `logging/metadata.json`.]
- **Artifact/log:** `logging/trace.jsonl`, `logging/metadata.json`, `output/EC_*.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [TODO — ví dụ: quyết định tách tính toán số tiền/ngày giờ khỏi LLM.]
- **Các phương án đã cân nhắc:** [Ít nhất hai phương án.]
- **Phương án đã chọn:** [Lựa chọn.]
- **Lý do:** [Trade-off về correctness, data quality, reproducibility, cost hoặc độ phức tạp.]
- **Bằng chứng quyết định phù hợp:** [Metric, artifact hoặc kết quả thử nghiệm.]

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [TODO — che secret nếu có. Ví dụ tham khảo: `TypeError: strptime() argument 1 must be str, not float` khi đọc timestamp rỗng của order canceled/unavailable.]
- **Lệnh hoặc bước tái hiện:** [Lệnh/bước.]
- **Nguyên nhân gốc:** [Root cause, không chỉ mô tả triệu chứng — ví dụ: pandas suy diễn ô CSV trống thành NaN (float) khi dùng `na_values=[""]` cùng `dtype=str`.]
- **Cách xử lý:** [Thay đổi cụ thể — ví dụ: bỏ `na_values`, giữ `keep_default_na=False` để ô trống là chuỗi rỗng.]
- **Cách xác minh sau khi sửa:** [Lệnh và kết quả.]
- **Điều học được:** [Bài học kỹ thuật.]

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

[TODO: Giải thích ngắn gọn bằng lời của bạn — không sao chép từ báo cáo nhóm hoặc thành viên khác:]

1. Dữ liệu đi từ CSV Olist đến evidence bundle như thế nào?
2. `claimed_order_id` trong input được dùng để join các CSV ra sao?
3. Verifier Agent kiểm tra những gì trước khi cho phép ghi output?
4. Vì sao Policy Agent không được đọc CSV thô mà chỉ nhận evidence bundle?
5. Case bị coi là hard-gate/fail dựa trên tiêu chí nào?

**Câu trả lời:**

[Viết câu trả lời tại đây.]

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Tô Minh Quân
**Ngày xác nhận:** [YYYY-MM-DD]
