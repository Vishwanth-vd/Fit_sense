// ==============================================================================
// FitSense AI - Skeleton Overlay CustomPainter
// ==============================================================================

import 'package:flutter/material.dart';

import '../../core/constants/pose_landmarks.dart';

class PosePoint {
  final double x;
  final double y;
  final double z;
  final double visibility;

  const PosePoint({
    required this.x,
    required this.y,
    this.z = 0.0,
    this.visibility = 1.0,
  });
}

class SkeletonOverlayPainter extends CustomPainter {
  final Map<int, PosePoint> landmarks;
  final String dominantSide;
  final double minVisibility;

  SkeletonOverlayPainter({
    required this.landmarks,
    this.dominantSide = 'LEFT',
    this.minVisibility = 0.5,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (landmarks.isEmpty) return;

    final linePaint = Paint()
      ..color = const Color(0xFF00E5FF)
          .withOpacity(0.85) // Neon Cyan
      ..strokeWidth = 3.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final dominantLinePaint = Paint()
      ..color =
          const Color(0xFF00E676) // Neon Emerald
      ..strokeWidth = 4.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final jointPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;

    final dominantJointPaint = Paint()
      ..color = const Color(0xFF00E676)
      ..style = PaintingStyle.fill;

    final glowPaint = Paint()
      ..color = const Color(0xFF00E676).withOpacity(0.3)
      ..style = PaintingStyle.fill;

    // 1. Draw skeletal connection lines
    for (final connection in PoseConnections.fullBodyConnections) {
      final p1Idx = connection[0];
      final p2Idx = connection[1];

      final p1 = landmarks[p1Idx];
      final p2 = landmarks[p2Idx];

      if (p1 == null || p2 == null) continue;
      if (p1.visibility < minVisibility || p2.visibility < minVisibility)
        continue;

      final p1Offset = Offset(p1.x * size.width, p1.y * size.height);
      final p2Offset = Offset(p2.x * size.width, p2.y * size.height);

      final isDominantConnection =
          (dominantSide == 'LEFT' &&
              PoseLandmarkIndex.leftSideLandmarks.contains(p1Idx) &&
              PoseLandmarkIndex.leftSideLandmarks.contains(p2Idx)) ||
          (dominantSide == 'RIGHT' &&
              PoseLandmarkIndex.rightSideLandmarks.contains(p1Idx) &&
              PoseLandmarkIndex.rightSideLandmarks.contains(p2Idx));

      canvas.drawLine(
        p1Offset,
        p2Offset,
        isDominantConnection ? dominantLinePaint : linePaint,
      );
    }

    // 2. Draw joint landmark dots
    for (final entry in landmarks.entries) {
      final idx = entry.key;
      final point = entry.value;

      if (point.visibility < minVisibility) continue;

      final offset = Offset(point.x * size.width, point.y * size.height);
      final isDominantJoint =
          (dominantSide == 'LEFT' &&
              PoseLandmarkIndex.leftSideLandmarks.contains(idx)) ||
          (dominantSide == 'RIGHT' &&
              PoseLandmarkIndex.rightSideLandmarks.contains(idx));

      if (isDominantJoint) {
        // Outer glow
        canvas.drawCircle(offset, 9.0, glowPaint);
        // Inner circle
        canvas.drawCircle(offset, 5.0, dominantJointPaint);
      } else {
        canvas.drawCircle(offset, 3.5, jointPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant SkeletonOverlayPainter oldDelegate) {
    return oldDelegate.landmarks != landmarks ||
        oldDelegate.dominantSide != dominantSide;
  }
}
