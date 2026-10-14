# Thiết kế thực nghiệm cho luận văn

## Câu hỏi nghiên cứu

1. Một definition Git có tái tạo được hai sandbox cùng mô hình Kali/web IDOR và đáp án APG riêng không?
2. Mạng overlay có cho phép truy cập chéo đúng đích khi hai sandbox dùng IP private trùng nhau không?
3. Kiểm tra quyền sở hữu đối tượng có chặn được request IDOR trong cùng điều kiện đăng nhập và kết nối không?

Đơn vị hạ tầng là hai sandbox của một pool, mỗi sandbox hai host/một router; hub VPN là thành phần bổ sung ngoài pool. Đơn vị chấm điểm mặc định của platform là Training Run và sandbox được gán cho run đó. Hai đội chỉ là cách tổ chức thực nghiệm, không phải hai nhóm host trong topology.

## Biến và điều kiện kiểm soát

| Thành phần | Thiết lập |
|---|---|
| Biến can thiệp bảo mật | `idor_enforce_owner=false` so với `true` |
| Biến kết nối | Trước khi bật và sau khi bật `wg-idor` |
| Kết quả quan sát | HTTP status, owner/ID trả về, sandbox identity, kết quả nộp APG, ping/handshake |
| Giữ cố định | Revision Git, image/flavor, phiên bản platform/runner, topology, account web, tài liệu 1001/1002 |
| Dữ liệu biến thể | `idor_flag` do platform sinh cho mỗi sandbox |

Ghi lại phiên bản platform, image ID thực tế, flavor, OS/kernel, commit SHA, pool ID, sandbox IDs và cách phân đội. Không chỉ ghi tên branch: pool mới phải dùng đúng revision được kiểm chứng.

## Trình tự thu thập bằng chứng

1. Dựng pool size 2; lưu allocation/provisioning output và ảnh topology của từng sandbox. Xác nhận mỗi sandbox đúng hai host, một router, cùng node quản lý do platform tự bổ sung.
2. Kiểm chứng trainee login ở cả hai Kali bằng console và user SSH config. Ghi lỗi thực tế nếu thất bại, không suy ra login đã thành công từ việc web trả HTTP 200.
3. Trước overlay, kiểm tra web nội bộ của từng sandbox. Không dùng cùng địa chỉ private để kết luận rằng request đã đi sang sandbox khác.
4. Dựng interconnect. Từ A ping Kali B và HTTP web B; từ B làm chiều ngược lại. Đối chiếu `/health` sandbox identity để chứng minh đúng đích; lưu handshake và route.
5. Đăng nhập alice, GET tài liệu 1001, đổi ID sang 1002. Ghi HTTP 200 và owner bob ở chế độ lỗi. Xác nhận request không session bị 401.
6. Nộp flag của web nội bộ theo từng run. Thực nghiệm nộp flag đối phương để ghi nhận platform không chấp nhận đáp án của sandbox khác. Nếu không kiểm tra bước này thì không tuyên bố đã chứng minh tính tách biệt của bộ chấm APG.
7. Tạo một lần triển khai đối chứng với `idor_enforce_owner=true`, giữ các điều kiện còn lại. Lặp lại request đã đăng nhập: tài liệu alice vẫn 200, tài liệu bob phải 403. Không đánh đồng việc đổi owner check với việc chặn đường mạng.
8. Chạy lại provisioning/interconnect để đánh giá khả năng lặp lại. Ghi downtime nếu service restart; hệ thống không được tạo key mới khi endpoint cũ còn tồn tại.

## Bảng ghi nhận trên cloud

Các ô dưới đây **chưa có kết quả**. Điền từ thực nghiệm thật, không lấy kết quả test local làm số liệu cloud.

| Mã | Thử nghiệm | Kỳ vọng | Kết quả thực tế | Bằng chứng |
|---|---|---|---|---|
| C01 | Console Kali A và B | Login thành công | Chưa chạy | |
| C02 | SSH trainee vào A và B | Đúng key/run, không sudo | Chưa chạy | |
| C03 | Kali nội bộ → web | HTTP 200, đúng sandbox | Chưa chạy | |
| C04 | Kali A ↔ Kali B | Ping được hai chiều | Chưa chạy | |
| C05 | Kali A → web B; Kali B → web A | HTTP 200, khác identity nội bộ | Chưa chạy | |
| C06 | IDOR không session | HTTP 401 | Chưa chạy | |
| C07 | Alice đọc tài liệu bob khi lỗi | HTTP 200 và flag của server đích | Chưa chạy | |
| C08 | Nộp APG đúng/sai sandbox | Đúng được nhận; đối phương bị từ chối | Chưa chạy | |
| C09 | Owner check bật | Tài liệu bob trả 403 | Chưa chạy | |
| C10 | Chạy lại provisioning/VPN | Không đổi key, cấu hình vẫn hoạt động | Chưa chạy | |

Trong báo cáo công khai, che flag, session cookie, private key và đường dẫn chứa dữ liệu cá nhân. Có thể so sánh SHA-256 của hai flag để chứng minh khác nhau mà không công bố đáp án. Password lab trong repo là fixture công khai, không được dùng làm password platform hay hub.

## Giới hạn của thực nghiệm

Ứng dụng mẫu lưu tài liệu cố định và session trong RAM; restart mất session. Server thư viện chuẩn phục vụ lab nhỏ, chưa đánh giá đồng thời nhiều người hoặc tải cao. Overlay hiện cho phép ICMP và HTTP 8080, không phải nối toàn bộ hai LAN hay management networks. Nguồn source hiện có là mô tả yêu cầu; cần đối chiếu ứng dụng IDOR gốc nếu luận văn phải bảo toàn nghiệp vụ cũ.
