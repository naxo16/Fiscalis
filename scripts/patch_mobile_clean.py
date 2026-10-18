import re

file_path = r"C:\Sistema_Fiscalizacion_Municipal\sgf_mobile\lib\presentation\pages\nueva_infraccion_screen.dart"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove unused fields _cBackground and _cPrimaryContainer
content = re.sub(r'  final Color _cBackground = const Color\(0xFFF9F9F9\);\r?\n', '', content)
content = re.sub(r'  final Color _cPrimaryContainer = const Color\(0xFF2D2D6D\);\r?\n', '', content)

# 2. Fix BuildContext async gap around line 163
old_sync_block = """        if (!context.mounted) return;
        try { await ref.read(syncServiceProvider).syncPendingInfracciones(); ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Guardado y enviado a Render'))); } catch (_) { ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Guardado localmente (Offline)'))); }"""

new_sync_block = """        if (!mounted) return;
        try {
          await ref.read(syncServiceProvider).syncPendingInfracciones();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Guardado y enviado a Render')),
            );
          }
        } catch (_) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Guardado localmente (Offline)')),
            );
          }
        }"""

# Handle both CRLF and LF
content = content.replace(old_sync_block.replace("\n", "\r\n"), new_sync_block.replace("\n", "\r\n"))
if old_sync_block in content:
    content = content.replace(old_sync_block, new_sync_block)

# Also fix line 167 catch (e) mounted check
content = content.replace("if (!context.mounted) return;", "if (!mounted) return;")

# 3. Remove unused _buildNavTab element at end of class
content = re.sub(r'  Widget _buildNavTab\(IconData icon, String label, \{required bool isActive\}\) \{[\s\S]*?\n  \}\r?\n\}', '}', content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated nueva_infraccion_screen.dart successfully")
