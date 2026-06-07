# Code Verification Guard

Code Verification Guard là một công cụ kiểm tra chuẩn mã nguồn theo hướng
portable và YAML-first. Công cụ quét một dự án và báo cáo các mẫu mã mà chủ dự
án đã khai báo là không hợp lệ đối với codebase đó.

Guard được thiết kế cho cả lập trình viên và các coding agent như Codex hoặc
Claude. Nó cung cấp cho dự án một lớp chính sách có thể thực thi để kiểm soát
coding standard, ranh giới kiến trúc, ràng buộc workflow, quy tắc đặt tên và
các kiểm tra đặc thù của từng dự án.

## Công Cụ Làm Gì

- Nạp rule set từ YAML manifest, scope, registry, profile và override.
- Quét target project root bằng các scope include/exclude có thể tái sử dụng.
- Chạy các matcher generic như regex, file-name, import, file-length, Flutter
  build-length, if-comment và Python docstring.
- Báo cáo violation kèm file path, line number, code line, severity và fix hint
  khi được cấu hình.
- Trả process status lỗi khi phát hiện severity được cấu hình là phải fail, để
  guard có thể chặn CI, script, hook hoặc workflow của agent.

## Nguyên Tắc Thiết Kế

Python engine phải luôn generic. Chính sách cụ thể nằm trong YAML.

Thêm hoặc sửa YAML khi cần rule, scope, profile, severity hoặc override mới cho
dự án. Chỉ sửa Python khi công cụ cần một năng lực generic mới, ví dụ matcher
type, reporter, loader behavior, CLI command, validation rule hoặc registry
behavior.

Công cụ này dùng mô hình source-only. Nó được thiết kế để copy, vendor hoặc
unzip vào dự án cần dùng, rồi chạy trực tiếp từ source tree đó.

## Yêu Cầu

- Python 3.12 trở lên
- Dependencies trong `pyproject.toml`:
  - `pyyaml`
  - `rich`
  - `typer`

Cài dependencies cho local development:

```powershell
python -m pip install -e .
```

Hoặc cài từ requirements tối thiểu:

```powershell
python -m pip install -r requirements.txt
```

## Bắt Đầu Nhanh

Chạy một project-specific ruleset từ thư mục guard đã vendor:

```powershell
python guard\run.py check --project . --ruleset memox
```

Chạy với profile override:

```powershell
python guard\run.py check --project . --ruleset memox --profile ci
```

In các resolved ruleset load paths:

```powershell
python guard\run.py check --project . --ruleset memox --debug
```

Output thành công có dạng:

```text
Code verification passed.
No violations found.
```

## CLI

```powershell
python guard\run.py --help
python guard\run.py check --help
```

Command `check` hỗ trợ:

| Option | Default | Mô tả |
| --- | --- | --- |
| `--project` | `.` | Project root cần quét. |
| `--config` | `code-verification-guard.yaml` | Tên file project config. |
| `--ruleset` | none | Tên ruleset bundle bắt buộc, ví dụ `memox`. |
| `--profile` | none | Profile override tùy chọn. |
| `--debug` | `false` | In các resolved ruleset load paths. |

`--ruleset` là bắt buộc. Nếu thiếu, command sẽ fail fast thay vì đoán policy
bundle nào cần áp dụng.

## Cấu Trúc Repository

```text
code_verification_guard/   Chỉ chứa Python engine
guard/                     Local CLI entrypoint
guard-manifest.yaml        Built-in rule set manifest
profiles/                  Built-in runtime profiles
scopes/                    Built-in reusable scopes
registries/                Built-in rule registries và project rule bundles
templates/                 YAML templates cho file config mới
docs/                      Ghi chú kiến trúc và contract cho agent
tests/                     Unit test và behavior test
scripts/create_zip.py      Helper đóng gói source bundle
code-verification-guard.yaml
                           Legacy/self-check project config
```

Các root YAML resources là source of truth built-in:

```text
guard-manifest.yaml
profiles/
scopes/
registries/
```

Không thêm bản copy resource đóng gói thứ hai dưới `code_verification_guard/`.

## Rule Sets

Giá trị CLI `--ruleset` trỏ tới một ruleset-local bundle dưới:

```text
registries/projects/<ruleset>/
```

Ví dụ, `--ruleset memox` sẽ nạp:

```text
registries/projects/memox/guard-manifest.yaml
```

Ruleset-local manifest đó có thể chọn các shared bundle từ root
`guard-manifest.yaml`.

Các shared bundle hiện có:

- `common`
- `python`
- `dart`
- `flutter`
- `java`
- `spring_boot`
- `typescript`
- `react`
- `memox`

Root shared bundle được dùng để ruleset-local manifest hoặc legacy project
config chọn vào. Chúng không được gọi trực tiếp bằng CLI `--ruleset` trừ khi có
một bundle cùng tên dưới `registries/projects/<ruleset>/`.

Project-specific ruleset nằm dưới:

```text
registries/projects/<ruleset>/
  guard-manifest.yaml
  config/
  rules/
```

Với policy thuộc riêng một dự án, hãy giữ file rule cụ thể trong
`registries/projects/<ruleset>/rules/`. Shared common hoặc language registry nên
được reference lại thay vì copy.

## Mô Hình YAML

Guard tách policy quét mã nguồn thành một vài loại file:

- Manifest: ánh xạ ruleset name tới scope file và registry file.
- Scope files: định nghĩa các nhóm include/exclude có thể tái sử dụng.
- Registry files: định nghĩa các rule cụ thể.
- Profile files: override failure behavior, severity và rule options.
- Project config: chọn local project defaults và legacy configuration.

Rule phải được định nghĩa trong registry files. Scope phải được định nghĩa trong
scope files. Profile chỉ nên override behavior và không được định nghĩa rule mới.

Dùng templates trong `templates/` khi tạo YAML mới:

| Template | Mục đích |
| --- | --- |
| `templates/code-verification-guard.yaml` | Project config |
| `templates/guard-manifest-rule-set.yaml` | Manifest ruleset entry |
| `templates/profile.yaml` | Profile override |
| `templates/registry.yaml` | Rule registry |
| `templates/scope.yaml` | Scope registry |

Giữ list indentation nằm dưới key:

```yaml
scopes:
  - sample_source
patterns:
  - "\\bsample\\b"
```

Tránh indentless list:

```yaml
scopes:
- sample_source
```

## Ví Dụ Scope

```yaml
version: 1

metadata:
  id: sample-scopes
  name: Sample Scopes
  description: Reusable scopes for sample rules.

scopes:
  sample_source:
    include:
      - "lib/**/*.dart"
    exclude:
      - "**/*.g.dart"
      - "**/*.freezed.dart"
      - "**/gen/**"
```

## Ví Dụ Rule Registry

```yaml
version: 1

metadata:
  id: sample-rules
  name: Sample Rules
  description: Sample project rules.
  owner: code-verification-guard

rules:
  - id: sample.no_bad_pattern
    type: regex
    severity: error
    enabled: true
    message: Avoid the bad pattern.
    scopes:
      - sample_source
    patterns:
      - "\\bbadPattern\\s*\\("
    tags:
      - sample
      - correctness
    fix:
      hint: Replace the bad pattern with the approved abstraction.
```

## Các Field Của Rule

Các field phổ biến:

| Field | Mô tả |
| --- | --- |
| `id` | Rule ID ổn định theo namespace, ví dụ `python.no_bare_except`. |
| `type` | Matcher type. |
| `severity` | Thường là `error` hoặc `warning`. |
| `enabled` | Rule có được chạy hay không. |
| `message` | Thông báo violation cho người đọc. |
| `scopes` | Các reusable scope ID cần quét. |
| `include` | Direct include patterns cho rule theo file cụ thể. |
| `exclude` | Rule-local exclude patterns. |
| `patterns` | Regex patterns dùng bởi pattern-based matcher. |
| `pattern` | Một regex pattern dùng bởi file-name rule. |
| `check` | Tên check chuyên dụng cho matcher có nhiều rule con. |
| `widget_base_classes` | Danh sách base widget classes để nhận diện shared widget public class. |
| `state_field_names` | Danh sách field names buộc phải có `States:` section. |
| `variant_field_names` | Danh sách field names buộc phải có `Variants:` section. |
| `allowed_values` | Giá trị hợp lệ cho `Category:`. |
| `known_contracts` | Danh sách interface names hợp lệ trong `Expected contracts:`. |
| `tags` | Nhãn tùy chọn để phân nhóm. |
| `fix.hint` | Hướng dẫn sửa tùy chọn hiển thị trong report. |

Dùng ID có namespace rõ ràng:

```text
common.no_trailing_whitespace
security.no_private_key
python.no_bare_except
flutter.no_hardcoded_color
memox.no_raw_card
```

Tránh ID mơ hồ như `rule1`, `check_something` hoặc `no_bad_code`.

## Matcher Types Được Hỗ Trợ

| Type | Mục đích | Field chính |
| --- | --- | --- |
| `regex` | Tìm regex pattern theo line hoặc toàn file. | `patterns`, optional `mode` |
| `file_name` | Validate tên file bằng regex. | `pattern` |
| `max_lines` | Giới hạn độ dài file. | `max_lines`, optional `count_mode` |
| `max_build_lines` | Giới hạn độ dài Flutter `Widget build(BuildContext context)`. | `max_lines`, optional `count_mode` |
| `forbidden_import` | Báo lỗi các import declaration bị cấm. | `patterns` |
| `if_comment` | Yêu cầu comment ngay phía trên các `if` statement khớp rule. | `patterns`, optional `comment_prefixes` |
| `python_docstring` | Kiểm tra docstring trên Python AST nodes. | optional `node_types` |
| `dart_shared_widget_doc` | Kiểm tra Dart doc blocks và API contract của shared widget public classes. | `check`, `widget_base_classes`, `state_field_names`, `variant_field_names`, `allowed_values`, `known_contracts` |

`regex` dùng line mode theo mặc định. Có thể chọn file mode bằng `mode` khi rule
cần match nhiều line.

`max_lines` và `max_build_lines` hỗ trợ `count_mode: logical` để đếm source line
theo logic, bỏ qua dòng trống và comment.

`python_docstring` hỗ trợ các giá trị `node_types` sau:

```yaml
node_types:
  - module
  - class
  - function
  - async_function
```

## Profiles Và Failure Behavior

Profile có thể thay đổi failure policy, disabled rules, severity overrides và
rule options mà không cần định nghĩa lại rule.

Ví dụ:

```yaml
version: 1

profile:
  name: ci

failure:
  fail_on:
    - error
  warning_as_error: false

overrides:
  disabled_rules: []
  severity: {}
  rule_options:
    common.max_file_lines:
      max_lines: 500
```

Process sẽ exit với status `1` khi violation khớp failure policy được cấu hình.
Warning có thể được report mà không làm fail, trừ khi active profile hoặc config
biến warning thành failure.

## Thêm Project Ruleset Mới

1. Tạo folder dưới `registries/projects/<ruleset>/`.
2. Thêm project-owned rule files dưới `registries/projects/<ruleset>/rules/`.
3. Thêm project-owned config files dưới `registries/projects/<ruleset>/config/`
   khi cần.
4. Thêm hoặc tái sử dụng scopes từ `scopes/*.yaml`.
5. Đăng ký ruleset trong root `guard-manifest.yaml`, hoặc thêm ruleset-local
   `registries/projects/<ruleset>/guard-manifest.yaml`.
6. Chạy guard với `--ruleset <ruleset>`.

Ưu tiên reference shared common và language bundle thay vì duplicate chúng vào
project folder.

## Thêm Rule Mới

Với rule thông thường, chỉ sửa YAML:

- `scopes/*.yaml`
- `registries/**/*.yaml`
- `profiles/*.yaml`
- `registries/projects/<ruleset>/guard-manifest.yaml`
- `registries/projects/<ruleset>/config/*.yaml`
- `registries/projects/<ruleset>/rules/*.yaml`
- project-level `code-verification-guard.yaml`

Chỉ sửa Python khi rule không thể biểu diễn bằng các matcher type hiện có.

Một rule tốt nên có:

- stable namespaced ID
- severity rõ ràng
- violation message rõ ràng
- scope ít false positive
- fix hint khi có thể
- include/exclude behavior tập trung

## Development

Chạy unit test suite:

```powershell
pytest -q
```

Compile Python package:

```powershell
python -m compileall -q code_verification_guard
```

Để verify MemoX ruleset từ MemoX repository root:

```powershell
python code-verification-guard\guard\run.py check --project . --ruleset memox
```

## Đóng Gói Source Bundle

Tạo source zip:

```powershell
python scripts\create_zip.py . code-verification-guard.zip
```

Source bundle nên bao gồm:

- `code_verification_guard/`
- `guard/`
- `guard-manifest.yaml`
- `profiles/`
- `scopes/`
- `registries/`
- `code-verification-guard.yaml`

Không đưa generated cache và build output vào bundle.

## Troubleshooting

`--ruleset is required`

Hãy truyền ruleset rõ ràng:

```powershell
python guard\run.py check --project . --ruleset memox
```

Tên được yêu cầu phải tồn tại dưới `registries/projects/<ruleset>/`.

Unsupported rule type

Kiểm tra field `type` trong registry file. Giá trị này phải khớp một trong các
matcher type được hỗ trợ ở trên.

Duplicate IDs

Rule, scope và matcher registry sẽ reject duplicate ID. Hãy đổi tên duplicate
hoặc bỏ definition bị thừa.

No files are scanned

Kiểm tra include/exclude patterns của active scope, rồi chạy lại với `--debug`
để xem resolved load paths.

False positive

Ưu tiên xử lý theo thứ tự:

1. Sửa source code nếu rule đúng.
2. Cải thiện rule, matcher, scope hoặc exclude strategy.
3. Dùng project overrides cho exception đặc thù của dự án.
4. Dùng profiles cho behavior đặc thù theo môi trường.

Không hardcode exception đặc thù của dự án vào Python engine.

## Tài Liệu

Các ghi chú kiến trúc và bảo trì nằm trong `docs/`:

- `docs/agent-architecture.md`
- `docs/agent-yaml-contract.md`
- `docs/agent-packaging.md`
- `docs/agent-verification.md`
- `docs/yaml-contract.md`

Khi thêm behavior có ảnh hưởng tới người dùng, hãy cập nhật README hoặc docs
liên quan trong cùng change.

## Quy Tắc Đóng Góp

- Giữ engine generic.
- Giữ policy cụ thể trong YAML.
- Không tạo một Python class riêng cho từng YAML rule.
- Chỉ thêm matcher mới cho một reusable matching capability mới.
- Dùng constants cho config keys, rule types, severity values, defaults và exit
  behavior.
- Giữ change nhỏ, tập trung và được verify bằng local verification mạnh nhất
  hợp lý.
