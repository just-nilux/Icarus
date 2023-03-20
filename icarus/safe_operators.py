from decimal import Decimal

def safe_divide(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) / Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )

def safe_multiply(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) * Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )

def safe_sum(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) + Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )

def safe_substract(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) - Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )
