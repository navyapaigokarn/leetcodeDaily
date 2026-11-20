// 3041. Maximize Consecutive Elements in an Array After Modification
// https://leetcode.com/problems/maximize-consecutive-elements-in-an-array-after-modification/

#include <vector>
#include <algorithm>
#include <unordered_map>

class Solution {
public:
    int maxSelectedElements(std::vector<int>& nums) {
        std::sort(nums.begin(), nums.end());
        std::unordered_map<int, int> dp;
        int maxLen = 0;
        for (int x : nums) {
            dp[x + 1] = dp[x] + 1;
            dp[x] = dp[x - 1] + 1;
        }
        for (auto& pair : dp) {
            maxLen = std::max(maxLen, pair.second);
        }
        return maxLen;
    }
};
