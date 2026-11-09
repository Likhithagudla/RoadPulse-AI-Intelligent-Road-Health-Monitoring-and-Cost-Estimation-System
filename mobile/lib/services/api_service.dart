import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class ApiService {
  // Configurable base URL: can be passed via --dart-define=ROAD_PULSE_API_URL=...
  // or dynamically updated with setBaseUrl(...)
  static String baseUrl = const String.fromEnvironment(
    'ROAD_PULSE_API_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static void setBaseUrl(String newUrl) {
    if (newUrl.trim().isNotEmpty) {
      String url = newUrl.trim();
      baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    }
  }

  // Session state and JWT Bearer token
  static String? currentUsername;
  static String? currentUserRole;
  static String? authToken;
  static Function()? onSessionExpired;

  static void clearSession() {
    authToken = null;
    currentUsername = null;
    currentUserRole = null;
  }

  Map<String, String> _authHeaders({Map<String, String>? additionalHeaders}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (authToken != null) {
      headers['Authorization'] = 'Bearer $authToken';
    }
    if (additionalHeaders != null) {
      headers.addAll(additionalHeaders);
    }
    return headers;
  }

  Future<Map<String, dynamic>> uploadImage(File imageFile, {
    double? latitude,
    double? longitude,
    String? roadName,
    int? surveyId,
    String region = "Default",
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/detect'));
      
      if (authToken != null) {
        request.headers['Authorization'] = 'Bearer $authToken';
      }

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
      request.fields['region'] = region;
      request.fields['save_results'] = 'true';

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200 || response.statusCode == 201) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to upload image: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      throw Exception('Error uploading image: $e');
    }
  }

  Future<Map<String, dynamic>> uploadVideo(File videoFile, {
    String? roadName,
    int? surveyId,
    String? gpsData,
    String region = "Default",
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/detect/video'));
      
      if (authToken != null) {
        request.headers['Authorization'] = 'Bearer $authToken';
      }

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
      request.fields['region'] = region;
      request.fields['frame_interval'] = '15';

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200 || response.statusCode == 201) {
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
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username.trim(),
          'password': password,
        }),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        authToken = data['access_token'] ?? data['token'];
        currentUserRole = data['role'] ?? 'user';
        currentUsername = username.trim();
        return data;
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? error['error']?['message'] ?? 'Failed to login');
      }
    } catch (e) {
      throw Exception('Login error: $e');
    }
  }

  Future<Map<String, dynamic>> register(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username.trim(),
          'password': password,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return json.decode(response.body);
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? error['error']?['message'] ?? 'Failed to register');
      }
    } catch (e) {
      throw Exception('Registration error: $e');
    }
  }

  Future<List<dynamic>> getDefects({int limit = 50, int offset = 0}) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/defects?limit=$limit&offset=$offset'),
        headers: _authHeaders(),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['defects'] ?? [];
      } else {
        throw Exception('Failed to load defects (${response.statusCode})');
      }
    } catch (e) {
      throw Exception('Error loading defects: $e');
    }
  }

  Future<Map<String, dynamic>> getStats() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/dashboard/stats'),
        headers: _authHeaders(),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to load stats (${response.statusCode})');
      }
    } catch (e) {
      throw Exception('Error loading stats: $e');
    }
  }

  Future<int> createSurvey(String roadName, String roadType, {String? surveyorName, double? startLat, double? startLng}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/surveys'),
        headers: _authHeaders(),
        body: json.encode({
          'road_name': roadName.trim(),
          'road_type': roadType,
          'start_latitude': startLat,
          'start_longitude': startLng,
          'surveyor_name': surveyorName ?? currentUsername ?? 'Mobile Surveyor',
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = json.decode(response.body);
        return data['id'];
      } else {
        final err = json.decode(response.body);
        throw Exception('Failed to create survey: ${err['detail'] ?? response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error creating survey: $e');
    }
  }

  Future<List<dynamic>> getSurveys({int limit = 50, int offset = 0}) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/surveys?limit=$limit&offset=$offset'),
        headers: _authHeaders(),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['surveys'] ?? [];
      } else {
        throw Exception('Failed to load surveys (${response.statusCode})');
      }
    } catch (e) {
      throw Exception('Error loading surveys: $e');
    }
  }

  Future<void> updateSurveyStatus(int surveyId, String status) async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/api/surveys/$surveyId/status'),
        headers: _authHeaders(),
        body: json.encode({'status': status}),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to update survey status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error updating survey status: $e');
    }
  }

  Future<Map<String, dynamic>> markRoadAsRepaired(String roadName, {int? surveyId, String? surveyorName}) async {
    try {
      final body = <String, dynamic>{
        'road_name': roadName.trim(),
        'surveyor_name': surveyorName ?? currentUsername ?? 'Mobile Worker',
      };
      if (surveyId != null) {
        body['survey_id'] = surveyId;
      }

      final response = await http.post(
        Uri.parse('$baseUrl/api/repairs'),
        headers: _authHeaders(),
        body: jsonEncode(body),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to mark road as repaired: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error marking road as repaired: $e');
    }
  }

  static void logout() {
    authToken = null;
    currentUsername = null;
    currentUserRole = null;
  }
}
