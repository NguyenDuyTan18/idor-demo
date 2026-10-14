# Cấp mỗi trainee một sandbox khác nhau

Sandbox được gán theo **Training Run của tài khoản portal**, không theo tài khoản Linux hay tài khoản web. Hai người có thể dùng cùng token của Training Instance nhưng phải đăng nhập bằng hai tài khoản CyberRangeCZ khác nhau.

## Instructor chuẩn bị

1. Pool IDOR có size **2**, đã Allocate hai sandbox và provisioning thành công. Chỉ đặt size 2 chưa tạo VM.
2. Training Definition IDOR đã import/review/Release; Training Instance dùng **cloud environment**, gắn đúng pool và có Start/End time hợp lệ. Sao chép access token của chính instance đó.
3. Trainee A và Trainee B có quyền trainee. Cho hai người mở bằng hai máy/profile trình duyệt khác nhau để giữ riêng phiên đăng nhập.
4. Access Level hiển thị topology và Open console theo chức năng gốc. Chuẩn bị user SSH bundle riêng của từng sandbox làm đường truy cập dự phòng.

## Hai người vào lab

1. Trainee A đăng nhập portal bằng tài khoản A; vào **Trainings → Run**, nhập token của instance.
2. Trainee B đăng nhập portal bằng tài khoản B và nhập **cùng token**.
3. Backend tìm sandbox còn trống trong pool và khóa/gán nó cho run. A và B nhận hai sandbox khác nhau. Instructor đối chiếu run ID và sandbox ID; không đoán theo thứ tự allocation.
4. Mỗi người mở topology trong run của mình, chọn **kali → Open console**, đăng nhập Linux `user-access / ClientLab-Only-2026!`. Kali của A thuộc sandbox A; Kali của B thuộc sandbox B.
5. Trong lúc thực hành giữ run đang mở. Khi kết thúc, nhập passkey công khai `finish-idor-lab`; đây chỉ là thao tác đóng run, không phải đáp án bài IDOR.

Mở hai tab bằng **cùng tài khoản portal** thường tiếp tục cùng run đang mở; đó không phải cách lấy hai sandbox. Nếu một đội có nhiều thành viên nhưng tổng pool chỉ có hai sandbox, mỗi đội dùng một đại diện mở run và phối hợp trên Kali của đội. Group trên portal không tự biến nhiều run thành một sandbox chung.

## Bảng gán thực tế

Instructor điền bảng sau sau khi A/B đã mở run:

| Đội | Tài khoản portal | Run ID | Sandbox ID trên portal | Sandbox UUID | Nova UUID Kali | Nova UUID web |
|---|---|---|---|---|---|---|
| A | tài khoản đại diện A | thực tế | thực tế | thực tế | thực tế | thực tế |
| B | tài khoản đại diện B | thực tế | thực tế | thực tế | thực tế | thực tế |

Sandbox ID dạng số trên portal có thể khác **sandbox UUID** truyền vào `global_sandbox_id`. Terraform cần UUID; không nhập run ID/pool ID vào trường này. Management SSH tới từng host có thể đọc `/etc/idor-free-lab-identity.json` để kiểm tra UUID và role. Lấy Nova VM UUID từ inventory/state allocation hoặc OpenStack, rồi đối chiếu đúng sandbox. Không suy ra chỉ từ IP vì hai LAN có IP trùng nhau.

Tài khoản A không được bảo đảm luôn nhận sandbox allocation đầu tiên. Trong `terraform.tfvars`, `teams.A` là sandbox **đã gán thực tế cho người A**. Bảng trên là cơ sở điền cấu hình mạng.

## SSH và trình duyệt cá nhân

Mỗi trainee chỉ nhận **user SSH config/key của sandbox mình**. Management SSH config/key dành cho instructor triển khai, không gửi cho trainee. Dùng bundle A để vào Kali A; bundle B để vào Kali B:

```bash
ssh -F /path/to/own-user-config kali
cat /home/user-access/battle-lab.txt
curl --noproxy '*' http://10.80.0.20:8080/health
```

Từ Kali A kiểm tra đối phương bằng `http://10.90.0.22:8080/health`; từ Kali B dùng `http://10.90.0.12:8080/health`. Trường `sandbox` trong JSON health phải là UUID của **đội kia**. Hai web dùng session riêng, nên cần đăng nhập lại trên URL đối phương.

Nếu Kali image chưa có GUI/VNC, dùng terminal hoặc mở web trên máy cá nhân qua tunnel tới **Kali của mình**:

```bash
# Ví dụ trainee A muốn mở web đội B
ssh -F /path/to/own-user-config -N -L 18080:10.90.0.22:8080 kali
```

Mở `http://127.0.0.1:18080`. Với trainee B, thay đích thành `10.90.0.12:8080`. Với web của chính sandbox mình, dùng đích `10.80.0.20:8080`.

## Khi không vào được

Thông báo **“There is no active training session matching access token”** trong ảnh là lỗi tìm Training Instance đang hoạt động theo token, xảy ra trước bước truy cập Kali. Kiểm tra token đúng instance, thời gian Start/End và múi giờ/server clock; tạo Sandbox Definition/pool không tự tạo phiên training đang hoạt động.

Nếu run mở nhưng báo thiếu sandbox, kiểm tra hai sandbox đã Allocate/provision xong, pool được assign đúng instance và không bị run khác chiếm. Nếu Access Level không thấy topology, kiểm tra Training Instance đang dùng cloud environment, pool đã được gán và trainee có role sandbox trainee. Nếu web nội bộ được nhưng web đội kia không được, kiểm tra bước Terraform/Ansible của mạng battle; pool size 2 tự nó không nối mạng.

Nguồn: [Training Instance](https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-instance/), [Training Run](https://docs.platform.cyberrange.cz/user-guide-basic/training-agenda/training-run/linear-training-run/), [backend cấp/tiếp tục run](https://github.com/cyberrangecz/backend-training/blob/fe3930412eefb2cf343b2e172df6d81cebf3041b/training-service/src/main/java/cz/cyberrange/platform/training/service/facade/TrainingRunFacade.java).
