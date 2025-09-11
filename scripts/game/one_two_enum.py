import json

# 计算双方各一只手时的T表（轮到我方先碰）
memo = {}
def solve(a, b, turn):
    state = (a, b, turn)
    if state in memo:
        if memo[state] is None:
            return 0.5
        return memo[state]
    
    memo[state] = None
    
    if turn == 'me':
        new_a = (a + b) % 10
        if new_a == 0:
            result = 1
        else:
            next_result = solve(new_a, b, 'opponent')
            result = next_result
    else:
        new_b = (b + a) % 10
        if new_b == 0:
            result = 0
        else:
            next_result = solve(a, new_b, 'me')
            result = next_result
            
    memo[state] = result
    return result

# 构建T表（键为字符串"[a, b]"）
result_dict = {}
for a in range(1, 10):
    for b in range(1, 10):
        outcome = solve(a, b, 'me')
        result_dict[f"[{a}, {b}]"] = outcome

# 定义get_T函数：当我方手为x，对方手为y且轮到我方行动时，我方的胜率
def get_T(x, y):
    if x == 0:
        return 1
    if y == 0:
        return 0
    key = f"[{x}, {y}]"
    return result_dict[key]

# 定义get_U函数：当我方手为x，对方手为y且轮到对方行动时，我方的胜率
def get_U(x, y):
    return 1 - get_T(y, x)

# 枚举所有a,b,c（1-9），检查条件并计算结果
three_hand_results = {}
for a in range(1, 10):
    for b in range(1, 10):
        for c in range(1, 10):
            if a + b + c == 10 or a + b + c == 20:
                # 条件1或2：碰b后c消失，碰c后b消失
                left_result = get_T((a + b) % 10, b)
                right_result = get_T((a + c) % 10, c)
                three_hand_results[f"[{a}, {b}, {c}]"] = {"0": left_result, "1": right_result}
            elif (2*b + a == 10 and 2*c + a == 20) or (2*b + a == 20 and 2*c + a == 10):
                # 条件3或4：碰b后b消失，碰c后c消失
                left_result = get_T((a + b) % 10, c)
                right_result = get_T((a + c) % 10, b)
                three_hand_results[f"[{a}, {b}, {c}]"] = {"0": left_result, "1": right_result}

# 保存结果到JSON文件
with open(r'scripts\game\one_two_enum.json', 'w') as f:
    json.dump(three_hand_results, f, indent=4)

print("三只手结果已保存到 scripts/game/one_two_enum.json 文件中")