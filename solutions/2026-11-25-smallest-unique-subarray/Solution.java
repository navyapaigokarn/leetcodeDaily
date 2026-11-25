// 3934. Smallest Unique Subarray
// https://leetcode.com/problems/smallest-unique-subarray/

class Solution {
    public int smallestUniqueSubarray(int[] nums) {
        int n = nums.length;
        java.util.Map<java.util.List<Integer>, Integer> count = new java.util.HashMap<>();
        for (int len = 1; len <= n; len++) {
            count.clear();
            java.util.List<Integer> sub = new java.util.ArrayList<>();
            for (int i = 0; i < len; i++) {
                sub.add(nums[i]);
            }
            count.put(new java.util.ArrayList<>(sub), count.getOrDefault(new java.util.ArrayList<>(sub), 0) + 1);
            for (int i = len; i < n; i++) {
                sub.remove(0);
                sub.add(nums[i]);
                count.put(new java.util.ArrayList<>(sub), count.getOrDefault(new java.util.ArrayList<>(sub), 0) + 1);
            }
            for (java.util.Map.Entry<java.util.List<Integer>, Integer> entry : count.entrySet()) {
                if (entry.getValue() == 1) {
                    return len;
                }
            }
        }
        return n;
    }
}
