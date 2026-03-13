// # --------------------------------------------------------------------------------------------- # 
// # | Name: Md. Shahanur Islam Shagor                                                           | # 
// # | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
// # | Voronezh State University of Forestry and Technologies                                    | # 
// # | Build for Blind people within 15$                                                         | # 
// # --------------------------------------------------------------------------------------------- # 

#include "navigation_planner.h"

#include <algorithm>

namespace wvab {

NavigationPlanner::NavigationPlanner() {
  risk_weights_["person"] = 2.0f;
  risk_weights_["car"] = 3.0f;
  risk_weights_["truck"] = 3.5f;
  risk_weights_["bus"] = 3.5f;
  risk_weights_["motorcycle"] = 2.5f;
  risk_weights_["bicycle"] = 2.0f;
  risk_weights_["stairs"] = 4.0f;
  risk_weights_["chair"] = 1.5f;
  risk_weights_["bench"] = 1.5f;
  risk_weights_["potted plant"] = 1.2f;
  risk_weights_["stop sign"] = 1.0f;
  risk_weights_["traffic light"] = 1.0f;
}

void NavigationPlanner::SetRiskWeight(const std::string& class_name, float weight) {
  risk_weights_[class_name] = weight;
}

NavigationDecision NavigationPlanner::Decide(const std::vector<Detection>& detections) const {
  NavigationDecision out;

  for (const auto& det : detections) {
    const auto it = risk_weights_.find(det.class_name);
    const float base_risk = (it != risk_weights_.end()) ? it->second : 1.0f;
    const float confidence = std::clamp(det.confidence, 0.0f, 1.0f);
    const float area_norm = std::clamp(det.area_norm, 0.0f, 1.0f);
    const float distance_boost = 1.0f + std::min(area_norm * 4.0f, 2.0f);
    const float total_risk = base_risk * confidence * distance_boost;

    if (det.x_center_norm < 0.33f) {
      out.risk.left += total_risk;
    } else if (det.x_center_norm > 0.67f) {
      out.risk.right += total_risk;
    } else {
      out.risk.center += total_risk;
    }
  }

  const float left = out.risk.left;
  const float center = out.risk.center;
  const float right = out.risk.right;

  if (center >= 4.5f && left >= 4.0f && right >= 4.0f) {
    out.instruction = "STOP - obstacle very close";
    out.severity = Severity::kDanger;
    return out;
  }

  if (center >= 3.0f) {
    if (left + 0.6f < right) {
      out.instruction = "GO LEFT";
    } else if (right + 0.6f < left) {
      out.instruction = "GO RIGHT";
    } else {
      out.instruction = "SLOW - path blocked ahead";
    }
    out.severity = Severity::kWarning;
    return out;
  }

  if (left + 0.4f < right && left < 3.0f) {
    out.instruction = "GO LEFT";
  } else if (right + 0.4f < left && right < 3.0f) {
    out.instruction = "GO RIGHT";
  } else {
    out.instruction = "GO STRAIGHT";
  }
  out.severity = Severity::kSafe;
  return out;
}

}  // namespace wvab
