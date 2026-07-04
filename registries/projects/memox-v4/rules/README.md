# MemoX V4 Guard Rule Registry

> **Ruleset `memox-v4`.** Clone của ruleset `memox` (v1) đã remap cho layout thực tế
> của repo **memox-V4**. Chạy bằng `--ruleset memox-v4`
> (`python guard/run.py check --project <memox-V4 root> --ruleset memox-v4`).
> Xem [§Delta so với ruleset `memox` (v1)](#delta-so-với-ruleset-memox-v1) ở cuối file
> để biết rule nào bị remap path và rule nào bị `enabled: false` vì không còn target trong v4.
>
> Rule ID vẫn giữ tiền tố `memox.<domain>.*` (Dart-doc trong app tham chiếu ID này); chỉ
> ruleset **bundle name** là `memox-v4`. Registry này self-contained: `guard-manifest.yaml`
> + `config/{scopes,overrides,profiles}.yaml` + `rules/` đều nằm trong
> `registries/projects/memox-v4/` (không dùng root manifest / `scopes/memox-scopes.yaml`).

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
| `memox-flutter-convention-rules.yaml` | `flutter_convention` | Flutter widget/constructor/lifecycle conventions: `super.key`, const, named params, State/setState, GlobalKey, delayed async |
| `memox-state-management-rules.yaml` | `state_management` | Riverpod v3: generated providers, keepAlive lifecycle, provider purity, watch/read/listen |
| `memox-error-handling-rules.yaml` | `error_handling` | AppFailure mapping tại data boundary, cấm low-level exception ở domain/UI/provider, catch hygiene (empty catch, `catchError`, `async void`, bắt `Error`), MxActionErrors helpers |
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
- `memox.screen_shell.no_redundant_content_shell`: cấm bọc `MxContentShell` trong feature screen/widget —
  `MxScaffold` family đã cấp gutter rồi; bọc lại = double-gutter, lệch so với các màn khác. Ngoại lệ
  (vd. `MxScaffold(useShell: false)`) dùng `// guard:allow-content-shell -- reason: ...` cùng dòng hoặc
  dòng kế tiếp.

## Giới hạn đã biết của engine

- Rule regex dùng **bounded window** (vd. `{0,1600}`) như `memox.screen_shell.use_mx_scaffold_family`,
  `memox.state_management.command_no_repository_ref_watch`: code dài vượt cửa sổ match sẽ **trượt
  im lặng** (miss, không false-positive). Đừng coi "guard pass" là bằng chứng tuyệt đối với các rule này.
- Rule "required pattern" (vd. `memox.observability.error_pipeline_wired`) hoạt động bằng negative
  lookahead trên toàn file — chỉ áp dụng được cho file cụ thể đã biết trước.

## Override / tắt rule

Không sửa rule để "nới" cho một file cụ thể. Dùng `registries/projects/memox-v4/config/overrides.yaml`:
`disabled_rules`, `severity`, hoặc `rule_options` (include/exclude/option bổ sung theo từng rule ID).

## Delta so với ruleset `memox` (v1)

Ruleset `memox` gốc viết cho một layout cũ. Repo **memox-V4** đã tái cấu trúc, nên bản
clone này remap toàn bộ path và **tắt** (`enabled: false`, kèm comment `# v4:`) các rule
không còn target trong v4. Rule bị tắt được **giữ lại** (không xoá) để dễ audit / bật lại
khi feature tương ứng landed.

### Bản đồ path (v1 → v4)

| v1 | v4 |
| --- | --- |
| `features/**/viewmodels/**`, `*_viewmodel.dart` | `features/**/providers/**`, `*_providers.dart` |
| feature dirs `folders/`, `flashcards/`, `study/`, `tts/` | `deck-detail/`+`library/`, `flashcard-editor/`, `study-session/`, `player/` (hyphenated) |
| `lib/app/router/**` (`route_paths`/`route_names`/…) | `lib/core/routes/**` (`app_routes.dart` = `class Routes`, `app_router.dart`) |
| `lib/app/di/**` | (không có — DI colocated `@riverpod`) |
| `shared/widgets`, `shared/feedback`, `shared/dialogs`, `shared/hooks`, `shared/viewmodels` | `shared/primitives`, `shared/composites`, `shared/layouts`, `shared/screens` |
| `shared/layouts/mx_*scaffold.dart` | `shared/composites/mx_scaffold.dart` |
| `lib/core/tokens/**` | (không có — token nằm ở `lib/core/theme/mx_*.dart`) |
| `lib/core/database/**` | `lib/data/datasources/local/**` (`dao/`, `tables.dart`) |
| `lib/data/mappers/**` | `lib/data/models/mappers/**` |
| `lib/domain/models/**` | `lib/domain/entities/**` |
| `lib/l10n/generated/**` | `lib/l10n/app_localizations*.dart` |

### Rule bị tắt trong v4 (premise không tồn tại / trái với kiến trúc v4)

- **hooks:** cả file `memox-hooks-rules.yaml` bị **bỏ khỏi manifest** — v4 không dùng `flutter_hooks`.
- **shared widget docs:** cả file `memox-shared-widget-doc-rules.yaml` (11 rule
  `shared_widget_doc.*`) bị **xoá hẳn** — v4 dùng prose dartdoc cho shared widget (0/27
  widget dùng block có cấu trúc `Category/Purpose/Use when/Public API`), và không có tool
  nào tiêu thụ các section đó. Scope `shared_widget_dart_doc_source` cũng đã gỡ.
- **DI:** `architecture.centralized_shared_preferences_provider`, `.core_di_no_ui_imports`,
  `.core_di_no_state_notifiers`, `.di_no_export_wrappers` — không có `lib/app/di`; SharedPreferences không dùng.
- **sync:** `architecture.drive_sync_isolated` — không có `lib/data/sync`, không có google dep.
- **routing:** `routing.use_shared_navigation_extension` (v4 dùng `context.push(Routes.x)` trực tiếp),
  `.app_router_no_feature_screen_imports` (router trung tâm import screen theo thiết kế),
  `.shell_fab_no_route_state_coupling` (không có `app_shell.dart`).
- **layer-naming:** `migration_file_prefix` (không có migrations), `route_file_suffix` (không có feature `routes/`).
- **coding:** `string_normalization_via_string_utils` (không có `StringUtils`),
  `crud_screen_class_naming` / `crud_controller_class_naming` / `crud_command_method_naming`
  (keyed theo vocab v1 Folder/Subfolder/Tag/Flashcard — cần retune sang Deck/Card).
- **state-management:** `use_app_async_builder` (không có `AppAsyncBuilder`),
  `async_draft_via_helper` (không có `MxAsyncDraft`).
- **study:** `srs_logic_single_source` (symbol `intervalForBox`/`boxAfterFinalization` + `study_repo_impl*`
  không tồn tại; SRS logic ở `domain/usecases/srs/srs_scheduler.dart`).
- Các rule "planned-feature" vốn đã disabled (`study.no_inline_guess_sampling`,
  `architecture.tts_controller_uses_playback_policy`) được remap path sang v4 nhưng **giữ disabled**.

Rule không nằm trong danh sách trên vẫn **enabled** và phản ánh nợ thật của v4 (vd.
`design_system.no_raw_text_style`, `coding.no_else`, `layer_naming.usecase_*`,
`shared_widget_doc.*`) — đừng tắt để "cho pass".

### Căn theo kiến trúc Flutter khuyến nghị (MVVM + Repository)

Quyết định (2026-07-04): ruleset bám theo **app architecture chính thức của Flutter** —
`ViewModel`/provider phụ thuộc **Repository** trực tiếp; **use-case là tầng TUỲ CHỌN**,
không bắt buộc. Do đó:

- `architecture.no_direct_infrastructure_access` được **viết lại**: cho phép feature
  provider đọc `*RepositoryProvider`; chỉ còn cấm provider đọc **thẳng DB thô**
  (`appDatabaseProvider`) — tức bỏ qua tầng Repository. (Trước đây cấm cả repository ⇒
  53 error giả, nay 0.)
- `state_management.command_no_repository_ref_watch` **thu hẹp** về chỉ match method
  trả về `void`/`Future<void>`. v4 dùng idiom `Future<XData> build()` → `_load()` và
  `ref.watch(...RepositoryProvider)` trong `_load()` là ĐÚNG (read-model builder reactive);
  regex cũ match cả `Future<XData>` nên bắt nhầm 7 chỗ `_load()`. Sau khi thu hẹp: 0
  false positive, vẫn bắt được watch-trong-mutation thật (nếu có).
- `architecture.widget_no_repository_provider_access` **giữ** (View → ViewModel, View
  KHÔNG đọc Repository trực tiếp — đúng khuyến nghị Flutter).
- `state_management.infrastructure_provider_keep_alive` **giữ** (repo/service là singleton
  app-scope ⇒ `keepAlive: true`; các finding còn lại là nợ thật cần sửa ở app).
- `flutter_convention.no_stateful_widget_in_features` **tắt** (khuyến nghị
  `HookConsumerWidget` thời-hooks; v4 không có hooks và dùng `StatefulWidget` hợp lệ cho
  vòng đời controller — `setState` vẫn bị cấm riêng qua `no_set_state`).
