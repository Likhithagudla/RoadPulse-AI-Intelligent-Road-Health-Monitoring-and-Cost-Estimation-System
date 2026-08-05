import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:share_plus/share_plus.dart';
import 'package:archive/archive_io.dart';
import '../providers/app_provider.dart';
import '../utils/gpx_utils.dart';

class RecordedVideosScreen extends StatefulWidget {
  const RecordedVideosScreen({super.key});

  @override
  State<RecordedVideosScreen> createState() => _RecordedVideosScreenState();
}

class _RecordedVideosScreenState extends State<RecordedVideosScreen> {
  List<Map<String, dynamic>> _videos = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadVideos();
  }

  Future<void> _loadVideos() async {
    try {
      final appDir = await getApplicationDocumentsDirectory();
      final videosDir = Directory(p.join(appDir.path, 'RoadScannerVideos'));
      
      if (!await videosDir.exists()) {
        setState(() {
          _videos = [];
          _isLoading = false;
        });
        return;
      }

      final entities = await videosDir.list().toList();
      final metaFiles = entities.where((e) => e is File && p.basename(e.path).startsWith('meta_')).toList();
      
      List<Map<String, dynamic>> loaded = [];
      for (var metaFile in metaFiles) {
        try {
          final content = await File(metaFile.path).readAsString();
          final Map<String, dynamic> data = jsonDecode(content);
          
          // Re-resolve paths from filenames to be robust. Support both old absolute and new relative paths.
          String videoName = data['videoFile'] ?? (data['videoPath'] != null ? p.basename(data['videoPath']) : '');
          String gpsName = data['gpsFile'] ?? (data['gpsPath'] != null ? p.basename(data['gpsPath']) : '');
          String srtName = data['srtFile'] ?? (data['srtPath'] != null ? p.basename(data['srtPath']) : '');

          if (videoName.isEmpty) continue;
          
          final videoPath = p.join(videosDir.path, videoName);
          final gpsPath = p.join(videosDir.path, gpsName);
          final srtPath = p.join(videosDir.path, srtName);
          
          // Ensure video still exists
          final videoExists = await File(videoPath).exists();
          if (videoExists) {
            data['metaFile'] = metaFile.path;
            data['resolvedVideoPath'] = videoPath;
            data['resolvedGpsPath'] = gpsPath;
            data['resolvedSrtPath'] = srtPath;
            loaded.add(data);
          }
        } catch(e) {
            print("Error parsing a meta file: $e");
        }
      }
      
      // Sort newest first
      loaded.sort((a, b) {
        final dateA = DateTime.parse(a['timestamp']);
        final dateB = DateTime.parse(b['timestamp']);
        return dateB.compareTo(dateA);
      });

      setState(() {
        _videos = loaded;
        _isLoading = false;
      });
    } catch (e) {
      print("Error loading videos: $e");
      setState(() => _isLoading = false);
    }
  }

  Future<void> _deleteVideo(Map<String, dynamic> video) async {
    try {
      final videoFile = File(video['resolvedVideoPath']);
      final gpsFile = File(video['resolvedGpsPath']);
      final metaFile = File(video['metaFile']);
      final srtFile = File(video['resolvedSrtPath'] ?? '');
      
      if (await videoFile.exists()) await videoFile.delete();
      if (await gpsFile.exists()) await gpsFile.delete();
      if (await metaFile.exists()) await metaFile.delete();
      if (await srtFile.exists()) await srtFile.delete();
      
      _loadVideos();
    } catch (e) {
      print("Delete error: $e");
    }
  }

  Future<void> _shareVideo(Map<String, dynamic> video) async {
    final videoFile = File(video['resolvedVideoPath'] ?? '');
    File gpsFile = File(video['resolvedGpsPath'] ?? '');
    File srtFile = File(video['resolvedSrtPath'] ?? '');
    
    if (!await videoFile.exists()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Video file not found.'), backgroundColor: Colors.redAccent),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Preparing bundle with GPS...'), duration: Duration(seconds: 2)),
    );
    
    try {
      final date = DateTime.parse(video['timestamp']);
      final formattedDate = DateFormat('MMM d, yyyy • h:mm a').format(date);
      final text = 'Road Survey Video: ${video['roadName'] ?? 'Unknown Road'} (${video['roadType']})\nRecorded on: $formattedDate';
      
      // Robust GPS file detection
      final videosDir = Directory(p.dirname(videoFile.path));
      final videoBasename = p.basenameWithoutExtension(videoFile.path);
      final timestampMatch = RegExp(r'\d+').firstMatch(videoBasename);
      final ts = timestampMatch?.group(0);

      print("[SHARE-DEBUG] === _shareVideo START ===");
      print("[SHARE-DEBUG] Video: ${videoFile.path} (Exists: ${await videoFile.exists()})");
      print("[SHARE-DEBUG] GPS resolved path: ${gpsFile.path}");
      print("[SHARE-DEBUG] GPS exists at resolved path: ${await gpsFile.exists()}");
      print("[SHARE-DEBUG] SRT resolved path: ${srtFile.path}");
      print("[SHARE-DEBUG] Extracted timestamp: $ts");
      print("[SHARE-DEBUG] Videos dir: ${videosDir.path}");
      
      // List ALL files in the directory for debugging
      final allFiles = await videosDir.list().toList();
      final allFileNames = allFiles.map((e) => p.basename(e.path)).toList();
      print("[SHARE-DEBUG] All files in dir (${allFileNames.length}): $allFileNames");

      // Strategy 1: Check the resolved path
      bool gpsFound = await gpsFile.exists();
      
      // Strategy 2: Try timestamp-based naming
      if (!gpsFound && ts != null) {
        print("[SHARE-DEBUG] GPS not at resolved path. Trying gps_$ts.gpx...");
        File altGps = File(p.join(videosDir.path, 'gps_$ts.gpx'));
        if (!await altGps.exists()) {
          altGps = File(p.join(videosDir.path, 'gps_$ts.json'));
        }
        if (await altGps.exists()) {
          gpsFile = altGps;
          gpsFound = true;
          print("[SHARE-DEBUG] ✓ Found GPS via timestamp: ${altGps.path}");
        }
      }
      
      // Strategy 3: Try metadata gpsFile field directly
      if (!gpsFound && video['gpsFile'] != null) {
        final metaGps = File(p.join(videosDir.path, video['gpsFile']));
        print("[SHARE-DEBUG] Trying metadata gpsFile: ${metaGps.path}");
        if (await metaGps.exists()) {
          gpsFile = metaGps;
          gpsFound = true;
          print("[SHARE-DEBUG] ✓ Found GPS via metadata field: ${metaGps.path}");
        }
      }
      
      // Strategy 4: Scan directory for ANY gps_*.gpx or .json file
      if (!gpsFound) {
        print("[SHARE-DEBUG] Scanning directory for any gps_*.gpx or .json file...");
        for (var entity in allFiles) {
          final name = p.basename(entity.path).toLowerCase();
          if (name.startsWith('gps_') && (name.endsWith('.gpx') || name.endsWith('.json'))) {
            // If timestamp matches the video timestamp, prefer it
            if (ts != null && name.contains(ts)) {
              gpsFile = File(entity.path);
              gpsFound = true;
              print("[SHARE-DEBUG] ✓ Found matching GPS file by scan: ${entity.path}");
              break;
            }
          }
        }
        // If no timestamp-matched GPS, take any GPS file as last resort
        if (!gpsFound) {
          for (var entity in allFiles) {
            final name = p.basename(entity.path).toLowerCase();
            if (name.startsWith('gps_') && (name.endsWith('.gpx') || name.endsWith('.json'))) {
              gpsFile = File(entity.path);
              gpsFound = true;
              print("[SHARE-DEBUG] ✓ Found GPS file by fallback scan: ${entity.path}");
              break;
            }
          }
        }
      }
      
      // Strategy 5: ULTIMATE FALLBACK - Create GPS file from embedded metadata
      if (!gpsFound && video['gpsData'] != null) {
        print("[SHARE-DEBUG] Strategy 5: Creating GPS file from embedded metadata...");
        final gpsDataList = video['gpsData'];
        if (gpsDataList is List && gpsDataList.isNotEmpty) {
          final tempDir = await getTemporaryDirectory();
          final tempGpsPath = p.join(tempDir.path, 'gps_${ts ?? 'recovered'}.gpx');
          final gpxContent = generateGpxContent(gpsDataList, video['roadName'] ?? 'Recovered Road', startTime: DateTime.parse(video['timestamp'] ?? DateTime.now().toIso8601String()));
          await File(tempGpsPath).writeAsString(gpxContent);
          gpsFile = File(tempGpsPath);
          gpsFound = true;
          print("[SHARE-DEBUG] ✓ Created GPX file from metadata: $tempGpsPath (${gpxContent.length} chars, ${gpsDataList.length} points)");
        } else {
          print("[SHARE-DEBUG] ✗ Metadata gpsData is empty or not a list: ${gpsDataList.runtimeType}");
        }
      }
      
      // SRT file recovery
      bool srtFound = await srtFile.exists();
      if (!srtFound && ts != null) {
        final altSrt = File(p.join(videosDir.path, 'video_$ts.srt'));
        if (await altSrt.exists()) {
          srtFile = altSrt;
          srtFound = true;
        }
      }
      
      // Log GPS file contents for debugging
      if (gpsFound) {
        final gpsContent = await gpsFile.readAsString();
        print("[SHARE-DEBUG] ✓ GPS file size: ${gpsContent.length} chars");
        print("[SHARE-DEBUG] GPS preview: ${gpsContent.substring(0, gpsContent.length < 300 ? gpsContent.length : 300)}");
      } else {
        print("[SHARE-DEBUG] ✗ NO GPS FILE FOUND even after all 5 strategies! GPS points in metadata: ${video['gpsPointCount'] ?? 'unknown'}");
      }
                   
      // Create a zip to bundle both video and GPS data seamlessly.
      final tempDir = await getTemporaryDirectory();
      final zipPath = p.join(tempDir.path, 'Survey_${date.millisecondsSinceEpoch}.zip');
      
      final encoder = ZipFileEncoder();
      encoder.create(zipPath);
      
      // CRITICAL: Use addFileSync (not addFile which is async in archive 4.0+)
      encoder.addFileSync(videoFile, p.basename(videoFile.path));
      print("[SHARE-DEBUG] ✓ Added video to ZIP: ${p.basename(videoFile.path)}");
      
      if (gpsFound) {
        encoder.addFileSync(gpsFile, p.basename(gpsFile.path));
        print("[SHARE-DEBUG] ✓ Added GPS to ZIP: ${p.basename(gpsFile.path)}");
      }
      if (srtFound) {
        encoder.addFileSync(srtFile, p.basename(srtFile.path));
        print("[SHARE-DEBUG] ✓ Added SRT to ZIP: ${p.basename(srtFile.path)}");
      }
      encoder.closeSync();

      if (!await File(zipPath).exists()) throw Exception("Failed to generate ZIP");
      
      // Verify ZIP contents
      print("[SHARE-DEBUG] ZIP created: $zipPath (${await File(zipPath).length()} bytes)");
      
      // Warn user if GPS is missing
      if (!gpsFound && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('⚠️ Warning: GPS data file not found! Your recording may not have captured GPS coordinates. Make sure Location/GPS is ON before recording.'),
            backgroundColor: Colors.orangeAccent,
            duration: Duration(seconds: 5),
          ),
        );
      }

      await Share.shareXFiles(
        [XFile(zipPath)],
        text: text,
      );
      
      print("[SHARE-DEBUG] === _shareVideo END ===");
    } catch (e) {
      print("Share error: $e");
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error preparing share: $e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  Future<void> _analyzeVideo(Map<String, dynamic> video) async {
    final provider = context.read<AppProvider>();
    final videoFile = File(video['resolvedVideoPath'] ?? '');
    final gpsFile = File(video['resolvedGpsPath'] ?? '');
    
    if (!await videoFile.exists()) return;
    
    String gpsDataJson = "[]";
    if (await gpsFile.exists()) {
      gpsDataJson = await gpsFile.readAsString();
    }
    
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

    final result = await provider.uploadVideoFile(
      videoFile,
      roadName: video['roadName'] ?? 'Unknown Road',
      roadType: video['roadType'] ?? 'Unknown',
      gpsData: gpsDataJson
    );
    
    if (!mounted) return;
    Navigator.pop(context); // close loading
    
    if (result.containsKey('error')) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Upload failed: ${result['error']}'), backgroundColor: Colors.redAccent),
      );
    } else {
      // Mark as uploaded
      video['uploaded'] = true;
      await File(video['metaFile']).writeAsString(jsonEncode(video));
      setState(() {});
      
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D1117),
      appBar: AppBar(
        title: const Text('Recorded Videos', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18, color: Colors.white)),
        backgroundColor: const Color(0xFF1A1F33),
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: SpinKitPulse(color: Color(0xFF00D4AA), size: 50.0))
          : _videos.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.video_collection_outlined, size: 60, color: Colors.white.withOpacity(0.2)),
                      const SizedBox(height: 16),
                      Text('No videos recorded yet.', style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 16)),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _videos.length,
                  itemBuilder: (context, index) {
                    final video = _videos[index];
                    final date = DateTime.parse(video['timestamp']);
                    final formattedDate = DateFormat('MMM d, yyyy • h:mm a').format(date);
                    final isUploaded = video['uploaded'] == true;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1A1F33),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.white.withOpacity(0.05)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF00D4AA).withOpacity(0.15),
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(Icons.videocam_rounded, color: Color(0xFF00D4AA), size: 28),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      video['roadName'] ?? 'Unknown Road',
                                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Colors.white),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      '${video['roadType']} • $formattedDate',
                                      style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 12),
                                    ),
                                    if (isUploaded) ...[
                                      const SizedBox(height: 8),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: Colors.green.withOpacity(0.15),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: const Text('ANALYZED', style: TextStyle(color: Colors.greenAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                                      ),
                                    ]
                                  ],
                                ),
                              ),
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    icon: const Icon(Icons.share_rounded, color: Colors.blueAccent),
                                    onPressed: () => _shareVideo(video),
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.delete_outline_rounded, color: Colors.white54),
                                    onPressed: () {
                                       showDialog(
                                         context: context,
                                         builder: (ctx) => AlertDialog(
                                           backgroundColor: const Color(0xFF141B2D),
                                           title: const Text('Delete Video?', style: TextStyle(color: Colors.white)),
                                           content: Text('This will permanently delete the local recording.', style: TextStyle(color: Colors.white.withOpacity(0.7))),
                                           actions: [
                                             TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel', style: TextStyle(color: Colors.white54))),
                                             ElevatedButton(
                                               style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                                               onPressed: () {
                                                 Navigator.pop(ctx);
                                                 _deleteVideo(video);
                                               },
                                               child: const Text('Delete', style: TextStyle(color: Colors.white)),
                                             ),
                                           ],
                                         ),
                                       );
                                    },
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          SizedBox(
                            width: double.infinity,
                            height: 44,
                            child: ElevatedButton.icon(
                              onPressed: isUploaded ? null : () => _analyzeVideo(video),
                              icon: Icon(isUploaded ? Icons.check_rounded : Icons.cloud_upload_rounded, size: 18),
                              label: Text(isUploaded ? 'Already Analyzed' : 'Analyze with AI', style: const TextStyle(fontWeight: FontWeight.bold)),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: isUploaded ? Colors.white.withOpacity(0.1) : const Color(0xFF6366F1),
                                foregroundColor: isUploaded ? Colors.white54 : Colors.white,
                                elevation: 0,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
