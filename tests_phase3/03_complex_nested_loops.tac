// Complex Test 3: Nested Loops (Outer: 5 iters, Inner: 4 iters -> Result = 20)
// Tests multi-header dominator trees, nested back-edges, and loop nesting
total = 0
i = 0

OUTER_LOOP:
if i >= 5 goto OUTER_END
j = 0

INNER_LOOP:
if j >= 4 goto INNER_END
total = total + 1
j = j + 1
goto INNER_LOOP

INNER_END:
i = i + 1
goto OUTER_LOOP

OUTER_END:
return total
