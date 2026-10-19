// Boundary Test 2: Zero-Trip Loop (Condition fails immediately)
// Tests branch bypass where loop body never executes, returns default value 99
i = 100
n = 10
res = 99

ZERO_LOOP:
if i < n goto LOOP_BODY
goto LOOP_EXIT

LOOP_BODY:
res = 0
i = i + 1
goto ZERO_LOOP

LOOP_EXIT:
return res
