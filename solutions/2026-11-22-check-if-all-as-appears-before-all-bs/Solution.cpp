// 2124. Check if All A's Appears Before All B's
// https://leetcode.com/problems/check-if-all-as-appears-before-all-bs/

#include <string>

class Solution {
public:
    bool checkString(std::string s) {
        for (size_t i = 0; i < s.length() - 1; ++i) {
            if (s[i] == 'b' && s[i + 1] == 'a') {
                return false;
            }
        }
        return true;
    }
};
