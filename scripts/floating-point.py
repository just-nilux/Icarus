from decimal import *

a = 12.5
b = 10.2
subs = a-b
sum = a+b
mul = a*b
print(f'a - b = {subs}')
print(f'a + b = {sum}')
print(f'a x b = {mul}')


#getcontext().prec = 6
getcontext().rounding = ROUND_DOWN
print('float(Decimal() - Decimal())')
print(f'a - b = {float(Decimal(a) - Decimal(b))}')
print(f'a + b = {float(Decimal(a) + Decimal(b))}')
print(f'a x b = {float(Decimal(a) * Decimal(b))}')

print('float((Decimal() - Decimal()).quantize(Decimal(), rounding=None))}')
quant_decimal = '.0001'
print(f'a - b = {float((Decimal(a) - Decimal(b)).quantize(Decimal(quant_decimal), rounding=None))}')
print(f'a + b = {float(Decimal(a) + Decimal(b))}')
print(f'a x b = {float((Decimal(a) * Decimal(b)).quantize(Decimal(quant_decimal), rounding=None))}')


print('float(Decimal(str()) - Decimal(str()))')
print(f'a - b = {float(Decimal(str(a)) - Decimal(str(b)))}')
print(f'a + b = {float(Decimal(str(a)) + Decimal(str(b)))}')
print(f'a x b = {float(Decimal(str(a)) * Decimal(str(b)))}')

# This might be the best:
print(f'a x b = {float( (Decimal(str(a)) * Decimal(str(b))).quantize(Decimal(quant_decimal), rounding=None) )}')
#steps:
a=0.06
b=0.04
print(f'{Decimal(a) * Decimal(b)}')
print(f'{(Decimal(a) * Decimal(b)).quantize(Decimal(quant_decimal), rounding=None)}')
print(f'{float((Decimal(a) * Decimal(b)).quantize(Decimal(quant_decimal), rounding=None))}')

print(f'{Decimal(str(a)) * Decimal(str(b))}')
print(f'{(Decimal(str(a)) * Decimal(str(b))).quantize(Decimal(quant_decimal), rounding=None)}')
print(f'{float((Decimal(str(a)) * Decimal(str(b))).quantize(Decimal(quant_decimal), rounding=None))}')

print(f'{Decimal(a) - Decimal(b)}')
print(f'{(Decimal(a) - Decimal(b)).quantize(Decimal(quant_decimal), rounding=None)}')
print(f'{float((Decimal(a) - Decimal(b)).quantize(Decimal(quant_decimal), rounding=None))}')

print(f'{Decimal(str(a)) - Decimal(str(b))}')
print(f'{(Decimal(str(a)) - Decimal(str(b))).quantize(Decimal(quant_decimal), rounding=None)}')
print(f'{float((Decimal(str(a)) - Decimal(str(b))).quantize(Decimal(quant_decimal), rounding=None))}')

print(Decimal.from_float(0.1))
print(getcontext().create_decimal_from_float(0.1))


getcontext().prec = 6
print(Decimal(str(0.123456789)))
print(getcontext().create_decimal_from_float(123.123456789))
print('\nRounding:')
getcontext().prec = 8
getcontext().rounding = ROUND_DOWN
b = 10.245555555
quant_decimal = '.0001'
print(f'number = {b}')
print(f"NONE: {Decimal(b).quantize(Decimal(quant_decimal), rounding=None)}")
print(f"ROUND_DOWN {Decimal(b).quantize(Decimal(quant_decimal), rounding=ROUND_DOWN)}")
print(f"ROUND_FLOOR {Decimal(b).quantize(Decimal(quant_decimal), rounding=ROUND_FLOOR)}")
print(f"ROUND_HALF_DOWN {Decimal(b).quantize(Decimal(quant_decimal), rounding=ROUND_HALF_DOWN)}")
print(f"ROUND_HALF_EVEN {Decimal(b).quantize(Decimal(quant_decimal), rounding=ROUND_HALF_EVEN)}")
print(f"ROUND_HALF_UP {Decimal(b).quantize(Decimal(quant_decimal), rounding=ROUND_HALF_UP)}")
print(f"ROUND_05UP {Decimal(b).quantize(Decimal(quant_decimal), rounding=ROUND_05UP)}")
print(f"ROUND_UP {Decimal(b).quantize(Decimal(quant_decimal), rounding=ROUND_UP)}")


getcontext().prec = 8
getcontext().rounding = ROUND_DOWN
print(f'\nPreset to {getcontext().rounding}')
print(f"10.249999955 {Decimal(str(10.249999955)).quantize(Decimal(quant_decimal))}")
print(f"10.244554444 {Decimal(str(10.244554444)).quantize(Decimal(quant_decimal))}")
print(f"10.999999999 {Decimal(str(10.999999999)).quantize(Decimal(quant_decimal))}")

getcontext().rounding = ROUND_UP
print(f'\nPreset to {getcontext().rounding}')
print(f"10.249999955 {float(Decimal(str(10.249999955)).quantize(Decimal(quant_decimal)))}")
print(f"10.244554444 {Decimal(str(10.244554444)).quantize(Decimal(quant_decimal))}")
print(f"10.999999999 {Decimal(str(10.999999999)).quantize(Decimal(quant_decimal))}")

import math
context = Context(prec=5, rounding=ROUND_DOWN)
print(context.create_decimal_from_float(math.pi))