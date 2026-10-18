import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SettingsNotifier extends StateNotifier<String> {
  SettingsNotifier() : super('http://127.0.0.1:8000') {
    _loadUrl();
  }

  Future<void> _loadUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final url = prefs.getString('server_url');
    if (url != null && url.isNotEmpty && !url.contains('onrender.com')) {
      state = url;
    } else {
      state = 'http://127.0.0.1:8000';
      await prefs.setString('server_url', 'http://127.0.0.1:8000');
    }
  }

  Future<void> setServerUrl(String url) async {
    state = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', url);
  }
}

final serverUrlProvider = StateNotifierProvider<SettingsNotifier, String>((ref) {
  return SettingsNotifier();
});
