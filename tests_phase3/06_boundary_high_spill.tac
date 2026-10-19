// Boundary Test 3: High Register Pressure and Spill Stress Test
// Forces 8 simultaneously live variables; when K=3, forces 5 spills to stack
v1 = 1
v2 = 2
v3 = 3
v4 = 4
v5 = 5
v6 = 6
v7 = 7
v8 = 8

// All 8 variables read simultaneously at termination, forcing overlapping live ranges
s1 = v1 + v2
s2 = s1 + v3
s3 = s2 + v4
s4 = s3 + v5
s5 = s4 + v6
s6 = s5 + v7
final_sum = s6 + v8

return final_sum
