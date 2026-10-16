// ==============================================================================
// FitSense AI - MediaPipe 33 Pose Landmark Definitions & Skeletal Topology
// ==============================================================================

class PoseLandmarkIndex {
  static const int nose = 0;
  static const int leftEyeInner = 1;
  static const int leftEye = 2;
  static const int leftEyeOuter = 3;
  static const int rightEyeInner = 4;
  static const int rightEye = 5;
  static const int rightEyeOuter = 6;
  static const int leftEar = 7;
  static const int rightEar = 8;
  static const int mouthLeft = 9;
  static const int mouthRight = 10;
  static const int leftShoulder = 11;
  static const int rightShoulder = 12;
  static const int leftElbow = 13;
  static const int rightElbow = 14;
  static const int leftWrist = 15;
  static const int rightWrist = 16;
  static const int leftPinky = 17;
  static const int rightPinky = 18;
  static const int leftIndex = 19;
  static const int rightIndex = 20;
  static const int leftThumb = 21;
  static const int rightThumb = 22;
  static const int leftHip = 23;
  static const int rightHip = 24;
  static const int leftKnee = 25;
  static const int rightKnee = 26;
  static const int leftAnkle = 27;
  static const int rightAnkle = 28;
  static const int leftHeel = 29;
  static const int rightHeel = 30;
  static const int leftFootIndex = 31;
  static const int rightFootIndex = 32;

  // Major side tracking groups for push-up biomechanics
  static const List<int> leftSideLandmarks = [11, 13, 15, 23, 25, 27];
  static const List<int> rightSideLandmarks = [12, 14, 16, 24, 26, 28];
}

class PoseConnections {
  /// Pairs of landmark indices defining the full human skeleton overlay
  static const List<List<int>> fullBodyConnections = [
    // Torso box
    [11, 12], // shoulders
    [11, 23], // left torso
    [12, 24], // right torso
    [23, 24], // hips
    // Left arm
    [11, 13], // shoulder to elbow
    [13, 15], // elbow to wrist
    // Right arm
    [12, 14], // shoulder to elbow
    [14, 16], // elbow to wrist
    // Left leg
    [23, 25], // hip to knee
    [25, 27], // knee to ankle
    // Right leg
    [24, 26], // hip to knee
    [26, 28], // knee to ankle
  ];
}
