#include <iostream>
#include <vector>

#include "navigation_planner.h"

int main() {
  wvab::NavigationPlanner planner;

  std::vector<wvab::Detection> detections = {
      {"person", 0.92f, 0.52f, 0.22f},
      {"chair", 0.80f, 0.50f, 0.10f},
      {"car", 0.75f, 0.85f, 0.18f},
  };

  const auto decision = planner.Decide(detections);

  std::cout << "Instruction: " << decision.instruction << "\n";
  std::cout << "Risk left/center/right: "
            << decision.risk.left << " / "
            << decision.risk.center << " / "
            << decision.risk.right << "\n";
  return 0;
}
