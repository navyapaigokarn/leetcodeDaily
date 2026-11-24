// 3411. Maximum Subarray With Equal Products
// https://leetcode.com/problems/maximum-subarray-with-equal-products/

class Solution {
    private long gcd(long a, long b) {
        while (b != 0) {
            long temp = b;
            b = a % b;
            a = temp;
        }
        return a;
    }

    private long lcm(long a, long b, long g) {
        return (a / g) * b;
    }

    public int maxLength(int[] nums) {
        int n = nums.length;
        int maxLen = 0;
        for (int i = 0; i < n; i++) {
            long currentGcd = nums[i];
            long currentLcm = nums[i];
            long currentProd = nums[i];
            for (int j = i; j < n; j++) {
                if (j > i) {
                    currentGcd = gcd(currentGcd, nums[j]);
                    currentLcm = lcm(currentLcm, nums[j], gcd(currentLcm, nums[j]));
                    currentProd *= nums[j];
                }
                if (currentProd == currentLcm * currentGcd) {
                    maxLen = Math.max(maxLen, j - i + 1);
                }
            }
        }
        return maxLen;
    }
}
