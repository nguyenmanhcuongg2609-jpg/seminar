# Kết quả benchmark: có Redis vs không Redis

- Thời điểm: 2026-10-15 14:47
- Máy: 12th Gen Intel(R) Core(TM) i7-12700H, 20 luồng CPU, Windows 11, Python 3.12.2
- Mỗi cấu hình chạy 1 lần, lấy trung vị (**chế độ chạy thử --quick, không dùng cho slide**)
- Truy vấn nặng: thông tin sản phẩm + điểm đánh giá + 5 sản phẩm tương tự (SQLite, 300.000 đánh giá)
- Truy vấn nhẹ: lấy 1 sản phẩm theo khóa chính

| Kịch bản | Trường hợp | req/s | p50 (ms) | p95 (ms) | p99 (ms) | Lỗi % | Số truy vấn DB | Cache hit % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1. Độ trễ khi ít tải (1 người dùng) | Không Redis | 5.3 | 183.3 | 230.9 | 283.3 | 0.00 | 100 | - |
| 1. Độ trễ khi ít tải (1 người dùng) | Có Redis | 384.2 | 2.2 | 3.5 | 4.3 | 0.00 | 0 | 100.0 |
| 2-10. Chịu tải: 10 người dùng đồng thời | Không Redis | 40.0 | 245.1 | 262.0 | 287.5 | 0.00 | 207 | - |
| 2-10. Chịu tải: 10 người dùng đồng thời | Có Redis | 790.6 | 12.2 | 21.2 | 28.4 | 0.00 | 0 | 100.0 |
| 2-50. Chịu tải: 50 người dùng đồng thời | Không Redis | 40.4 | 1,143.8 | 1,531.7 | 1,749.8 | 0.00 | 235 | - |
| 2-50. Chịu tải: 50 người dùng đồng thời | Có Redis | 681.4 | 67.7 | 108.8 | 136.3 | 0.00 | 0 | 100.0 |
| 3. Truy cập thực tế (80% vào 20% sản phẩm hot) | Không Redis | 59.6 | 719.6 | 1,199.0 | 1,250.5 | 0.00 | 348 | - |
| 3. Truy cập thực tế (80% vào 20% sản phẩm hot) | Có Redis | 153.0 | 64.0 | 1,112.4 | 1,260.7 | 0.00 | 218 | 74.3 |
| 4. Cache lạnh vs cache nóng (50 người dùng, 10 giây) | Cache lạnh | 55.5 | 1,015.4 | 1,523.9 | 1,723.2 | 0.00 | 232 | 26.3 |
| 4. Cache lạnh vs cache nóng (50 người dùng, 10 giây) | Cache nóng | 146.4 | 64.6 | 1,127.5 | 1,225.6 | 0.00 | 220 | 72.9 |
| 5a. Phản ví dụ: truy vấn nhẹ, 1 người dùng | Không Redis | 453.5 | 2.0 | 3.3 | 3.7 | 0.00 | 100 | - |
| 5a. Phản ví dụ: truy vấn nhẹ, 1 người dùng | Có Redis | 274.0 | 3.3 | 5.2 | 6.1 | 0.00 | 0 | 100.0 |
| 5b. Phản ví dụ: truy vấn nhẹ, 50 người dùng | Không Redis | 791.1 | 55.4 | 95.3 | 173.0 | 0.00 | 3,976 | - |
| 5b. Phản ví dụ: truy vấn nhẹ, 50 người dùng | Có Redis | 779.5 | 61.0 | 83.6 | 97.1 | 0.00 | 0 | 100.0 |
