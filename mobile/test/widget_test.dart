import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:road_ai_mobile/main.dart';
import 'package:road_ai_mobile/providers/app_provider.dart';

void main() {
  testWidgets('RoadAIMobileApp smoke test renders splash and title', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AppProvider()),
        ],
        child: const RoadAIMobileApp(),
      ),
    );

    // Initial frame renders SplashScreen
    await tester.pump();

    // Verify ROADPULSE title appears on the splash screen
    expect(find.text('ROADPULSE'), findsOneWidget);
    expect(find.text('A I'), findsOneWidget);

    // Advance timer so SplashScreen 3s navigation timer completes cleanly
    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();
  });
}
