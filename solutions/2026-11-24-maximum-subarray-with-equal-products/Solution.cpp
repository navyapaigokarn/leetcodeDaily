// 3411. Maximum Subarray With Equal Products
// https://leetcode.com/problems/maximum-subarray-with-equal-products/

#include <vector>
#include <algorithm>

class Solution {
private:
    long long gcd(long long a, long long b) {
        while (b != 0) {
            long long temp = b;
            b = a % b;
            a = temp;
        }
        return a;
    }

    long long lcm(long long a, long long b, long long g) {
        return (a / g) * b;
    }

public:
    int maxLength(std::vector<int>& nums) {
        int n = nums.size();
        int maxLen = 0;
        for (int i = 0; i < n; i++) {
            long long currentGcd = nums[i];
            long long currentLcm = nums[i];
            long long currentProd = nums[i];
            for (int j = i; j < n; j++) {
                if (j > i) {
                    currentGcd = gcd(currentGcd, nums[j]);
                    currentLcm = lcm(currentLcm, nums[j], gcd(currentLcm, nums[j]));
                    currentProd *= nums[j];
                }
                if (currentProd == currentLcm * currentGcd) {
                    maxLen = std::max(maxLen, j - i + 1);
                }
            }
        }
        return maxLen;
    }
};
