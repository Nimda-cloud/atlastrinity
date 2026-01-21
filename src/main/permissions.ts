/**
 * AtlasTrinity - macOS Permissions Handler
 */

import { systemPreferences, dialog, shell } from 'electron';

interface PermissionStatus {
  accessibility: boolean;
  microphone: boolean;
  screenRecording: boolean;
}

/**
 * Check all required permissions for AtlasTrinity
 */
export async function checkPermissions(): Promise<boolean> {
  const status = await getPermissionStatus();
  return status.accessibility && status.microphone && status.screenRecording;
}

/**
 * Get detailed permission status
 */
async function getPermissionStatus(): Promise<PermissionStatus> {
  const accessibility = systemPreferences.isTrustedAccessibilityClient(false);
  const microphone = await checkMicrophonePermission();
  const screenRecording = await checkScreenRecordingPermission();

  return {
    accessibility,
    microphone,
    screenRecording,
  };
}

/**
 * Check microphone permission
 */
async function checkMicrophonePermission(): Promise<boolean> {
  const status = systemPreferences.getMediaAccessStatus('microphone');
  return status === 'granted';
}

/**
 * Check screen recording permission
 */
async function checkScreenRecordingPermission(): Promise<boolean> {
  const status = systemPreferences.getMediaAccessStatus('screen');
  return status === 'granted';
}

/**
 * Request all required permissions with user-friendly dialogs
 */
export async function requestPermissions(): Promise<void> {
  const status = await getPermissionStatus();

  // Request Accessibility if not granted
  if (!status.accessibility) {
    const result = await dialog.showMessageBox({
      type: 'info',
      title: 'Доступ до Accessibility',
      message: 'AtlasTrinity потребує доступу до Accessibility API для автоматизації macOS.',
      detail:
        'Натисніть "Відкрити налаштування" і додайте AtlasTrinity до списку дозволених додатків.',
      buttons: ['Відкрити налаштування', 'Пізніше'],
      defaultId: 0,
    });

    if (result.response === 0) {
      await shell.openExternal(
        'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'
      );
    }
  }

  // Request Microphone if not granted
  if (!status.microphone) {
    await systemPreferences.askForMediaAccess('microphone');
  }

  // Request Screen Recording if not granted
  if (!status.screenRecording) {
    const result = await dialog.showMessageBox({
      type: 'info',
      title: 'Доступ до запису екрану',
      message: 'AtlasTrinity потребує доступу до запису екрану для візуальної верифікації.',
      detail:
        'Натисніть "Відкрити налаштування" і додайте AtlasTrinity до списку дозволених додатків.',
      buttons: ['Відкрити налаштування', 'Пізніше'],
      defaultId: 0,
    });

    if (result.response === 0) {
      await shell.openExternal(
        'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'
      );
    }
  }
}
