import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class ApiService {
  // Use for physical device via USB (requires 'adb reverse tcp:8000 tcp:8000')
  static const String baseUrl = "http://127.0.0.1:8000";
  
  // Track the logged in user
  static String? currentUsername;

  Future<Map<String, dynamic>> uploadImage(File imageFile, {
    double? latitude,
    double? longitude,
    String? roadName,
    int? surveyId,
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/detect'));
      
      request.files.add(
        await http.MultipartFile.fromPath(
          'file', 
          imageFile.path,
          contentType: MediaType('image', 'jpeg'),
        ),
      );

      if (latitude != null) request.fields['latitude'] = latitude.toString();
      if (longitude != null) request.fields['longitude'] = longitude.toString();
      if (roadName != null) request.fields['road_name'] = roadName;
      if (surveyId != null) request.fields['survey_id'] = surveyId.toString();

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to upload image: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error uploading image: $e');
    }
  }

  Future<Map<String, dynamic>> uploadVideo(File videoFile, {
    String? roadName,
    int? surveyId,
    String? gpsData,
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/detect/video'));
      
      request.files.add(
        await http.MultipartFile.fromPath(
          'file', 
          videoFile.path,
          contentType: MediaType('video', 'mp4'),
        ),
      );

      if (roadName != null) request.fields['road_name'] = roadName;
      if (surveyId != null) request.fields['survey_id'] = surveyId.toString();
      if (gpsData != null) request.fields['gps_data'] = gpsData;
      request.fields['frame_interval'] = '15';

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to upload video: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error uploading video: $e');
    }
  }

  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      // 1. Check for Hardcoded Test Credentials (Bypass Server)
      if (username == 'test123' && password == 'test') {
        currentUsername = 'test123';
        return {
          'message': 'Login successful (Offline Test Mode)',
          'username': 'test123',
          'token': 'demo-token-123'
        };
      }

      // 2. Otherwise Try Server Login with Timeout
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username,
          'password': password,
        }),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        currentUsername = username;
        return json.decode(response.body);
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to login');
      }
    } catch (e) {
      // 3. Fallback for test account if server is unreachable
      if (username == 'test123' && password == 'test') {
        currentUsername = 'test123';
        return {
          'message': 'Login successful (Offline Mode)',
          'username': 'test123',
          'token': 'demo-token-123'
        };
      }
      throw Exception('Login error: $e');
    }
  }

  Future<Map<String, dynamic>> register(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to register');
      }
    } catch (e) {
      throw Exception('Registration error: $e');
    }
  }

  Future<List<dynamic>> getDefects() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/defects?limit=50'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['defects'];
      } else {
        throw Exception('Failed to load defects');
      }
    } catch (e) {
      throw Exception('Error loading defects: $e');
    }
  }

  Future<Map<String, dynamic>> getStats() async {
    final response = await http.get(Uri.parse('$baseUrl/api/dashboard/stats'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load stats');
    }
  }

  Future<int> createSurvey(String roadName, String roadType, {String? surveyorName, double? startLat, double? startLng}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/surveys'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'road_name': roadName,
          'road_type': roadType,
          'start_latitude': startLat,
          'start_longitude': startLng,
          'surveyor_name': surveyorName ?? currentUsername ?? 'Mobile User',
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['id'];
      } else {
        throw Exception('Failed to create survey');
      }
    } catch (e) {
      throw Exception('Error creating survey: $e');
    }
  }

  Future<List<dynamic>> getSurveys() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/surveys?limit=50'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['surveys'];
      } else {
        throw Exception('Failed to load surveys');
      }
    } catch (e) {
      throw Exception('Error loading surveys: $e');
    }
  }

  Future<void> updateSurveyStatus(int surveyId, String status) async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/api/surveys/$surveyId/status?status=$status'),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to update survey status');
      }
    } catch (e) {
      throw Exception('Error updating survey status: $e');
    }
  }

  Future<Map<String, dynamic>> markRoadAsRepaired(String roadName, {int? surveyId, String? surveyorName}) async {
    try {
      final body = {
        'road_name': roadName,
        if (surveyId != null) 'survey_id': surveyId,
        if (surveyorName != null) 'surveyor_name': surveyorName,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/api/repairs'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to mark road as repaired');
      }
    } catch (e) {
      throw Exception('Error marking road as repaired: $e');
    }
  }
}
