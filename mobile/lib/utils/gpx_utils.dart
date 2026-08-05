/// GPX 1.1 XML generation utility for RoadPulse AI
/// Converts GPS track data (lat/lon/time) into standard GPX format.

String generateGpxContent(List<dynamic> gpsTrack, String roadName, {DateTime? startTime}) {
  final effectiveStartTime = startTime ?? DateTime.now();
  final buffer = StringBuffer();

  buffer.writeln('<?xml version="1.0" encoding="UTF-8"?>');
  buffer.writeln('<gpx version="1.1" creator="RoadPulse AI"');
  buffer.writeln('  xmlns="http://www.topografix.com/GPX/1/1"');
  buffer.writeln('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"');
  buffer.writeln('  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">');
  buffer.writeln('  <metadata>');
  buffer.writeln('    <name>Road Survey - ${escapeXml(roadName)}</name>');
  buffer.writeln('    <time>${effectiveStartTime.toUtc().toIso8601String()}</time>');
  buffer.writeln('  </metadata>');
  buffer.writeln('  <trk>');
  buffer.writeln('    <name>${escapeXml(roadName)}</name>');
  buffer.writeln('    <trkseg>');

  for (final point in gpsTrack) {
    if (point is Map) {
      final timeSec = (point['time'] as num?)?.toDouble() ?? 0.0;
      final lat = point['latitude'];
      final lon = point['longitude'];
      final pointTime = effectiveStartTime.add(
        Duration(milliseconds: (timeSec * 1000).round()),
      );

      buffer.writeln('      <trkpt lat="$lat" lon="$lon">');
      buffer.writeln('        <time>${pointTime.toUtc().toIso8601String()}</time>');
      buffer.writeln('      </trkpt>');
    }
  }

  buffer.writeln('    </trkseg>');
  buffer.writeln('  </trk>');
  buffer.writeln('</gpx>');

  return buffer.toString();
}

String escapeXml(String input) {
  return input
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&apos;');
}
