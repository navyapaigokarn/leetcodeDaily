// 2567. Minimum Score by Changing Two Elements
// https://leetcode.com/problems/minimum-score-by-changing-two-elements/

#include <vector>
#include <algorithm>

class Solution {
public:
    int minimizeSum(std::vector<int>& nums) {
        std::sort(nums.begin(), nums.end());
        int n = nums.size();
        int ans = nums[n - 1] - nums[0];
        ans = std::min(ans, nums[n - 1] - nums[2]);
        ans = std::min(ans, nums[n - 3] - nums[0]);
        ans = std::min(ans, nums[n - 2] - nums[1]);
        return ans;
    }
};
