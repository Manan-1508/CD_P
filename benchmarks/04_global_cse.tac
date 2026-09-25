// Benchmark 04: Global Common Subexpression Elimination across Basic Blocks
// Demonstrates expressions available along incoming paths and reused across blocks

x = a + b
y = c * d
if x > 50 goto L_FAST

// Block 2: Re-evaluates identical expression (a + b)
t1 = a + b
z = t1 + 10
goto L_END

L_FAST:
// Block 3: Re-evaluates identical expression (c * d)
t2 = c * d
z = t2 * 2

L_END:
result = z + y
return result
