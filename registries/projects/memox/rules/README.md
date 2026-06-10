# MemoX Guard Rule Registry

Thư mục này chứa toàn bộ rule của `code-verification-guard` cho project MemoX, **tách theo nghiệp vụ (domain)**: mỗi file một domain, mỗi rule một ID theo convention thống nhất.

## Quy ước đặt ID

```
memox.<domain>.<rule_name>
```

- `<domain>` trùng với slug của file chứa rule (file `memox-<domain>-rules.yaml`, đổi `-` thành `_`).
  Ví dụ: rule trong `memox-design-system-rules.yaml` luôn có ID dạng `memox.design_system.*`.
- `<rule_name>` là snake_case, ưu tiên dạng mệnh lệnh/phủ định mô tả đúng hành vi:
  `no_raw_card`, `use_mx_scaffold_family`, `provider_no_ui_side_effects`, `file_name_snake_case`.
- Không lặp lại domain trong rule name (`memox.shared_widget.no_app_wiring`, không phải
  `memox.shared_widget.shared_widget_no_app_wiring`).

Muốn biết một rule nằm ở file nào: nhìn segment `<domain>` trong ID là ra thẳng tên file.

## Danh mục file theo domain

| File | Domain | Nghiệp vụ |
| --- | --- | --- |
| `memox-architecture-rules.yaml` | `architecture` | Phân lớp Clean Architecture, chiều dependency, DI, ranh giới data layer (transaction, DAO, raw SQL) |
| `memox-coding-rules.yaml` | `coding` | Naming (file/class/biến/CRUD member), style (`no_else`), maintainability (part-of, TODO ticket) |
| `memox-dart-convention-rules.yaml` | `dart_convention` | Convention Dart: package import, snake_case file name |
| `memox-state-management-rules.yaml` | `state_management` | Riverpod v3: generated providers, keepAlive lifecycle, provider purity, watch/read/listen |
| `memox-error-handling-rules.yaml` | `error_handling` | AppFailure mapping, exception surfacing, catch hygiene, MxActionErrors helpers |
| `memox-observability-rules.yaml` | `observability` | AppLogger routing, cấm gọi Sentry trực tiếp, cấm log dữ liệu nhạy cảm |
| `memox-i18n-rules.yaml` | `i18n` | Cấm hardcode chuỗi hiển thị; mọi copy đi qua `context.l10n` / ARB |
| `memox-design-system-rules.yaml` | `design_system` | Dùng Mx component thay raw Material widget; màu/typography qua theme |
| `memox-design-token-rules.yaml` | `design_token` | Cấm literal màu/spacing/radius/typography/duration ngoài file token/theme |
| `memox-screen-shell-rules.yaml` | `screen_shell` | Contract MxScaffold family, page gutter, layout literal trên screen, shell watch-free |
| `memox-responsive-layout-rules.yaml` | `responsive_layout` | Quyền sở hữu MediaQuery/kích thước màn hình, child widget dùng constraints/ResponsiveRules |
| `memox-performance-rules.yaml` | `performance` | Refetch flicker, list builder, heavy work trong build, image cache, intrinsic/shrinkWrap |
| `memox-routing-rules.yaml` | `routing` | RoutePaths/RouteNames constants, navigation extension dùng chung, router composition |
| `memox-shared-widget-rules.yaml` | `shared_widget` | Contract widget Mx*: tên file `mx_*`, public type `Mx*`, không app wiring, build bị giới hạn |
| `memox-shared-widget-doc-rules.yaml` | `shared_widget_doc` | Dart-doc bắt buộc cho shared widget (Purpose / Use when / Category / Public API) |
| `memox-hooks-rules.yaml` | `hooks` | Hooks chỉ ở presentation, custom hook prefix `useMx`, dùng shared hooks |
| `memox-ui-async-guard-rules.yaml` | `ui_async_guard` | Race-guard async trong State: `if (!mounted) return;` đứng riêng, `_snapshot` record |
| `memox-action-density-rules.yaml` | `action_density` | Mật độ action trên card/list/dashboard: không button large/full-width |
| `memox-study-rules.yaml` | `study` | Ranh giới domain feature Study (Guess sampling, SRS interval/box logic ở một nguồn duy nhất) |
| `memox-dependencies-rules.yaml` | `dependencies` | Quản trị pubspec.yaml: cấm path/git dep, cấm version `any` |
| `memox-testing-rules.yaml` | `testing` | Vệ sinh test: giới hạn dòng, `skip` phải có lý do |

## Cấu trúc một rule

```yaml
- id: memox.<domain>.<rule_name>   # bắt buộc, theo convention trên
  type: regex                      # regex | forbidden_import | file_name | max_lines | max_build_lines | dart_shared_widget_doc
  severity: error                  # error (chặn CI) | warning (cảnh báo)
  enabled: true
  message: Mô tả vi phạm + hướng xử lý.   # người đọc đầu tiên là dev bị chặn commit
  scopes:                          # tham chiếu scope đặt tên sẵn (xem bên dưới); HOẶC dùng include/exclude trực tiếp
    - feature_ui
  patterns:                        # regex (Python re); với type file_name dùng `pattern` (số ít)
    - \bCard\s*\(
  mode: file                       # tùy chọn: match cả file (mặc định match theo dòng)
  tags: [memox, design-system]
  fix:
    hint: Gợi ý sửa hiển thị trong report.
```

## Scopes

- Ruleset registry-local (`registries/projects/memox/guard-manifest.yaml`) load scope từ
  `registries/projects/memox/config/scopes.yaml`.
- Ruleset trong manifest gốc (`guard-manifest.yaml` ở repo root, mục `rule_sets.memox`) load từ
  `scopes/flutter-scopes.yaml` + `scopes/memox-scopes.yaml`.
- **Hai file scope phải đồng bộ**: thêm scope mới ở một nơi thì thêm cả nơi còn lại, nếu không
  ruleset kia sẽ fail với `Unknown rule scope`.
- Một rule có thể khai báo nhiều scope; include/exclude của các scope được union lại.

## Quy trình thêm / sửa rule

1. Chọn đúng file theo domain. Nếu nghiệp vụ mới chưa có file, tạo `memox-<domain>-rules.yaml`
   với header comment + `metadata`, rồi đăng ký vào **cả hai** manifest:
   `registries/projects/memox/guard-manifest.yaml` và `guard-manifest.yaml` (root, mục `rule_sets.memox`).
2. Đặt ID theo convention; không tái sử dụng ID cũ cho rule khác nghĩa.
3. Style YAML: list item phải thụt lề dưới key cha (`rules:` → 2 space rồi `- id:`) —
   validator trong `config_manager` sẽ từ chối list item ở cột 0.
4. Viết test trong `tests/` (các test memox tra rule theo ID bằng glob `*-rules.yaml`,
   nên đổi tên file không phá test, nhưng **đổi ID thì phải cập nhật test**).
5. Chạy verify:

   ```bash
   python -m pytest tests -q
   python guard/run.py check --project <memox-project-root> --ruleset memox
   ```

6. Khi đổi/xóa ID: grep cả repo app MemoX (doc comment trong `lib/**`, `docs/**`) —
   nhiều file Dart tham chiếu rule ID trong Dart-doc để giải thích vì sao wrapper tồn tại.

## Chính sách severity

- `error`: chặn gate. Chỉ dùng khi codebase hiện tại **đã sạch** với rule đó và quy ước là bắt buộc.
- `warning`: nợ hiện hữu hoặc heuristic mới chưa kiểm chứng. Mỗi warning-rule nên ghi rõ trong
  `message` điều kiện để promote lên error (vd. `memox.i18n.no_hardcoded_strings_shared`,
  `memox.dependencies.no_any_version`).

## Quy ước có chủ đích (opinionated — không phải Flutter mặc định)

Một số rule **cố ý lệch khỏi pattern Flutter chuẩn**; dev mới cần biết trước để không bất ngờ:

- `memox.hooks.text_controller_requires_mx_hook`: pattern `TextEditingController` trong `State` +
  `dispose()` (chuẩn Flutter) bị cấm trong presentation — MemoX chọn flutter_hooks với hook `useMx*`.
- `memox.coding.no_else`: cấm `else` — bắt buộc early-return/switch expression.
- `memox.state_management.use_app_async_builder`: cấm render `AsyncValue.when` trực tiếp trên UI feature.
- `memox.ui_async_guard.*`: bắt buộc style guard 2 dòng (`if (!mounted) return;` + so sánh `_snapshot`).

## Giới hạn đã biết của engine

- Rule regex dùng **bounded window** (vd. `{0,1600}`) như `memox.screen_shell.use_mx_scaffold_family`,
  `memox.state_management.command_no_repository_ref_watch`: code dài vượt cửa sổ match sẽ **trượt
  im lặng** (miss, không false-positive). Đừng coi "guard pass" là bằng chứng tuyệt đối với các rule này.
- Rule "required pattern" (vd. `memox.observability.error_pipeline_wired`) hoạt động bằng negative
  lookahead trên toàn file — chỉ áp dụng được cho file cụ thể đã biết trước.

## Override / tắt rule

Không sửa rule để "nới" cho một file cụ thể. Dùng `registries/projects/memox/config/overrides.yaml`:
`disabled_rules`, `severity`, hoặc `rule_options` (include/exclude/option bổ sung theo từng rule ID).
