import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_specimen/main.dart';

/// Registers [family] from files staged in `assets/fonts/` by
/// `tool/stage_fonts.sh`.
Future<void> loadFamily(String family, List<String> files) async {
  final loader = FontLoader(family);
  for (final file in files) {
    loader.addFont(
      File('assets/fonts/$file').readAsBytes().then(ByteData.sublistView),
    );
  }
  await loader.load();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await loadFamily('RoofSans', ['RoofSansVariable.ttf']);
    await loadFamily('PretendardJP', [
      'PretendardJP-Regular.ttf',
      'PretendardJP-Bold.ttf',
    ]);
  });

  for (final size in metricsSizes) {
    test('RoofSans line metrics equal PretendardJP at $size', () {
      final roof = measureLine('RoofSans', size);
      final pretendard = measureLine('PretendardJP', size);

      // An unregistered family falls back to the test font, so equal
      // metrics there would mean a family did not load.
      final fallback = measureLine('UnregisteredFamily', size);
      expect(
        roof.height,
        isNot(closeTo(fallback.height, metricsTolerance)),
        reason: 'RoofSans resolved to the fallback font',
      );
      expect(
        pretendard.height,
        isNot(closeTo(fallback.height, metricsTolerance)),
        reason: 'PretendardJP resolved to the fallback font',
      );

      expect(roof.height, closeTo(pretendard.height, metricsTolerance));
      expect(roof.ascent, closeTo(pretendard.ascent, metricsTolerance));
      expect(roof.descent, closeTo(pretendard.descent, metricsTolerance));
      expect(sameLineMetrics(roof, pretendard), isTrue);
    });
  }

  testWidgets('metrics table shows MATCH for every size', (tester) async {
    await tester.pumpWidget(const SpecimenApp());

    expect(find.text('MATCH'), findsNWidgets(metricsSizes.length));
    expect(find.text('DIFF'), findsNothing);
  });

  testWidgets('weight labels name the requested weight', (tester) async {
    await tester.pumpWidget(const SpecimenApp());

    expect(find.text('fontWeight w300'), findsOneWidget);
    expect(find.text('wght 300'), findsOneWidget);
  });

  testWidgets('weight labels show the boldText override', (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(boldText: true);
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);

    await tester.pumpWidget(const SpecimenApp());

    expect(find.text('boldText: true'), findsOneWidget);
    expect(find.text('fontWeight w300 → w700 (boldText)'), findsOneWidget);
    expect(find.text('wght 300 (style weight w700, boldText)'), findsOneWidget);
  });
}
