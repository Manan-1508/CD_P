// Benchmark 01: Arithmetic Optimization, Algebraic Identities & DAG CSE
// Demonstrates constant folding, identity rules (x*1, x+0, x-x), and commutative CSE (a+b == b+a)

t1 = 15 * 4
t2 = a + b
t3 = b + a
t4 = t2 * 1
t5 = t3 + 0
x = t4 + t5
t6 = 100 - 100
y = x + t6
return y
