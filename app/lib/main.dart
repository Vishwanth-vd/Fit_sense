// ==============================================================================
// FitSense AI - Flutter Application Entry Point
// ==============================================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'ui/screens/camera_preview_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Immersive transparent status bar and dark navigation bar
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: Color(0xFF121212),
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  runApp(const FitSenseApp());
}

class FitSenseApp extends StatelessWidget {
  const FitSenseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FitSense AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF121212),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00E676), // Neon Emerald
          secondary: Color(0xFF00E5FF), // Neon Cyan
          surface: Color(0xFF1E1E1E),
          background: Color(0xFF121212),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF121212),
          elevation: 0,
        ),
      ),
      home: const CameraPreviewScreen(),
    );
  }
}
