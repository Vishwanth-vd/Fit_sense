// ==============================================================================
// FitSense AI - Camera Preview & Pose Detection Screen (Phase P2)
// Wired to flutter_mp_pose_landmarker EventChannel (real MediaPipe on-device)
// ==============================================================================

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_mp_pose_landmarker/flutter_mp_pose_landmarker.dart';

import '../../core/constants/pose_landmarks.dart';
import '../../services/fps_calculator.dart';
import '../widgets/skeleton_overlay_painter.dart';

class CameraPreviewScreen extends StatefulWidget {
  const CameraPreviewScreen({super.key});

  @override
  State<CameraPreviewScreen> createState() => _CameraPreviewScreenState();
}

class _CameraPreviewScreenState extends State<CameraPreviewScreen>
    with WidgetsBindingObserver {
  bool _isConfigured = false;
  bool _isLoading = true;
  String? _errorMessage;

  final FpsCalculator _fpsCalculator = FpsCalculator();
  double _fps = 0.0;
  String _dominantSide = 'LEFT';
  Map<int, PosePoint> _currentLandmarks = {};
  StreamSubscription<PoseLandMarker>? _poseSubscription;
  Timer? _fpsTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initPoseLandmarker();

    // Refresh FPS badge every 250 ms
    _fpsTimer = Timer.periodic(const Duration(milliseconds: 250), (_) {
      if (mounted) {
        setState(() => _fps = _fpsCalculator.currentFps);
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _fpsTimer?.cancel();
    _poseSubscription?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      PoseLandmarker.pauseDetection();
    } else if (state == AppLifecycleState.resumed) {
      PoseLandmarker.resumeDetection();
    }
  }

  // ---------------------------------------------------------------------------
  // Initialisation
  // ---------------------------------------------------------------------------
  Future<void> _initPoseLandmarker() async {
    setState(() => _isLoading = true);
    try {
      // Configure: CPU delegate, lite model (fastest on device)
      await PoseLandmarker.setConfig(
        delegate: 0, // CPU
        model: 1, // lite
        minPoseDetectionConfidence: 0.5,
        minPoseTrackingConfidence: 0.5,
        minPosePresenceConfidence: 0.5,
        analysisWidth: 640,
        analysisHeight: 480,
      );
      _subscribePoseStream();
      if (mounted) setState(() {_isConfigured = true; _isLoading = false;});
    } on PlatformException catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Pose engine failed to start: ${e.message}';
          _isLoading = false;
        });
      }
    }
  }

  void _subscribePoseStream() {
    _poseSubscription?.cancel();
    _poseSubscription =
        PoseLandmarker.poseLandmarkStream.listen(_onPoseFrame, onError: (e) {
      if (mounted) setState(() => _errorMessage = 'Stream error: $e');
    });
  }

  // ---------------------------------------------------------------------------
  // Per-frame callback — convert plugin landmarks → PosePoint map
  // ---------------------------------------------------------------------------
  void _onPoseFrame(PoseLandMarker result) {
    _fpsCalculator.onFrame();

    // Build index → PosePoint map (33 MediaPipe landmarks)
    final Map<int, PosePoint> pts = {};
    for (int i = 0; i < result.landmarks.length; i++) {
      final lm = result.landmarks[i];
      pts[i] = PosePoint(
        x: lm.x,
        y: lm.y,
        z: lm.z,
        visibility: lm.visibility,
      );
    }

    // Dominant side: compare average visibility of LEFT vs RIGHT key joints
    final leftAvg = _avgVisibility(pts, PoseLandmarkIndex.leftSideLandmarks);
    final rightAvg =
        _avgVisibility(pts, PoseLandmarkIndex.rightSideLandmarks);
    final side = leftAvg >= rightAvg ? 'LEFT' : 'RIGHT';

    if (mounted) {
      setState(() {
        _currentLandmarks = pts;
        _dominantSide = side;
      });
    }
  }

  double _avgVisibility(Map<int, PosePoint> pts, List<int> indices) {
    if (indices.isEmpty) return 0.0;
    double sum = 0.0;
    int count = 0;
    for (final idx in indices) {
      final p = pts[idx];
      if (p != null) {
        sum += p.visibility;
        count++;
      }
    }
    return count > 0 ? sum / count : 0.0;
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(color: Color(0xFF00E676)),
              SizedBox(height: 16),
              Text('Starting pose engine…',
                  style: TextStyle(color: Colors.white54)),
            ],
          ),
        ),
      );
    }

    if (_errorMessage != null) {
      return _buildErrorView(_errorMessage!);
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // ── 1. Native Camera Preview (CameraX via plugin) ─────────────────
          if (_isConfigured)
            const AndroidView(
              viewType: 'pose_landmarker/camera_preview',
              creationParamsCodec: StandardMessageCodec(),
            ),

          // ── 2. Real-time Skeleton Overlay ──────────────────────────────────
          CustomPaint(
            painter: SkeletonOverlayPainter(
              landmarks: _currentLandmarks,
              dominantSide: _dominantSide,
              minVisibility: 0.5,
            ),
            size: Size.infinite,
          ),

          // ── 3. Top HUD ─────────────────────────────────────────────────────
          SafeArea(
            child: Align(
              alignment: Alignment.topCenter,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 16.0, vertical: 12.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _fpsBadge(),
                    _sideBadge(),
                  ],
                ),
              ),
            ),
          ),

          // ── 4. Bottom Info Card ────────────────────────────────────────────
          SafeArea(
            child: Align(
              alignment: Alignment.bottomCenter,
              child: _infoCard(),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Widgets
  // ---------------------------------------------------------------------------
  Widget _fpsBadge() {
    final isGood = _fps >= 20.0;
    final color = isGood ? const Color(0xFF00E676) : const Color(0xFFFFD600);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color, width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.speed, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            _fps > 0 ? '${_fps.toStringAsFixed(1)} FPS' : 'Starting…',
            style: TextStyle(
                color: color, fontWeight: FontWeight.bold, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _sideBadge() {
    const color = Color(0xFF00E5FF);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color, width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.accessibility_new, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            'Side: $_dominantSide',
            style: const TextStyle(
                color: color, fontWeight: FontWeight.bold, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _infoCard() {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E).withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.info_outline,
                  color: Color(0xFF00E676), size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'FitSense AI — Pose Stream Active',
                  style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 15),
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF00E676).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'ON-DEVICE',
                  style: TextStyle(
                      color: Color(0xFF00E676),
                      fontWeight: FontWeight.bold,
                      fontSize: 11),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Place phone ~2 m away, full body visible (side view). '
            'Zero video is stored or transmitted.',
            style: TextStyle(color: Colors.white70, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(String message) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline,
                  color: Colors.redAccent, size: 72),
              const SizedBox(height: 20),
              const Text(
                'Camera Error',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                message,
                style: const TextStyle(color: Colors.white70, fontSize: 13),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: _initPoseLandmarker,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00E676),
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 24, vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
