import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';

class AudioService {
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();

  bool _isRecording = false;
  bool _isPaused = false;
  String? _currentRecordingPath;

  bool get isRecording => _isRecording;
  bool get isPaused => _isPaused;
  String? get currentRecordingPath => _currentRecordingPath;

  // 播放控制
  bool get isPlaying => _player.state == PlayerState.playing;
  bool get isStopped => _player.state == PlayerState.stopped;

  Future<bool> hasPermission() async {
    return await _recorder.hasPermission();
  }

  Future<void> startRecording(String filePath) async {
    if (_isRecording) return;

    final hasPermission = await this.hasPermission();
    if (!hasPermission) {
      throw Exception('Microphone permission not granted');
    }

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 16000,
        numChannels: 1,
      ),
      path: filePath,
    );

    _isRecording = true;
    _isPaused = false;
    _currentRecordingPath = filePath;
  }

  Future<String?> stopRecording() async {
    if (!_isRecording) return null;

    final path = await _recorder.stop();
    _isRecording = false;
    _isPaused = false;
    return path;
  }

  Future<void> cancelRecording() async {
    if (!_isRecording) return;

    await _recorder.stop();
    _isRecording = false;
    _isPaused = false;
    _currentRecordingPath = null;
  }

  // 播放音频
  Future<void> playAudio(String audioUrl) async {
    if (isPlaying) {
      await _player.pause();
    } else {
      // 播放音频（会自动处理暂停后继续）
      if (audioUrl.startsWith('http')) {
        await _player.play(UrlSource(audioUrl));
      } else {
        await _player.play(DeviceFileSource(audioUrl));
      }
    }
  }

  // 暂停播放
  Future<void> pauseAudio() async {
    await _player.pause();
  }

  // 停止播放
  Future<void> stopAudio() async {
    await _player.stop();
  }

  // 获取播放器实例（用于监听播放进度）
  AudioPlayer get player => _player;

  Future<void> dispose() async {
    await _recorder.dispose();
    await _player.dispose();
  }
}
