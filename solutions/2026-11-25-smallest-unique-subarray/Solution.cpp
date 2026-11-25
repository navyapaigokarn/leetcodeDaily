// 3934. Smallest Unique Subarray
// https://leetcode.com/problems/smallest-unique-subarray/

#include <vector>
#include <map>
#include <algorithm>

class Solution {
public:
    int smallestUniqueSubarray(std::vector<int>& nums) {
        int n = nums.size();
        for (int len = 1; len <= n; ++len) {
            std::map<std::vector<int>, int> count;
            std::vector<int> sub(nums.begin(), nums.begin() + len);
            count[sub]++;
            for (int i = len; i < n; ++i) {
                sub.erase(sub.begin());
                sub.push_back(nums[i]);
                count[sub]++;
            }
            for (auto const& [key, val] : count) {
                if (val == 1) {
                    return len;
                }
            }
        }
        return n;
    }
};
