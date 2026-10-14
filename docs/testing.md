# Kiểm tra bản IDOR riêng

Ngày kiểm tra: 14/10/2026.

- 28 test pass: 24 test app HTTP/config và 4 kiểm tra liên kết topology, training/APG, role server và quyền truy cập attacker.
- Coverage app: 121 statements, 21 missed, **83%**. Những phần còn thiếu chủ yếu ở CLI và các lỗi HTTP malformed.
- Topology `idor-apg` pass parser chính thức `TopologyDefinition.from_file` (upstream package 2.2.0, backend-sandbox-platform commit 0c39cf3f9118ddc6320c081a8169af3bdb640c51).
- Tất cả YAML/JSON parse thành công. Biến APG `idor_flag` khớp Training Level và config mà server role inject.
- Ansible core 2.21.5 trong Linux/WSL: `ansible-playbook --syntax-check` pass với inventory có hosts/server/attacker/router và role user-access v1.0.0, ansible.posix 2.1.0.
- Local Git repo đã init branch main, chưa có commit hoặc remote. Không push hay tạo resources platform.

App được tái sử dụng từ service IDOR đã kiểm tra trước đó; lần này kiểm tra lại HTTP và thay topology/config/training cho repo riêng. Không lấy nội dung FTP/backdoor của mẫu. Mẫu tại D:/demo-trainning-APG không được script áp dụng thay đổi.

Các kiểm tra local chưa xác nhận image/flavor thực tế, allocation cloud, router isolation, provisioning trên VM, APG answer storage hoặc import/chấm bài trong Training Service. Các bước đó cần instance CyberRangeCZ của bạn. Role server và attacker đã có HTTP health checks để phát hiện lỗi khi provisioning thật.

Chạy lại bằng `python3 -m unittest discover -s tests -v` sau khi cài requirements-dev.txt trong venv. Syntax-check không thực thi task Ansible.
