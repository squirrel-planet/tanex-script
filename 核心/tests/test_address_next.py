# 地址类型.next方法测试
# 测试address.next方法支持地址的加减运算
def test_address_next_integer(run_tsuc):
    # 测试address与整数的加法
    source = '\n    -> "standard";\n    addr = address{100};\n    new_addr = addr.next(5);\n    standard_output << (new_addr.address_string == 105);\n    '
    assert run_tsuc(source) == 'true'

def test_address_next_negative(run_tsuc):
    # 测试address与负整数的加法（减法）
    source = '\n    -> "standard";\n    addr = address{100};\n    new_addr = addr.next(-5);\n    standard_output << (new_addr.address_string == 95);\n    '
    assert run_tsuc(source) == 'true'

def test_address_next_address(run_tsuc):
    # 测试address与address的加法
    source = '\n    -> "standard";\n    addr_one = address{100};\n    addr_two = address{50};\n    new_addr = addr_one.next(addr_two);\n    standard_output << (new_addr.address_string == 150);\n    '
    assert run_tsuc(source) == 'true'

def test_address_next_number(run_tsuc):
    # 测试address与number的加法（只取整数部分）
    source = '\n    -> "standard";\n    addr = address{100};\n    num = number{\'10.7\'};\n    new_addr = addr.next(num);\n    standard_output << (new_addr.address_string == 110);\n    '
    assert run_tsuc(source) == 'true'

def test_address_next_zero(run_tsuc):
    # 测试加零
    source = '\n    -> "standard";\n    addr = address{100};\n    new_addr = addr.next(0);\n    standard_output << (new_addr.address_string == 100);\n    '
    assert run_tsuc(source) == 'true'

def test_address_next_type_error(run_tsuc):
    # 测试错误类型参数：next 只接受 address / integer / number，传 string 应报错
    source = '\n    -> "standard";\n    addr = address{100};\n    result = addr.next("invalid") | next_error : true : false;\n    standard_output << result;\n    '
    assert run_tsuc(source) == 'true'
