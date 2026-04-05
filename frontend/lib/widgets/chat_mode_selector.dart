import 'package:flutter/material.dart';
import '../models/chat_state.dart';

class ChatModeSelector extends StatelessWidget {
  final ChatMode currentMode;
  final ValueChanged<ChatMode> onModeChanged;
  final bool isLoggedIn;

  const ChatModeSelector({
    Key? key,
    required this.currentMode,
    required this.onModeChanged,
    this.isLoggedIn = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: ChatMode.values.map((mode) {
          final isSelected = mode == currentMode;
          final bool isFast = mode == ChatMode.fast;
          final bool isThinking = mode == ChatMode.thinking;
          final bool isExpert = mode == ChatMode.expert;

          // 游客模式下，思考和专家模式禁用
          final bool isDisabled = !isLoggedIn && (isThinking || isExpert);

          return Expanded(
            child: GestureDetector(
              onTap: isDisabled ? null : () => onModeChanged(mode),
              child: Opacity(
                opacity: isDisabled ? 0.5 : 1.0,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? (isFast
                            ? const Color(0xFF4CAF50)
                            : isThinking
                                ? const Color(0xFF2196F3)
                                : const Color(0xFFFF9800))
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (isFast)
                        const Icon(Icons.bolt, size: 18, color: Colors.white),
                      if (isThinking)
                        const Icon(Icons.psychology, size: 18, color: Colors.white),
                      if (isExpert)
                        const Icon(Icons.science, size: 18, color: Colors.white),
                      const SizedBox(width: 8),
                      Text(
                        _getModeLabel(mode),
                        style: TextStyle(
                          color: isSelected ? Colors.white : Colors.grey.shade700,
                          fontWeight: FontWeight.bold, // 所有按钮都使用粗体
                          fontSize: 15, // 稍微增大字体
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  String _getModeLabel(ChatMode mode) {
    switch (mode) {
      case ChatMode.fast:
        return '⚡ 快速';
      case ChatMode.thinking:
        return '🧠 思考';
      case ChatMode.expert:
        return '🔬 专家';
    }
  }
}
