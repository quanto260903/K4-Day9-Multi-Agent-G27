# Member Role Report — Day 9: Multi Agent A2A

> **LƯU Ý:** File này là khung nháp, phần 1-3 được điền sẵn dựa trên bằng chứng commit thật (`git log`). Các phần 4-8 (giải thích kỹ thuật, quyết định, blocker, hiểu biết end-to-end, cam kết) **PHẢI do chính bạn tự viết** dựa trên phần việc bạn thực sự làm — không sao chép, không để trống khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                          |
| --------------- | ---------------------------------- |
| Họ và tên       | Sái Hồng Anh                       |
| MSSV            | 2A202601018                        |
| Khóa/Lớp        | [K4]                                |
| Vai trò chính   | Domain Agent & Policy Agent developer |
| Ngày hoàn thành | [YYYY-MM-DD]                       |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Theo commit `ae9b9e6` ("update a", tài khoản `saihonganh-prog`):

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | ------------------- | ---------------- | ------------------ | ----------- |
| Delivery Agent | `src/agents/delivery_agent.py` (`DeliveryAgent.run`) | order timestamps, item shipping_limit_date từ DataStore | `delivery_variance_hours`, `seller_handoff_analysis`, `late_handoff_seller_ids` | [Tự đánh giá] |
| Order & Product Agent | `src/agents/order_product_agent.py` (`OrderProductAgent.run`) | order_id, DataStore | items, sellers_involved, product_ids, category_names | [Tự đánh giá] |
| Payment Agent | `src/agents/payment_agent.py` (`PaymentAgent.run`) | order_id, items từ Order&Product Agent | payment_reconciliation (item/freight/expected/payment total, reconciled) | [Tự đánh giá] |
| Policy Agent | `src/agents/policy_agent.py` (`PolicyAgent.run`) | evidence bundle từ Coordinator | case_assessment, root_cause, financial_resolution, resolution_actions | [Tự đánh giá] |
| Verifier Agent | `src/agents/verifier_agent.py` (`VerifierAgent.verify`) | output đã lắp ráp + evidence bundle | danh sách lỗi (schema/limit/ID) trước khi ghi file | [Tự đánh giá] |

Chỉ nhận ownership cho phần bạn **trực tiếp** viết/hiểu — nếu phần nào bạn không tự viết dù đứng tên commit, hãy ghi rõ và không nhận ownership.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | -------------------------------- | -------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ------------------------------ | ------------------- | --------------- |
| [Mô tả cụ thể] | [Đường dẫn file] | [Artifact/metrics/report] | [Lệnh/artifact] |

[Nêu một output cụ thể (ví dụ: kết quả chạy `python main.py`, số case pass Verifier) mà phần việc của bạn tạo ra hoặc giúp xác minh.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

[TODO: Phần của bạn giải quyết vấn đề gì trong pipeline?]

### Cách triển khai

[TODO: Mô tả thuật toán/quy tắc dữ liệu bạn triển khai — ví dụ công thức delivery_variance_hours, cách đối soát payment, cách áp EC_POLICY_V2 theo thứ tự ưu tiên, các check của Verifier. Không chỉ chép lại tên hàm.]

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
[TODO: Ghi lệnh thực tế đã chạy, ví dụ: python main.py]
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả.]
- **Artifact/log:** [Đường dẫn; không chứa secret.]

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** [TODO]
- **Các phương án đã cân nhắc:** [Ít nhất hai phương án.]
- **Phương án đã chọn:** [Lựa chọn.]
- **Lý do:** [Trade-off về correctness, data quality, reproducibility, cost hoặc độ phức tạp.]
- **Bằng chứng quyết định phù hợp:** [Metric, artifact hoặc kết quả thử nghiệm.]

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [TODO — che secret nếu có.]
- **Lệnh hoặc bước tái hiện:** [Lệnh/bước.]
- **Nguyên nhân gốc:** [Root cause, không chỉ mô tả triệu chứng.]
- **Cách xử lý:** [Thay đổi cụ thể.]
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

**Họ và tên:** Sái Hồng Anh
**Ngày xác nhận:** [YYYY-MM-DD]
