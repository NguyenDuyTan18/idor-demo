# IDOR Battle Lab — CyberRangeCZ

Hai trainee dùng hai sandbox riêng trong **một pool size 2**. Mỗi sandbox có Kali, web ServiceDesk chứa lỗi IDOR và gateway. Hai LAN riêng vẫn được giữ; instructor gắn thêm một mạng Neutron chung vào bốn VM để hai đội truy cập web của nhau. Không cần thêm VM hub.

```text
Pool size 2
  Sandbox A: Kali 10.80.0.10 ── LAN A ── web 10.80.0.20:8080
  Sandbox B: Kali 10.80.0.10 ── LAN B ── web 10.80.0.20:8080

  Mạng battle chung 10.90.0.0/24, một network UUID trên OpenStack:
    Kali A .11      web A .12:8080
    Kali B .21      web B .22:8080
    Kali A → web B; Kali B → web A
```

Đây là lab thực hành tự do: **không có câu hỏi IDOR, flag hoặc APG**. Training Definition dùng một Access Level để CyberRangeCZ hiển thị topology và Open console theo cơ chế gốc. Access Level bắt buộc có passkey; `finish-idor-lab` được công khai trong nội dung và chỉ dùng để kết thúc run. Các web có database/session riêng; hai đội thực nghiệm quyền đọc và cập nhật phiếu của đối phương, ghi kết quả vào báo cáo luận văn.

## Cấu trúc Git

```text
topology.yml
training-definition.json
requirements-{dev,runner}.txt
app/{portal.py,portal.html}
provisioning/
  playbook.yml
  requirements.yml
  group_vars/all.yml
  files/servicedesk.service
battle-network/
  terraform/{versions,variables,main,outputs}.tf
  terraform/terraform.tfvars.example
  terraform/.terraform.lock.hcl
  terraform/modules/existing-vms/main.tf
  terraform/tests/battle.tftest.hcl
  configure-guests.yml
  inventory.example.yml
  guest/configure_nic.py
tests/{test_lab,test_battle_nic}.py
docs/{deployment,trainee-access,verification}.md
```

Đặt `topology.yml` ở **root repo**. `topology.yml` mô tả một sandbox; pool size 2 dựng hai bản. Khai báo mạng battle trong topology sẽ tạo hai mạng khác nhau, vì vậy mạng chung được triển khai riêng bằng `battle-network/terraform` sau allocation. Sandbox Service không tự chạy thư mục bổ sung này.

## Triển khai

1. Kiểm tra tên image/flavor và management user trong `topology.yml` tồn tại trên cloud. CIDR của lab phải không trùng management network hoặc route đang dùng.
2. Tạo Sandbox Definition từ `https://github.com/NguyenDuyTan18/demo-IDOR.git`, revision **master** hoặc commit SHA đã push. Tạo pool size 2 và Allocate đủ hai sandbox.
3. Import `training-definition.json` thành definition mới, review/Release rồi tạo Training Instance: cloud environment, gán pool trên, Start/End time đang có hiệu lực.
4. Hai tài khoản portal khác nhau dùng cùng access token của instance, mỗi tài khoản mở một Training Run. Instructor ghi lại trainee → run → sandbox → VM thực tế.
5. Điền UUID thật vào Terraform, xem plan rồi triển khai mạng chung bằng tài khoản cloud của instructor. Chạy playbook cấu hình NIC theo đúng management SSH config của từng sandbox.

Chi tiết: [triển khai](docs/deployment.md), [cấp và truy cập sandbox](docs/trainee-access.md), [mạng hai đội](battle-network/README.md).

Access Level làm topology và Open console xuất hiện mà không cần sửa hoặc build lại frontend v2026.02. Sơ đồ chỉ biểu diễn Kali, web, gateway và LAN thuộc sandbox của run hiện tại. Mạng battle nối sang sandbox còn lại được gắn sau allocation nên không xuất hiện thành một cạnh trên sơ đồ; địa chỉ đối phương nằm trong nội dung level và `/home/user-access/battle-lab.txt`.

## Địa chỉ và tài khoản lab

| Truy cập | Giá trị |
|---|---|
| Linux trên Kali của mỗi người | `user-access / ClientLab-Only-2026!` |
| Web nội bộ trong sandbox mình | `http://10.80.0.20:8080` |
| Web đội A qua mạng chung | `http://10.90.0.12:8080` |
| Web đội B qua mạng chung | `http://10.90.0.22:8080` |
| Đăng nhập ServiceDesk | `alice / IdorLab-Only-2026!` |

Đây là tài khoản fixture công khai, cấu hình ở `provisioning/group_vars/all.yml`. Tài khoản portal quyết định sandbox được cấp; tên Linux giống nhau không có nghĩa hai người dùng chung VM. Kali có file `/home/user-access/battle-lab.txt` ghi đội và URL đối phương sau khi nối mạng.

## Kiểm tra source

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m coverage run --source=app,battle-network/guest -m unittest discover -s tests -v
python3 -m coverage report --fail-under=80
cd battle-network/terraform
terraform init
terraform fmt -check -recursive
terraform validate
terraform test
```

Terraform tests dùng mock, không dựng cloud. Kết quả và giới hạn: [verification](docs/verification.md). Việc push source không tạo pool, không nối mạng cloud và không triển khai frontend.
