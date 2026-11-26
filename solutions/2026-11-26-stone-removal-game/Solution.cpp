// 3360. Stone Removal Game
// https://leetcode.com/problems/stone-removal-game/

#include <iostream>

class Solution {
public:
    bool canAliceWin(int n) {
        int stonesToRemove = 10;
        bool aliceTurn = true;
        while (n >= stonesToRemove) {
            n -= stonesToRemove;
            stonesToRemove--;
            aliceTurn = !aliceTurn;
        }
        return !aliceTurn;
    }
};
