// Benchmark 02: Conditional Branching & Dead Code Elimination
// Demonstrates multi-block control flow, dead temporary elimination, and unread dead assignments

a = 20
b = 10
t1 = a + b
dead1 = 999 * 888
if a > b goto L_TRUE

// False Branch
t2 = a - b
dead2 = dead1 + 50
ans = t2 * 2
goto L_EXIT

L_TRUE:
t3 = a * 2
dead3 = 42 + 10
ans = t3 + 5

L_EXIT:
return ans
