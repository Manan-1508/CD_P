// Complex Test 1: Factorial Calculation (n = 6 -> Result = 720)
// Demonstrates loop counter, accumulator multiplication, and termination
n = 6
fact = 1
i = 1

FACT_LOOP:
if i > n goto FACT_END
fact = fact * i
i = i + 1
goto FACT_LOOP

FACT_END:
return fact
