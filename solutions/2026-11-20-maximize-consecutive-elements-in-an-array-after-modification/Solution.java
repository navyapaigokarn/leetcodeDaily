// 3041. Maximize Consecutive Elements in an Array After Modification
// https://leetcode.com/problems/maximize-consecutive-elements-in-an-array-after-modification/

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

class Solution {
    public int maxSelectedElements(int[] nums) {
        Arrays.sort(nums);
        Map<Integer, Integer> dp = new HashMap<>();
        int maxLen = 0;
        for (int x : nums) {
            dp.put(x + 1, dp.getOrDefault(x, 0) + 1);
            dp.put(x, dp.getOrDefault(x - 1, 0) + 1);
        }
        for (int val : dp.values()) {
            maxLen = Math.max(maxLen, val);
        }
        return maxLen;
    }
}
