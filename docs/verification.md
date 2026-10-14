# Bằng chứng kiểm tra và giới hạn

Kiểm tra local ngày 14/10/2026. Chưa đăng nhập deployment, chưa tạo pool, chưa attach NIC trên cloud và chưa triển khai frontend của người dùng.

## TDD: topology trong Training Run

User journey: trainee mở bài trên cloud và thấy topology/Open console của sandbox được gán, không cần sửa frontend của platform.

| Giai đoạn | Lệnh/đích kiểm tra | Kết quả |
|---|---|---|
| RED | `DefinitionTests` | Thất bại vì level còn là `INFO_LEVEL` và `topology.yml` thiếu `groups` |
| GREEN | `python -m unittest discover -s tests -v` | 20 tests đạt sau khi đổi sang `ACCESS_LEVEL`, thêm nội dung/passkey bắt buộc và group hợp lệ |
| Mã frontend tham chiếu | `updateTopologyAllowed` | Cho phép topology khi level type là Access và Training Instance không dùng local environment |

Topology chỉ mô tả một sandbox. Test không khẳng định UI có thể vẽ cạnh sang sandbox khác; mạng battle là attachment OpenStack ngoài Topology Definition và được xác minh bằng health check sau triển khai.

| Hạng mục | Kết quả |
|---|---|
| Python unittest | 20 tests đạt: web/session/IDOR, hai HTTP server riêng, schema lab và NIC helper |
| Coverage statement | app 97%, NIC helper 91%, tổng 95%; ngưỡng 80% đạt |
| Terraform | fmt/validate đạt với Terraform 1.16.6, OpenStack provider 3.4.0 |
| Terraform mock tests | 5 tests đạt: bốn port/attachment, không DHCP/gateway, từ chối placeholder/VM trùng/sai role/pool sai |
| Ansible | Cả provisioning và configure-guests đều đạt syntax-check trên Ansible core 2.20.10 |
| Topology trong Training Run | Definition dùng Access Level chuẩn; không phụ thuộc frontend patch |
| Dependency audit | pip-audit cho requirements-dev và requirements-runner: không phát hiện lỗ hổng đã biết trong bộ dependency được resolve lúc kiểm tra |

TDD: sáu tests NIC đầu tiên thất bại khi helper chưa tồn tại, sau đó đạt khi triển khai helper; bổ sung tests cho NetworkManager/networkd/oneshot, MAC sai, profile ngoại lai, IP chưa được đặt và default route thay đổi. Web có tests IDOR đọc/cập nhật, phiên đối chứng owner-check, phiên hết hạn, database và cookie tách riêng. Trình duyệt đã kiểm tra login đúng/sai, đọc/cập nhật phiếu và logout của cùng app ServiceDesk trong bản free-lab trước; giao diện app không thay đổi trong bản battle.

Mock Terraform thay thế OpenStack provider và module đọc VM hiện hữu. Ban đầu mock nested computed network không cung cấp IP mong đợi; tách discovery module và override output trong tests. Những tests này không chứng minh Nova UUID thật, quota/project, security group, hot-plug hoặc dữ liệu trả về của cloud deployment.

NIC tests dùng filesystem/command runner giả lập. Cần kiểm tra bốn VM thật, routing, HTTP hai chiều và sau reboot. Ansible syntax-check không phải provisioning thành công trên VM.

Backend training tham chiếu: `fe3930412eefb2cf343b2e172df6d81cebf3041b`. Access Level là loại level chuẩn dành cho truy cập cloud và yêu cầu passkey; source không sửa frontend v2026.02. Chưa chạy cloud E2E trên deployment thật.

## Kiểm tra chấp nhận trên deployment

1. Hai tài khoản portal mở run bằng cùng token, nhận hai sandbox ID khác nhau.
2. Kali console/SSH của mỗi trainee tới đúng sandbox; identity và health mang UUID tương ứng.
3. Terraform plan chỉ tạo addon và attach đúng bốn VM; LAN/management gốc hoạt động.
4. Kali A truy cập web B `.22`; Kali B truy cập web A `.12`, health khớp UUID đội kia.
5. API trên web đối phương cho đọc/cập nhật phiếu Bob khi đã đăng nhập Alice; database bên đích thay đổi, web nội bộ không thay đổi.
6. Reboot thử theo lịch thực nghiệm, NIC giữ IP và HTTP hai chiều hoạt động.

## Tự đánh giá

| Tiêu chí | Điểm /5 | Bằng chứng và điểm cần cải thiện |
|---|---|---|
| Chính xác | 4 | Python/Ansible/Terraform kiểm tra đạt; cần xác nhận topology và mạng battle trên cloud thật |
| Đầy đủ | 4 | Có source, cấu hình mạng, hướng dẫn hai run/sandbox, Git/ZIP; chưa có credentials để nghiệm thu deployment |
| Rõ ràng | 4 | Bảng phân biệt portal ID/UUID, địa chỉ hai đội; thuật ngữ Nova/Neutron còn cần nền tảng OpenStack |
| Thực hiện được | 4 | Có tfvars/inventory mẫu, lệnh plan/apply, health và mapping guard; operator phải điền ID thực tế |
| Ngắn gọn | 4 | README dẫn tới hướng dẫn riêng; tài liệu triển khai vẫn dài vì có hai bước platform và cloud |

Trung bình: **4.0/5**. Cải thiện ưu tiên: chạy nghiệm thu cloud hai chiều và reboot; ghi lại run/sandbox/VM, topology và HTTP evidence trong luận văn. Người dùng có thể đồng ý với đánh giá này nếu phân biệt rõ source đã kiểm tra với deployment chưa chạy.
