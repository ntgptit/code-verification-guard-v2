import 'package:flutter/material.dart';

class MxMissingDocButton extends StatelessWidget {
  const MxMissingDocButton({required this.label, super.key});

  final String label;

  @override
  Widget build(BuildContext context) => Text(label);
}

/// Purpose:
/// Category:
///
/// Public API:
/// label visible text
class MxBrokenButton extends StatelessWidget {
  const MxBrokenButton({
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
  Widget build(BuildContext context) =>
      TextButton(onPressed: onPressed, child: Text(label));
}
