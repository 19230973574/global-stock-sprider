#!/usr/bin/env python3
import sys
print("检查longport.openapi的内容")

from longport.openapi import *

print("\n=== 所有导出的内容:")
print(dir())

print("\n=== 检查Period相关:")
if 'Period' in globals():
    print("Period:", Period)
    print("Period的值:", dir(Period))

print("\n=== 检查Candlestick相关:")
if 'Candlestick' in globals():
    print("Candlestick:", Candlestick)
