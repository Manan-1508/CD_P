// Error Test 2: Undefined Branch Target Label
// Tests semantic checker identifying branches jumping to non-existent labels
x = 5
y = 10
if x < y goto NON_EXISTENT_LABEL
return x
