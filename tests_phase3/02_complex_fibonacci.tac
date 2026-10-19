// Complex Test 2: Iterative Fibonacci Sequence (n = 8 -> Result = 21)
// Demonstrates dual variable recurrence, temp assignment, and loop control
n = 8
a = 0
b = 1
count = 1

FIB_LOOP:
if count >= n goto FIB_END
temp = a + b
a = b
b = temp
count = count + 1
goto FIB_LOOP

FIB_END:
return b
