import 'package:flutter/material.dart';

/// Displays a reusable primary action button.
///
/// Purpose:
/// Provides a consistent button surface for primary user actions.
///
/// Use when:
/// A screen needs a save, create, continue, or submit action.
///
/// Do not use when:
/// The action is destructive, secondary, or only navigational.
///
/// Category:
/// button
///
/// Public API:
/// - label: visible button text
/// - onPressed: action callback
/// - isLoading: shows progress and disables action
/// - variant: visual style
/// - size: button size
///
/// States:
/// default, loading, disabled
///
/// Variants:
/// primary, secondary, danger, ghost
///
/// Expected contracts:
/// MxSharedComponent, MxLabeledComponent, MxActionableComponent,
/// MxLoadableComponent, MxSizableComponent<MxButtonSize>,
/// MxVariantComponent<MxButtonVariant>
class MxButton extends StatelessWidget {
  const MxButton({
    required this.label,
    required this.onPressed,
    required this.isLoading,
    required this.variant,
    required this.size,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final String variant;
  final String size;

  @override
  Widget build(BuildContext context) {
    return const SizedBox.shrink();
  }
}

/// Displays a reusable shared text field.
///
/// Purpose:
/// Provides a consistent text input surface for memo entry.
///
/// Use when:
/// A screen needs a controller-backed text field with change handling.
///
/// Do not use when:
/// The input is not text-based or needs a custom picker or slider.
///
/// Category:
/// input
///
/// Public API:
/// - label: visible field label
/// - controller: text editing controller
/// - onChanged: text change callback
/// - errorText: inline error message
/// - isLoading: shows a loading state
///
/// States:
/// default, loading, error
///
/// Expected contracts:
/// MxSharedComponent, MxLabeledComponent, MxTextInputComponent,
/// MxErrorDisplayComponent, MxLoadableComponent
class MxTextField extends StatelessWidget {
  const MxTextField({
    required this.label,
    required this.controller,
    required this.onChanged,
    required this.errorText,
    required this.isLoading,
    super.key,
  });

  final String label;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final String? errorText;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: label,
        errorText: errorText,
      ),
    );
  }
}
