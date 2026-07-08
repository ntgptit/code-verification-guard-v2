# MemoX V5 Guard Rule Registry

> **Ruleset `memox-v5`.** Bộ rule cho repo **memox-v5** (Expo SDK 57 + React Native +
> TypeScript). Chạy bằng `--ruleset memox-v5`
> (`python guard/run.py check --project <memox-v5 root> --ruleset memox-v5`).
> Registry này self-contained: `guard-manifest.yaml` + `config/{scopes,overrides,profiles}.yaml`
> + `rules/` đều nằm trong `registries/projects/memox-v5/`.

## Stack v5 (khác v4)

| | memox-v4 (Flutter) | memox-v5 (React Native) |
| --- | --- | --- |
| Ngôn ngữ | Dart | TypeScript (strict, noUncheckedIndexedAccess) |
| Routing | GoRouter (`lib/core/routes`) | expo-router file-based (`src/app`) |
| State | Riverpod v3 | Zustand (`*-store.ts`) |
| Error | AppFailure + Result kiểu Dart | neverthrow (Result/ResultAsync) |
| Styling | Mx tokens (`lib/core/theme/mx_*.dart`) | NativeWind v4 + tailwind.config.js theme |
| Forms | — | react-hook-form + Zod (`zodResolver`) |
| Lint/format | dart analyze | Biome (gate riêng trong `npm run check`) |
| Test | flutter_test | Jest (jest-expo) |

## Layout repo v5

- `src/app/**` — route files (expo-router). Phải **mỏng**: compose feature screens.
- `src/features/<feature>/**` — module tính năng.
- `src/shared/{ui,lib,utils}/**` — code dùng chung, KHÔNG được import features.
- `src/components|constants|hooks/**` + `src/app/explore.tsx` — **bộ kit template giữ làm
  tham khảo code màn hình, không phải product code** → bị exclude khỏi mọi scope. Đừng
  "dọn" các exclude này.
- `docs/design/**` — design snapshots (exclude).
- `scripts/check-boundaries.mjs` — script boundary riêng của repo (chạy trong `npm run check`).

## Phân công với các gate khác của repo

Guard **không** lặp lại việc của gate sẵn có:

- **Biome** own formatting + lint chung (quote style, import type, v.v.).
- **tsc --noEmit** own type-safety.
- **scripts/check-boundaries.mjs** own rule "feature A không import feature B" —
  regex per-file KHÔNG diễn đạt được so sánh A ≠ B, nên guard chỉ giữ hai chiều
  regex làm được: `shared_no_feature_import` và `features_no_route_import`.

## Danh mục file theo domain

| File | Domain | Nghiệp vụ |
| --- | --- | --- |
| `memox-architecture-rules.yaml` | `architecture` | Ranh giới shared/features/app-routes, route mỏng (không zustand/fetch trực tiếp) |
| `memox-coding-rules.yaml` | `coding` | `no_else` (early-return contract), cấm `@ts-ignore`, console discipline |
| `memox-naming-rules.yaml` | `naming` | File kebab-case; `stores/` → `*-store.ts`; `schemas/` → `*-schema.ts` |
| `memox-state-management-rules.yaml` | `state_management` | Zustand chỉ trong store files; selector bắt buộc; cấm `getState()` trong component |
| `memox-error-handling-rules.yaml` | `error_handling` | neverthrow: cấm empty catch, `_unsafeUnwrap` ngoài test, shared/lib ưu tiên Result |
| `memox-design-token-rules.yaml` | `design_token` | NativeWind: cấm màu/size arbitrary `[...]`, hạn chế StyleSheet.create |
| `memox-routing-rules.yaml` | `routing` | Chỉ expo-router: cấm @react-navigation trực tiếp, window.location, `<a href>` |
| `memox-forms-rules.yaml` | `forms` | Zod duy nhất; useForm phải đi qua zodResolver |
| `memox-dependencies-rules.yaml` | `dependencies` | package.json: cấm `*`/`latest`, cấm git/file deps |
| `memox-testing-rules.yaml` | `testing` | Cấm `.only`; `.skip` phải có lý do |

## Delta so với ruleset `memox-v4`

Domain Flutter-specific **không mang sang** (premise không tồn tại trong RN/v5):
`dart-convention`, `flutter-convention`, `screen-shell` (MxScaffold), `responsive-layout`
(MediaQuery ownership), `ui-async-guard` (`mounted`), `action-density`, `layer-naming`
(usecase/DAO suffix), `hooks` (flutter_hooks), `shared-widget` (+doc), `study` (chưa có
feature code trong v5), `i18n` (v5 chưa setup i18n), `observability` (chưa có logger),
`performance` (chưa có convention list/image), `design-system` (chưa có bộ Mx component
RN — "MemoX Design System" trong docs/design là JSX web kit tham khảo).

Khi các mảng trên landed trong v5 (logger, i18n, shared UI kit...), thêm file
`memox-<domain>-rules.yaml` mới và đăng ký vào `guard-manifest.yaml` của registry này.

## Seed rules đang tắt (`enabled: false`, comment `# v5-seed:`)

Repo v5 mới chỉ có skeleton (`src/features`, `src/shared/{ui,lib}` chưa có code), nên các
rule trỏ vào chỗ chưa tồn tại bị engine cảnh báo `rule_without_targets`. Chúng được giữ
lại ở trạng thái tắt — **BẬT LẠI khi target đầu tiên landed**:

| Rule | Bật khi |
| --- | --- |
| `memox.architecture.features_no_route_import` | feature đầu tiên có code trong `src/features/` |
| `memox.state_management.store_creation_only_in_store_files` | feature/shared module đầu tiên |
| `memox.naming.store_file_suffix` | store Zustand đầu tiên (thư mục `stores/`) |
| `memox.naming.schema_file_suffix` | Zod schema module đầu tiên (thư mục `schemas/`) |
| `memox.error_handling.shared_lib_prefer_result` | module đầu tiên trong `src/shared/lib/` |

## Quy ước

- Rule ID: `memox.<domain>.<rule_name>` — `<domain>` trùng slug file. Giữ nguyên convention v4.
- Severity: `error` chỉ khi codebase hiện tại đã sạch và quy ước bắt buộc; heuristic mới
  để `warning` (profile local/ci đang bật `warning_as_error: true` nên vẫn gate).
- Override cho file cụ thể: dùng `config/overrides.yaml` (`disabled_rules` / `rule_options`),
  không nới rule gốc.
- Regex là Python `re` (per-line mặc định; `mode: file` + `(?s)` cho required-pattern
  kiểu negative-lookahead như `memox.forms.use_form_requires_zod_resolver`).
