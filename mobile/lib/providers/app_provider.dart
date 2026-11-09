import 'dart:io';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';

class AppProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  final LocationService _locationService = LocationService();

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _username;
  String? get username => _username;

  String? _role;
  String? get role => _role;

  int? _currentSurveyId;
  int? get currentSurveyId => _currentSurveyId;

  bool _isScanning = false;
  bool get isScanning => _isScanning;

  bool _isPaused = false;
  bool get isPaused => _isPaused;

  List<dynamic> _defects = [];
  List<dynamic> get defects => _defects;

  List<dynamic> _surveys = [];
  List<dynamic> get surveys => _surveys;

  Map<String, dynamic> _stats = {};
  Map<String, dynamic> get stats => _stats;

  void setScanning(bool scanning) {
    _isScanning = scanning;
    notifyListeners();
  }

  void setPaused(bool paused) {
    _isPaused = paused;
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    notifyListeners();
    try {
      final res = await _apiService.login(username, password);
      final token = res['access_token'] ?? res['token'];
      if (token != null) {
        _username = username;
        _role = res['role'] ?? 'user';
        _isLoading = false;
        notifyListeners();
        return true;
      }
    } catch (e) {
      print("Login error: $e");
    }
    _isLoading = false;
    notifyListeners();
    return false;
  }

  Future<void> refreshData() async {
    _isLoading = true;
    notifyListeners();
    try {
      _defects = await _apiService.getDefects();
      _surveys = await _apiService.getSurveys();
      _stats = await _apiService.getStats();
    } catch (e) {
      print("Refresh error: $e");
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> startSurvey(String roadName, String roadType) async {
    try {
      Position? pos = await _locationService.getCurrentLocation();
      _currentSurveyId = await _apiService.createSurvey(
        roadName, 
        roadType,
        surveyorName: _username,
        startLat: pos?.latitude,
        startLng: pos?.longitude,
      );
      _isPaused = false;
      notifyListeners();
    } catch (e) {
      print("Failed to start survey: $e");
    }
  }

  Future<void> stopSurvey({String status = 'pending'}) async {
    if (_currentSurveyId != null) {
      try {
        await _apiService.updateSurveyStatus(_currentSurveyId!, status);
      } catch (e) {
        print("Failed to update status on stop: $e");
      }
    }
    _currentSurveyId = null;
    _isPaused = false;
    notifyListeners();
  }

  Future<Map<String, dynamic>> uploadCapture(File imageFile, {String? roadName}) async {
    Position? pos = await _locationService.getCurrentLocation();
    
    final result = await _apiService.uploadImage(
      imageFile,
      latitude: pos?.latitude,
      longitude: pos?.longitude,
      roadName: roadName,
      surveyId: _currentSurveyId,
    );
    
    if (result.containsKey('defects') || result.containsKey('detections')) {
      final rawList = result['defects'] ?? result['detections'] ?? [];
      for (var d in rawList) {
        d['survey_id'] = _currentSurveyId;
      }
      _defects.addAll(rawList);
      notifyListeners();
    }
    
    return result;
  }

  Future<Map<String, dynamic>> uploadVideoFile(File videoFile, {required String roadName, required String roadType, String? gpsData}) async {
    _isLoading = true;
    notifyListeners();
    Map<String, dynamic> result = {};
    try {
      // First create a survey
      Position? pos = await _locationService.getCurrentLocation();
      int? surveyId = await _apiService.createSurvey(
        roadName, 
        roadType,
        surveyorName: _username,
        startLat: pos?.latitude,
        startLng: pos?.longitude,
      );

      // Upload video
      result = await _apiService.uploadVideo(
        videoFile,
        roadName: roadName,
        surveyId: surveyId,
        gpsData: gpsData,
      );
      
      // Update survey status to completed
      await _apiService.updateSurveyStatus(surveyId, 'completed');

    } catch (e) {
      print("Failed to upload video: $e");
      result = {'error': e.toString()};
    } finally {
      _isLoading = false;
      notifyListeners();
      await refreshData();
    }
    return result;
  }

  void logout() {
    _username = null;
    _role = null;
    _isScanning = false;
    _isPaused = false;
    _currentSurveyId = null;
    ApiService.logout();
    notifyListeners();
  }

  Future<bool> markRepaired(String roadName, {int? surveyId}) async {
    try {
      await _apiService.markRoadAsRepaired(
        roadName,
        surveyId: surveyId,
        surveyorName: _username,
      );
      return true;
    } catch (e) {
      print("Failed to mark road as repaired: $e");
      return false;
    }
  }
}
