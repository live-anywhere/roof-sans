import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

/// Mixed-script text drawn at every weight.
const sample = '한글 ㅅㄴ 강남 Latin 0123 日本語「東京」へ、カタカナ 漢字 大韓民國 ①⑩ ½⅓ cảm ơn';

/// Text laid out for the line metrics comparison.
const metricsSample = '한글 Aa 日本';
const metricsFamilies = ['RoofSans', 'PretendardJP'];
const metricsSizes = <double>[12, 16, 24];

/// Largest difference, in logical pixels, still reported as `MATCH`.
const metricsTolerance = 0.01;

const weights = [
  FontWeight.w300,
  FontWeight.w400,
  FontWeight.w500,
  FontWeight.w600,
  FontWeight.w700,
  FontWeight.w800,
  FontWeight.w900,
];

const _locales = {'ko': Locale('ko', 'KR'), 'ja': Locale('ja', 'JP')};

/// Lays out [metricsSample] in [family] at [fontSize] with no `height`
/// override and returns the first line's metrics.
LineMetrics measureLine(String family, double fontSize) {
  final painter = TextPainter(
    text: TextSpan(
      text: metricsSample,
      style: TextStyle(fontFamily: family, fontSize: fontSize),
    ),
    textDirection: TextDirection.ltr,
  )..layout();
  final metrics = painter.computeLineMetrics().first;
  painter.dispose();
  return metrics;
}

/// Whether [a] and [b] have the same height, ascent, and descent within
/// [metricsTolerance].
bool sameLineMetrics(LineMetrics a, LineMetrics b) =>
    (a.height - b.height).abs() <= metricsTolerance &&
    (a.ascent - b.ascent).abs() <= metricsTolerance &&
    (a.descent - b.descent).abs() <= metricsTolerance;

void main() => runApp(const SpecimenApp());

class SpecimenApp extends StatefulWidget {
  const SpecimenApp({super.key});

  @override
  State<SpecimenApp> createState() => _SpecimenAppState();
}

class _SpecimenAppState extends State<SpecimenApp> {
  String _language = 'ko';

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Roof Sans specimen',
      locale: _locales[_language],
      supportedLocales: _locales.values,
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: SpecimenScreen(
        language: _language,
        onLanguageChanged: (language) => setState(() => _language = language),
      ),
    );
  }
}

class SpecimenScreen extends StatelessWidget {
  const SpecimenScreen({
    super.key,
    required this.language,
    required this.onLanguageChanged,
  });

  final String language;
  final ValueChanged<String> onLanguageChanged;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _header(context),
              const SizedBox(height: 16),
              for (final weight in weights) _WeightSample(weight: weight),
              const SizedBox(height: 16),
              const _MetricsTable(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _header(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('boldText: ${MediaQuery.boldTextOf(context)}'),
        Text('locale: ${Localizations.localeOf(context)}'),
        if (MediaQuery.boldTextOf(context))
          const Text(
            'boldText merges w700 into every style: only the fontWeight lines '
            'show what the app draws.',
          ),
        const SizedBox(height: 8),
        SegmentedButton<String>(
          segments: [
            for (final code in _locales.keys)
              ButtonSegment(value: code, label: Text(code)),
          ],
          selected: {language},
          onSelectionChanged: (selection) => onLanguageChanged(selection.first),
        ),
      ],
    );
  }
}

/// One weight drawn twice: through `fontWeight`, then through the `wght`
/// axis alone, so the two lines can be compared.
///
/// With the system bold-text setting on, `Text` merges `FontWeight.bold` into
/// every style, so each line's label also shows the weight Flutter requests.
class _WeightSample extends StatelessWidget {
  const _WeightSample({required this.weight});

  final FontWeight weight;

  @override
  Widget build(BuildContext context) {
    final boldText = MediaQuery.boldTextOf(context);
    final label = Theme.of(context).textTheme.labelSmall;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('w${weight.value}', style: label),
          Text(fontWeightLabel(weight, boldText: boldText), style: label),
          Text(
            sample,
            style: TextStyle(
              fontFamily: 'RoofSans',
              fontWeight: weight,
              fontSize: 18,
            ),
          ),
          Text(wghtLabel(weight, boldText: boldText), style: label),
          Text(
            sample,
            style: TextStyle(
              fontFamily: 'RoofSans',
              fontVariations: [FontVariation('wght', weight.value.toDouble())],
              fontSize: 18,
            ),
          ),
        ],
      ),
    );
  }
}

/// Label for the `fontWeight` line; under bold text it names the weight
/// actually requested.
String fontWeightLabel(FontWeight weight, {required bool boldText}) => boldText
    ? 'fontWeight w${weight.value} → w${FontWeight.bold.value} (boldText)'
    : 'fontWeight w${weight.value}';

/// Label for the `wght` axis line; under bold text the style weight becomes
/// w700 while the axis stays at the set value, which can trigger fake bold.
String wghtLabel(FontWeight weight, {required bool boldText}) => boldText
    ? 'wght ${weight.value} (style weight w${FontWeight.bold.value}, boldText)'
    : 'wght ${weight.value}';

class _MetricsTable extends StatelessWidget {
  const _MetricsTable();

  @override
  Widget build(BuildContext context) {
    const columns = ['size', 'family', 'height', 'ascent', 'descent', ''];
    return Table(
      defaultColumnWidth: const IntrinsicColumnWidth(),
      children: [
        TableRow(children: [for (final title in columns) _cell(title)]),
        for (final size in metricsSizes) ..._rowsFor(size),
      ],
    );
  }

  List<TableRow> _rowsFor(double size) {
    final metrics = {
      for (final family in metricsFamilies) family: measureLine(family, size),
    };
    final result =
        sameLineMetrics(metrics['RoofSans']!, metrics['PretendardJP']!)
        ? 'MATCH'
        : 'DIFF';
    return [
      for (final family in metricsFamilies)
        TableRow(
          children: [
            _cell(family == metricsFamilies.first ? '${size.toInt()}' : ''),
            _cell(family),
            _cell(metrics[family]!.height.toStringAsFixed(3)),
            _cell(metrics[family]!.ascent.toStringAsFixed(3)),
            _cell(metrics[family]!.descent.toStringAsFixed(3)),
            _cell(family == metricsFamilies.first ? result : ''),
          ],
        ),
    ];
  }

  Widget _cell(String text) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
    child: Text(text),
  );
}
