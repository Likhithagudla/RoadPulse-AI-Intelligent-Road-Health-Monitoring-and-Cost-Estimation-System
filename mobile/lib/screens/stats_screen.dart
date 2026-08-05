import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/app_provider.dart';

class StatsScreen extends StatelessWidget {
  const StatsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Overall Statistics'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<AppProvider>().refreshData(),
          ),
        ],
      ),
      body: Consumer<AppProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          final stats = provider.stats;
          if (stats.isEmpty) {
            return const Center(child: Text('No statistical data available'));
          }

          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              _buildStatsGrid(stats),
              const SizedBox(height: 24),
              _buildDefectDistribution(stats['defects_by_type'] ?? {}),
              const SizedBox(height: 24),
              _buildSeverityAnalysis(stats['severity_overview'] ?? {}),
              const SizedBox(height: 100), // Space for bottom nav
            ],
          );
        },
      ),
    );
  }

  Widget _buildStatsGrid(Map<String, dynamic> stats) {
    final overview = stats['overview'] ?? {};
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 16,
      mainAxisSpacing: 16,
      childAspectRatio: 1.5,
      children: [
        _buildStatCard('Defects', overview['total_defects']?.toString() ?? '0', Icons.warning_amber_rounded, Colors.redAccent),
        _buildStatCard('Surveys', overview['total_surveys']?.toString() ?? '0', Icons.poll_rounded, Colors.blueAccent),
        _buildStatCard('Roads', overview['total_roads']?.toString() ?? '0', Icons.add_road_rounded, Colors.greenAccent),
        _buildStatCard('Est. Cost', '₹' + (overview['total_repair_cost'] ?? 0).toString(), Icons.payments_rounded, Colors.amberAccent),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: -0.5)),
            Text(label, style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.5))),
          ],
        ),
      ),
    );
  }

  Widget _buildDefectDistribution(Map<String, dynamic> typeData) {
    final List<PieChartSectionData> sections = [];
    final List<Color> colors = [Colors.indigoAccent, Colors.purpleAccent, Colors.cyanAccent, Colors.tealAccent];
    int index = 0;

    typeData.forEach((key, value) {
      if (value > 0) {
        sections.add(PieChartSectionData(
          color: colors[index % colors.length],
          value: value.toDouble(),
          title: '',
          radius: 40,
        ));
        index++;
      }
    });

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Text('Defect Distribution', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 24),
            SizedBox(
              height: 150,
              child: sections.isEmpty 
                ? const Center(child: Text('No data')) 
                : PieChart(PieChartData(sections: sections, centerSpaceRadius: 40)),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: typeData.keys.map((k) {
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(width: 8, height: 8, decoration: const BoxDecoration(color: Colors.indigoAccent, shape: BoxShape.circle)),
                    const SizedBox(width: 4),
                    Text(k, style: const TextStyle(fontSize: 10)),
                  ],
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSeverityAnalysis(Map<String, dynamic> severity) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Text('Severity Analysis', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 16),
            _buildSeverityRow('High', severity['High'] ?? 0, Colors.redAccent),
            const SizedBox(height: 12),
            _buildSeverityRow('Medium', severity['Medium'] ?? 0, Colors.amberAccent),
            const SizedBox(height: 12),
            _buildSeverityRow('Low', severity['Low'] ?? 0, Colors.greenAccent),
          ],
        ),
      ),
    );
  }

  Widget _buildSeverityRow(String label, int count, Color color) {
    return Row(
      children: [
        SizedBox(width: 60, child: Text(label, style: const TextStyle(fontSize: 12))),
        Expanded(
          child: LinearProgressIndicator(
            value: 0.5, // Placeholder for actual ratio
            backgroundColor: color.withOpacity(0.1),
            valueColor: AlwaysStoppedAnimation<Color>(color),
            borderRadius: BorderRadius.circular(10),
            minHeight: 8,
          ),
        ),
        const SizedBox(width: 12),
        SizedBox(width: 30, child: Text(count.toString(), style: const TextStyle(fontWeight: FontWeight.bold))),
      ],
    );
  }
}
