// Error Test 4: Duplicate Label Definition
// Tests symbol resolution detecting ambiguous duplicate label definitions
a = 15
b = 25

CHECK_POINT:
if a == b goto CHECK_POINT
a = a + 1

CHECK_POINT:
return a
