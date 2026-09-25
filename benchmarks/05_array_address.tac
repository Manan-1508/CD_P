// Benchmark 05: Array Addressing & Redundant Offset Computation
// Simulates 1D array index translation: a[i] = b[i] + c[i] with 4-byte element offsets

i = 0
size = 100

L_CHECK:
if i >= size goto L_DONE

// Array base offset calculation for index i
offset1 = i * 4
val_b = b[offset1]

// Redundant calculation of index i * 4
offset2 = i * 4
val_c = c[offset2]

sum_val = val_b + val_c

// Third identical offset calculation for target assignment
offset3 = i * 4
a[offset3] = sum_val

i = i + 1
goto L_CHECK

L_DONE:
return 0
