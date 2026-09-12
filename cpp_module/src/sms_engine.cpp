// ============================================================
// sms_engine.cpp — compute engine for the Student Management System
//
// One binary, three modes (chosen by argv[1]); all input arrives as
// tab-separated text on stdin and all results are printed as
// tab-separated text on stdout (wire format in cpp_module/README.md):
//
//   grades      final % = 50% assignment avg + 50% exam avg, Pass >= 40
//   attendance  per-course %, eligible at >= 75%
//   rank        students ranked within a section by final %
//
// Python (backend/cpp_engine.py) collects raw data from MySQL and owns
// persistence; this module is pure computation on in-memory data.
//
// Build: python scripts/build_cpp.py   (g++ -std=c++14 -Wall -Wextra)
// ============================================================

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

const double PASS_MARK_PCT = 40.0;   // confirmed grading scheme
const double ATTENDANCE_MIN_PCT = 75.0;  // confirmed eligibility rule

// One student's mark aggregates (already normalized by SQL: each *_sum
// is the sum of per-assessment percentages, so 0..100 * count).
struct GradeRecord {
    int student_id = 0;
    std::string name;
    std::string roll;
    double assign_sum = 0.0;
    int assign_n = 0;
    double exam_sum = 0.0;
    int exam_n = 0;

    // Percentage averages; a missing component counts as 0 (the
    // confirmed rule), which falls out of n == 0 here.
    double assign_pct() const { return assign_n > 0 ? assign_sum / assign_n : 0.0; }
    double exam_pct() const { return exam_n > 0 ? exam_sum / exam_n : 0.0; }
    // Final score: equal 50/50 weighting of the two components.
    double final_pct() const { return 0.5 * assign_pct() + 0.5 * exam_pct(); }
};

struct AttendanceRecord {
    int student_id = 0;
    std::string name;
    std::string roll;
    int present = 0;
};

std::string trim(const std::string& s) {
    const char* ws = " \t\r\n";
    std::size_t begin = s.find_first_not_of(ws);
    if (begin == std::string::npos) return "";
    std::size_t end = s.find_last_not_of(ws);
    return s.substr(begin, end - begin + 1);
}

bool to_int(const std::string& s, int& out) {
    try {
        std::size_t used = 0;
        out = std::stoi(s, &used);
        return used == s.size();
    } catch (...) {
        return false;
    }
}

bool to_double(const std::string& s, double& out) {
    try {
        std::size_t used = 0;
        out = std::stod(s, &used);
        return used == s.size();
    } catch (...) {
        return false;
    }
}

std::vector<std::string> split_tabs(const std::string& line) {
    std::vector<std::string> parts;
    std::string item;
    std::istringstream stream(line);
    while (std::getline(stream, item, '\t')) parts.push_back(item);
    // A trailing tab yields no extra empty token; that is fine because
    // every field we parse is required and validated anyway.
    return parts;
}

std::vector<GradeRecord> read_grade_records(std::istream& in) {
    std::vector<GradeRecord> records;
    std::string line;
    while (std::getline(in, line)) {
        if (trim(line).empty()) continue;
        auto parts = split_tabs(line);
        // Expected: id, name, roll, assign_sum, assign_n, exam_sum, exam_n
        if (parts.size() < 7) continue;
        GradeRecord r;
        if (!to_int(trim(parts[0]), r.student_id)) continue;
        r.name = trim(parts[1]);
        r.roll = trim(parts[2]);
        if (!to_double(trim(parts[3]), r.assign_sum)) continue;
        if (!to_int(trim(parts[4]), r.assign_n)) continue;
        if (!to_double(trim(parts[5]), r.exam_sum)) continue;
        if (!to_int(trim(parts[6]), r.exam_n)) continue;
        records.push_back(r);
    }
    return records;
}

// Fixed two-decimal formatting keeps stdout parseable and stable.
std::string pct(double value) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(2) << value;
    return out.str();
}

// ---------- mode: grades ----------
// O(n) over the n students after parsing: each record is handled once.
int run_grades(std::istream& in) {
    for (const GradeRecord& r : read_grade_records(in)) {
        const double final_pct = r.final_pct();
        std::cout << r.student_id << '\t'
                  << pct(r.assign_pct()) << '\t'
                  << pct(r.exam_pct()) << '\t'
                  << pct(final_pct) << '\t'
                  << (final_pct >= PASS_MARK_PCT ? "PASS" : "FAIL") << '\n';
    }
    return 0;
}

// ---------- mode: attendance ----------
// O(n) over the n students; the eligibility test is one comparison.
int run_attendance(std::istream& in) {
    std::string first;
    if (!std::getline(in, first)) return 0;
    int sessions = 0;
    if (!to_int(trim(first), sessions) || sessions < 0) {
        std::cerr << "attendance: first line must be the session count\n";
        return 1;
    }

    std::string line;
    while (std::getline(in, line)) {
        if (trim(line).empty()) continue;
        auto parts = split_tabs(line);
        // Expected: id, name, roll, present
        if (parts.size() < 4) continue;
        AttendanceRecord r;
        if (!to_int(trim(parts[0]), r.student_id)) continue;
        r.name = trim(parts[1]);
        r.roll = trim(parts[2]);
        if (!to_int(trim(parts[3]), r.present)) continue;

        // No recorded sessions -> 0% (nothing to be eligible for yet).
        const double percentage = sessions > 0 ? (r.present * 100.0) / sessions : 0.0;
        const bool eligible = percentage >= ATTENDANCE_MIN_PCT;
        std::cout << r.student_id << '\t'
                  << r.present << '\t'
                  << sessions << '\t'
                  << pct(percentage) << '\t'
                  << (eligible ? "ELIGIBLE" : "NOT_ELIGIBLE") << '\n';
    }
    return 0;
}

// ---------- mode: rank ----------
// Ranking = one sort plus one pass.
//   * std::sort / std::stable_sort: O(n log n) comparisons.
//   * Ordering: final % descending; ties broken by roll number
//     ascending (numeric-aware when both rolls are numeric), so the
//     output is fully deterministic.
//   * Equal final % share the same rank (competition ranking:
//     1, 2, 2, 4), so the tie-break only fixes display order.
bool roll_less(const std::string& a, const std::string& b) {
    int na = 0, nb = 0;
    if (to_int(a, na) && to_int(b, nb)) return na < nb;
    return a < b;
}

int run_rank(std::istream& in) {
    std::vector<GradeRecord> records = read_grade_records(in);
    std::stable_sort(records.begin(), records.end(),
                     [](const GradeRecord& a, const GradeRecord& b) {
                         const double fa = a.final_pct();
                         const double fb = b.final_pct();
                         if (fa != fb) return fa > fb;   // higher % first
                         return roll_less(a.roll, b.roll);  // deterministic tie order
                     });

    // Competition ranking: the first row is rank 1; a row whose score
    // equals the previous row keeps that rank (1, 2, 2, 4 ...); any new
    // score takes its 1-based position as the rank.
    int current_rank = 1;
    for (std::size_t i = 0; i < records.size(); ++i) {
        if (i == 0 || records[i].final_pct() != records[i - 1].final_pct()) {
            current_rank = static_cast<int>(i) + 1;
        }
        std::cout << current_rank << '\t'
                  << records[i].student_id << '\t'
                  << pct(records[i].final_pct()) << '\n';
    }
    return 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    std::ios::sync_with_stdio(false);
    if (argc != 2) {
        std::cerr << "usage: sms_engine <grades|attendance|rank>\n";
        return 2;
    }
    const std::string mode = argv[1];
    if (mode == "grades") return run_grades(std::cin);
    if (mode == "attendance") return run_attendance(std::cin);
    if (mode == "rank") return run_rank(std::cin);
    std::cerr << "unknown mode: " << mode << "\n";
    return 2;
}
