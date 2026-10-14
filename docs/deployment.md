# Triển khai Git và CyberRangeCZ

## 1. Source và yêu cầu môi trường

Repo: `https://github.com/NguyenDuyTan18/demo-IDOR.git`, nhánh `main`. Dùng commit SHA đã push làm revision nếu muốn cố định bản cho luận văn. `topology.yml`, `training-definition.json` và `provisioning/` nằm tại root.

Cloud cần có image `kali`, `debian-12-x86_64`, flavor `standard.kali`, `standard.small`; các image có management user `debian`, sudo và SSH phù hợp. Đây là tên cấu hình phải xác nhận trên deployment của bạn, có thể sửa trước khi dựng pool. Platform tự bổ sung các node quản lý; topology gồm hai host và một gateway cho mỗi sandbox.

CIDR `10.80.0.0/24`, `10.90.0.0/24`, WAN `100.100.100.0/24` không được trùng management network/route hiện có. Mạng battle yêu cầu Nova hỗ trợ attach NIC và bốn VM nằm trong **cùng OpenStack project** có quyền dùng mạng mới.

Runner provisioning cần Ansible, passlib và `ansible.posix` 2.0.0. Role `user-access` pin v1.0.0 tại `provisioning/requirements.yml`. Server dùng Python stdlib, không cần pip trên VM. Provisioning cần apt/Git hoạt động. Nếu kiểm tra thủ công trên Linux controller:

```bash
python3 -m pip install -r requirements-runner.txt
ansible-galaxy role install -r provisioning/requirements.yml
ansible-galaxy collection install -r provisioning/requirements.yml
```

Không chạy `provisioning/playbook.yml` với inventory tự đoán; Sandbox Service cung cấp inventory và các biến `global_sandbox_id`, `global_ssh_public_user_key` cho mỗi allocation.

## 2. Dựng hai sandbox

1. Instructor vào **Sandbox Agenda → Sandbox Definitions → Create**.
2. Git URL: `https://github.com/NguyenDuyTan18/demo-IDOR.git`; Revision: `main` hoặc commit SHA. Không dùng link `/tree/main` trong trường clone URL.
3. Kiểm tra preview có `kali`, `web`, `gateway`, một practice-lan.
4. **Pools → Create**, chọn definition IDOR, size **2**; **Allocate** đủ hai sandbox, chờ networking/provisioning thành công.
5. Kiểm tra Ansible output: định danh sandbox ghi trên từng host, ServiceDesk hoạt động, Kali truy cập web `10.80.0.20:8080` trong sandbox mình.

Hai sandbox bước này còn độc lập. Không dùng pool cũ đã dựng từ revision trước để giả định tự nhận file mới. Dựng pool mới từ revision mới hoặc reprovision có kiểm soát; addon cần file identity từ playbook hiện tại.

## 3. Tạo phiên thực hành tự do

1. **Training Agenda → Linear Training Definitions → Upload**, chọn `training-definition.json`. Import thành bài IDOR mới.
2. Một Access Level tên `IDOR Battle Lab`; không bật variant sandboxes, không cấu hình câu hỏi IDOR/đáp án/APG. Passkey công khai `finish-idor-lab` chỉ đóng run. Review rồi Release.
3. Access Level hiển thị topology và console theo frontend chuẩn; không cần patch frontend.
4. Tạo **Training Instance**, chọn IDOR definition, **Cloud environment**, Start/End time và Assign Pool vừa dựng. Chia sẻ access token với hai trainee.
5. Hai tài khoản riêng mở hai run. Ghi bảng ánh xạ tại [trainee-access](trainee-access.md).

## 4. Cho hai đội truy cập web của nhau

Instructor làm theo [battle-network/README.md](../battle-network/README.md) sau khi có ánh xạ run thực tế. `battlectl.py` kiểm tra ánh xạ, sinh file Terraform/inventory cục bộ rồi điều phối Terraform và Ansible. Terraform chỉ tạo mạng/subnet/security group, bốn port và bốn attachment trên VM có sẵn. Ansible đặt IP NIC bổ sung dựa trên MAC rồi kiểm tra health của web đội kia.

Mạng chung được quản lý ngoài Terraform allocation của CyberRangeCZ. Vì vậy NIC bổ sung không xuất hiện tự động trong topology preview của platform; trainee xem địa chỉ ở `/home/user-access/battle-lab.txt`. Khi trả/huỷ pool, tháo addon trước; không dùng lại UUID/state của pool trước cho một pool mới.

## 5. Ghi nhận thực nghiệm

- Xác nhận A/B có hai run và hai sandbox khác nhau.
- Từ Kali A/B, health của web nội bộ mang UUID đội mình; health của URL đối phương mang UUID đội kia.
- Đăng nhập Alice, mở phiếu `1201` của Alice; đọc/cập nhật phiếu `1401` của Bob qua API để quan sát IDOR.
- Ghi owner, URL/IP đích, HTTP status, dữ liệu trước/sau và sandbox UUID. Thực nghiệm trên web đội kia phải đổi database của đội kia, không đổi database cục bộ.
- Dựng một phiên đối chứng với `lab_enforce_owner: true`; GET/POST phiếu của Bob trả 403. Đây là phiên triển khai riêng, không phải nút cấu hình do trainee được sudo.

Tham chiếu: [Sandbox Definition](https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/sandbox-definition/), [Pool](https://docs.platform.cyberrange.cz/user-guide-basic/sandbox-agenda/pool/), [Training Definition](https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-definition/linear-training-definition/), [provisioning và biến global sandbox UUID](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-provisioning/).
