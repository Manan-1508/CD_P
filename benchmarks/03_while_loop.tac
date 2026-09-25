// Benchmark 03: Iterative Loop & Control Flow Graph
// Demonstrates loop condition, back-edge, natural loop detection, and invariant calculations

i = 0
sum = 0
n = 10
base_cost = 5 * 20

LOOP_START:
if i >= n goto LOOP_END
t1 = i * 4
sum = sum + t1
i = i + 1
goto LOOP_START

LOOP_END:
total = sum + base_cost
return total
