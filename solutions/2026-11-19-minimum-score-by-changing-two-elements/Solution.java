// 2567. Minimum Score by Changing Two Elements
// https://leetcode.com/problems/minimum-score-by-changing-two-elements/

class Solution {
    public int minimizeSum(int[] nums) {
        java.util.Arrays.sort(nums);
        int n = nums.length;
        int ans = nums[n - 1] - nums[0];
        ans = Math.min(ans, nums[n - 1] - nums[2]);
        ans = Math.min(ans, nums[n - 3] - nums[0]);
        ans = Math.min(ans, nums[n - 2] - nums[1]);
        return ans;
    }
}
