import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:geolocator/geolocator.dart';
import 'package:file_picker/file_picker.dart';
import 'package:video_player/video_player.dart';
import '../providers/app_provider.dart';
import '../utils/gpx_utils.dart';
import 'login_screen.dart';
import 'recorded_videos_screen.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen>
    with SingleTickerProviderStateMixin {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _roadNameController =
      TextEditingController();
  final TextEditingController _roadTypeController =
      TextEditingController();
  Timer? _scanTimer;
  bool _isInit = false;
  List<Map<String, dynamic>> _currentDetections = [];
  late AnimationController _pulseController;
  
  // Video recording state
  bool _isRecordingVideo = false;
  List<Map<String, dynamic>> _gpsTrack = [];
  DateTime? _videoStartTime;
  StreamSubscription<Position>? _positionStreamSubscription;

  @override
  void initState() {
    super.initState();
    // Camera is no longer initialized here to save battery
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  Future<bool> _ensureCameraInitialized() async {
    if (_isInit && _controller != null && _controller!.value.isInitialized) return true;
    
    setState(() => _isInit = false); // Show loader if needed
    
    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        _controller = CameraController(
          _cameras![0],
          // ResolutionPreset.veryHigh targets 1080p (1080x1920) at ~30 FPS
          // This satisfies: FPS: 20-40, Resolution: Max 1080x1920, Min 480x520
          ResolutionPreset.veryHigh, 
          enableAudio: false,
          imageFormatGroup: ImageFormatGroup.jpeg, 
        );
        await _controller!.initialize();
        if (!mounted) return false;
        setState(() {
          _isInit = true;
        });
        return true;
      }
    } catch (e) {
      print("Camera init error: $e");
    }
    return false;
  }

  Future<void> _disposeCamera() async {
    if (_controller != null) {
      await _controller!.dispose();
      _controller = null;
      if (mounted) {
        setState(() {
          _isInit = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    _scanTimer?.cancel();
    _roadNameController.dispose();
    _roadTypeController.dispose();
    _pulseController.dispose();
    _positionStreamSubscription?.cancel();
    super.dispose();
  }

  Future<void> _startScanning() async {
    if (_roadNameController.text.isEmpty || _roadTypeController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Please enter Road Name and Road Type'),
          backgroundColor: Colors.redAccent.withOpacity(0.9),
          behavior: SnackBarBehavior.floating,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
      return;
    }

    // Lazy load camera
    final isReady = await _ensureCameraInitialized();
    if (!isReady) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to initialize camera')),
        );
      }
      return;
    }

    final provider = context.read<AppProvider>();
    provider.setScanning(true);
    provider.startSurvey(_roadNameController.text, _roadTypeController.text);

    _scanTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      if (!provider.isScanning || provider.isPaused) return;
      await _captureAndProcess();
    });
  }

  void _stopScanning() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF141B2D),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('End Survey',
            style: TextStyle(fontWeight: FontWeight.w800)),
        content: const Text('Are you sure you want to end this survey?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Cancel',
                style: TextStyle(color: Colors.white.withOpacity(0.5))),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              final provider = context.read<AppProvider>();
              provider.setScanning(false);
              _scanTimer?.cancel();
              provider.stopSurvey(status: 'completed');
              _disposeCamera(); // Save battery
              setState(() {
                _currentDetections.clear();
              });
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('End Survey',
                style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Future<void> _captureAndProcess() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    try {
      final XFile image = await _controller!.takePicture();
      final provider = context.read<AppProvider>();
      final result = await provider.uploadCapture(File(image.path),
          roadName: _roadNameController.text);

      if (mounted && (result.containsKey('defects') || result.containsKey('detections'))) {
        final rawList = result['defects'] ?? result['detections'] ?? [];
        final detections =
            List<Map<String, dynamic>>.from(rawList);
        setState(() {
          _currentDetections = detections;
        });

        // Clear detections after 4 seconds
        Future.delayed(const Duration(seconds: 4), () {
          if (mounted) {
            setState(() {
              _currentDetections.clear();
            });
          }
        });
      }
    } catch (e) {
      print("Capture error: $e");
    }
  }

  Future<void> _startVideoRecording() async {
    if (_roadNameController.text.isEmpty || _roadTypeController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Please enter Road Name and Road Type'),
          backgroundColor: Colors.redAccent.withOpacity(0.9),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }
    
    // Lazy load camera
    final isReady = await _ensureCameraInitialized();
    if (!isReady) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to initialize camera')),
        );
      }
      return;
    }
    
    if (_controller == null || !_controller!.value.isInitialized) return;

    try {
      await _controller!.startVideoRecording();
      setState(() {
        _isRecordingVideo = true;
        _gpsTrack = [];
        _videoStartTime = DateTime.now();
      });

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.deniedForever || permission == LocationPermission.denied) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Warning: GPS Permission denied. No coordinates will be recorded.'), backgroundColor: Colors.redAccent),
          );
        }
        // Proceed but without GPS listeners if needed
      }

      bool isEnabled = await Geolocator.isLocationServiceEnabled();
      if (!isEnabled) {
         if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Error: Please enable GPS/Location on your device before recording.'), backgroundColor: Colors.redAccent),
          );
        }
        return;
      }

      const LocationSettings locationSettings = LocationSettings(
        accuracy: LocationAccuracy.bestForNavigation,
        distanceFilter: 0,
      );

      _positionStreamSubscription = Geolocator.getPositionStream(locationSettings: locationSettings)
          .listen((Position? pos) {
        if (pos != null && _videoStartTime != null && _isRecordingVideo) {
          final timeSec = DateTime.now().difference(_videoStartTime!).inMilliseconds / 1000.0;
          
          _gpsTrack.add({
            'time': timeSec,
            'latitude': pos.latitude,
            'longitude': pos.longitude,
            'heading': pos.heading,
          });
        }
      });
    } catch (e) {
      print("Error starting video recording: $e");
    }
  }

  Future<void> _stopVideoRecording() async {
    if (_controller == null || !_controller!.value.isRecordingVideo) return;
    
    _positionStreamSubscription?.cancel();
    
    try {
      final XFile? videoFile = await _controller!.stopVideoRecording();
      setState(() {
        _isRecordingVideo = false;
      });
      _disposeCamera(); // Save battery
      
      if (videoFile == null) return;

      print("[RECORD-DEBUG] Recording stopped. GPS track points: ${_gpsTrack.length}");
      if (_gpsTrack.isNotEmpty) {
        print("[RECORD-DEBUG] First GPS point: ${_gpsTrack.first}");
        print("[RECORD-DEBUG] Last GPS point: ${_gpsTrack.last}");
      } else {
        print("[RECORD-DEBUG] ⚠️ WARNING: GPS track is EMPTY! No coordinates were captured during recording.");
        print("[RECORD-DEBUG] Check: Was Location/GPS turned ON? Was location permission granted?");
      }
      
      final appDir = await getApplicationDocumentsDirectory();
      final videosDir = Directory(p.join(appDir.path, 'RoadScannerVideos'));
      if (!await videosDir.exists()) {
        await videosDir.create(recursive: true);
      }
      
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final savedVideoPath = p.join(videosDir.path, 'video_$timestamp.mp4');
      final savedGpsPath = p.join(videosDir.path, 'gps_$timestamp.gpx');
      final savedSrtPath = p.join(videosDir.path, 'video_$timestamp.srt');
      final savedMetaPath = p.join(videosDir.path, 'meta_$timestamp.json');
      
      await File(videoFile.path).copy(savedVideoPath);
      // Save GPS coordinates in standard GPX 1.1 XML format
      final gpxContent = generateGpxContent(_gpsTrack, _roadNameController.text, startTime: _videoStartTime);
      await File(savedGpsPath).writeAsString(gpxContent);
      print("[RECORD-DEBUG] GPS file saved as GPX to: $savedGpsPath (${gpxContent.length} bytes)");
      
      // 1. Generate SRT subtitle file for video tracker
      StringBuffer srtBuffer = StringBuffer();
      for (int i = 0; i < _gpsTrack.length; i++) {
        final track = _gpsTrack[i];
        final timeSec = track['time'] as double;
        final nextTimeSec = (i + 1 < _gpsTrack.length) ? _gpsTrack[i+1]['time'] as double : timeSec + 1.0;
        
        String formatTime(double seconds) {
            int h = (seconds / 3600).floor();
            int m = ((seconds % 3600) / 60).floor();
            int s = (seconds % 60).floor();
            int ms = ((seconds * 1000) % 1000).floor();
            return "${h.toString().padLeft(2,'0')}:${m.toString().padLeft(2,'0')}:${s.toString().padLeft(2,'0')},${ms.toString().padLeft(3,'0')}";
        }
        srtBuffer.writeln("${i + 1}");
        srtBuffer.writeln("${formatTime(timeSec)} --> ${formatTime(nextTimeSec)}");
        srtBuffer.writeln("Lat: ${track['latitude']}, Lng: ${track['longitude']}");
        if (i < _gpsTrack.length - 1) srtBuffer.writeln();
      }
      await File(savedSrtPath).writeAsString(srtBuffer.toString());

      // 2 & 3. Validate video size and resolution
      bool showWarning = false;
      double recordedWidth = 0.0;
      double recordedHeight = 0.0;
      try {
        final videoController = VideoPlayerController.file(File(savedVideoPath));
        await videoController.initialize();
        recordedWidth = videoController.value.size.width;
        recordedHeight = videoController.value.size.height;
        await videoController.dispose();
        
        final double minSide = recordedWidth < recordedHeight ? recordedWidth : recordedHeight;
        final double maxSide = recordedWidth > recordedHeight ? recordedWidth : recordedHeight;
        
        // Validate: Min 480×520, Max 1080×1920 (Orientation agnostic)
        if (minSide < 480 || maxSide < 520 || minSide > 1080 || maxSide > 1920) {
          showWarning = true;
        }
      } catch (e) {
        print("Video validation error: $e");
      }
      
      final metaData = {
        'id': timestamp.toString(),
        'roadName': _roadNameController.text.isNotEmpty ? _roadNameController.text : 'Unknown Road',
        'roadType': _roadTypeController.text.isNotEmpty ? _roadTypeController.text : 'Unknown',
        'timestamp': DateTime.now().toIso8601String(),
        'videoFile': 'video_$timestamp.mp4',
        'gpsFile': 'gps_$timestamp.gpx',
        'srtFile': 'video_$timestamp.srt',
        'uploaded': false,
        'gpsData': _gpsTrack, // Embed GPS data as JSON fallback for backend API
        'gpsPointCount': _gpsTrack.length,
        'targetFps': 30, // Required: 20-40 FPS
        'resolutionMin': '480x520',
        'resolutionMax': '1080x1920',
      };
      await File(savedMetaPath).writeAsString(jsonEncode(metaData));
      print("[RECORD-DEBUG] Metadata saved with ${_gpsTrack.length} embedded GPS points");
      
      if (!mounted) return;
      
      if (_gpsTrack.isEmpty) {
        // Critical warning about missing GPS
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('⚠️ Recording saved but NO GPS coordinates captured! Location may have been disabled or permission denied. Defects will NOT appear on the map.'),
            backgroundColor: Colors.redAccent,
            duration: Duration(seconds: 8),
          ),
        );
      } else if (showWarning) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Warning: Video resolution (${recordedWidth.toInt()}x${recordedHeight.toInt()}) is outside the allowed range (Min: 480×520, Max: 1080×1920).'),
            backgroundColor: Colors.orangeAccent.withValues(alpha: 0.9),
            duration: const Duration(seconds: 5),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ Recording saved with ${_gpsTrack.length} GPS points! (${recordedWidth.toInt()}x${recordedHeight.toInt()}) Access it from "Recorded Videos".'),
            backgroundColor: Colors.greenAccent.withValues(alpha: 0.9),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      print("Error stopping video recording: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    final surveyDefectCount = provider.isScanning
        ? provider.defects
            .where((d) => d['survey_id'] == provider.currentSurveyId)
            .length
        : 0;

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // Camera preview
          _buildCameraPreview(),
          // Top bar
          _buildTopBar(provider),
          // Detection overlays
          if (_currentDetections.isNotEmpty) _buildDetectionResults(),
          // Bottom panel
          _buildBottomPanel(provider, surveyDefectCount),
        ],
      ),
    );
  }

  Widget _buildCameraPreview() {
    if (!_isInit || _controller == null) {
      return Container(
        color: const Color(0xFF0F172A),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF00D4AA).withOpacity(0.1),
                      blurRadius: 40,
                      spreadRadius: 10,
                    ),
                  ],
                ),
                child: Icon(
                  Icons.videocam_off_rounded,
                  size: 50,
                  color: Colors.white.withOpacity(0.2),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Camera Idle',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.4),
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Ready to start scan or recording',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.25),
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      );
    }
    return SizedBox.expand(
      child: CameraPreview(_controller!),
    );
  }

  Widget _buildTopBar(AppProvider provider) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: EdgeInsets.only(
          top: MediaQuery.of(context).padding.top + 8,
          left: 16,
          right: 16,
          bottom: 12,
        ),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Colors.black.withOpacity(0.7),
              Colors.transparent,
            ],
          ),
        ),
        child: Row(
          children: [
            // Road Scanner title
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.4),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.white.withOpacity(0.1)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.gps_fixed_rounded,
                      size: 16, color: Colors.white.withOpacity(0.8)),
                  const SizedBox(width: 8),
                  const Text(
                    'Road Scanner',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            // Status indicator
            if (provider.isScanning)
              AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  return Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: provider.isPaused
                          ? Colors.orange.withOpacity(0.2)
                          : Colors.green.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: provider.isPaused
                            ? Colors.orange.withOpacity(0.5)
                            : Colors.green.withOpacity(0.5),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: provider.isPaused
                                ? Colors.orange
                                : Colors.green.withOpacity(
                                    0.5 + 0.5 * _pulseController.value),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          provider.isPaused ? 'PAUSED' : 'SCANNING',
                          style: TextStyle(
                            color: provider.isPaused
                                ? Colors.orange
                                : Colors.greenAccent,
                            fontWeight: FontWeight.w800,
                            fontSize: 11,
                            letterSpacing: 1,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            const Spacer(),
            // Logout button
            Container(
              decoration: BoxDecoration(
                color: Colors.redAccent.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: IconButton(
                icon: Icon(Icons.logout_rounded,
                    color: Colors.redAccent.withOpacity(0.8), size: 22),
                onPressed: () {
                  context.read<AppProvider>().logout();
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(
                        builder: (context) => const LoginScreen()),
                    (route) => false,
                  );
                },
                padding: const EdgeInsets.all(8),
                constraints: const BoxConstraints(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetectionResults() {
    return Positioned(
      bottom: 310,
      left: 16,
      right: 16,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFF141B2D).withOpacity(0.92),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.4),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: _currentDetections.take(3).map((detection) {
            final String className =
                (detection['class_name'] ?? detection['class'] ?? 'Unknown').toString();
            final double confidence =
                (detection['confidence'] ?? 0.0).toDouble();
            final num areaSqm = detection['estimated_area_sqm'] ?? 0.0;
            final double areaCm2 = areaSqm * 10000;
            final String severity = _getSeverity(confidence);
            final Color severityColor = _getSeverityColor(severity);

            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Container(
                    width: 3,
                    height: 24,
                    decoration: BoxDecoration(
                      color: _getDefectColor(className),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      className.replaceAll('_', ' '),
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  Text(
                    '${(confidence * 100).toStringAsFixed(0)}%',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                      color: Colors.white.withOpacity(0.7),
                    ),
                  ),
                  if (areaCm2 > 0) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.blueAccent.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.blueAccent.withOpacity(0.3)),
                      ),
                      child: Text(
                        '${areaCm2.toStringAsFixed(0)} cm²',
                        style: const TextStyle(
                          color: Colors.blueAccent,
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(width: 8),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: severityColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                      border:
                          Border.all(color: severityColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      severity,
                      style: TextStyle(
                        color: severityColor,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildBottomPanel(AppProvider provider, int surveyDefectCount) {
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(context).padding.bottom + 70,
        ),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Colors.transparent,
              Colors.black.withOpacity(0.6),
              Colors.black.withOpacity(0.9),
            ],
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // No defects message
            if (provider.isScanning &&
                _currentDetections.isEmpty &&
                !provider.isPaused)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green.withOpacity(0.2)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.check_circle_outline_rounded,
                        color: Colors.greenAccent.withOpacity(0.8), size: 18),
                    const SizedBox(width: 8),
                    Text(
                      'No defects detected',
                      style: TextStyle(
                        color: Colors.greenAccent.withOpacity(0.8),
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ),
              ),

            // Road name row with defect count
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1A1F33).withOpacity(0.9),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withOpacity(0.06)),
              ),
              child: Row(
                children: [
                  ShaderMask(
                    shaderCallback: (bounds) => const LinearGradient(
                      colors: [Color(0xFF6366F1), Color(0xFF818CF8)],
                    ).createShader(bounds),
                    child: const Icon(Icons.add_road_rounded,
                        color: Colors.white, size: 22),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: provider.isScanning
                        ? Text(
                            _roadNameController.text,
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 15,
                            ),
                          )
                        : TextField(
                            controller: _roadNameController,
                            style: const TextStyle(
                                color: Colors.white, fontSize: 15),
                            decoration: InputDecoration(
                              hintText: 'Road Name',
                              hintStyle: TextStyle(
                                  color: Colors.white.withOpacity(0.3)),
                              border: InputBorder.none,
                              contentPadding: EdgeInsets.zero,
                              isDense: true,
                            ),
                          ),
                  ),
                  if (provider.isScanning)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: surveyDefectCount > 0
                            ? Colors.redAccent.withOpacity(0.15)
                            : Colors.green.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: surveyDefectCount > 0
                              ? Colors.redAccent.withOpacity(0.3)
                              : Colors.green.withOpacity(0.3),
                        ),
                      ),
                      child: Text(
                        '$surveyDefectCount defects',
                        style: TextStyle(
                          color: surveyDefectCount > 0
                              ? Colors.redAccent
                              : Colors.greenAccent,
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 10),

            // Road type row
            if (!provider.isScanning)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1A1F33).withOpacity(0.9),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.white.withOpacity(0.06)),
                ),
                child: Row(
                  children: [
                    ShaderMask(
                      shaderCallback: (bounds) => const LinearGradient(
                        colors: [Color(0xFF00D4AA), Color(0xFF0EA5E9)],
                      ).createShader(bounds),
                      child: const Icon(Icons.merge_type_rounded,
                          color: Colors.white, size: 22),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: _roadTypeController,
                        style: const TextStyle(
                            color: Colors.white, fontSize: 15),
                        decoration: InputDecoration(
                          hintText: 'Road Type (e.g. NH, SH, VR)',
                          hintStyle: TextStyle(
                              color: Colors.white.withOpacity(0.3)),
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.zero,
                          isDense: true,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1A1F33).withOpacity(0.9),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.white.withOpacity(0.06)),
                ),
                child: Row(
                  children: [
                    ShaderMask(
                      shaderCallback: (bounds) => const LinearGradient(
                        colors: [Color(0xFF00D4AA), Color(0xFF0EA5E9)],
                      ).createShader(bounds),
                      child: const Icon(Icons.merge_type_rounded,
                          color: Colors.white, size: 22),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      _roadTypeController.text,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 12),

            // Action buttons
            if (!provider.isScanning && !_isRecordingVideo)
              Column(
                children: [
                  Row(
                    children: [
                      SizedBox(
                        height: 54,
                        width: 54,
                        child: ElevatedButton(
                          onPressed: () => Navigator.push(
                            context,
                            MaterialPageRoute(builder: (context) => const RecordedVideosScreen()),
                          ),
                          style: ElevatedButton.styleFrom(
                            padding: EdgeInsets.zero,
                            backgroundColor: const Color(0xFF1E2438).withOpacity(0.95),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                              side: BorderSide(color: Colors.white.withOpacity(0.08)),
                            ),
                            elevation: 0,
                          ),
                          child: const Icon(Icons.video_collection_rounded, color: Colors.orangeAccent, size: 24),
                        ),
                      ),
                      const SizedBox(width: 8),
                      SizedBox(
                        height: 54,
                        width: 54,
                        child: ElevatedButton(
                          onPressed: () => _showUploadVideoDialog(context),
                          style: ElevatedButton.styleFrom(
                            padding: EdgeInsets.zero,
                            backgroundColor: const Color(0xFF1E2438).withOpacity(0.95),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                              side: BorderSide(color: Colors.white.withOpacity(0.08)),
                            ),
                            elevation: 0,
                          ),
                          child: const Icon(Icons.upload_file_rounded, color: Colors.white, size: 24),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: SizedBox(
                          height: 54,
                          child: ElevatedButton(
                            onPressed: _startScanning,
                            style: ElevatedButton.styleFrom(
                              padding: EdgeInsets.zero,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                              ),
                              elevation: 0,
                            ),
                            child: Ink(
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [
                                    Color(0xFF7C3AED),
                                    Color(0xFF6366F1),
                                    Color(0xFF818CF8),
                                  ],
                                ),
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: Container(
                                alignment: Alignment.center,
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(4),
                                      decoration: BoxDecoration(
                                        color: Colors.white.withOpacity(0.2),
                                        shape: BoxShape.circle,
                                      ),
                                      child: const Icon(Icons.play_arrow_rounded,
                                          color: Colors.white, size: 22),
                                    ),
                                    const SizedBox(width: 10),
                                    const Text(
                                      'Start Scanning',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w700,
                                        fontSize: 16,
                                        color: Colors.white,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: SizedBox(
                          height: 54,
                          child: ElevatedButton(
                            onPressed: _startVideoRecording,
                            style: ElevatedButton.styleFrom(
                              padding: EdgeInsets.zero,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                              ),
                              elevation: 0,
                            ),
                            child: Ink(
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFE11D48), Color(0xFFBE123C)],
                                ),
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: Container(
                                alignment: Alignment.center,
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(Icons.videocam_rounded, color: Colors.white, size: 24),
                                    const SizedBox(width: 10),
                                    const Text('Record Video', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Colors.white)),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              )
            else if (_isRecordingVideo)
               Row(
                 children: [
                   Expanded(
                     child: SizedBox(
                       height: 54,
                       child: ElevatedButton.icon(
                         onPressed: _stopVideoRecording,
                         icon: const Icon(Icons.stop_rounded, size: 24),
                         label: const Text('STOP RECORDING', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14, letterSpacing: 0.5)),
                         style: ElevatedButton.styleFrom(
                           backgroundColor: Colors.redAccent,
                           foregroundColor: Colors.white,
                           elevation: 0,
                           shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                         ),
                       ),
                     ),
                   ),
                 ],
               )
            else
              // Pause and End Survey buttons
              Row(
                children: [
                  Expanded(
                    child: SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: () =>
                            provider.setPaused(!provider.isPaused),
                        icon: Icon(
                          provider.isPaused
                              ? Icons.play_arrow_rounded
                              : Icons.pause_rounded,
                          size: 22,
                        ),
                        label: Text(
                          provider.isPaused ? 'RESUME' : 'PAUSE',
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 13,
                            letterSpacing: 0.5,
                          ),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor:
                              const Color(0xFF1E2438).withOpacity(0.95),
                          foregroundColor: Colors.white,
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                            side: BorderSide(
                                color: Colors.white.withOpacity(0.08)),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SizedBox(
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _stopScanning,
                        icon: const Icon(Icons.stop_rounded, size: 22),
                        label: const Text(
                          'END SURVEY',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 13,
                            letterSpacing: 0.5,
                          ),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.redAccent,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  String _getSeverity(double confidence) {
    if (confidence >= 0.8) return 'HIGH';
    if (confidence >= 0.6) return 'MEDIUM';
    return 'LOW';
  }

  Color _getSeverityColor(String severity) {
    switch (severity) {
      case 'HIGH':
        return Colors.redAccent;
      case 'MEDIUM':
        return Colors.orangeAccent;
      default:
        return Colors.greenAccent;
    }
  }

  Color _getDefectColor(String className) {
    final lower = className.toLowerCase();
    if (lower.contains('pothole')) return Colors.orangeAccent;
    if (lower.contains('crack')) return Colors.redAccent;
    if (lower.contains('manhole')) return const Color(0xFF00BCD4);
    return const Color(0xFF6366F1);
  }

  void _showUploadVideoDialog(BuildContext context) {
    final localRoadNameController = TextEditingController(text: _roadNameController.text);
    final localRoadTypeController = TextEditingController(text: _roadTypeController.text);
    String? selectedGpsData;
    String? gpsFileName;

    showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Upload Video',
      transitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (context, anim1, anim2) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return Center(
              child: Material(
                color: Colors.transparent,
                child: Container(
                  width: MediaQuery.of(context).size.width * 0.85,
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: const Color(0xFF141B2D),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: Colors.white.withOpacity(0.1)),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withOpacity(0.5), blurRadius: 30, offset: const Offset(0, 10)),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ShaderMask(
                        shaderCallback: (bounds) => const LinearGradient(
                          colors: [Color(0xFF00D4AA), Color(0xFF0EA5E9)],
                        ).createShader(bounds),
                        child: const Icon(Icons.video_library_rounded, size: 48, color: Colors.white),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Upload Video Analysis',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Confirm road details and attach mapping data if available.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 13, color: Colors.white.withOpacity(0.6)),
                      ),
                      const SizedBox(height: 24),
                      // Road Name Input
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1A1F33),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.white.withOpacity(0.05)),
                        ),
                        child: TextField(
                          controller: localRoadNameController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            icon: Icon(Icons.add_road_rounded, color: Colors.white.withOpacity(0.5)),
                            hintText: 'Road Name',
                            hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                            border: InputBorder.none,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Road Type Input
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1A1F33),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.white.withOpacity(0.05)),
                        ),
                        child: TextField(
                          controller: localRoadTypeController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            icon: Icon(Icons.merge_type_rounded, color: Colors.white.withOpacity(0.5)),
                            hintText: 'Road Type (e.g. NH, SH)',
                            hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
                            border: InputBorder.none,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      // GPS File Picker
                      InkWell(
                        onTap: () async {
                          final result = await FilePicker.platform.pickFiles(
                            type: FileType.custom,
                            allowedExtensions: ['gpx', 'json'],
                          );
                          if (result != null) {
                            final file = File(result.files.single.path!);
                            final content = await file.readAsString();
                            setDialogState(() {
                              selectedGpsData = content;
                              gpsFileName = result.files.single.name;
                            });
                          }
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          decoration: BoxDecoration(
                            color: selectedGpsData != null 
                                ? const Color(0xFF00D4AA).withOpacity(0.1) 
                                : Colors.white.withOpacity(0.03),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: selectedGpsData != null 
                                  ? const Color(0xFF00D4AA).withOpacity(0.4) 
                                  : Colors.white.withOpacity(0.1)
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                selectedGpsData != null ? Icons.gps_fixed_rounded : Icons.location_off_rounded,
                                color: selectedGpsData != null ? const Color(0xFF00D4AA) : Colors.white.withOpacity(0.3),
                                size: 20,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  gpsFileName ?? 'Attach GPS Data (Optional)',
                                  style: TextStyle(
                                    color: selectedGpsData != null ? Colors.white : Colors.white.withOpacity(0.3),
                                    fontSize: 13,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              if (selectedGpsData != null)
                                IconButton(
                                  icon: const Icon(Icons.close_rounded, size: 16, color: Colors.redAccent),
                                  onPressed: () {
                                    setDialogState(() {
                                      selectedGpsData = null;
                                      gpsFileName = null;
                                    });
                                  },
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),
                      Row(
                        children: [
                          Expanded(
                            child: TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: Text('Cancel', style: TextStyle(color: Colors.white.withOpacity(0.5))),
                            ),
                          ),
                          Expanded(
                            child: ElevatedButton(
                              onPressed: () {
                                if (localRoadNameController.text.isEmpty || localRoadTypeController.text.isEmpty) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Please enter both Road Name and Type')),
                                  );
                                  return;
                                }
                                Navigator.pop(context);
                                _pickAndUploadVideo(localRoadNameController.text, localRoadTypeController.text, gpsData: selectedGpsData);
                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF6366F1),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                padding: const EdgeInsets.symmetric(vertical: 12),
                              ),
                              child: const Text('Select Video', style: TextStyle(color: Colors.white)),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          }
        );
      },
    );
  }

  Future<void> _pickAndUploadVideo(String roadName, String roadType, {String? gpsData}) async {
    final XFile? video = await _picker.pickVideo(source: ImageSource.gallery);
    if (video != null) {
      if (!mounted) return;
      final provider = context.read<AppProvider>();
      
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => PopScope(
          canPop: false,
          child: AlertDialog(
            backgroundColor: const Color(0xFF141B2D),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SpinKitPulse(color: Color(0xFF00D4AA), size: 50.0),
                const SizedBox(height: 16),
                const Text('Uploading & Analyzing...', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('This may take a few minutes.', style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 12)),
              ],
            ),
          ),
        ),
      );

      final result = await provider.uploadVideoFile(File(video.path), roadName: roadName, roadType: roadType, gpsData: gpsData);
      
      if (!mounted) return;
      Navigator.pop(context); // close loading dialog

      if (result.containsKey('error')) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Upload failed: ${result['error']}'),
            backgroundColor: Colors.redAccent,
          ),
        );
      } else {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF141B2D),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Text('Analysis Complete', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            content: Text(
              'Frames processed: ${result['frames_processed'] ?? 0}\nDefects found: ${result['total_defects'] ?? 0}\nEstimated Cost: ₹${result['estimated_total_cost'] ?? 0}',
              style: const TextStyle(color: Colors.white, fontSize: 15),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('OK', style: TextStyle(color: Color(0xFF00D4AA))),
              ),
            ],
          ),
        );
      }
    }
  }
}
