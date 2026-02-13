#ifndef WVAB_NAVIGATION_PLANNER_H
#define WVAB_NAVIGATION_PLANNER_H

#include <string>
#include <unordered_map>
#include <vector>

namespace wvab {

enum class Severity {
  kSafe = 0,
  kWarning = 1,
  kDanger = 2
};

struct Detection {
  std::string class_name;
  float confidence = 0.0f;      // 0..1
  float x_center_norm = 0.5f;   // 0..1 (left to right)
  float area_norm = 0.0f;       // 0..1 (bbox area / frame area)
};

struct LaneRisk {
  float left = 0.0f;
  float center = 0.0f;
  float right = 0.0f;
};

struct NavigationDecision {
  std::string instruction = "GO STRAIGHT";
  Severity severity = Severity::kSafe;
  LaneRisk risk;
};

class NavigationPlanner {
 public:
  NavigationPlanner();

  NavigationDecision Decide(const std::vector<Detection>& detections) const;

  void SetRiskWeight(const std::string& class_name, float weight);

 private:
  std::unordered_map<std::string, float> risk_weights_;
};

}  // namespace wvab

#endif  // WVAB_NAVIGATION_PLANNER_H
