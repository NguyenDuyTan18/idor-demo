# Truy cập được web nhưng không vào được sandbox

Hai kiểm tra này đi qua các thành phần khác nhau. `/health` thành công chứng minh web và đường HTTP đang hoạt động; không chứng minh tài khoản Linux, SSH key hoặc Guacamole hoạt động. Chưa có log của deployment hiện tại, nên nguyên nhân dưới đây là các khả năng cần phân biệt, không phải kết luận chẩn đoán đã xác nhận.

| Biểu hiện | Kiểm tra phù hợp |
|---|---|
| Đang ở Training Definition Preview | Chuyển sang Pool Detail hoặc Training Run thật; Preview dùng topology giả |
| Open console đóng ngay sau nhập mật khẩu | Xác nhận Linux user `user-access`, không dùng tài khoản web `alice`; kiểm tra password auth và trạng thái account |
| Console timeout trước khi đăng nhập | Kiểm tra Guacamole, SSH port, access path, trạng thái allocation; thay mật khẩu không sửa lỗi transport |
| SSH bằng user-config báo Permission denied | Dùng bundle của đúng run/sandbox, kiểm tra public key của run trong authorized_keys của attacker |
| Open console SSH được nhưng Open GUI không được | Xác nhận Kali image có desktop/VNC/RDP và GUI metadata; repo không cài GUI server |
| IP nội bộ trả web của mình thay vì đối phương | Dùng `10.200.0.12/.22`, không dùng địa chỉ private trùng `10.30.20.5` |
| VPN không có handshake | Kiểm tra endpoint/UDP 51820, egress của cả server và Kali, key và security group của hub |

## Các thay đổi trong source mới

Host attacker dùng role `user-access` v1.0.0, có password lab được cấu hình, shell `/bin/bash`, không được sudo và dùng public key do platform cấp. File `00-idor-user-access.conf` đặt rule cho đúng user trước các drop-in phổ biến của image. Provisioning chạy `sshd -t`, đọc `sshd -T -C ...`, xác nhận cả password/public-key auth và account không khóa.

OpenSSH thường dùng giá trị đầu tiên nhận được cho từng keyword, vì vậy chỉ thêm `PasswordAuthentication yes` vào một file `99-*` có thể chưa đủ. Nguồn: [sshd_config](https://man.openbsd.org/sshd_config). Các rule AllowUsers/DenyUsers, PAM hoặc Match theo địa chỉ riêng của image vẫn cần kiểm tra trên VM thật.

## Lệnh instructor chẩn đoán

Dùng **management SSH config đúng sandbox**, rồi thực hiện trên attacker:

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C user=user-access,host=attacker,addr=<IP-nguồn-kết-nối-thật>
sudo passwd -S user-access
getent passwd user-access
sudo systemctl status ssh --no-pager
sudo journalctl -u ssh -n 80 --no-pager
```

Chạy `ssh -vvv -F <user-config> attacker` từ máy trainee để xác định lỗi key hay transport. Nếu SSH bằng user-config hoạt động nhưng console Guacamole thất bại, kiểm tra log/connection settings của Guacamole thay vì chỉ thay đổi web service.

Sau khi thay source, push revision mới rồi tạo pool mới để dựng và kiểm chứng. Việc sửa file local không thay đổi VM của pool cũ. Nguồn hướng dẫn truy cập: [CyberRangeCZ Sandbox Access](https://docs.platform.cyberrange.cz/user-guide-advanced/sandboxes/sandbox-access/).
