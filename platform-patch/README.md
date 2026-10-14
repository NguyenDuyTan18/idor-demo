# Hiện topology ở màn thực hành tự do

Frontend chuẩn quyết định hiện topology cho Training/Access Level. Info Level chỉ có nội dung và nút Next/Finish, nên phù hợp yêu cầu không nhập đáp án nhưng mặc định thiếu nút console/SSH.

`allow-free-lab.patch` bổ sung điều kiện: Info Level có title chính xác **`IDOR Free Lab`** được hiện topology khi run dùng cloud environment. Các Info Level khác và local environment giữ hành vi hiện tại. Patch không thêm một loại level hoặc API tự tạo sandbox.

File được sửa trong repository **frontend-platform**:

```text
libs/agenda/training-agenda/run-detail/components/level/abstract-level.component.ts
```

## Kiểm tra và áp dụng bởi operator

Thực hiện trên checkout source frontend tương ứng deployment, với working tree sạch hoặc đã bảo toàn thay đổi riêng:

```bash
git apply --check <path-to-demo-IDOR>/platform-patch/allow-free-lab.patch
git apply <path-to-demo-IDOR>/platform-patch/allow-free-lab.patch
node <path-to-demo-IDOR>/platform-patch/test-policy.cjs libs/agenda/training-agenda/run-detail/components/level/abstract-level.component.ts
```

Sau đó chạy build/test của đúng phiên bản frontend và triển khai image mới theo quy trình hiện có. Gói này không chạy build/deploy platform thay bạn. Nếu `git apply --check` thất bại, dừng và đối chiếu hàm `updateTopologyAllowed` trong phiên bản thật; không dùng `--reject` hoặc ép áp patch.

Nguồn tham chiếu đã kiểm tra: frontend commit `6e6e156c1dfdeac86741f4f51b74fcaf4f092c2a`, backend-training commit `fe3930412eefb2cf343b2e172df6d81cebf3041b`. Chưa xác nhận đây là source của bản **v2026.02** trong ảnh người dùng.

## Bằng chứng và giới hạn

Test policy trên hàm gốc thất bại vì Info Level của lab bị ẩn. Hàm sau patch đạt 9 trường hợp: cloud lab được hiện; Info Level thông thường/Assessment vẫn ẩn; Training/Access vẫn hiện; local environment vẫn ẩn cho mọi loại level. `git apply --check` đạt trên checkout tham chiếu. Đây là kiểm tra logic riêng, chưa phải build/test toàn bộ Angular hoặc E2E trên platform thật.

Tham chiếu: [frontend topology policy](https://github.com/cyberrangecz/frontend-platform/blob/6e6e156c1dfdeac86741f4f51b74fcaf4f092c2a/libs/agenda/training-agenda/run-detail/components/level/abstract-level.component.ts), [backend cấp sandbox khi mở run](https://github.com/cyberrangecz/backend-training/blob/fe3930412eefb2cf343b2e172df6d81cebf3041b/training-service/src/main/java/cz/cyberrange/platform/training/service/facade/TrainingRunFacade.java).
