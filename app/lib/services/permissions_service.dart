// ==============================================================================
// FitSense AI - Device Permissions Service
// ==============================================================================

import 'package:permission_handler/permission_handler.dart';

class PermissionsService {
  /// Checks and requests runtime Camera permission for MediaPipe pose estimation.
  static Future<bool> requestCameraPermission() async {
    final status = await Permission.camera.status;

    if (status.isGranted) {
      return true;
    }

    final result = await Permission.camera.request();
    return result.isGranted;
  }

  /// Whether camera permission has been permanently denied in OS settings.
  static Future<bool> isCameraPermanentlyDenied() async {
    final status = await Permission.camera.status;
    return status.isPermanentlyDenied;
  }

  /// Opens application OS settings for the user to manually enable permissions.
  static Future<bool> openSettings() async {
    return openAppSettings();
  }
}
