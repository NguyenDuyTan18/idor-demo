# Mạng battle giữa hai sandbox

Phần này được instructor triển khai **sau** CyberRangeCZ allocation. Nó tạo đúng một mạng Neutron trong cùng project và gắn thêm một NIC vào Kali/web của mỗi sandbox. Không tạo VM hoặc gateway mới; gateway gốc của mỗi sandbox vẫn phục vụ LAN riêng.

| Alias | IP mới | Đích web đối phương |
|---|---|---|
| team-a-kali | 10.90.0.11/24 | http://10.90.0.22:8080 |
| team-a-web | 10.90.0.12/24 | — |
| team-b-kali | 10.90.0.21/24 | http://10.90.0.12:8080 |
| team-b-web | 10.90.0.22/24 | — |

DHCP và gateway tắt trên subnet mới. Security group chỉ cho IPv4 ICMP và TCP 8080 trong `10.90.0.0/24`. Trainee truy cập dịch vụ IDOR của đối phương qua mạng này; SSH quản lý dùng mạng gốc.

## Chuẩn bị trên Linux instructor controller

- Terraform >=1.7,<2, OpenStack provider 3.x; lockfile hiện pin 3.4.0.
- Ansible và dependencies ở `requirements-runner.txt`.
- Cloud credentials có quyền Neutron/Nova attach interface trong cùng project, đặt trong `clouds.yaml` ngoài Git hoặc biến môi trường `OS_*` theo cấu hình hiện có.
- Hai management SSH config của **hai sandbox thực tế đã gán**, chỉ instructor sử dụng. Giải nén bundle theo hướng dẫn deployment và thử alias `kali`, `web` của từng config.
- Bảng run → sandbox UUID → Nova VM UUID đã đối chiếu. `/etc/idor-free-lab-identity.json` trên từng host phải đúng UUID và role.

Mạng `10.90.0.0/24` phải không trùng route hiện có. Helper từ chối overlap với NIC khác và kiểm tra default route trước/sau, nhưng không thay thế kiểm tra cloud của operator.

## 1. Điền định danh thực tế

Từ root repo:

```bash
cp battle-network/terraform/terraform.tfvars.example battle-network/terraform/terraform.tfvars
cp battle-network/inventory.example.yml battle-network/inventory.yml
```

Trong `terraform.tfvars`, thay `pool_id`, cloud profile và cả sáu UUID. `teams.A` phải khớp sandbox được cấp cho tài khoản đội A, tương tự B. VM UUID là Nova ID, không phải tên `kali`/`web`. Hai sandbox UUID và bốn VM UUID phải khác nhau. Nếu dùng xác thực `OS_*`, đặt `cloud_name = null`.

Trong `inventory.yml`, thay hai đường dẫn `/absolute/path/...-management-config` bằng SSH config tương ứng. `ansible_user: debian` phải khớp management user của image. Với đường dẫn có khoảng trắng cần quote đúng trong SSH args. Giữ tùy chọn tắt SSH multiplex để hai alias trùng tên không dùng nhầm kết nối.

## 2. Xem plan và triển khai

```bash
cd battle-network/terraform
terraform init
terraform validate
terraform plan -out=battle.tfplan
```

Kiểm tra selected VM names/UUID, bốn địa chỉ và project trong plan. Cấu hình có đọc VM hiện hữu, kiểm tra Kali có IP gốc `.10`/web `.20`; không tạo compute instance. Không đổi UUID để ép plan qua nếu ánh xạ sai.

Sau khi operator đã review plan:

```bash
terraform apply battle.tfplan
terraform output -json > ../cloud-outputs.json
cd ../..
ansible-playbook -i battle-network/inventory.yml battle-network/configure-guests.yml
```

`cloud-outputs.json` chứa UUID port, MAC và mapping của bốn VM. Guest playbook kiểm tra identity thực tế trước khi sửa NIC, chọn NIC theo MAC, đặt IP tĩnh, bật dịch vụ tự cấu hình khi boot và kiểm tra HTTP đối phương. NetworkManager hoặc systemd-networkd được dùng nếu đang chạy; nếu không, oneshot đặt IP bằng `ip` mỗi lần boot. Không restart NIC quản lý.

Nếu hot-plug chưa tạo NIC trong guest, kiểm tra trạng thái Nova/hypervisor trước khi chạy lại playbook. Nếu playbook dừng tại identity/MAC/default route, đọc lỗi và đối chiếu mapping; không bỏ assert. Sau reboot VM, kiểm tra lại `ip -4 addr`, `ip route`, `systemctl status idor-battle-nic` và health hai chiều.

## 3. Trainee thực hành

Từ Kali A:

```bash
cat ~/battle-lab.txt
curl --noproxy '*' http://10.90.0.22:8080/health
curl --noproxy '*' -sS -c /tmp/idor-opponent.cookies \
  -d 'username=alice&password=IdorLab-Only-2026!' http://10.90.0.22:8080/login
curl --noproxy '*' -sS -b /tmp/idor-opponent.cookies http://10.90.0.22:8080/api/tickets/1401
curl --noproxy '*' -sS -b /tmp/idor-opponent.cookies \
  -d 'status=closed' http://10.90.0.22:8080/api/tickets/1401
```

Từ Kali B thay URL bằng `http://10.90.0.12:8080`. Endpoint yêu cầu đăng nhập nhưng mặc định thiếu kiểm tra owner. Dùng cookie riêng cho từng web; ghi kết quả vào báo cáo, không nộp đáp án trong training.

## 4. Thu hồi mạng khi kết thúc

Instructor ngừng phiên thực hành, dừng/tắt `idor-battle-nic` trên bốn VM bằng management access. Với NetworkManager, hạ/xoá profile `idor-battle`; với networkd, gỡ riêng file `00-idor-battle.network` do lab tạo và reload cấu hình. Không sửa profile/file của NIC khác.

Trong thư mục Terraform đã dùng, xem `terraform plan -destroy` rồi operator chạy `terraform destroy` để tháo attachment và xoá tài nguyên **của addon**. VM gốc là data source, không do module này quản lý. Thực hiện trước khi trả/huỷ pool. Giữ Terraform state riêng tư để có thể thu hồi đúng tài nguyên; không commit state/plan, credentials, management bundle hoặc inventory thật lên Git.

## Giới hạn kiểm tra

Terraform mock tests và Ansible syntax-check đã chạy; chưa thực thi Nova/Neutron hoặc helper trên VM thật. Boot persistence và HTTP qua mạng thật phải được xác nhận trên cloud của bạn. Cấu hình này không phù hợp khi mỗi sandbox nằm trong một OpenStack project khác nhau mà chưa có cơ chế chia sẻ mạng do operator thiết kế.

Tham chiếu: [OpenStack network API](https://docs.openstack.org/openstacksdk/latest/user/proxies/network.html), [compute API](https://docs.openstack.org/openstacksdk/latest/user/proxies/compute.html), [Terraform mock testing](https://developer.hashicorp.com/terraform/language/tests/mocking).
