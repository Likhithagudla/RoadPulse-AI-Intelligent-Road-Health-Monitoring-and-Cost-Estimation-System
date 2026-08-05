import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/app_provider.dart';
import 'login_screen.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';

class HistoryScreen extends StatefulWidget {
  final VoidCallback? onBack;
  const HistoryScreen({super.key, this.onBack});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppProvider>().refreshData();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0E1A),
      body: SafeArea(
        child: Column(
          children: [
            // Custom top bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              child: Row(
                children: [
                  // Back arrow
                  GestureDetector(
                    onTap: widget.onBack,
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white.withOpacity(0.08)),
                      ),
                      child: Icon(Icons.arrow_back_ios_new_rounded,
                          color: Colors.white.withOpacity(0.6), size: 18),
                    ),
                  ),
                  const SizedBox(width: 12),
                  ShaderMask(
                    shaderCallback: (bounds) => const LinearGradient(
                      colors: [Color(0xFF00D4AA), Color(0xFF0EA5E9)],
                    ).createShader(bounds),
                    child: const Icon(Icons.history_rounded,
                        size: 28, color: Colors.white),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Inspection History',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  // Refresh
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: IconButton(
                      icon: Icon(Icons.refresh_rounded,
                          color: Colors.white.withOpacity(0.6), size: 22),
                      onPressed: () =>
                          context.read<AppProvider>().refreshData(),
                      padding: const EdgeInsets.all(8),
                      constraints: const BoxConstraints(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  // Logout
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.redAccent.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: IconButton(
                      icon: Icon(Icons.logout_rounded,
                          color: Colors.redAccent.withOpacity(0.7), size: 22),
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
            // Search bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF141B2D),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.white.withOpacity(0.06)),
                ),
                child: TextField(
                  controller: _searchController,
                  onChanged: (value) => setState(() => _searchQuery = value),
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Search roads...',
                    hintStyle: TextStyle(
                      color: Colors.white.withOpacity(0.25),
                      fontSize: 14,
                    ),
                    prefixIcon: Icon(Icons.search_rounded,
                        color: Colors.white.withOpacity(0.3), size: 20),
                    suffixIcon: _searchQuery.isNotEmpty
                        ? IconButton(
                            icon: Icon(Icons.close_rounded,
                                color: Colors.white.withOpacity(0.3), size: 18),
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _searchQuery = '');
                            },
                          )
                        : null,
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                  ),
                ),
              ),
            ),
            // Survey list
            Expanded(
              child: Consumer<AppProvider>(
                builder: (context, provider, child) {
                  if (provider.isLoading && provider.surveys.isEmpty) {
                    return const Center(
                      child: CircularProgressIndicator(
                        color: Color(0xFF00D4AA),
                      ),
                    );
                  }

                  if (provider.surveys.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(24),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.03),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(Icons.history_rounded,
                                size: 64,
                                color: Colors.white.withOpacity(0.08)),
                          ),
                          const SizedBox(height: 20),
                          Text(
                            'No inspections yet',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                              color: Colors.white.withOpacity(0.4),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Start scanning to see survey history',
                            style: TextStyle(
                              fontSize: 13,
                              color: Colors.white.withOpacity(0.2),
                            ),
                          ),
                        ],
                      ),
                    );
                  }

                  // Filter surveys by search query
                  final filteredSurveys = _searchQuery.isEmpty
                      ? provider.surveys
                      : provider.surveys.where((s) {
                          final name = (s['road_name'] ?? '').toString().toLowerCase();
                          final type = (s['road_type'] ?? '').toString().toLowerCase();
                          final state = (s['state'] ?? '').toString().toLowerCase();
                          final q = _searchQuery.toLowerCase();
                          return name.contains(q) || type.contains(q) || state.contains(q);
                        }).toList();

                  if (filteredSurveys.isEmpty) {
                    return Center(
                      child: Text(
                        'No roads matching "$_searchQuery"',
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.white.withOpacity(0.3),
                        ),
                      ),
                    );
                  }

                  return RefreshIndicator(
                    onRefresh: () => provider.refreshData(),
                    color: const Color(0xFF00D4AA),
                    child: AnimationLimiter(
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
                        itemCount: filteredSurveys.length,
                        itemBuilder: (context, index) {
                          final survey = filteredSurveys[index];
                          return AnimationConfiguration.staggeredList(
                            position: index,
                            duration: const Duration(milliseconds: 375),
                            child: SlideAnimation(
                              verticalOffset: 50.0,
                              child: FadeInAnimation(
                                child: _buildSurveyCard(survey),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSurveyCard(dynamic survey) {
    final DateTime? date = survey['survey_date'] != null
        ? DateTime.tryParse(survey['survey_date'])
        : null;
    final String formattedDate = date != null
        ? DateFormat('dd MMM yyyy, hh:mm a').format(date)
        : 'Unknown Date';
    final int defectCount = survey['total_defects'] ?? 0;
    final String status =
        (survey['status'] ?? 'pending').toString().toLowerCase();

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF141B2D),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.04)),
      ),
      child: InkWell(
        onTap: () {},
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          survey['road_name'] ?? 'Unnamed Road',
                          style: const TextStyle(
                              fontSize: 17, fontWeight: FontWeight.w800),
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${survey['road_type'] ?? 'N/A'} • ${survey['state'] ?? 'N/A'}',
                          style: TextStyle(
                              fontSize: 12,
                              color: Colors.white.withOpacity(0.35),
                              fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                  ),
                  _buildStatusBadge(status),
                ],
              ),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.25),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.white.withOpacity(0.03)),
                ),
                child: Row(
                  children: [
                    _buildMetaItem(Icons.warning_amber_rounded,
                        '$defectCount', 'Defects', Colors.orangeAccent),
                    Container(
                      width: 1,
                      height: 30,
                      color: Colors.white.withOpacity(0.05),
                    ),
                    _buildMetaItem(Icons.calendar_today_rounded,
                        formattedDate.split(',')[0], 'Date',
                        const Color(0xFF00D4AA)),
                  ],
                ),
              ),
              // Repair status badge
              if (survey['repair_status'] != null) ...[
                const SizedBox(height: 12),
                _buildRepairStatusBadge(
                  survey['repair_status'],
                  survey['repair_admin_notes'],
                ),
              ],
              // Mark as Repaired button - only for completed surveys with no pending/approved repair
              if (status == 'completed' &&
                  survey['repair_status'] != 'pending' &&
                  survey['repair_status'] != 'approved') ...[
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _showMarkRepairedDialog(survey),
                    icon: const Icon(Icons.build_circle_rounded, size: 18),
                    label: const Text('Mark as Repaired',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00D4AA).withOpacity(0.15),
                      foregroundColor: const Color(0xFF00D4AA),
                      side: BorderSide(color: const Color(0xFF00D4AA).withOpacity(0.3)),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      elevation: 0,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  void _showMarkRepairedDialog(dynamic survey) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A1F35),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Row(
          children: [
            ShaderMask(
              shaderCallback: (bounds) => const LinearGradient(
                colors: [Color(0xFF00D4AA), Color(0xFF0EA5E9)],
              ).createShader(bounds),
              child: const Icon(Icons.build_circle_rounded,
                  size: 28, color: Colors.white),
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Text('Mark as Repaired',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            ),
          ],
        ),
        content: Text(
          'Are you sure this road "${survey['road_name']}" has been repaired and all defects are fixed?\n\nThis will be sent to the admin for review.',
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: 14,
            height: 1.5,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Cancel',
                style: TextStyle(color: Colors.white.withOpacity(0.5))),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final provider = context.read<AppProvider>();
              final success = await provider.markRepaired(
                survey['road_name'] ?? '',
                surveyId: survey['id'],
              );
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      success
                          ? 'Repair submitted! Pending admin approval.'
                          : 'Failed to submit repair. Check connection.',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    backgroundColor:
                        success ? const Color(0xFF00D4AA) : Colors.redAccent,
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                    margin: const EdgeInsets.all(16),
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00D4AA),
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            ),
            child: const Text('Confirm',
                style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  Widget _buildRepairStatusBadge(String status, String? adminNotes) {
    Color bgColor;
    Color textColor;
    IconData icon;
    String message;

    switch (status) {
      case 'approved':
        bgColor = const Color(0xFF00D4AA).withOpacity(0.12);
        textColor = const Color(0xFF00D4AA);
        icon = Icons.check_circle_rounded;
        message = 'Repair verified by admin ✓';
        break;
      case 'rejected':
        bgColor = Colors.redAccent.withOpacity(0.12);
        textColor = Colors.redAccent;
        icon = Icons.cancel_rounded;
        message = adminNotes != null && adminNotes.isNotEmpty
            ? 'Rejected: $adminNotes'
            : 'Repair rejected by admin';
        break;
      default: // pending
        bgColor = Colors.amber.withOpacity(0.12);
        textColor = Colors.amber;
        icon = Icons.hourglass_top_rounded;
        message = 'Repair submitted, awaiting admin review';
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: textColor.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Icon(icon, color: textColor, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: textColor,
                fontSize: 12,
                fontWeight: FontWeight.w600,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetaItem(
      IconData icon, String value, String label, Color color) {
    return Expanded(
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 16, color: color.withOpacity(0.7)),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(value,
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 13)),
              Text(label,
                  style: TextStyle(
                      fontSize: 10,
                      color: Colors.white.withOpacity(0.25))),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color color;
    IconData icon;
    switch (status) {
      case 'completed':
        color = const Color(0xFF00D4AA);
        icon = Icons.check_circle_outline_rounded;
        break;
      case 'processing':
        color = Colors.amberAccent;
        icon = Icons.pending_outlined;
        break;
      case 'failed':
        color = Colors.redAccent;
        icon = Icons.error_outline_rounded;
        break;
      default:
        color = const Color(0xFF818CF8);
        icon = Icons.schedule_rounded;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            status.toUpperCase(),
            style: TextStyle(
                color: color,
                fontSize: 10,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5),
          ),
        ],
      ),
    );
  }
}
